import os
import logging
from flask import Flask
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from config import Config
from app.auth.supabase_client import supabase_auth
from app.auth.models import SupabaseUser
from app.i18n import init_babel

# Inicializar Flask-Login
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

# Inicializar CSRF Protection
csrf = CSRFProtect()

@login_manager.user_loader
def load_user(user_id):
    """Cargar usuario para Flask-Login usando Supabase"""
    return SupabaseUser.get_by_id(user_id)

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Configurar logging
    if app.debug:
        logging.basicConfig(level=logging.INFO)
        app.logger.setLevel(logging.INFO)
        # También habilitar logging de werkzeug
        logging.getLogger('werkzeug').setLevel(logging.INFO)
    
    # Inicializar extensiones
    login_manager.init_app(app)
    csrf.init_app(app)
    
    # Inicializar Babel para internacionalización
    babel = init_babel(app)
    
    # Hacer que csrf_token esté disponible en todos los templates
    @app.context_processor
    def inject_csrf_token():
        from flask_wtf.csrf import generate_csrf
        return dict(csrf_token=generate_csrf)
    
    # Hacer que las funciones de internacionalización estén disponibles en templates
    @app.context_processor
    def inject_i18n():
        from app.i18n import get_current_language, get_available_languages, _, _n
        return dict(
            current_language=get_current_language(),
            available_languages=get_available_languages(),
            _=_,
            _n=_n
        )
    
    # Inicializar Supabase para autenticación
    supabase_auth.init_app(app)
    
    # Registrar blueprints
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)
    
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    return app
