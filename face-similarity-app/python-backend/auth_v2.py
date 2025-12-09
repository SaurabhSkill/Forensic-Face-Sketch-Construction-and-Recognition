"""
Enhanced Authentication Module with Role-Based Access and OTP
Supports Admin (with OTP) and Officer roles
"""

import os
import jwt
import bcrypt
import random
import string
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify
from database import get_db, User, OTP

# JWT Configuration
JWT_SECRET = os.environ.get('JWT_SECRET', 'forensic-face-recognition-secret-key-change-in-production')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24

# OTP Configuration
OTP_LENGTH = 6
OTP_EXPIRATION_MINUTES = 3

# Email Configuration for OTP
SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))
SMTP_EMAIL = os.environ.get('SMTP_EMAIL', '')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')

# Allowed email domains for officers (government only)
OFFICER_EMAIL_DOMAINS = [
    '@forensic.gov.in',
    '@police.gov.in',
    '@stateforensic.gov.in'
]


def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception as e:
        print(f"Password verification error: {e}")
        return False


def generate_token(user_id: int, email: str, role: str) -> str:
    """Generate a JWT token for a user with role"""
    payload = {
        'user_id': user_id,
        'email': email,
        'role': role,
        'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        'iat': datetime.utcnow()
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token


def decode_token(token: str) -> dict:
    """Decode and verify a JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise Exception('Token has expired')
    except jwt.InvalidTokenError:
        raise Exception('Invalid token')


def generate_otp() -> str:
    """Generate a 6-digit OTP"""
    return ''.join(random.choices(string.digits, k=OTP_LENGTH))


def generate_temp_password() -> str:
    """Generate a temporary password for new officers"""
    # Format: 2 uppercase + 4 digits + 2 special chars
    uppercase = ''.join(random.choices(string.ascii_uppercase, k=2))
    digits = ''.join(random.choices(string.digits, k=4))
    special = ''.join(random.choices('!@#$%', k=2))
    password = uppercase + digits + special
    # Shuffle to make it random
    password_list = list(password)
    random.shuffle(password_list)
    return ''.join(password_list)


def send_email(to_email: str, subject: str, body: str) -> bool:
    """Send email using SMTP"""
    try:
        if not SMTP_EMAIL or not SMTP_PASSWORD:
            print("Warning: SMTP credentials not configured. Email not sent.")
            print(f"Would send to {to_email}: {subject}")
            print(f"Body: {body}")
            return False
        
        msg = MIMEMultipart()
        msg['From'] = SMTP_EMAIL
        msg['To'] = to_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'html'))
        
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_EMAIL, SMTP_PASSWORD)
        text = msg.as_string()
        server.sendmail(SMTP_EMAIL, to_email, text)
        server.quit()
        
        print(f"Email sent successfully to {to_email}")
        return True
        
    except Exception as e:
        print(f"Email sending error: {e}")
        return False


def send_otp_email(to_email: str, otp: str) -> bool:
    """Send OTP to admin email"""
    subject = "FaceFind Forensics - Your OTP Code"
    body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2 style="color: #00cc6a;">FaceFind Forensics</h2>
            <p>Your OTP code for admin login is:</p>
            <h1 style="color: #00ff88; font-size: 36px; letter-spacing: 5px;">{otp}</h1>
            <p>This code will expire in <strong>3 minutes</strong>.</p>
            <p>If you didn't request this code, please ignore this email.</p>
            <hr style="border: 1px solid #eee; margin: 20px 0;">
            <p style="color: #666; font-size: 12px;">FaceFind Forensics - Secure Facial Recognition System</p>
        </body>
    </html>
    """
    return send_email(to_email, subject, body)


def send_temp_password_email(to_email: str, officer_name: str, temp_password: str) -> bool:
    """Send temporary password to new officer"""
    subject = "FaceFind Forensics - Your Account Credentials"
    body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2 style="color: #00cc6a;">Welcome to FaceFind Forensics</h2>
            <p>Dear {officer_name},</p>
            <p>Your forensic officer account has been created. Here are your login credentials:</p>
            <div style="background: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <p><strong>Email:</strong> {to_email}</p>
                <p><strong>Temporary Password:</strong> <span style="color: #00ff88; font-size: 18px; font-weight: bold;">{temp_password}</span></p>
            </div>
            <p><strong style="color: #ff4444;">Important:</strong> You will be required to change this password on your first login.</p>
            <p>Please keep these credentials secure and do not share them with anyone.</p>
            <hr style="border: 1px solid #eee; margin: 20px 0;">
            <p style="color: #666; font-size: 12px;">FaceFind Forensics - Secure Facial Recognition System</p>
        </body>
    </html>
    """
    return send_email(to_email, subject, body)


def validate_officer_email_domain(email: str) -> bool:
    """Check if email belongs to an allowed government domain"""
    email_lower = email.lower()
    return any(email_lower.endswith(domain) for domain in OFFICER_EMAIL_DOMAINS)


def store_otp(user_id: int, otp: str, db) -> bool:
    """Store OTP in database with expiration"""
    try:
        # Hash the OTP before storing
        otp_hash = hash_password(otp)
        
        # Calculate expiration time
        expires_at = datetime.utcnow() + timedelta(minutes=OTP_EXPIRATION_MINUTES)
        
        # Invalidate any existing OTPs for this user
        db.query(OTP).filter(OTP.user_id == user_id, OTP.is_used == 0).update({'is_used': 1})
        
        # Create new OTP record
        new_otp = OTP(
            user_id=user_id,
            otp_hash=otp_hash,
            expires_at=expires_at
        )
        
        db.add(new_otp)
        db.commit()
        
        return True
        
    except Exception as e:
        print(f"Error storing OTP: {e}")
        db.rollback()
        return False


def verify_otp(user_id: int, otp: str, db) -> bool:
    """Verify OTP for a user"""
    try:
        # Get the latest unused OTP for this user
        otp_record = db.query(OTP).filter(
            OTP.user_id == user_id,
            OTP.is_used == 0
        ).order_by(OTP.created_at.desc()).first()
        
        if not otp_record:
            return False
        
        # Check if OTP has expired
        if datetime.utcnow() > otp_record.expires_at:
            otp_record.is_used = 1  # Mark as used (expired)
            db.commit()
            return False
        
        # Verify OTP
        if verify_password(otp, otp_record.otp_hash):
            # Mark OTP as used
            otp_record.is_used = 1
            db.commit()
            return True
        
        return False
        
    except Exception as e:
        print(f"Error verifying OTP: {e}")
        return False


# ============================================================================
# MIDDLEWARE DECORATORS
# ============================================================================

def token_required(f):
    """Decorator to protect routes with JWT authentication"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Get token from Authorization header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(' ')[1]
            except IndexError:
                return jsonify({'error': 'Invalid authorization header format'}), 401
        
        if not token:
            return jsonify({'error': 'Authentication token is missing'}), 401
        
        try:
            # Decode token
            payload = decode_token(token)
            
            # Get user from database
            db = next(get_db())
            try:
                user = db.query(User).filter(User.id == payload['user_id']).first()
                if not user:
                    return jsonify({'error': 'User not found'}), 401
                
                # Add user to request context
                request.current_user = user
            finally:
                db.close()
                
        except Exception as e:
            return jsonify({'error': str(e)}), 401
        
        return f(*args, **kwargs)
    
    return decorated


def admin_only(f):
    """Decorator to restrict access to admin users only"""
    @wraps(f)
    @token_required
    def decorated(*args, **kwargs):
        user = request.current_user
        
        if user.role != 'admin':
            return jsonify({'error': 'Access denied. Admin privileges required.'}), 403
        
        return f(*args, **kwargs)
    
    return decorated


def officer_only(f):
    """Decorator to restrict access to officer users only"""
    @wraps(f)
    @token_required
    def decorated(*args, **kwargs):
        user = request.current_user
        
        if user.role != 'officer':
            return jsonify({'error': 'Access denied. Officer privileges required.'}), 403
        
        return f(*args, **kwargs)
    
    return decorated


def authenticated(f):
    """Decorator for routes accessible by any authenticated user"""
    @wraps(f)
    @token_required
    def decorated(*args, **kwargs):
        # User is already authenticated by token_required
        return f(*args, **kwargs)
    
    return decorated
