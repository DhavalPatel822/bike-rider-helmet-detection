"""Password Change with OTP Verification"""
import hashlib
import logging
from datetime import datetime
from send_otp import OTPManager
from email_service import EmailService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Simulated user database (use real database in production)
users_db = {
    'user@example.com': {
        'password_hash': hashlib.sha256('oldpassword123'.encode()).hexdigest(),
        'name': 'Test User',
        'email': 'user@example.com'
    }
}

class PasswordManager:
    def __init__(self):
        self.otp_manager = OTPManager()
        self.email_service = EmailService()
    
    def hash_password(self, password):
        """Hash password using SHA256"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def user_exists(self, email):
        """Check if user exists"""
        return email in users_db
    
    def initiate_password_change(self, email):
        """Step 1: Send OTP for password change"""
        try:
            # Check if user exists
            if not self.user_exists(email):
                logger.warning(f"Password change attempted for non-existent user: {email}")
                return False, "User not found"
            
            logger.info(f"Initiating password change for {email}")
            
            # Send OTP
            success, message = self.otp_manager.send_otp(email)
            
            if success:
                logger.info(f"✓ OTP sent successfully for password change: {email}")
            else:
                logger.error(f"✗ Failed to send OTP for password change: {email}")
            
            return success, message
            
        except Exception as e:
            error_msg = f"Error initiating password change: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def change_password(self, email, otp, new_password):
        """Step 2: Verify OTP and change password"""
        try:
            # Verify user exists
            if not self.user_exists(email):
                logger.warning(f"Password change attempted for non-existent user: {email}")
                return False, "User not found"
            
            # Verify OTP
            logger.info(f"Verifying OTP for password change: {email}")
            otp_valid, otp_message = self.otp_manager.verify_otp(email, otp)
            
            if not otp_valid:
                logger.warning(f"OTP verification failed for {email}: {otp_message}")
                return False, otp_message
            
            # Validate new password
            if not new_password or len(new_password) < 8:
                logger.warning(f"Invalid password length for {email}")
                return False, "Password must be at least 8 characters long"
            
            if new_password.lower() == 'password' or new_password == '12345678':
                logger.warning(f"Weak password attempt for {email}")
                return False, "Password is too weak. Please choose a stronger password."
            
            # Check if new password is same as old password
            current_hash = users_db[email]['password_hash']
            new_hash = self.hash_password(new_password)
            
            if current_hash == new_hash:
                logger.warning(f"New password same as old password for {email}")
                return False, "New password must be different from the current password"
            
            # Update password
            users_db[email]['password_hash'] = new_hash
            users_db[email]['password_changed_at'] = datetime.now()
            
            logger.info(f"✓ Password changed successfully for {email}")
            
            # Send confirmation email
            logger.info(f"Sending password change confirmation to {email}")
            self.email_service.send_password_change_confirmation(email)
            
            return True, "Password changed successfully! Please login with your new password."
            
        except Exception as e:
            error_msg = f"Error changing password: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def add_user(self, email, name, password):
        """Add a new user (for testing)"""
        if email in users_db:
            return False, "User already exists"
        
        users_db[email] = {
            'password_hash': self.hash_password(password),
            'name': name,
            'email': email
        }
        logger.info(f"User added: {email}")
        return True, "User added successfully"

# Example usage
if __name__ == "__main__":
    password_manager = PasswordManager()
    
    print("=== Password Change System Test ===\n")
    
    # Option to add test user
    add_user = input("Do you want to add a test user? (y/n): ").lower()
    if add_user == 'y':
        email = input("Enter email: ")
        name = input("Enter name: ")
        password = input("Enter initial password: ")
        success, message = password_manager.add_user(email, name, password)
        print(f"{message}\n")
    
    # Test password change flow
    test_email = input("Enter email for password change: ")
    
    if not password_manager.user_exists(test_email):
        print(f"Error: User {test_email} does not exist!")
    else:
        # Step 1: Request OTP
        print("\n--- Step 1: Requesting OTP ---")
        success, message = password_manager.initiate_password_change(test_email)
        print(f"Result: {message}")
        
        if success:
            # Step 2: Enter OTP and new password
            print("\n--- Step 2: Change Password ---")
            
            # Show OTP for testing (in production, user gets this via email)
            otp_info = password_manager.otp_manager.get_otp_info(test_email)
            if otp_info['exists']:
                print(f"DEBUG: OTP is {otp_info['otp']} (check your email)\n")
            
            otp_code = input("Enter OTP: ")
            new_password = input("Enter new password (min 8 characters): ")
            confirm_password = input("Confirm new password: ")
            
            if new_password != confirm_password:
                print("Error: Passwords do not match!")
            else:
                success, message = password_manager.change_password(
                    test_email, 
                    otp_code, 
                    new_password
                )
                print(f"\nResult: {message}")
                
                if success:
                    print("\n✓ Password changed successfully!")
                    print("You can now login with your new password.")