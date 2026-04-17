# # import torch
# # from ultralytics import YOLO
# # import os
# # import cv2

# # model = YOLO('best.pt')

# # source_path = "test/images"

# # output_path = "test_output"

# # results= model.predict (
# #     source=source_path,
# #     conf=0.5,
# #     project=output_path,
# #     name='Predictions Images',
# #     save=True,
# #     save_txt=True,
# #     save_conf=True,
# # )

# # print("detection completed successfully")
# # print(f"Results saved in: runs\\detect\\{output_path}\\Predictions Images\\")
# import os
# import uuid
# import cv2
# from flask import Flask, request, jsonify, send_from_directory
# from ultralytics import YOLO

# app = Flask(__name__)

# # --- Configuration ---
# UPLOAD_FOLDER = 'static/uploads'
# os.makedirs(UPLOAD_FOLDER, exist_ok=True)
# model = YOLO('best.pt')

# # Global or Session-based stats (Reset logic)
# stats = {"violations": 0, "safe": 0, "frames": 0, "fps": 0}

# def reset_stats():
#     global stats
#     stats = {"violations": 0, "safe": 0, "frames": 0, "fps": 0}

# # --- Routes ---

# @app.route("/predict", methods=["POST"])
# def predict():
#     if 'file' not in request.files:
#         return jsonify({"error": "No file uploaded"}), 400

#     reset_stats()

#     # 1. Save uploaded file
#     file = request.files["file"]
#     unique_id = str(uuid.uuid4())
#     filename = unique_id + ".jpg"
#     path = os.path.join(UPLOAD_FOLDER, filename)
#     file.save(path)

#     # 2. Run Inference
#     # Use [0] because model() returns a list of Results objects
#     results = model(path, conf=0.3)[0]
#     img = cv2.imread(path)

#     v, s = 0, 0

#     # 3. Process Detections
#     for box in results.boxes:
#         cls = int(box.cls[0])
#         conf = float(box.conf[0])
#         name = model.names[cls]

#         # Convert tensor coordinates to integers
#         x1, y1, x2, y2 = map(int, box.xyxy[0])

#         # Flexible label matching
#         if "no" in name.lower() or "without" in name.lower():
#             label = f"NO HELMET {conf:.2f}"
#             color = (0, 0, 255) # Red
#             v += 1
#         else:
#             label = f"HELMET {conf:.2f}"
#             color = (0, 255, 0) # Green
#             s += 1

#         # Draw on image
#         cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
#         cv2.putText(img, label, (x1, y1 - 10),
#                     cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

#     # 4. Update Stats
#     stats["violations"] = v
#     stats["safe"] = s
#     stats["frames"] = 1

#     # 5. Save Processed Image
#     out_name = "result_" + filename
#     out_path = os.path.join(UPLOAD_FOLDER, out_name)
#     cv2.imwrite(out_path, img)

#     # 6. Return Response
#     # Note: returning the file path or a URL
#     return jsonify({
#         "status": "success",
#         "violations": v,
#         "safe": s,
#         "image_url": f"/static/uploads/{out_name}"
#     })

# # Helper to serve the static files if needed
# @app.route('/static/uploads/<filename>')
# def serve_file(filename):
#     return send_from_directory(UPLOAD_FOLDER, filename)

# if __name__ == "__main__":
#     app.run(debug=True, port=5000)
import os
import uuid
import cv2
from flask import Flask, request, jsonify, send_from_directory
from ultralytics import YOLO

app = Flask(__name__)

UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


model = YOLO('best.pt')

@app.route("/predict", methods=["POST"])
def predict():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    unique_id = str(uuid.uuid4())
    filename = unique_id + ".jpg"
    path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(path)

    results = model(path, conf=0.20)[0] 
    img = cv2.imread(path)

    v, s = 0, 0

    
    for box in results.boxes:
        cls = int(box.cls[0])
        conf = float(box.conf[0])

        x1, y1, x2, y2 = map(int, box.xyxy[0])

        if "no" in os.name or "without" in os.name or "head" in os.name:
            label = f"NO HELMET {conf:.2f}"
            color = (0, 0, 255) 
            v += 1
        else:
            label = f"HELMET {conf:.2f}"
            color = (0, 255, 0) 
            s += 1

        
        cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
        cv2.putText(img, label, (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    out_name = "result_" + filename
    out_path = os.path.join(UPLOAD_FOLDER, out_name)
    cv2.imwrite(out_path, img)

    return jsonify({
        "status": "success",
        "violations": v,
        "safe": s,
        "image_url": f"/static/uploads/{out_name}",
        "detected_classes": [model.names[int(b.cls[0])] for b in results.boxes] 
    })

@app.route('/static/uploads/<filename>')
def serve_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
    