# Bike Helmet Detection System

## 🚀 Features

- **AI-powered helmet detection** using YOLOv8
- **User authentication** with login/logout
- **Change password** from login page (email-based)
- **Forgot password** with email reset
- **Real-time image processing**
- **Live webcam detection** with color-coded results
- **Standalone webcam script** for direct detection
- **Web-based interface** with statistics display

## 🎯 Detection Results

The system shows both categories always:
- 🟢 **Green boxes** → People **With Helmet** (Safe)
- 🔴 **Red boxes** → People **Without Helmet** (Unsafe)

## 📱 Web App Usage

### Login Credentials
- **Username:** `admin`
- **Password:** `admin123`
- **Email:** `admin@example.com`

### Features
1. **Image Upload Detection**: Upload photos to detect helmets
2. **Live Webcam Detection**: Real-time detection from webcam
3. **Results Display**: Shows both categories (with/without helmet) always
4. **Statistics**: Total count, with helmet count, without helmet count

### Access
- **URL:** `http://localhost:5000`
- **Start:** `python app.py`

## 📷 Standalone Webcam Usage

### Run Webcam Detection
```bash
python webcam_detection.py
```

### Controls
- **Start:** Script automatically starts webcam
- **Stop:** Press `q` key to quit
- **Output:** Live video with detection boxes

### Requirements
- Webcam connected
- Model file: `best.pt`

## 🛠️ Setup Instructions

### Option 1: Web Application
```bash
python app.py
# Open http://localhost:5000
```

### Option 2: Standalone Webcam
```bash
python webcam_detection.py
# Press 'q' to quit
```

### Email Configuration for Password Reset

To enable password reset via email, configure your email settings in `email_config.py`:

```python
EMAIL_CONFIG = {
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587,
    'sender_email': 'your-email@gmail.com',
    'sender_password': 'your-app-password'
}
```

### Gmail Setup
1. Enable 2-factor authentication
2. Generate App Password: https://support.google.com/accounts/answer/185833
3. Use your Gmail address and the generated App Password

### Network Access
- **Local:** http://localhost:5000
- **Network:** http://YOUR_IP_ADDRESS:5000

## 🔧 API Endpoints

- `GET /` - Main web interface
- `POST /api/login` - User authentication
- `POST /api/detect` - Image detection
- `GET /api/webcam` - Live webcam stream
- `GET /health` - System health check

## 📊 Results Format

The API returns comprehensive results:

```json
{
  "success": true,
  "statistics": {
    "total": 5,
    "with_helmet": 3,
    "without_helmet": 2,
    "summary": "Found 3 with helmet, 2 without helmet"
  },
  "detections": [...]
}
```

## 📁 Files

- `app.py` - Main Flask web application
- `webcam_detection.py` - Standalone webcam script
- `templates/index.html` - Web interface
- `best.pt` - YOLOv8 model
- `users.json` - User database
- `email_config.py` - Email configuration

## ⚠️ Default Login Credentials
- **Username**: admin
- **Password**: admin123 (may change if you use change password)
- **Email**: admin@example.com

## Usage
1. **Login** with username and password
2. **Change Password** (from login page):
   - Click "🔑 Change Password" button
   - Enter your email address
   - Enter current password
   - Set new password and confirm
   - Password updated successfully!
3. **Upload Image** for helmet detection
4. **View Results** with detection statistics
5. **Forgot Password** - get password via email
6. **Logout** when done

## API Endpoints
- `GET /` - Main application
- `POST /api/login` - User login
- `POST /api/forgot-password` - Password reset via email
- `POST /api/change-password` - Change user password
- `POST /api/detect` - Upload image for helmet detection
- `GET /results/<filename>` - Get processed image
- `GET /health` - Health check

## Usage
1. Login with credentials
2. Upload an image
3. View detection results with statistics
4. Use "Forgot Password" to reset via email
5. Change password in settings