# import cv2
# from ultralytics import YOLO

# # Load model
# model = YOLO("best.pt")   # 👈 તમારો model path
# print(model.names)

# # Open webcam
# cap = cv2.VideoCapture(0)

# if not cap.isOpened():
#     print("❌ Webcam not found")
#     exit()

# print("✅ Webcam started... Press 'q' to quit")
# print("🟢 Green boxes = With Helmet")
# print("🔴 Red boxes = Without Helmet")

# while True:
#     ret, frame = cap.read()
#     if not ret: break

#     # Run YOLO with a set confidence
#     results = model(frame, conf=0.3) 

#     for r in results:
#         for box in r.boxes:
#             name = str(name).lower().strip()

#             # no_helmet_classes = ["no_helmet", "without_helmet", "no helmet"]

#             # if name in no_helmet_classes:
#             #     label = f"NO HELMET {conf:.2f}"
#             #     color = (0, 0, 255)
   
#             # else:
#             #     label = f"HELMET {conf:.2f}"
#             #     color = (0, 255, 0)

#             # Get data
#             c = int(box.cls[0])
#             label = model.names[c] # Uses the model's actual names
#             conf = float(box.conf[0])
            
#             # Logic for colors based on the label name
#             color = (0, 255, 0) if "With Helmet" in label else (0, 0, 255)
           
#             # Coordinates
#             x1, y1, x2, y2 = map(int, box.xyxy[0])

#             # Draw
#             cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
#             cv2.putText(frame, f"{label} {conf:.2f}", (x1, y1-10), 
#                         cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

#     cv2.imshow("Detection", frame)
#     if cv2.waitKey(1) & 0xFF == ord('q'): break
# # Release
# cap.release()
# cv2.destroyAllWindows()

# print("✅ Webcam detection stopped")
import cv2
from ultralytics import YOLO

# 1. Load model
try:
    model = YOLO("best.pt") 
    print("✅ Model loaded successfully")
    # This will help us see exactly what the class names are
    print("Your Model Classes are:", model.names)
except Exception as e:
    print(f"❌ Error loading model: {e}")
    exit()

cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret: break

    # Lowered confidence (conf=0.25) to catch 'Without Helmet' detections
    results = model(frame, conf=0.25, stream=True) 

    for r in results:
        for box in r.boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            
            # Get the exact name from your 'best.pt'
            original_name = model.names[cls_id].lower()
            
            # Improved Logic: Check for 'helmet' vs 'no helmet'
            # If your model uses index 0 for helmet and 1 for no helmet, 
            # you can also use: if cls_id == 1:
            if "no" in original_name or "without" in original_name or "head" in original_name:
                label = f"NO HELMET {conf:.2f}"
                color = (0, 0, 255) # Red
            else:
                label = f"HELMET {conf:.2f}"
                color = (0, 255, 0) # Green

            x1, y1, x2, y2 = map(int, box.xyxy[0])

            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, label, (x1, y1 - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    cv2.imshow("Helmet Detection System", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()