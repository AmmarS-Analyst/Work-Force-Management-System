"""
Security decorators for the Agent Management System.
See DOCUMENTATION.txt for detailed security implementation.
"""

from functools import wraps
from flask import redirect, url_for, flash
from flask_login import current_user, logout_user

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("You must be an admin to access this page.", "warning")
            return redirect_based_on_role(current_user)
        
        if not current_user.has_role('admin'):
            flash("You must be an admin to access this page.", "warning")
            return redirect_based_on_role(current_user)
        
        return f(*args, **kwargs)
    return decorated_function

def role_required(allowed_roles):
    """
    Allows access only to users with at least one of the specified roles.
    Usage: @role_required(['admin', 'tm'])
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash("Please log in to access this page.", "warning")
                return redirect(url_for('auth.login'))

            if not any(current_user.has_role(role) for role in allowed_roles):
                flash("Access denied: you don't have permission to access this page.", "danger")
                return redirect_based_on_role(current_user)
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def permission_required(permission):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash("Please log in to access this page.", "warning")
                return redirect(url_for('auth.login'))

            if not current_user.has_permission(permission):
                flash("You don't have permission to access that page.", "danger")
                return redirect_based_on_role(current_user)

            return f(*args, **kwargs)
        return decorated_function
    return decorator

def redirect_based_on_role(user):
    """Redirect user to appropriate page based on their role with strict separation"""
    from flask import redirect, url_for
    from flask_login import logout_user
    
    if not user or not hasattr(user, 'roles'):
        flash("❌ Access denied: No valid role assigned.", "danger")
        logout_user()
        return redirect(url_for('auth.login'))
    
    user_roles = [role.name.lower() for role in user.roles]
    
    # STRICT Role-based redirection
    if any('admin' in role for role in user_roles):
        return redirect(url_for('main.index'))
    elif any('data' in role or 'entry' in role for role in user_roles):
        return redirect(url_for('main.index'))
    elif any('tm' in role or 'manager' in role for role in user_roles):
        return redirect(url_for('main.distribution'))
    elif any('tl' in role or 'leader' in role for role in user_roles):
        return redirect(url_for('main.distribution'))
    else:
        # No valid role - logout and redirect to login
        flash("❌ Access denied: No valid role assigned.", "danger")
        logout_user()
        return redirect(url_for('auth.login'))