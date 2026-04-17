"""
Email Configuration Settings
Configure your email server settings here
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Email Configuration
EMAIL_CONFIG = {
    'SMTP_SERVER': 'smtp.gmail.com',  # For Gmail (change if using other provider)
    'SMTP_PORT': 587,  # TLS port
    'SENDER_EMAIL': os.getenv('SENDER_EMAIL', 'your_email@gmail.com'),
    'SENDER_PASSWORD': os.getenv('SENDER_PASSWORD', 'your_app_password'),
    'USE_TLS': True,
    'USE_SSL': False,
    'TIMEOUT': 30,
}

# OTP Configuration
OTP_CONFIG = {
    'OTP_LENGTH': 6,
    'OTP_EXPIRY_MINUTES': 10,
    'MAX_OTP_ATTEMPTS': 3,
}

# Application Settings
APP_CONFIG = {
    'APP_NAME': 'Your Application',
    'SUPPORT_EMAIL': 'support@yourapp.com',
}

# Email Templates
EMAIL_TEMPLATES = {
    'OTP_SUBJECT': 'Your OTP Code - {app_name}',
    'OTP_BODY': '''
    <html>
        <body style="font-family: Arial, sans-serif; padding: 20px; background-color: #f4f4f4;">
            <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                <h2 style="color: #333;">Hello!</h2>
                <p style="color: #666; font-size: 16px;">Your OTP code is:</p>
                <div style="background-color: #f0f0f0; padding: 20px; text-align: center; border-radius: 5px; margin: 20px 0;">
                    <h1 style="color: #4CAF50; letter-spacing: 10px; margin: 0; font-size: 36px;">{otp_code}</h1>
                </div>
                <p style="color: #666; font-size: 14px;">This code will expire in <strong>{expiry_minutes} minutes</strong>.</p>
                <p style="color: #666; font-size: 14px;">If you didn't request this code, please ignore this email.</p>
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                <p style="color: #999; font-size: 12px; text-align: center;">
                    This is an automated email from {app_name}. Please do not reply.
                </p>
            </div>
        </body>
    </html>
    ''',
    'PASSWORD_CHANGE_SUBJECT': 'Password Changed Successfully - {app_name}',
    'PASSWORD_CHANGE_BODY': '''
    <html>
        <body style="font-family: Arial, sans-serif; padding: 20px; background-color: #f4f4f4;">
            <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                <h2 style="color: #4CAF50;">✓ Password Changed Successfully!</h2>
                <p style="color: #666; font-size: 16px;">Your password has been changed successfully.</p>
                <div style="background-color: #f9f9f9; padding: 15px; border-left: 4px solid #4CAF50; margin: 20px 0;">
                    <p style="margin: 0; color: #666;"><strong>Time:</strong> {timestamp}</p>
                </div>
                <p style="color: #d32f2f; font-size: 14px;">
                    ⚠️ If you didn't make this change, please contact support immediately.
                </p>
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                <p style="color: #999; font-size: 12px; text-align: center;">
                    Support: {support_email}<br>
                    This is an automated email from {app_name}. Please do not reply.
                </p>
            </div>
        </body>
    </html>
    '''
}
"""OTP Generation and Management"""
import random
import string
import logging
from datetime import datetime, timedelta
from email_service import EmailService
from email_config import OTP_CONFIG

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# In-memory OTP storage (use database in production)
otp_storage = {}

class OTPManager:
    def __init__(self):
        self.email_service = EmailService()
        self.otp_length = OTP_CONFIG['OTP_LENGTH']
        self.expiry_minutes = OTP_CONFIG['OTP_EXPIRY_MINUTES']
        self.max_attempts = OTP_CONFIG['MAX_OTP_ATTEMPTS']
    
    def generate_otp(self):
        """Generate random OTP"""
        otp = ''.join(random.choices(string.digits, k=self.otp_length))
        logger.info(f"OTP generated: {otp}")
        return otp
    
    def send_otp(self, email):
        """Generate and send OTP to email"""
        try:
            # Validate email
            if not email or '@' not in email:
                return False, "Invalid email address"
            
            # Generate OTP
            otp_code = self.generate_otp()
            expiry_time = datetime.now() + timedelta(minutes=self.expiry_minutes)
            
            # Store OTP
            otp_storage[email] = {
                'otp': otp_code,
                'expiry': expiry_time,
                'attempts': 0,
                'created_at': datetime.now()
            }
            
            logger.info(f"OTP stored for {email}: {otp_code} (expires at {expiry_time})")
            
            # Send email
            success, message = self.email_service.send_otp_email(
                email, 
                otp_code, 
                self.expiry_minutes
            )
            
            if success:
                logger.info(f"✓ OTP sent successfully to {email}")
                return True, f"OTP sent to {email}. Check your email inbox (and spam folder)."
            else:
                logger.error(f"✗ Failed to send OTP: {message}")
                # Remove OTP from storage if email failed
                if email in otp_storage:
                    del otp_storage[email]
                return False, f"Failed to send OTP: {message}"
                
        except Exception as e:
            error_msg = f"Error sending OTP: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def verify_otp(self, email, entered_otp):
        """Verify OTP"""
        try:
            # Check if OTP exists
            if email not in otp_storage:
                logger.warning(f"OTP not found for {email}")
                return False, "OTP not found. Please request a new OTP."
            
            otp_data = otp_storage[email]
            
            # Check if expired
            if datetime.now() > otp_data['expiry']:
                logger.warning(f"OTP expired for {email}")
                del otp_storage[email]
                return False, "OTP expired. Please request a new OTP."
            
            # Check attempts
            if otp_data['attempts'] >= self.max_attempts:
                logger.warning(f"Maximum OTP attempts exceeded for {email}")
                del otp_storage[email]
                return False, "Maximum attempts exceeded. Please request a new OTP."
            
            # Verify OTP
            if otp_data['otp'] == entered_otp:
                logger.info(f"✓ OTP verified successfully for {email}")
                del otp_storage[email]  # Remove OTP after successful verification
                return True, "OTP verified successfully"
            else:
                otp_data['attempts'] += 1
                remaining = self.max_attempts - otp_data['attempts']
                logger.warning(f"Invalid OTP attempt for {email}. {remaining} attempts remaining.")
                
                if remaining > 0:
                    return False, f"Invalid OTP. {remaining} attempt(s) remaining."
                else:
                    del otp_storage[email]
                    return False, "Maximum attempts exceeded. Please request a new OTP."
                
        except Exception as e:
            error_msg = f"Error verifying OTP: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def get_otp_info(self, email):
        """Get OTP information for debugging"""
        if email in otp_storage:
            otp_data = otp_storage[email]
            return {
                'exists': True,
                'otp': otp_data['otp'],
                'expiry': otp_data['expiry'].strftime('%Y-%m-%d %H:%M:%S'),
                'attempts': otp_data['attempts'],
                'created_at': otp_data['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            }
        return {'exists': False}

# Example usage
if __name__ == "__main__":
    otp_manager = OTPManager()
    
    print("=== OTP System Test ===\n")
    
    # Test send OTP
    test_email = input("Enter email address to test: ")
    
    print("\n1. Sending OTP...")
    success, message = otp_manager.send_otp(test_email)
    print(f"Result: {message}\n")
    
    if success:
        # Show OTP info (for testing only)
        otp_info = otp_manager.get_otp_info(test_email)
        if otp_info['exists']:
            print(f"DEBUG INFO (for testing):")
            print(f"OTP Code: {otp_info['otp']}")
            print(f"Expires: {otp_info['expiry']}\n")
        
        # Test verify OTP
        entered_otp = input("Enter the OTP you received: ")
        success, message = otp_manager.verify_otp(test_email, entered_otp)
        print(f"\n2. Verification Result: {message}")