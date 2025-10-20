import os
from datetime import timedelta

class Config:
    # ==================== CORE APPLICATION SETTINGS ====================
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev123')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL') or 'postgresql://postgres:admin@localhost/agent_management'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # ==================== FLASK-LOGIN SETTINGS ====================
    LOGIN_VIEW = 'auth.login'
    SESSION_PROTECTION = None  # Set to 'strong' for production
    
    # ==================== SESSION SETTINGS ====================
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=360)
    SESSION_COOKIE_SECURE = False  # Set to True for HTTPS in production
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # ==================== CSRF PROTECTION ====================
    WTF_CSRF_ENABLED = True
    WTF_CSRF_SECRET_KEY = SECRET_KEY
    
    # ==================== DATABASE CONNECTION POOL ====================
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 15,
        'max_overflow': 25,
        'pool_recycle': 300,
        'pool_pre_ping': True,
        'pool_timeout': 30,
    }
    
    # ==================== FILE UPLOAD SETTINGS ====================
    MAX_CONTENT_LENGTH = 200 * 1024 * 1024  # 200MB max file size
    UPLOAD_CHUNK_SIZE = 8192  # 8KB chunks for file uploads
    
    # ==================== APPLICATION PATHS ====================
    TEMPLATE_FOLDER = os.path.join(os.path.dirname(__file__), 'templates')
    STATIC_FOLDER = 'static'
    
    # ==================== DEFAULT VALUES ====================
    DEFAULT_DESIGNATION = 'Cold Caller'
    DEFAULT_ROLE = 'Full-Timer'
    
    # ==================== PRODUCTION SETTINGS ====================
    # Uncomment and modify these for production deployment
    # SESSION_COOKIE_SECURE = True
    # SESSION_PROTECTION = 'strong'
    # SECRET_KEY = os.getenv('SECRET_KEY')  # Must be set in production
