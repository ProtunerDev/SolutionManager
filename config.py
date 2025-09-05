import os
from dotenv import load_dotenv

# Determinar qué archivo .env cargar basado en FLASK_ENV
flask_env = os.environ.get('FLASK_ENV', 'development')
if flask_env == 'production':
    load_dotenv('.env.production')
else:
    load_dotenv('.env')

class Config:
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key'
    
    # App URL for redirects
    APP_URL = os.environ.get('APP_URL') or 'http://127.0.0.1:5000'
    
    # Internationalization
    LANGUAGES = {
        'en': 'English',
        'es': 'Español'
    }
    BABEL_DEFAULT_LOCALE = 'en'
    BABEL_DEFAULT_TIMEZONE = 'UTC'
    
    # Supabase
    SUPABASE_URL = os.environ.get('SUPABASE_URL')
    SUPABASE_ANON_KEY = os.environ.get('SUPABASE_ANON_KEY') 
    SUPABASE_SERVICE_ROLE_KEY = os.environ.get('SUPABASE_SERVICE_ROLE_KEY')
    
    # Database PostgreSQL local
    DB_HOST = os.environ.get('DB_HOST') or 'localhost'
    DB_NAME = os.environ.get('DB_NAME') or 'SolutionManager'
    DB_USER = os.environ.get('DB_USER') or 'postgres'
    DB_PASSWORD = os.environ.get('DB_PASSWORD') or ''
    DB_PORT = int(os.environ.get('DB_PORT') or 5432)
    
    # Storage Configuration
    STORAGE_TYPE = os.environ.get('STORAGE_TYPE') or 'local'
    
    # Local Storage (desarrollo)
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app', 'static', 'uploads')
    
    # S3 Storage (producción)
    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
    AWS_S3_BUCKET = os.environ.get('AWS_S3_BUCKET')
    AWS_S3_REGION = os.environ.get('AWS_S3_REGION') or 'us-east-1'

    @staticmethod
    def init_app(app):
        pass

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

class TestingConfig(Config):
    TESTING = True
    DB_NAME = os.getenv('TEST_DB_NAME', 'SolutionManager_test')

# Configuración por defecto
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
