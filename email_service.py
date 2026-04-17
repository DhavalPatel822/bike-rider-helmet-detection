"""Email Service with Comprehensive Error Handling"""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email_config import EMAIL_CONFIG, APP_CONFIG, EMAIL_TEMPLATES

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.smtp_server = EMAIL_CONFIG['SMTP_SERVER']
        self.smtp_port = EMAIL_CONFIG['SMTP_PORT']
        self.sender_email = EMAIL_CONFIG['SENDER_EMAIL']
        self.sender_password = EMAIL_CONFIG['SENDER_PASSWORD']
        self.use_tls = EMAIL_CONFIG.get('USE_TLS', True)
        self.timeout = EMAIL_CONFIG.get('TIMEOUT', 30)
    
    def send_email(self, recipient_email, subject, html_body):
        """Send email with comprehensive error handling"""
        try:
            # Validate inputs
            if not recipient_email:
                return False, "Recipient email is required"
            
            if not self.sender_email or self.sender_email == 'your_email@gmail.com':
                return False, "Please configure SENDER_EMAIL in .env file"
            
            if not self.sender_password or self.sender_password == 'your_app_password':
                return False, "Please configure SENDER_PASSWORD in .env file"
            
            # Create message
            message = MIMEMultipart('alternative')
            message['From'] = self.sender_email
            message['To'] = recipient_email
            message['Subject'] = subject
            
            # Attach HTML body
            html_part = MIMEText(html_body, 'html')
            message.attach(html_part)
            
            # Connect to SMTP server
            logger.info(f"Connecting to {self.smtp_server}:{self.smtp_port}")
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=self.timeout) as server:
                # Enable debug output for troubleshooting
                server.set_debuglevel(0)  # Set to 1 for verbose debugging
                
                if self.use_tls:
                    logger.info("Starting TLS encryption...")
                    server.starttls()
                
                logger.info("Authenticating...")
                server.login(self.sender_email, self.sender_password)
                
                logger.info(f"Sending email to {recipient_email}...")
                server.sendmail(self.sender_email, recipient_email, message.as_string())
                
            logger.info("✓ Email sent successfully!")
            return True, "Email sent successfully"
            
        except smtplib.SMTPAuthenticationError as e:
            error_msg = f"Authentication failed. Please check your email and password. Error: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
            
        except smtplib.SMTPConnectError as e:
            error_msg = f"Failed to connect to SMTP server. Error: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
            
        except smtplib.SMTPServerDisconnected as e:
            error_msg = f"Server disconnected. Error: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
            
        except smtplib.SMTPException as e:
            error_msg = f"SMTP error occurred. Error: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
            
        except TimeoutError as e:
            error_msg = f"Connection timed out. Error: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def send_otp_email(self, recipient_email, otp_code, expiry_minutes=10):
        """Send OTP email"""
        try:
            subject = EMAIL_TEMPLATES['OTP_SUBJECT'].format(
                app_name=APP_CONFIG['APP_NAME']
            )
            
            body = EMAIL_TEMPLATES['OTP_BODY'].format(
                otp_code=otp_code,
                expiry_minutes=expiry_minutes,
                app_name=APP_CONFIG['APP_NAME']
            )
            
            logger.info(f"Preparing to send OTP email to {recipient_email}")
            return self.send_email(recipient_email, subject, body)
            
        except Exception as e:
            error_msg = f"Error preparing OTP email: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def send_password_change_confirmation(self, recipient_email):
        """Send password change confirmation"""
        try:
            from datetime import datetime
            
            subject = EMAIL_TEMPLATES['PASSWORD_CHANGE_SUBJECT'].format(
                app_name=APP_CONFIG['APP_NAME']
            )
            
            body = EMAIL_TEMPLATES['PASSWORD_CHANGE_BODY'].format(
                timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                support_email=APP_CONFIG['SUPPORT_EMAIL'],
                app_name=APP_CONFIG['APP_NAME']
            )
            
            logger.info(f"Preparing to send password change confirmation to {recipient_email}")
            return self.send_email(recipient_email, subject, body)
            
        except Exception as e:
            error_msg = f"Error preparing password change email: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

# Test function
if __name__ == "__main__":
    email_service = EmailService()
    
    # Test email sending
    test_email = input("Enter test email address: ")
    success, message = email_service.send_otp_email(test_email, "123456", 10)
    
    print(f"\nResult: {'SUCCESS' if success else 'FAILED'}")
    print(f"Message: {message}")