from supabase import create_client, Client
from flask import current_app, session
import logging

logger = logging.getLogger(__name__)

class SupabaseAuthClient:
    """Cliente Supabase completo para Magic Links y gestión de usuarios"""
    
    def __init__(self):
        self.supabase: Client = None
        self.service_supabase: Client = None
        
    def init_app(self, app):
        """Inicializar cliente Supabase"""
        try:
            # Cliente público para magic links
            self.supabase = create_client(
                app.config['SUPABASE_URL'],
                app.config['SUPABASE_ANON_KEY']
            )
            
            # Cliente de servicio para operaciones admin
            self.service_supabase = create_client(
                app.config['SUPABASE_URL'],
                app.config['SUPABASE_SERVICE_ROLE_KEY']
            )
            
            logger.info("Supabase auth client initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing Supabase: {e}")
            raise
    
    def send_magic_link(self, email, redirect_to=None):
        """Enviar magic link por email"""
        try:
            options = {}
            if redirect_to:
                options['redirect_to'] = redirect_to
            
            response = self.supabase.auth.sign_in_with_otp({
                "email": email,
                "options": options
            })
            
            logger.info(f"Magic link sent to: {email}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending magic link to {email}: {e}")
            return False
    
    def verify_otp(self, email, token):
        """Verificar token OTP del magic link"""
        try:
            response = self.supabase.auth.verify_otp({
                "email": email,
                "token": token,
                "type": "email"
            })
            
            if response.user:
                # Guardar sesión en Flask session
                if response.session:
                    session['access_token'] = response.session.access_token
                    session['refresh_token'] = response.session.refresh_token
                    session['user_id'] = response.user.id
                
                logger.info(f"User verified successfully: {email}")
                return response.user.model_dump()
            
            return None
            
        except Exception as e:
            logger.error(f"Error verifying OTP: {e}")
            return None
    
    def get_user(self, access_token=None):
        """Obtener usuario actual usando token de acceso"""
        try:
            # Usar token proporcionado o de la sesión
            token = access_token or session.get('access_token')
            
            if not token:
                return None
            
            # Establecer el token en el cliente
            self.supabase.auth.set_session(token, session.get('refresh_token', ''))
            
            # Obtener usuario actual
            user_response = self.supabase.auth.get_user()
            
            if user_response and user_response.user:
                return user_response.user.model_dump()
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None
    
    def get_user_by_id(self, user_id):
        """Obtener usuario por ID usando service client"""
        try:
            response = self.service_supabase.auth.admin.get_user_by_id(user_id)
            
            if response and response.user:
                return response.user.model_dump()
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting user by ID {user_id}: {e}")
            return None
    
    def refresh_session(self):
        """Refrescar sesión usando refresh token"""
        try:
            refresh_token = session.get('refresh_token')
            if not refresh_token:
                return False
            
            response = self.supabase.auth.refresh_session(refresh_token)
            
            if response and response.session:
                # Actualizar tokens en sesión
                session['access_token'] = response.session.access_token
                session['refresh_token'] = response.session.refresh_token
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error refreshing session: {e}")
            return False
    
    def sign_out(self):
        """Cerrar sesión"""
        try:
            # Cerrar sesión en Supabase
            self.supabase.auth.sign_out()
            
            # Limpiar sesión Flask
            session.pop('access_token', None)
            session.pop('refresh_token', None)
            session.pop('user_id', None)
            
            logger.info("User signed out successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error signing out: {e}")
            return False
    
    def invite_user(self, email, redirect_to=None):
        """Invitar usuario usando service client"""
        try:
            options = {}
            if redirect_to:
                options['redirect_to'] = redirect_to
            
            response = self.service_supabase.auth.admin.invite_user_by_email(
                email, 
                options=options
            )
            
            if response and response.user:
                logger.info(f"User invited successfully: {email}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error inviting user {email}: {e}")
            return False
    
    def list_users(self, page=1, per_page=50):
        """Listar usuarios (admin)"""
        try:
            response = self.service_supabase.auth.admin.list_users(
                page=page,
                per_page=per_page
            )
            
            if response and response.users:
                return [user.model_dump() for user in response.users]
            
            return []
            
        except Exception as e:
            logger.error(f"Error listing users: {e}")
            return []
    
    def delete_user(self, user_id):
        """Eliminar usuario (admin)"""
        try:
            response = self.service_supabase.auth.admin.delete_user(user_id)
            logger.info(f"User deleted: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting user {user_id}: {e}")
            return False
    
    def get_session_info(self):
        """Obtener información de la sesión actual"""
        return {
            'has_access_token': bool(session.get('access_token')),
            'has_refresh_token': bool(session.get('refresh_token')),
            'user_id': session.get('user_id'),
            'session_keys': list(session.keys())
        }

# Instancia global
supabase_auth = SupabaseAuthClient()

# Para compatibilidad con imports existentes
supabase = None

def get_supabase_client():
    """Obtener cliente de Supabase (con service role para operaciones admin)"""
    global supabase
    if supabase is None:
        from flask import current_app
        supabase = create_client(
            current_app.config['SUPABASE_URL'],
            current_app.config['SUPABASE_SERVICE_ROLE_KEY']
        )
    return supabase