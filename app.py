import cv2
import threading
import numpy as np
import json
import os
import random
import smtplib
from email.mime.text import MIMEText
from flask import Flask, render_template, jsonify, request, Response
from ultralytics import YOLO
import base64
from PIL import Image

import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from detect_video import process_video

# ── Load .env FIRST so SENDER_EMAIL / SENDER_PASSWORD are set before anything uses them ──
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__, template_folder='templates')

# ═════════════════════════════════════════════════════════════════════════════
#  EMAIL — loaded from .env  (EMAIL_USER / EMAIL_PASS)
#
#  Create a file called  .env  in the same folder as app.py and add:
#
#      EMAIL_USER=your-real-gmail@gmail.com
#      EMAIL_PASS=abcdefghijklmnop          ← 16-char App Password, no spaces
#
#  Get App Password → https://myaccount.google.com/apppasswords
# ═════════════════════════════════════════════════════════════════════════════
SENDER_EMAIL    = "dhavalpatel80220@gmail.com"
SENDER_PASSWORD = "yyle hbwr wzep txdn"

# ── OTP storage ───────────────────────────────────────────────────────────────
otp_storage = {}

# ── YOLO model ────────────────────────────────────────────────────────────────
model = YOLO("best.pt")

CLASS_NAMES = {
    0: "With Helmet",
    1: "Without Helmet"
}

# ── Webcam globals ────────────────────────────────────────────────────────────
current_frame  = None
detection_data = {"with_helmet": 0, "without_helmet": 0, "detections": []}
webcam_active  = False
webcam_thread  = None

# ── Video-stream globals ──────────────────────────────────────────────────────
video_current_frame     = None
video_detection_active  = False
video_stats             = {"with_helmet": 0, "without_helmet": 0, "total": 0}
video_processing_thread = None

UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ═════════════════════════════════════════════════════════════════════════════
#  USER MANAGEMENT
# ═════════════════════════════════════════════════════════════════════════════
def load_users():
    if os.path.exists('users.json'):
        with open('users.json', 'r') as f:
            return json.load(f)
    default = {"admin": {"password": "admin", "email": ""}}
    save_users(default)
    return default

def save_users(users):
    with open('users.json', 'w') as f:
        json.dump(users, f, indent=2)

# ═════════════════════════════════════════════════════════════════════════════
#  EMAIL HELPER  — returns (success: bool, error_message: str)
# ═════════════════════════════════════════════════════════════════════════════
def send_otp_email(receiver_email, otp_code):
    """
    Send a 6-digit OTP via Gmail SMTP (port 587 / STARTTLS).
    Returns (True, "") on success or (False, "reason") on failure.
    """
    # ── quick pre-flight checks ──────────────────────────────────────────────
    if not SENDER_EMAIL or SENDER_EMAIL == "your-email@gmail.com":
        msg = "EMAIL_USER is not set in .env file. Add EMAIL_USER=your-gmail@gmail.com"
        print(f"❌ {msg}")
        return False, msg

    if not SENDER_PASSWORD or SENDER_PASSWORD in ("abcdefghijklmnop", "abcd efgh ijkl mnop", ""):
        msg = ("EMAIL_PASS is not set in .env file. "
               "Go to https://myaccount.google.com/apppasswords, "
               "generate a 16-char App Password, and add EMAIL_PASS=yourpassword to .env")
        print(f"❌ {msg}")
        return False, msg

    if len(SENDER_PASSWORD.replace(" ", "")) != 16:
        msg = (f"EMAIL_PASS looks wrong — should be exactly 16 characters "
               f"(got {len(SENDER_PASSWORD.replace(' ', ''))}). "
               f"Copy it fresh from https://myaccount.google.com/apppasswords.")
        print(f"❌ {msg}")
        return False, msg

    # ── build message ────────────────────────────────────────────────────────
    body = (
        f"Hello,\n\n"
        f"Your Helmet Detection App OTP is:\n\n"
        f"        {otp_code}\n\n"
        f"This code expires in 10 minutes.\n"
        f"If you did not request this, please ignore this email.\n\n"
        f"— Helmet Detection Team"
    )
    msg            = MIMEText(body)
    msg["Subject"] = "OTP – Helmet Detection App"
    msg["From"]    = SENDER_EMAIL
    msg["To"]      = receiver_email

    # ── send ─────────────────────────────────────────────────────────────────
    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
            print(f"✅ OTP email sent  →  {receiver_email}  (OTP = {otp_code})")
            return True, ""

    except smtplib.SMTPAuthenticationError:
        msg_err = ("Gmail rejected the login. Check: 1) EMAIL_USER/EMAIL_PASS in .env, "
                   "2) You used App Password (not normal Gmail password), "
                   "3) 2-Step Verification is enabled. "
                   "Fix: https://myaccount.google.com/apppasswords")
        print(f"❌ SMTPAuthenticationError: {msg_err}")
        return False, "Gmail authentication failed. Check .env file — EMAIL_USER and EMAIL_PASS must be correct App Password."

    except smtplib.SMTPRecipientsRefused:
        msg_err = f"Gmail refused the recipient address: {receiver_email}"
        print(f"❌ {msg_err}")
        return False, f"Invalid recipient email: {receiver_email}"

    except smtplib.SMTPException as e:
        msg_err = f"SMTP error: {e}"
        print(f"❌ {msg_err}")
        return False, msg_err

    except OSError as e:
        msg_err = (f"Network error connecting to smtp.gmail.com: {e}. "
                   "Make sure your computer has internet and port 587 is not blocked.")
        print(f"❌ {msg_err}")
        return False, msg_err

    except Exception as e:
        msg_err = f"Unexpected error: {type(e).__name__}: {e}"
        print(f"❌ {msg_err}")
        return False, msg_err


# ═════════════════════════════════════════════════════════════════════════════
#  WEBCAM THREAD
# ═════════════════════════════════════════════════════════════════════════════
def detect_helmets_thread():
    global current_frame, detection_data, webcam_active

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Webcam not found")
        webcam_active = False
        return

    print("✅ Webcam capture started...")

    while webcam_active:
        ret, frame = cap.read()
        if not ret:
            break

        frame         = cv2.resize(frame, (640, 480))
        current_frame = frame.copy()
        results       = model(frame, conf=0.3)

        with_helmet_count    = 0
        without_helmet_count = 0
        detections_list      = []

        for r in results:
            for box in r.boxes:
                cls  = int(box.cls[0])
                conf = float(box.conf[0])
                if conf < 0.3:
                    continue

                label           = CLASS_NAMES.get(cls, "Unknown")
                x1, y1, x2, y2 = map(int, box.xyxy[0])

                if cls == 0:
                    color = (0, 255, 0)
                    with_helmet_count += 1
                elif cls == 1:
                    color = (0, 0, 255)
                    without_helmet_count += 1
                else:
                    color = (255, 255, 0)

                thickness  = 3 if cls == 1 else 2
                font_scale = 0.8 if cls == 1 else 0.7
                cv2.rectangle(current_frame, (x1, y1), (x2, y2), color, thickness)
                cv2.putText(current_frame, f"{label} {conf:.2f}",
                            (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX,
                            font_scale, color, 2)

                detections_list.append({
                    "label": label,
                    "confidence": round(conf, 2),
                    "coordinates": [x1, y1, x2, y2]
                })

        detection_data = {
            "with_helmet":    with_helmet_count,
            "without_helmet": without_helmet_count,
            "detections":     detections_list
        }

    cap.release()
    print("✅ Webcam capture stopped")


# ═════════════════════════════════════════════════════════════════════════════
#  VIDEO STREAM THREAD
# ═════════════════════════════════════════════════════════════════════════════
def process_video_stream_thread(file_path):
    global video_current_frame, video_detection_active, video_stats

    cap = cv2.VideoCapture(file_path)
    if not cap.isOpened():
        print(f"❌ Cannot open video: {file_path}")
        video_detection_active = False
        return

    total_with    = 0
    total_without = 0
    print(f"✅ Video stream started: {file_path}")

    while video_detection_active:
        ret, frame = cap.read()
        if not ret:
            video_detection_active = False
            break

        frame         = cv2.resize(frame, (640, 480))
        results       = model(frame, conf=0.3)
        frame_with    = 0
        frame_without = 0

        for r in results:
            for box in r.boxes:
                cls  = int(box.cls[0])
                conf = float(box.conf[0])
                if conf < 0.3:
                    continue

                label           = CLASS_NAMES.get(cls, "Unknown")
                x1, y1, x2, y2 = map(int, box.xyxy[0])

                if cls == 0:
                    color = (0, 255, 0)
                    frame_with += 1
                elif cls == 1:
                    color = (0, 0, 255)
                    frame_without += 1
                else:
                    color = (255, 255, 0)

                thickness  = 3 if cls == 1 else 2
                font_scale = 0.8 if cls == 1 else 0.7
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)
                cv2.putText(frame, f"{label} {conf:.2f}",
                            (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX,
                            font_scale, color, 2)

        overlay = f"With Helmet: {frame_with}  |  Without Helmet: {frame_without}"
        cv2.rectangle(frame, (0, 0), (640, 35), (0, 0, 0), -1)
        cv2.putText(frame, overlay, (10, 24),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        video_current_frame = frame.copy()
        total_with    = max(total_with,    frame_with)
        total_without = max(total_without, frame_without)
        video_stats   = {
            "with_helmet":    total_with,
            "without_helmet": total_without,
            "total":          total_with + total_without
        }

    cap.release()
    print("✅ Video stream finished")


# ═════════════════════════════════════════════════════════════════════════════
#  MAIN ROUTE
# ═════════════════════════════════════════════════════════════════════════════
@app.route('/')
def index():
    return render_template('index.html')


# ═════════════════════════════════════════════════════════════════════════════
#  AUTH ROUTES  (ALL ORIGINAL — UNCHANGED)
# ═════════════════════════════════════════════════════════════════════════════
@app.route('/api/login', methods=['POST'])
def login():
    data     = request.json
    username = data.get('username')
    password = data.get('password')
    users    = load_users()
    if username in users and users[username]['password'] == password:
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Invalid credentials"})


@app.route('/api/change-password', methods=['POST'])
def change_password():
    data         = request.json
    username     = data.get('username', '')
    email        = data.get('email', '').lower().strip()
    old_password = data.get('old_password')
    new_password = data.get('new_password')
    users        = load_users()

    if email:
        for user, user_data in users.items():
            if user_data.get('email', '').lower().strip() == email \
               and user_data['password'] == old_password:
                user_data['password'] = new_password
                save_users(users)
                return jsonify({"success": True, "message": "Password changed successfully"})

    if username and username in users and users[username]['password'] == old_password:
        users[username]['password'] = new_password
        save_users(users)
        return jsonify({"success": True, "message": "Password changed successfully"})

    return jsonify({"success": False, "error": "Invalid credentials"})


# ── STEP 1: Generate OTP and email it ─────────────────────────────────────────
@app.route('/api/forgot-password', methods=['POST'])
def forgot_password():
    try:
        data  = request.get_json(force=True, silent=True)
        if not data:
            return jsonify({"success": False, "error": "Invalid request data"}), 400

        email = data.get('email', '').lower().strip()

        if not email:
            return jsonify({"success": False, "error": "Email is required"})

        otp = str(random.randint(100000, 999999))
        otp_storage[email] = otp
        print(f"🔑 OTP generated for {email} → {otp}")

        success, error_msg = send_otp_email(email, otp)

        if success:
            return jsonify({"success": True, "message": f"OTP sent to {email}. Check your inbox."})
        else:
            otp_storage.pop(email, None)
            return jsonify({"success": False, "error": error_msg})
    except Exception as e:
        return jsonify({"success": False, "error": f"Server error: {str(e)}"}), 500


# ── STEP 2: Verify OTP + update password ──────────────────────────────────────
@app.route('/api/reset-password', methods=['POST'])
def reset_password():
    try:
        data     = request.get_json(force=True, silent=True)
        if not data:
            return jsonify({"success": False, "message": "Invalid request data"}), 400

        email    = data.get("email", "").lower().strip()
        otp      = str(data.get("otp", "")).strip()
        new_pass = data.get("new_password", "")

        print(f"🔑 Reset attempt  email={email}  otp={otp}  stored={otp_storage.get(email,'NOT FOUND')}")

        if not email or not otp or not new_pass:
            return jsonify({"success": False, "message": "All fields are required."})

        if email not in otp_storage:
            return jsonify({"success": False,
                            "message": "No OTP found for this email. Please request a new one."})

        if otp_storage[email] != otp:
            return jsonify({"success": False,
                            "message": "Incorrect OTP. Please check your email and try again."})

        # ── OTP matched ───────────────────────────────────────────────────────
        otp_storage.pop(email)
        users   = load_users()
        updated = False

        for user, user_data in users.items():
            if user_data.get('email', '').lower().strip() == email:
                user_data['password'] = new_pass
                updated = True
                break

        if updated:
            save_users(users)
            return jsonify({"success": True,
                            "message": "Password reset successfully! You can now login."})
        else:
            return jsonify({
                "success": False,
                "message": (
                    "OTP was correct, but no account is linked to this email address. "
                    'Add your email to users.json like this: '
                    '{"admin": {"password": "admin", "email": "you@gmail.com"}}'
                )
            })

    except Exception as e:
        return jsonify({"success": False, "message": f"Server error: {e}"}), 500


# ── backward-compat alias ─────────────────────────────────────────────────────
@app.route('/api/verify-reset', methods=['POST'])
def verify_reset():
    return reset_password()


# ── DEBUG: Test email from browser ────────────────────────────────────────────
@app.route('/api/test-email')
def test_email():
    to = request.args.get('to', SENDER_EMAIL)
    otp = "123456"
    success, error_msg = send_otp_email(to, otp)
    if success:
        return jsonify({"success": True, "message": f"Test email sent to {to}. Check inbox."})
    else:
        return jsonify({"success": False, "error": error_msg}), 500


# ═════════════════════════════════════════════════════════════════════════════
#  ★ NEW: REGISTRATION ROUTES
# ═════════════════════════════════════════════════════════════════════════════

# STEP 1 — Send OTP to the email the user wants to register with
@app.route('/api/register/send-otp', methods=['POST'])
def register_send_otp():
    """Send a verification OTP to the new user's email."""
    try:
        data     = request.get_json(force=True, silent=True)
        if not data:
            return jsonify({"success": False, "error": "Invalid request data"}), 400

        username = data.get('username', '').strip()
        email    = data.get('email', '').lower().strip()
        password = data.get('password', '')

        # ── basic validation ──────────────────────────────────────────────────
        if not username or not email or not password:
            return jsonify({"success": False, "error": "Username, email and password are required."})

        if len(username) < 3:
            return jsonify({"success": False, "error": "Username must be at least 3 characters."})

        if len(password) < 6:
            return jsonify({"success": False, "error": "Password must be at least 6 characters."})

        users = load_users()

        # ── check duplicates ──────────────────────────────────────────────────
        if username in users:
            return jsonify({"success": False, "error": f"Username '{username}' is already taken."})

        for u, ud in users.items():
            if ud.get('email', '').lower().strip() == email:
                return jsonify({"success": False,
                                "error": f"Email '{email}' is already registered."})

        # ── generate & send OTP ───────────────────────────────────────────────
        otp = str(random.randint(100000, 999999))
        # Store pending registration keyed by email
        otp_storage[f"reg:{email}"] = {
            "otp":      otp,
            "username": username,
            "password": password
        }
        print(f"🔑 Registration OTP for {email} ({username}) → {otp}")

        success, error_msg = send_otp_email(email, otp)
        if success:
            return jsonify({"success": True,
                            "message": f"OTP sent to {email}. Check your inbox to verify."})
        else:
            otp_storage.pop(f"reg:{email}", None)
            return jsonify({"success": False, "error": error_msg})

    except Exception as e:
        return jsonify({"success": False, "error": f"Server error: {str(e)}"}), 500


# STEP 2 — Verify OTP and create the account
@app.route('/api/register/verify-otp', methods=['POST'])
def register_verify_otp():
    """Verify the registration OTP and create the new user account."""
    try:
        data  = request.get_json(force=True, silent=True)
        if not data:
            return jsonify({"success": False, "message": "Invalid request data"}), 400

        email = data.get('email', '').lower().strip()
        otp   = str(data.get('otp', '')).strip()

        if not email or not otp:
            return jsonify({"success": False, "message": "Email and OTP are required."})

        reg_key = f"reg:{email}"
        if reg_key not in otp_storage:
            return jsonify({"success": False,
                            "message": "No pending registration for this email. Please start again."})

        pending = otp_storage[reg_key]
        if pending["otp"] != otp:
            return jsonify({"success": False, "message": "Incorrect OTP. Check your email."})

        # ── OTP correct — create account ─────────────────────────────────────
        otp_storage.pop(reg_key)
        users = load_users()

        # Double-check username/email not taken (race condition guard)
        if pending["username"] in users:
            return jsonify({"success": False,
                            "message": f"Username '{pending['username']}' was just taken. Choose another."})

        users[pending["username"]] = {
            "password": pending["password"],
            "email":    email
        }
        save_users(users)
        print(f"✅ New user registered: {pending['username']} ({email})")
        return jsonify({"success": True,
                        "message": "Account created successfully! You can now log in."})

    except Exception as e:
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500


# ── legacy /send_otp alias (kept exactly as original) ─────────────────────────
@app.route('/send_otp', methods=['POST'])
def send_otp():
    email = request.json.get('email')
    # send otp logic
    return jsonify({
        "success": True,
        "message": "OTP sent successfully"
    })


# ═════════════════════════════════════════════════════════════════════════════
#  IMAGE DETECTION
# ═════════════════════════════════════════════════════════════════════════════
@app.route('/api/detect', methods=['POST'])
def detect_image():
    if 'image' not in request.files:
        return jsonify({"success": False, "error": "No image provided"}), 400
    file = request.files['image']
    if file.filename == '':
        return jsonify({"success": False, "error": "No image selected"}), 400
    try:
        img   = Image.open(file.stream)
        frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        results = model(frame, conf=0.3)

        with_helmet    = 0
        without_helmet = 0

        for r in results:
            for box in r.boxes:
                cls  = int(box.cls[0])
                conf = float(box.conf[0])
                if conf < 0.3:
                    continue
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                if cls == 0:
                    color = (0, 255, 0);  with_helmet    += 1
                elif cls == 1:
                    color = (0, 0, 255);  without_helmet += 1
                else:
                    color = (255, 255, 0)
                thickness  = 3 if cls == 1 else 2
                font_scale = 0.8 if cls == 1 else 0.7
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)
                label = CLASS_NAMES.get(cls, "Unknown")
                cv2.putText(frame, f"{label} {conf:.2f}", (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, 2)

        _, buffer = cv2.imencode('.jpg', frame)
        img_b64   = base64.b64encode(buffer).decode('utf-8')
        total     = with_helmet + without_helmet

        return jsonify({
            "success":   True,
            "image_url": f"data:image/jpeg;base64,{img_b64}",
            "statistics": {
                "total":          total,
                "with_helmet":    with_helmet,
                "without_helmet": without_helmet,
                "summary": f"🟢 {with_helmet} With Helmet | 🔴 {without_helmet} Without Helmet"
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ═════════════════════════════════════════════════════════════════════════════
#  WEBCAM ROUTES
# ═════════════════════════════════════════════════════════════════════════════
@app.route('/api/webcam/start', methods=['GET', 'POST'])
def start_webcam():
    global webcam_active, webcam_thread
    if webcam_active:
        return jsonify({"success": False, "error": "Webcam already running"})
    webcam_active = True
    webcam_thread = threading.Thread(target=detect_helmets_thread, daemon=True)
    webcam_thread.start()
    return jsonify({"success": True, "message": "Webcam started"})

@app.route('/api/webcam/stop', methods=['GET', 'POST'])
def stop_webcam():
    global webcam_active
    webcam_active = False
    return jsonify({"success": True, "message": "Webcam stopped"})

@app.route('/api/webcam')
def webcam():
    def generate_frames():
        global current_frame
        while webcam_active:
            if current_frame is not None:
                _, buffer  = cv2.imencode('.jpg', current_frame)
                frame_data = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n'
                       b'Content-Length: ' + str(len(frame_data)).encode() + b'\r\n\r\n' +
                       frame_data + b'\r\n')
    return app.response_class(generate_frames(),
                              mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/helmet-status')
def helmet_status():
    total = detection_data['with_helmet'] + detection_data['without_helmet']
    return jsonify({
        "status":         "success",
        "with_helmet":    detection_data['with_helmet'],
        "without_helmet": detection_data['without_helmet'],
        "total_detected": total,
        "webcam_active":  webcam_active
    })


# ═════════════════════════════════════════════════════════════════════════════
#  VIDEO STREAM ROUTES
# ═════════════════════════════════════════════════════════════════════════════
@app.route('/api/video-stream')
def video_stream():
    def generate():
        global video_current_frame
        while video_detection_active or video_current_frame is not None:
            if video_current_frame is not None:
                _, buffer  = cv2.imencode('.jpg', video_current_frame)
                frame_data = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n'
                       b'Content-Length: ' + str(len(frame_data)).encode() + b'\r\n\r\n' +
                       frame_data + b'\r\n')
            if not video_detection_active:
                break
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/video-stats')
def video_stats_api():
    return jsonify({"active": video_detection_active, "stats": video_stats})

@app.route('/api/detect-video', methods=['POST'])
def detect_video_api():
    global video_detection_active, video_current_frame, video_processing_thread, video_stats

    if 'video' not in request.files:
        return jsonify({"success": False, "error": "No video file provided"})

    video_detection_active = False
    if video_processing_thread and video_processing_thread.is_alive():
        video_processing_thread.join(timeout=2)

    file      = request.files['video']
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)
    print(f"✅ Video saved: {file_path}  exists={os.path.exists(file_path)}")

    video_current_frame = None
    video_stats         = {"with_helmet": 0, "without_helmet": 0, "total": 0}

    video_detection_active  = True
    video_processing_thread = threading.Thread(
        target=process_video_stream_thread, args=(file_path,), daemon=True)
    video_processing_thread.start()

    def run_saved():
        try:
            process_video(file_path)
        except Exception as e:
            print(f"process_video error: {e}")
    threading.Thread(target=run_saved, daemon=True).start()

    return jsonify({
        "success":    True,
        "stream_url": "/api/video-stream",
        "stats_url":  "/api/video-stats",
        "message":    "Video processing started"
    })


# ═════════════════════════════════════════════════════════════════════════════
#  RUN
# ═════════════════════════════════════════════════════════════════════════════
if __name__ == '__main__':
    print("=" * 60)
    print("🚀  HELMET DETECTION API  →  http://localhost:5000")
    print("=" * 60)
    print()
    print("📧  EMAIL SETUP (.env file in same folder as app.py):")
    print("  Create a file named  .env  and add these two lines:")
    print("      EMAIL_USER=your-gmail@gmail.com")
    print("      EMAIL_PASS=abcdefghijklmnop   ← 16-char App Password")
    print()
    print("  🔗 Get App Password → https://myaccount.google.com/apppasswords")
    print("  🧪 Test email       → http://localhost:5000/api/test-email?to=you@gmail.com")
    print()
    print(f"  Current EMAIL_USER = {SENDER_EMAIL}")
    print(f"  Current EMAIL_PASS = {'✅ set' if SENDER_PASSWORD not in ('abcdefghijklmnop','') else '❌ NOT SET'}")
    print()
    print("=" * 60)
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)