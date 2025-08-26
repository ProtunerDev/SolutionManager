"""
Authentication Models Module (Simplified)

This module provides user authentication models and functionality including:
- User model with Supabase email/password authentication
- Simple user session management
- NO role management (all handled by Supabase directly)
"""

from flask_login import UserMixin
from flask import current_app, session
from app.auth.supabase_client import supabase_auth
import logging
import requests

logger = logging.getLogger(__name__)

class SupabaseUser(UserMixin):
    """Usuario autenticado con Supabase usando Email/Password (Simplificado)"""
    
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
    
    def get_id(self):
        """Requerido por Flask-Login"""
        return str(self.id)
    
    def is_authenticated(self):
        """Verificar si está autenticado"""
        return True
    
    def is_active(self):
        """Verificar si está activo"""
        return True
    
    def is_anonymous(self):
        """Verificar si es anónimo"""
        return False
    
    @staticmethod
    def authenticate(email, password):
        """
        Autenticar usuario con email y password
        
        Args:
            email (str): Email del usuario
            password (str): Password del usuario
            
        Returns:
            SupabaseUser: Usuario autenticado o None si falla
        """
        try:
            logger.info(f"🔐 Attempting authentication for: {email}")
            
            # Autenticar con Supabase
            response = supabase_auth.supabase.auth.sign_in_with_password({
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
                user = SupabaseUser(user_data)
                
                logger.info(f"✅ User authenticated successfully: {email}")
                return user
            else:
                logger.warning(f"❌ Authentication failed for: {email}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Authentication error for {email}: {e}")
            return None
    
    @staticmethod
    def get_by_id(user_id):
        """
        Obtener usuario por ID
        
        Args:
            user_id (str): ID del usuario
            
        Returns:
            SupabaseUser: Usuario o None si no se encuentra
        """
        try:
            # Usar access_token de la sesión para obtener usuario
            access_token = session.get('access_token')
            if not access_token:
                return None
            
            # Obtener usuario usando el cliente de auth
            user_data = supabase_auth.get_user(access_token)
            
            if user_data and user_data.get('id') == user_id:
                return SupabaseUser(user_data)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting user by ID {user_id}: {e}")
            return None
    
    @staticmethod  
    def refresh_session():
        """
        Refrescar sesión del usuario
        
        Returns:
            bool: True si se refrescó exitosamente
        """
        try:
            return supabase_auth.refresh_session()
        except Exception as e:
            logger.error(f"Error refreshing session: {e}")
            return False
    
    def to_dict(self):
        """Convertir usuario a diccionario"""
        return {
            'id': self.id,
            'email': self.email,
            'username': self.username,
            'full_name': self.full_name,
            'created_at': self.created_at,
            'last_sign_in_at': self.last_sign_in_at
        }
    
    def __repr__(self):
        return f'<SupabaseUser {self.email}>'
