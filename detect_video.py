import cv2
from ultralytics import YOLO
import os

model = YOLO("best.pt")

def process_video(video_path):

    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        print(f"❌ Cannot open video: {video_path}")
        return None, {"total": 0, "with_helmet": 0, "without_helmet": 0}

    filename = os.path.basename(video_path)
    output_filename = f"result_{filename}"
    output_path = f"static/uploads/{output_filename}"

    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps    = cap.get(cv2.CAP_PROP_FPS) or 20.0

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    # Track MAX seen in any single frame (not cumulative)
    max_with_helmet    = 0
    max_without_helmet = 0
    max_total          = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        results = model(frame)

        # Count per frame
        frame_with    = 0
        frame_without = 0

        for r in results:
            for box in r.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                conf = float(box.conf[0])
                cls  = int(box.cls[0])

                if cls == 0:
                    color = (0, 255, 0)
                    label = "With Helmet"
                    frame_with += 1
                else:
                    color = (0, 0, 255)
                    label = "Without Helmet"
                    frame_without += 1

                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(frame, f"{label} {conf:.2f}",
                            (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.6, color, 2)

        # Update max counts
        frame_total = frame_with + frame_without
        if frame_total > max_total:
            max_total          = frame_total
            max_with_helmet    = frame_with
            max_without_helmet = frame_without

        out.write(frame)

    cap.release()
    out.release()

    statistics = {
        "total":          max_total,
        "with_helmet":    max_with_helmet,
        "without_helmet": max_without_helmet
    }

    return output_filename, statistics

    cap = cv2.VideoCapture(video_path)

    

    filename = os.path.basename(video_path)
    output_filename = f"result_{filename}"
    output_path = f"static/uploads/{output_filename}"
    if not cap.isOpened():
        print(f"❌ Cannot open video: {video_path}")
        return output_filename, {"total": 0, "with_helmet": 0, "without_helmet": 0}

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    #out = cv2.VideoWriter(output_path, fourcc, 20.0, (640, 480))

    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps    = cap.get(cv2.CAP_PROP_FPS) or 20.0
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    # Track statistics
    total = 0
    with_helmet = 0
    without_helmet = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            print("here..")
            break

        results = model(frame)

        for r in results:
            for box in r.boxes:

                x1, y1, x2, y2 = map(int, box.xyxy[0])
                conf = float(box.conf[0])
                cls = int(box.cls[0])

                if cls == 0:
                    color = (0, 255, 0)
                    label = "With Helmet"
                    with_helmet += 1
                else:
                    color = (0, 0, 255)
                    label = "Without Helmet"
                    without_helmet += 1

                total += 1

                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(frame, f"{label} {conf:.2f}",
                            (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.6, color, 2)

        out.write(frame)

    cap.release()
    out.release()

    statistics = {
        "total": total,
        "with_helmet": with_helmet,
        "without_helmet": without_helmet
    }

    # Return filename only (not full path) — Flask route builds the URL
    return output_filename, statistics