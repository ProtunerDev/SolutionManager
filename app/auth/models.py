"""
Authentication Models Module

This module provides user authentication models and functionality including:
- User model with Supabase email/password authentication
- Restricted access to pre-registered users only
- User session management
"""

from flask_login import UserMixin
from flask import current_app, session
from app.auth.supabase_client import supabase_auth
import logging
import requests

logger = logging.getLogger(__name__)

class SupabaseUser(UserMixin):
    """Usuario autenticado con Supabase usando Email/Password"""
    
    def __init__(self, user_data):
        """
        Inicializar usuario con datos de Supabase
        
        Args:
            user_data: Datos del usuario desde Supabase auth
        """
        self.id = user_data.get('id')
        self.email = user_data.get('email')
        self.user_metadata = user_data.get('user_metadata', {})
        self.app_metadata = user_data.get('app_metadata', {})
        
        # Extraer información adicional
        self.username = self.user_metadata.get('username', self.email.split('@')[0] if self.email else 'user')
        self.full_name = self.user_metadata.get('full_name', '')
        self.created_at = user_data.get('created_at')
        self.last_sign_in_at = user_data.get('last_sign_in_at')
        
        # Determinar rol
        self.role = self._determine_role()
    
    def _determine_role(self):
        """Determinar rol del usuario basado en metadata de Supabase"""
        
        # Prioridad 1: Rol explícito en app_metadata (asignado por admin)
        if self.app_metadata.get('role'):
            return self.app_metadata.get('role')
        
        # Prioridad 2: Flag de admin en user_metadata 
        if self.user_metadata.get('is_admin') == True:
            return 'admin'
        
        # Prioridad 3: Rol en claims personalizados
        if self.app_metadata.get('claims', {}).get('role'):
            return self.app_metadata.get('claims', {}).get('role')
        
        # Por defecto: usuario regular
        return 'user'
    
    @classmethod
    def authenticate(cls, email, password):
        """
        Autenticar usuario con email y password
        
        Args:
            email: Email del usuario
            password: Password del usuario
            
        Returns:
            SupabaseUser si la autenticación es exitosa, None si no
        """
        try:
            from app.auth.supabase_client import get_supabase_client
            supabase = get_supabase_client()
            
            # Autenticar con email y password
            response = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            if response.user and response.session:
                # Guardar tokens en la sesión de Flask
                session['access_token'] = response.session.access_token
                session['refresh_token'] = response.session.refresh_token
                session['user_id'] = response.user.id
                
                # Crear objeto SupabaseUser
                user_data = response.user.__dict__ if hasattr(response.user, '__dict__') else response.user
                user = cls(user_data)
                
                logger.info(f"✅ User authenticated successfully: {email}")
                return user
            else:
                logger.warning(f"❌ Authentication failed for: {email}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Authentication error for {email}: {e}")
            return None
    
    @classmethod
    def verify_access_token(cls, access_token, refresh_token=None):
        """Verificar access token de Supabase"""
        try:
            from app.auth.supabase_client import supabase
            
            # Verificar token con Supabase
            response = supabase.auth.get_user(access_token)
            
            if response.user:
                user_data = response.user.__dict__
                
                # Crear usuario local
                user = cls(user_data)
                user.access_token = access_token
                user.refresh_token = refresh_token
                
                return user
            
            return None
            
        except Exception as e:
            logger.error(f"Error verifying access token: {e}")
            return None
    
    @classmethod
    def get_by_id(cls, user_id):
        """
        Obtener usuario por ID (para Flask-Login)
        
        Args:
            user_id: ID del usuario
            
        Returns:
            SupabaseUser si existe, None si no
        """
        try:
            # Verificar si es el usuario de la sesión actual
            current_session_user_id = session.get('user_id')
            access_token = session.get('access_token')
            
            if current_session_user_id == user_id and access_token:
                return cls.verify_access_token(access_token)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting user by ID {user_id}: {e}")
            return None
    
    @classmethod
    def user_exists(cls, email):
        """
        Verificar si un usuario existe en Supabase (sin password)
        
        Args:
            email: Email a verificar
            
        Returns:
            True si existe, False si no
        """
        try:
            from app.auth.supabase_client import get_supabase_client
            supabase = get_supabase_client()
            
            # Intentar obtener usuarios y buscar por email
            try:
                # La API devuelve una lista directamente
                response = supabase.auth.admin.list_users()
                
                # Verificar el tipo de respuesta
                if hasattr(response, 'users'):
                    users = response.users
                elif isinstance(response, list):
                    users = response
                else:
                    # Podría ser un objeto con atributos
                    users = getattr(response, 'data', [])
                
                # Buscar el usuario por email
                for user in users:
                    user_email = getattr(user, 'email', None) or (user.get('email') if isinstance(user, dict) else None)
                    if user_email == email:
                        return True
                
                return False
                
            except Exception as e:
                logger.error(f"Error listing users: {e}")
                return False
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking if user exists {email}: {e}")
            return False
    
    @classmethod
    def reset_password_request(cls, email):
        """
        Solicitar reset de password
        
        Args:
            email: Email del usuario
            
        Returns:
            True si se envió el email, False si no
        """
        try:
            from app.auth.supabase_client import get_supabase_client
            supabase = get_supabase_client()
            
            # Verificar que el usuario existe primero
            if not cls.user_exists(email):
                return False
            
            # Enviar email de reset
            response = supabase.auth.reset_password_for_email(email, {
                "redirect_to": current_app.config.get('APP_URL', 'http://127.0.0.1:5000') + '/auth/supabase_callback'
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Error requesting password reset for {email}: {e}")
            return False
    
    @classmethod
    def reset_password_with_token(cls, access_token, new_password):
        """
        Resetear password usando token de Supabase
        
        Args:
            access_token: Token de acceso de Supabase
            new_password: Nueva contraseña
            
        Returns:
            True si se actualizó correctamente, False si no
        """
        try:
            from app.auth.supabase_client import get_supabase_client
            supabase = get_supabase_client()
            
            logger.info(f"Attempting to reset password with token (first 20 chars): {access_token[:20]}...")
            
            # Método correcto: Usar el endpoint de update_user directamente con el token
            # Primero necesitamos establecer temporalmente el token en el cliente
            
            # Guardar el token actual
            original_token = supabase.auth.get_session()
            
            try:
                # Establecer el token de reset temporalmente
                # Los tokens de reset vienen con un refresh_token vacío, usamos un placeholder
                response = supabase.auth.set_session(access_token, "placeholder_refresh_token")
                
                logger.info("Session set with reset token, attempting password update...")
                
                # Actualizar la contraseña
                update_response = supabase.auth.update_user({
                    "password": new_password
                })
                
                if update_response.user:
                    logger.info(f"Password reset successfully for user: {update_response.user.email}")
                    return True
                else:
                    logger.error("Failed to update password - no user in update response")
                    return False
                    
            except Exception as session_error:
                logger.warning(f"Session method failed: {session_error}")
                
                # Método alternativo: Hacer una llamada HTTP directa al endpoint de Supabase
                try:
                    import json
                    from flask import current_app
                    
                    url = f"{current_app.config['SUPABASE_URL']}/auth/v1/user"
                    headers = {
                        'Authorization': f'Bearer {access_token}',
                        'Content-Type': 'application/json',
                        'apikey': current_app.config['SUPABASE_KEY']
                    }
                    
                    data = {
                        'password': new_password
                    }
                    
                    response = requests.put(url, headers=headers, json=data)
                    
                    if response.status_code == 200:
                        user_data = response.json()
                        logger.info(f"Password reset successfully via HTTP for user: {user_data.get('email', 'unknown')}")
                        return True
                    else:
                        logger.error(f"HTTP method failed with status {response.status_code}: {response.text}")
                        return False
                        
                except Exception as http_error:
                    logger.error(f"HTTP method also failed: {http_error}")
                    return False
            
            finally:
                # Restaurar sesión original si existía
                try:
                    if original_token:
                        supabase.auth.set_session(original_token.access_token, original_token.refresh_token)
                    else:
                        supabase.auth.sign_out()
                except:
                    pass  # Ignore cleanup errors
                
        except Exception as e:
            error_str = str(e).lower()
            logger.error(f"Error resetting password with token: {e}")
            if any(keyword in error_str for keyword in ['expired', 'invalid', 'token']):
                logger.error(f"Token expired or invalid: {e}")
            else:
                logger.error(f"Other error resetting password: {e}")
            return False
    
    @classmethod
    def delete_user(cls, user_id):
        """
        Eliminar usuario de Supabase (solo admin)
        
        Args:
            user_id: ID del usuario a eliminar
            
        Returns:
            True si se eliminó correctamente, False si no
        """
        try:
            from app.auth.supabase_client import supabase
            
            # Eliminar usuario usando admin API
            response = supabase.auth.admin.delete_user(user_id)
            
            logger.info(f"✅ User deleted: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting user {user_id}: {e}")
            return False
    
    @classmethod
    def update_user_role(cls, user_id, role):
        """
        Actualizar rol de usuario en Supabase (solo admin)
        
        Args:
            user_id: ID del usuario
            role: Nuevo rol ('admin' o 'user')
            
        Returns:
            True si se actualizó correctamente, False si no
        """
        try:
            from app.auth.supabase_client import supabase
            
            # Actualizar metadata del usuario
            response = supabase.auth.admin.update_user_by_id(user_id, {
                "app_metadata": {
                    "role": role
                },
                "user_metadata": {
                    "is_admin": role == 'admin'
                }
            })
            
            if response.user:
                logger.info(f"✅ User role updated: {user_id} -> {role}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error updating user role {user_id}: {e}")
            return False
    
    @classmethod
    def list_all_users(cls):
        """
        Listar todos los usuarios con sus roles (solo admin)
        
        Returns:
            Lista de usuarios con información básica y roles
        """
        try:
            from app.auth.supabase_client import supabase
            
            # Obtener todos los usuarios usando admin API
            response = supabase.auth.admin.list_users()
            
            users_list = []
            if response.users:
                for user in response.users:
                    user_data = user.__dict__ if hasattr(user, '__dict__') else user
                    
                    # Crear objeto temporal para determinar rol
                    temp_user = cls(user_data)
                    
                    users_list.append({
                        'id': user_data.get('id'),
                        'email': user_data.get('email'),
                        'role': temp_user.role,
                        'created_at': user_data.get('created_at'),
                        'last_sign_in_at': user_data.get('last_sign_in_at'),
                        'email_confirmed_at': user_data.get('email_confirmed_at')
                    })
            
            return users_list
            
        except Exception as e:
            logger.error(f"Error listing users: {e}")
            return []
    
    @classmethod
    def get_user_by_email(cls, email):
        """
        Obtener usuario por email desde Supabase (solo admin)
        
        Args:
            email: Email del usuario
            
        Returns:
            SupabaseUser si existe, None si no
        """
        try:
            from app.auth.supabase_client import supabase
            
            # Obtener usuario por email usando admin API
            response = supabase.auth.admin.get_user_by_email(email)
            
            if response and response.user:
                user_data = response.user.__dict__ if hasattr(response.user, '__dict__') else response.user
                return cls(user_data)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting user by email {email}: {e}")
            return None
    
    def get_id(self):
        """ID del usuario para Flask-Login"""
        return str(self.id)
    
    def is_admin(self):
        """Verificar si es administrador"""
        return self.role == 'admin'
    
    def can_edit(self):
        """Verificar si puede editar"""
        return self.role in ['admin', 'user']
    
    def can_delete(self):
        """Verificar si puede eliminar"""
        return self.role == 'admin'
    
    def refresh_session(self):
        """Refrescar sesión del usuario"""
        try:
            refresh_token = session.get('refresh_token')
            if refresh_token:
                response = supabase_auth.refresh_session(refresh_token)
                if response and response.session:
                    session['access_token'] = response.session.access_token
                    session['refresh_token'] = response.session.refresh_token
                    return True
            return False
        except:
            return False
    
    def logout(self):
        """Cerrar sesión"""
        try:
            from app.auth.supabase_client import supabase
            supabase.auth.sign_out()
            session.clear()
            return True
        except:
            session.clear()
            return True
    
    def to_dict(self):
        """Convertir usuario a diccionario"""
        return {
            'id': self.id,
            'email': self.email,
            'username': self.username,
            'full_name': self.full_name,
            'role': self.role,
            'created_at': self.created_at,
            'last_sign_in_at': self.last_sign_in_at
        }

# Alias para compatibilidad
User = SupabaseUser
