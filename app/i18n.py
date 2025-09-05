"""
Internationalization Module

Handles language detection, translation, and locale management.
"""

from flask import request, session, current_app, g
from flask_babel import Babel, get_locale as babel_get_locale, gettext, ngettext
import logging

logger = logging.getLogger(__name__)

babel = Babel()

def init_babel(app):
    """Initialize Babel with the Flask app"""
    babel.init_app(app, locale_selector=get_locale)
    return babel

def get_locale():
    """
    Determine the best locale for the user based on:
    1. URL parameter (for temporary language switching)
    2. User session preference
    3. User's browser Accept-Language header
    4. Default language
    """
    
    # 1. Check URL parameter (for language switching)
    requested_language = request.args.get('lang')
    if requested_language and requested_language in current_app.config['LANGUAGES']:
        session['language'] = requested_language
        return requested_language
    
    # 2. Check user session
    if 'language' in session:
        language = session['language']
        if language in current_app.config['LANGUAGES']:
            return language
    
    # 3. Check browser Accept-Language header
    return request.accept_languages.best_match(current_app.config['LANGUAGES'].keys()) or current_app.config.get('BABEL_DEFAULT_LOCALE', 'en')

def get_current_language():
    """Get the current language code"""
    return str(babel_get_locale())

def get_available_languages():
    """Get available languages for the language selector"""
    return current_app.config['LANGUAGES']

def set_user_language(language_code):
    """Set user's preferred language in session"""
    if language_code in current_app.config['LANGUAGES']:
        session['language'] = language_code
        session.permanent = True
        logger.info(f"User language set to: {language_code}")
        return True
    return False

# Translation helpers
def _(string):
    """Translate a string"""
    return gettext(string)

def _n(singular, plural, num):
    """Translate a string with plural forms"""
    return ngettext(singular, plural, num)
