"""
Admin routes for the Agent Management System.
See DOCUMENTATION.txt for detailed route descriptions.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models import User, Role, TeamManager, TeamLeader, Agent
from app.decorators import admin_required
from app.services import UserService

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
user_service = UserService()

@admin_bp.route('/')
@login_required
@admin_required
def dashboard():
    users = User.query.options(db.joinedload(User.roles)).all()
    roles = Role.query.order_by(Role.name).all()
    team_managers = TeamManager.query.order_by(TeamManager.name).all()
    team_leaders = TeamLeader.query.order_by(TeamLeader.name).all()
    agents = Agent.query.order_by(Agent.name).all()
    
    return render_template('index.html',
                         users_admin=users,
                         roles=roles,
                         teamManagers=team_managers,
                         teamLeaders=team_leaders,
                         agents=agents,
                         current_user=current_user)

@admin_bp.route('/create-user', methods=['POST'])
@login_required
@admin_required
def create_user():
    username = request.form.get('username', '').strip().lower()
    password = request.form.get('password', 'user123')
    role_name = request.form.get('role', '').strip().lower()
    tm_id = request.form.get('tm_id', type=int) if request.form.get('tm_id') else None
    tl_id = request.form.get('tl_id', type=int) if request.form.get('tl_id') else None
    
    success, message = user_service.create_user(
        username, password, role_name, current_user, tm_id, tl_id
    )
    
    flash(message, 'success' if success else 'danger')
    return redirect(url_for('main.index'))

@admin_bp.route('/delete-user/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    success, message = user_service.delete_user(user_id, current_user)
    flash(message, 'success' if success else 'danger')
    return redirect(url_for('main.index'))

@admin_bp.route('/create-team-manager', methods=['POST'])
@login_required
@admin_required
def create_team_manager():
    name = request.form.get('name', '').strip()
    group_name = request.form.get('group_name', '').strip()

    success, message = user_service.create_team_manager(
        name=name,
        group_name=group_name,
        current_user=current_user
    )

    flash(message, 'success' if success else 'danger')
    return redirect(url_for('main.index'))


@admin_bp.route('/create-team-leader', methods=['POST'])
@login_required
@admin_required
def create_team_leader():
    name = request.form.get('name', '').strip()
    tm_id = request.form.get('tm_id', type=int)

    # ✅ Fetch TM info (name & group) from DB
    tm = TeamManager.query.get(tm_id)
    if not tm:
        flash("❌ Invalid Team Manager selected", "danger")
        return redirect(url_for('main.index'))

    # ✅ Call service with TM details
    success, message = user_service.create_team_leader(
        name=name,
        tm_id=tm_id,
        tm_name=tm.name,
        group_name=tm.group_name,
        current_user=current_user
    )

    flash(message, 'success' if success else 'danger')
    return redirect(url_for('main.index'))


@admin_bp.route('/delete-team-leader/<int:tl_id>', methods=['POST'])
@login_required
@admin_required
def delete_team_leader(tl_id):
    success, message = user_service.delete_team_leader(tl_id, current_user)
    flash(message, 'success' if success else 'danger')
    return redirect(url_for('main.index'))

@admin_bp.route('/delete-team-manager/<int:tm_id>', methods=['POST'])
@login_required
@admin_required
def delete_team_manager(tm_id):
    success, message = user_service.delete_team_manager(tm_id, current_user)
    flash(message, 'success' if success else 'danger')
    return redirect(url_for('main.index'))

@admin_bp.route('/deactivate-team-manager/<int:tm_id>', methods=['POST'])
@login_required
@admin_required
def deactivate_team_manager(tm_id):
    success, message = user_service.deactivate_team_manager(tm_id, current_user)
    flash(message, 'success' if success else 'danger')
    return redirect(url_for('main.index'))

@admin_bp.route('/replace-team-manager', methods=['POST'])
@login_required
@admin_required
def replace_team_manager():
    old_tm_id = request.form.get('old_tm_id', type=int)
    new_name = request.form.get('new_tm_name', '').strip()
    new_group_name = request.form.get('new_group_name', '').strip()
    effective_date = request.form.get('effective_date', '').strip()
    keep_old_tm = bool(request.form.get('keep_old_tm'))
    
    success, message = user_service.replace_team_manager(
        old_tm_id, new_name, new_group_name, effective_date, current_user, keep_old_tm
    )
    
    flash(message, 'success' if success else 'danger')
    return redirect(url_for('main.index'))