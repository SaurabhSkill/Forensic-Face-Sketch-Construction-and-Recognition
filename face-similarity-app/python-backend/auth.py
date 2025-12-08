"""
Authentication module for Forensic Face Recognition System
Handles user registration, login, and JWT token management
"""

import os
import jwt
import bcrypt
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify
from database import get_db, User

# JWT Configuration
JWT_SECRET = os.environ.get('JWT_SECRET', 'forensic-face-recognition-secret-key-change-in-production')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24

# Allowed email domains for registration (government/forensic/police only)
ALLOWED_EMAIL_DOMAINS = [
    '@forensic.gov.in',
    '@police.gov.in',
    '@stateforensic.gov.in'
]

# Allowed Officer IDs (verified officers who can register)
# In production, this could be fetched from a database or external service
ALLOWED_OFFICER_IDS = [
    'F12345',
    'F56789',
    'POL-9988',
    'POL-1234',
    'SF-4567',
    'F99999',
    'POL-5555',
    'F11111',
    'POL-7777'
]


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password string
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash
    
    Args:
        password: Plain text password to verify
        hashed_password: Hashed password from database
        
    Returns:
        True if password matches, False otherwise
    """
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception as e:
        print(f"Password verification error: {e}")
        return False


def generate_token(user_id: int, email: str) -> str:
    """
    Generate a JWT token for a user
    
    Args:
        user_id: User's database ID
        email: User's email address
        
    Returns:
        JWT token string
    """
    payload = {
        'user_id': user_id,
        'email': email,
        'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        'iat': datetime.utcnow()
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token


def decode_token(token: str) -> dict:
    """
    Decode and verify a JWT token
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded payload dictionary
        
    Raises:
        Exception: If token is expired or invalid
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise Exception('Token has expired')
    except jwt.InvalidTokenError:
        raise Exception('Invalid token')


def validate_email_domain(email: str) -> bool:
    """
    Check if email belongs to an allowed government domain
    
    Args:
        email: Email address to validate
        
    Returns:
        True if email domain is allowed, False otherwise
    """
    email_lower = email.lower()
    return any(email_lower.endswith(domain) for domain in ALLOWED_EMAIL_DOMAINS)


def validate_officer_id(officer_id: str) -> bool:
    """
    Check if officer ID is in the allowed list
    
    Args:
        officer_id: Officer ID to validate
        
    Returns:
        True if officer ID is allowed, False otherwise
    """
    return officer_id in ALLOWED_OFFICER_IDS


def token_required(f):
    """
    Decorator to protect routes with JWT authentication
    
    Usage:
        @app.route('/api/protected')
        @token_required
        def protected_route():
            user = request.current_user
            return jsonify({'message': f'Hello {user.full_name}'})
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Get token from Authorization header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                # Expected format: "Bearer <token>"
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
