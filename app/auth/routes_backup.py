"""
Authentication Routes Module

This module provides routes for user authentication including:
- Email/password login
- Password reset
- User logout  
- Admin user invitations
"""

import logging
from flask import render_template, url_for, flash, redirect, request, session, jsonify
from flask_login import login_user, current_user, logout_user, login_required
from flask_wtf.csrf import generate_csrf
from app.auth import bp
from app.auth.forms import LoginForm, ForgotPasswordForm, ResetPasswordForm, InviteUserForm
from app.auth.models import SupabaseUser
from app.auth.supabase_client import supabase_auth

# Configurar logger
logger = logging.getLogger(__name__)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    """Ruta de login con email y password"""
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        
        # Autenticar usuario
        user = SupabaseUser.authenticate(email, password)
        
        if user:
            # Login exitoso
            login_user(user, remember=form.remember_me.data)
            flash(f'Welcome back, {user.username}!', 'success')
            
            # Redirigir a página solicitada o dashboard
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('main.home'))
        else:
            flash('Invalid email or password. Please check your credentials.', 'danger')
    
    return render_template('auth/login.html', title='Sign In', form=form)

@bp.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    """Solicitar reset de password"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        email = form.email.data
        
        if SupabaseUser.reset_password_request(email):
            flash(f'Password reset instructions sent to {email}', 'info')
            return redirect(url_for('auth.login'))
        else:
            flash('Email not found. Please contact administrator.', 'danger')
    
    return render_template('auth/forgot_password.html', title='Reset Password', form=form)

@bp.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    """Resetear password (desde email)"""
    # Obtener token desde URL fragment o query params
    access_token = request.args.get('access_token')
    token_type = request.args.get('token_type')
    expires_at = request.args.get('expires_at')
    
    if not access_token:
        flash('Invalid or missing reset token.', 'danger')
        return redirect(url_for('auth.login'))
    
    # Validar que sea un token de recuperación válido
    if token_type != 'bearer':
        flash('Invalid token type.', 'danger')
        return redirect(url_for('auth.login'))
    
    # Verificar si el token ya expiró basado en expires_at
    if expires_at:
        try:
            import time
            expires_timestamp = int(expires_at)
            current_timestamp = int(time.time())
            
            logger.info(f"Token validation - Current: {current_timestamp}, Expires: {expires_timestamp}, Diff: {expires_timestamp - current_timestamp} seconds")
            
            if current_timestamp >= expires_timestamp:
                logger.warning(f"Token expired - Current time: {current_timestamp}, Expires at: {expires_timestamp}")
                flash('The reset link has expired. Please request a new password reset.', 'warning')
                return redirect(url_for('auth.forgot_password'))
            else:
                logger.info(f"Token is valid - Expires in {expires_timestamp - current_timestamp} seconds")
        except (ValueError, TypeError) as e:
            # Si no se puede parsear expires_at, continuar con la validación normal
            logger.warning(f"Could not parse expires_at '{expires_at}': {e}")
            pass
    
    form = ResetPasswordForm()
    if form.validate_on_submit():
        if form.password.data != form.password2.data:
            flash('Passwords must match.', 'danger')
        else:
            # Resetear password usando el token de Supabase
            success = SupabaseUser.reset_password_with_token(access_token, form.password.data)
            
            if success:
                flash('Password updated successfully. Please login with your new password.', 'success')
                return redirect(url_for('auth.login'))
            else:
                flash('The reset link has expired. Please request a new password reset.', 'warning')
                return redirect(url_for('auth.forgot_password'))
    
    return render_template('auth/reset_password.html', title='Reset Password', form=form, token=access_token)

@bp.route('/supabase_callback')
def supabase_callback():
    """Manejar callback de Supabase para reset password"""
    # Esta ruta maneja el callback inicial de Supabase
    # Los parámetros vienen en el fragment (#) de la URL
    # JavaScript se encargará de procesarlos y redirigir a reset_password
    
    return render_template('auth/supabase_callback.html')

@bp.route('/expired_link')
def expired_link():
    """Manejar enlaces expirados de Supabase"""
    flash('The reset link has expired. Please request a new password reset.', 'warning')
    return redirect(url_for('auth.forgot_password'))

@bp.route('/logout')
@login_required
def logout():
    """Cerrar sesión"""
    if hasattr(current_user, 'logout'):
        current_user.logout()
    
    logout_user()
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))

@bp.route('/invite_user', methods=['GET', 'POST'])
@login_required
def invite_user():
    # Solo admin puede invitar usuarios
    if not current_user.is_admin:
        flash('No tienes permisos para invitar usuarios.', 'error')
        return redirect(url_for('main.index'))
    
    form = InviteUserForm()
    
    if form.validate_on_submit():
        from app.auth.supabase_client import get_supabase_client
        supabase = get_supabase_client()
        
        try:
            # Determinar rol (admin por defecto si es el primer usuario)
            user_role = form.role.data if hasattr(form, 'role') and form.role.data else 'user'
            
            logger.info(f"Attempting to create user: {form.email.data} with role: {user_role}")
            
            # Verificar si el usuario ya existe
            try:
                existing_user = supabase.auth.admin.get_user_by_email(form.email.data)
                if existing_user and existing_user.user:
                    flash(f'El usuario {form.email.data} ya existe.', 'warning')
                    return render_template('auth/invite_user.html', form=form)
            except Exception as check_error:
                logger.info(f"User check completed (not found or error): {check_error}")
            
            # Crear usuario en Supabase con metadata
            create_user_data = {
                "email": form.email.data,
                "password": form.password.data,
                "email_confirm": True,
                "app_metadata": {
                    "role": user_role
                },
                "user_metadata": {
                    "is_admin": user_role == 'admin',
                    "invited_by": current_user.email,
                    "created_via": "admin_panel"
                }
            }
            
            logger.info(f"Creating user with data: {create_user_data}")
            response = supabase.auth.admin.create_user(create_user_data)
            
            if response.user:
                flash(f'Usuario {form.email.data} creado exitosamente con rol {user_role}.', 'success')
                logger.info(f"User created successfully: {form.email.data} with role {user_role}, user_id: {response.user.id}")
                return redirect(url_for('auth.manage_users'))
            else:
                error_msg = "No se pudo crear el usuario. Respuesta vacía de Supabase."
                flash(error_msg, 'error')
                logger.error(f"Create user failed: {error_msg}")
                
        except Exception as e:
            error_details = str(e)
            logger.error(f"Error creating user {form.email.data}: {error_details}")
            
            # Determinar el tipo de error para dar mejor feedback
            if "not allowed" in error_details.lower():
                flash(f'Error: El dominio de email {form.email.data} no está permitido en la configuración de Supabase. Contacta al administrador del sistema.', 'error')
            elif "already exists" in error_details.lower():
                flash(f'El usuario {form.email.data} ya existe.', 'warning')
            elif "invalid email" in error_details.lower():
                flash(f'El email {form.email.data} no es válido.', 'error')
            elif "password" in error_details.lower():
                flash(f'Error con la contraseña. Debe tener al menos 6 caracteres.', 'error')
            else:
                flash(f'Error al crear el usuario: {error_details}', 'error')
    
    return render_template('auth/invite_user.html', form=form)

@bp.route('/manage_users')
@login_required
def manage_users():
    """Gestión de usuarios (solo admin)"""
    if not current_user.is_admin:
        flash('No tienes permisos para gestionar usuarios.', 'error')
        return redirect(url_for('main.index'))
    
    users = SupabaseUser.list_all_users()
    return render_template('auth/manage_users.html', users=users)

@bp.route('/change_role', methods=['POST'])
@login_required
def change_role():
    """Cambiar rol de usuario (solo admin)"""
    if not current_user.is_admin:
        return {'success': False, 'message': 'No tienes permisos para cambiar roles.'}, 403
    
    try:
        from flask import jsonify
        data = request.get_json()
        user_id = data.get('user_id')
        new_role = data.get('role')
        
        if not user_id or not new_role:
            return jsonify({'success': False, 'message': 'Datos incompletos.'})
        
        if new_role not in ['admin', 'user']:
            return jsonify({'success': False, 'message': 'Rol inválido.'})
        
        success = SupabaseUser.update_user_role(user_id, new_role)
        
        if success:
            return jsonify({'success': True, 'message': f'Rol actualizado a {new_role}.'})
        else:
            return jsonify({'success': False, 'message': 'Error al actualizar rol.'})
            
    except Exception as e:
        logger.error(f"Error changing role: {e}")
        return jsonify({'success': False, 'message': 'Error interno del servidor.'})
    
    return jsonify({'success': False, 'message': 'Error desconocido.'})

@bp.route('/delete_user', methods=['POST'])
@login_required
def delete_user():
    """Eliminar usuario (solo admin)"""
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'No tienes permisos para eliminar usuarios.'}), 403
    
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'success': False, 'message': 'ID de usuario requerido.'})
        
        # No permitir que el admin se elimine a sí mismo
        if user_id == current_user.id:
            return jsonify({'success': False, 'message': 'No puedes eliminarte a ti mismo.'})
        
        success = SupabaseUser.delete_user(user_id)
        
        if success:
            return jsonify({'success': True, 'message': 'Usuario eliminado correctamente.'})
        else:
            return jsonify({'success': False, 'message': 'Error al eliminar usuario.'})
            
    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        return jsonify({'success': False, 'message': 'Error interno del servidor.'})
    
    return jsonify({'success': False, 'message': 'Error desconocido.'})