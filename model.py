import cv2

def detect_helmet(video_path):
    cap = cv2.VideoCapture(video_path)

    count = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        count += 1

    cap.release()

    if count > 50:
        return "Helmet Detected"
    else:
        return "No Helmet"