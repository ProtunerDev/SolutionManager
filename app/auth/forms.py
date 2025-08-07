"""
Authentication Forms Module

This module provides form classes for user authentication including:
- Email/password login form
- Password reset form  
- User invitation form (admin)
"""

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, SelectField
from wtforms.validators import DataRequired, Email, Length, EqualTo

class LoginForm(FlaskForm):
    """Formulario de login con email y password"""
    email = StringField('Email', validators=[
        DataRequired(),
        Email(message='Please enter a valid email address.')
    ])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=6, message='Password must be at least 6 characters long.')
    ])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class ForgotPasswordForm(FlaskForm):
    """Formulario para solicitar reset de password"""
    email = StringField('Email', validators=[
        DataRequired(),
        Email(message='Please enter a valid email address.')
    ])
    submit = SubmitField('Reset Password')

class ResetPasswordForm(FlaskForm):
    """Formulario para resetear password"""
    password = PasswordField('New Password', validators=[
        DataRequired(),
        Length(min=6, message='Password must be at least 6 characters long.')
    ])
    password2 = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match.')
    ])
    submit = SubmitField('Update Password')

class InviteUserForm(FlaskForm):
    """Formulario para invitar usuarios (admin only)"""
    email = StringField('Email', validators=[
        DataRequired(),
        Email(message='Please enter a valid email address.')
    ])
    password = PasswordField('Temporary Password', validators=[
        DataRequired(),
        Length(min=6, message='Password must be at least 6 characters long.')
    ])
    role = SelectField('Role', choices=[
        ('user', 'User'),
        ('admin', 'Administrator')
    ], default='user', validators=[DataRequired()])
    submit = SubmitField('Create User')

# ❌ ELIMINAR: Ya no necesitamos estas clases
# - MagicLinkForm 
# - VerifyTokenForm
