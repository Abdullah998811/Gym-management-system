import os
from datetime import timedelta
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
# Only load local .env file in development environment
if os.getenv('APP_ENV', 'development').strip().lower() == 'development':
    load_dotenv(os.path.join(basedir, '.env'))

KNOWN_INSECURE_SECRETS = {
    'dev-secret-key-fallback-only-for-local-use-gms-2026',
    'change-this-in-production-use-a-strong-random-key',
    'replace-with-a-secure-secret-key-in-production',
    'dev-secret-key-gms-super-secure-key-2026',
    'secret',
    'secret_key',
    'default'
}

class Config:
    APP_ENV = os.getenv('APP_ENV', 'development').strip().lower()
    ENV = APP_ENV
    
    # DEBUG must be False in production and may be True only in development
    flask_debug = os.getenv('FLASK_DEBUG', '0').strip().lower() in ('1', 'true')
    DEBUG = (flask_debug and APP_ENV == 'development')

    secret = os.getenv('SECRET_KEY')
    if APP_ENV == 'production':
        if not secret or not secret.strip() or secret.strip() in KNOWN_INSECURE_SECRETS:
            raise RuntimeError(
                "CRITICAL ERROR: SECRET_KEY must be set to a strong random value in production environment! "
                "Generate one with: python -c 'import secrets; print(secrets.token_hex(32))'"
            )
    else:
        if not secret or not secret.strip():
            secret = 'dev-secret-key-fallback-only-for-local-use-gms-2026'
    SECRET_KEY = secret

    # Database configuration
    db_url = os.getenv('DATABASE_URL')
    if db_url:
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        SQLALCHEMY_DATABASE_URI = db_url
    else:
        instance_dir = os.path.join(basedir, 'instance')
        os.makedirs(instance_dir, exist_ok=True)
        SQLALCHEMY_DATABASE_URI = "sqlite:///gym_management.db"

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    } if not SQLALCHEMY_DATABASE_URI.startswith("sqlite") else {}

    # Session & Security Settings - Read session lifetime in minutes from ONE place
    try:
        session_mins = int(os.getenv('SESSION_LIFETIME_MINUTES', os.getenv('PERMANENT_SESSION_LIFETIME', '30')))
    except (ValueError, TypeError):
        session_mins = 30
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=session_mins)

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = (APP_ENV == 'production') or (os.getenv('SESSION_COOKIE_SECURE', 'False').lower() in ('true', '1'))
    
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600

    # File uploads
    UPLOAD_FOLDER = os.path.join(basedir, 'instance', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max limit
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}

class TestConfig(Config):
    APP_ENV = 'testing'
    ENV = 'testing'
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SESSION_COOKIE_SECURE = False
    DEBUG = False
    SECRET_KEY = 'test-secret-key'
