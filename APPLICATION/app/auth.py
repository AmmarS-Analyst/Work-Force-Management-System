"""
Authentication routes for the Agent Management System.
See DOCUMENTATION.txt for detailed route descriptions.
"""

from os import name
from flask import Blueprint, request, flash, redirect, url_for, render_template
from flask_login import login_user, logout_user, login_required, current_user
from app.models import User

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # If already logged in, send to dashboard immediately (no loading)
    if current_user.is_authenticated:
        return redirect(get_dashboard_url(current_user))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        remember = bool(request.form.get('remember'))

        user = User.validate(username, password)   # adjust to your model method
        if user:
            if not user.is_active:
                flash("❌ Account inactive. Contact admin.", 'danger')
                return render_template('login.html')

            # successful login
            login_user(user, remember=remember)
            flash(f"✅ Welcome, {user.username}!", "success")

            # render loading.html and pass target_url
            target_url = get_dashboard_url(user)
            return render_template('loading.html', target_url=target_url, username=user.username)
        else:
            flash('❌ Invalid username or password.', 'danger')

    return render_template('login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('✅ Logged out successfully.', 'success')
    return redirect(url_for('auth.login'))


def get_dashboard_url(user):
    """Return URL for user’s dashboard based on roles (use your real endpoints)"""
    user_roles = [role.name.lower() for role in user.roles]

    if any('admin' in role for role in user_roles):
        return url_for('main.index')
    if any('data' in role or 'entry' in role for role in user_roles):
        return url_for('main.index')
    if any('tm' in role or 'manager' in role for role in user_roles):
        return url_for('main.distribution')
    if any('tl' in role or 'leader' in role for role in user_roles):
        return url_for('main.distribution')

    # no valid role
    flash("❌ No valid role assigned. Contact administrator.", "danger")
    logout_user()
    return url_for('auth.login')