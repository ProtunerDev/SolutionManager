"""
Authentication Routes Module (Simplified)

This module provides routes for user authentication including:
- Email/password login
- Password reset
- User logout  
- NO user management (handled by Supabase directly)
"""

import logging
from flask import render_template, url_for, flash, redirect, request, session, jsonify
from flask_login import login_user, current_user, logout_user, login_required
from flask_wtf.csrf import generate_csrf
from app.auth import bp
from app.auth.forms import LoginForm, ForgotPasswordForm, ResetPasswordForm
from app.auth.models import SupabaseUser
from app.auth.supabase_client import supabase_auth
from app.extensions import limiter

# Configurar logger
logger = logging.getLogger(__name__)

@bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
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
@limiter.limit("3 per hour")
def forgot_password():
    """Envía enlace de reset de password"""
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        email = form.email.data
        
        # Intentar enviar reset
        success = supabase_auth.send_password_reset(email)
        
        if success:
            flash(f'Password reset instructions have been sent to {email}', 'info')
            return redirect(url_for('auth.login'))
        else:
            flash('Error sending password reset email. Please try again.', 'danger')
    
    return render_template('auth/forgot_password.html', title='Reset Password', form=form)

@bp.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    """Reset de password usando token"""
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    
    # Obtener token de la URL
    token = request.args.get('token')
    if not token:
        flash('Invalid or missing reset token.', 'danger')
        return redirect(url_for('auth.forgot_password'))
    
    form = ResetPasswordForm()
    if form.validate_on_submit():
        new_password = form.password.data
        
        # Intentar resetear password
        success = supabase_auth.reset_password(token, new_password)
        
        if success:
            flash('Your password has been updated. You can now sign in.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('Error updating password. The token may be invalid or expired.', 'danger')
    
    return render_template('auth/reset_password.html', title='Reset Password', form=form)

@bp.route('/logout')
@login_required
def logout():
    """Cerrar sesión"""
    # Limpiar archivos temporales en S3 si el usuario abandona el flujo
    temp_solution_id = session.get('temp_solution_id')
    if temp_solution_id:
        try:
            from app.utils.storage_factory import get_file_storage
            get_file_storage().delete_temp_files(temp_solution_id)
            logger.info(f"Cleaned up temp files on logout: {temp_solution_id}")
        except Exception as e:
            logger.warning(f"Could not clean temp files on logout: {e}")

    supabase_auth.sign_out()
    logout_user()
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))

@bp.route('/csrf_token')
def csrf_token():
    """Endpoint para obtener token CSRF para AJAX"""
    return jsonify({'csrf_token': generate_csrf()})

@bp.route('/profile')
@login_required
def profile():
    """Página de perfil del usuario"""
    return render_template('auth/profile.html', title='My Profile', user=current_user)
