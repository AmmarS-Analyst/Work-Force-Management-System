"""
Main application routes for the Agent Management System.
See DOCUMENTATION.txt for detailed route descriptions.
"""

#Working Routes

from datetime import datetime, timedelta
import time
from flask import (
    Blueprint, render_template, request, redirect, url_for,
    flash, jsonify, current_app
)
from flask_login import login_required, current_user, logout_user
from werkzeug.utils import secure_filename
from sqlalchemy import func
from flask import abort
from app import db
from app.models import (
    RawCallLog, UpdatedCallLog, DeleteRequest, User, Role,
    TeamManager, TeamLeader, Agent, AgentAssignmentRequest,
    ActivityLog, DistributionRequest
)
from app.decorators import role_required

# Import services
from app.services.distribution_service import DistributionService
from app.services.file_service import FileService
from app.services.log_service import LogService

main = Blueprint('main', __name__)

# Service instances
distribution_service = DistributionService()
file_service = FileService()
log_service = LogService()

# ==================== DISTRIBUTION ROUTES ==================== #

from flask import request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
# from app.main import main
from app.services.distribution_service import DistributionService
from app.decorators import role_required

distribution_service = DistributionService()


@main.route('/distribution', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'tm', 'tl'])
def distribution():
    """Distribution page - Admin/TM direct updates or TL requests"""
    try:
        if request.method == 'POST':
            if current_user.has_role('tl'):
                return _handle_tl_distribution_request()
            else:
                return _handle_admin_tm_distribution_update()

        # GET request → render page
        return distribution_service.get_distribution_page(current_user)

    except Exception as e:
        flash(f"❌ Distribution error: {str(e)}", 'error')
        return redirect(url_for('main.index'))


# ==================== DISTRIBUTION HELPERS ==================== #

def _handle_tl_distribution_request():
    """Process TL distribution requests (swap TL etc.)"""
    agent = request.form.get('agent', '').strip()
    date = request.form.get('date', '').strip()
    swap_tl = request.form.get('swap_tl', '').strip()
    reason = request.form.get('reason', '').strip()

    success, message = distribution_service.handle_tl_request(
        agent=agent,
        date=date,
        swap_tl=swap_tl,
        reason=reason,
        current_user=current_user
    )

    flash(message, 'success' if success else 'error')
    return redirect(url_for('main.distribution'))


def _handle_admin_tm_distribution_update():
    """Process Admin/Team Manager distribution updates"""
    agent = request.form.get('agent', '').strip()
    date = request.form.get('date', '').strip()
    designation = request.form.get('designation', '').strip()
    role = request.form.get('role', '').strip()

    # ✅ Normalize empty inputs → "Unassigned"
    group_name = request.form.get('group_name', '').strip()
    tm_name = request.form.get('tm_name', '').strip()
    tl_name = request.form.get('tl_name', '').strip()

    group_name = group_name if group_name else "Unassigned"
    tm_name = tm_name if tm_name else "Unassigned"
    tl_name = tl_name if tl_name else None  # TL can be None

    success, message, _ = distribution_service.update_agent_designation(
        agent=agent,
        date=date,
        designation=designation,
        role=role,
        group_name=group_name,
        tm_name=tm_name,
        tl_name=tl_name,
        current_user=current_user
    )

    flash(message, 'success' if success else 'error')
    return redirect(url_for('main.distribution'))


@main.route('/distribution/request/<int:request_id>/<action>', methods=['POST'])
@login_required
@role_required(['admin', 'tm'])
def handle_distribution_request(request_id, action):
    """Route distribution request approval/denial"""
    if not current_user.has_role('tm'):
        flash("❌ Unauthorized", "error")
        return redirect(url_for('main.distribution'))
    
    success, message = distribution_service.handle_request_decision(
        request_id, action, current_user
    )
    flash(message, 'success' if success else 'error')
    return redirect(url_for('main.distribution'))


# @main.route('/api/get_tl_agents/<tl_name>')
# @login_required
# @role_required(['admin', 'tm', 'tl'])
# def get_tl_agents(tl_name):
#     """API endpoint for TL agents"""
#     agents = distribution_service.get_tl_agents(tl_name)
#     return jsonify(agents)


@main.route('/assign_tl', methods=['POST'])
@login_required
@role_required(['admin', 'tm'])
def assign_tl():
    """Route direct TL assignment"""
    agent = request.form.get('agent', '').strip()
    tl_id = request.form.get('tl_id', type=int)
    date = request.form.get('effective_date', '').strip()
    
    success, message = distribution_service.assign_tl_directly(
        agent, tl_id, date, current_user
    )
    flash(message, 'success' if success else 'error')
    return redirect(url_for('main.distribution'))


@main.route('/tl/request-assignment', methods=['POST'])
@login_required
@role_required(['admin', 'tl'])
def tl_request_assignment():
    """Route TL assignment requests"""
    agent = request.form.get('agent_name', '').strip()
    action = request.form.get('action', '').strip()
    date = request.form.get('effective_date', '').strip()
    reason = request.form.get('reason', '').strip()
    swap_tl = request.form.get('swap_with_tl', '').strip()
    swap_agent = request.form.get('swap_with_agent', '').strip()
    
    success, message = distribution_service.create_tl_assignment_request(
        agent, action, date, reason, swap_tl, swap_agent, current_user
    )
    flash(message, 'success' if success else 'error')
    return redirect(url_for('main.distribution'))


@main.route('/tm/request-assignment', methods=['POST'])
@login_required
@role_required(['admin', 'tm'])
def tm_request_assignment():
    """Route TM assignment requests"""
    agent = request.form.get('agent_name', '').strip()
    action = request.form.get('action', '').strip()
    date = request.form.get('effective_date', '').strip()
    reason = request.form.get('reason', '').strip()
    replace_tl = request.form.get('replace_with_tl', '').strip()
    request_tl = request.form.get('requesting_tl', '').strip()
    
    success, message = distribution_service.handle_tm_assignment(
        agent, action, date, reason, replace_tl, request_tl, current_user
    )
    flash(message, 'success' if success else 'error')
    return redirect(url_for('main.distribution'))


@main.route('/api/search-agent', methods=['GET'])
@login_required
@role_required(['admin', 'tm', 'tl'])
def search_agent():
    """API: 
    - Default: latest + previous + updated dates list
    - With date: that date's record(s)
    """
    agent_name = request.args.get('name', '').strip()
    selected_date = request.args.get('date', '').strip()

    if not agent_name:
        return jsonify({"mode": "error", "records": [], "dates": []})

    results = distribution_service.search_agent_records(agent_name, selected_date)
    return jsonify(results)


# ==================== FILE/UPLOAD ROUTES ==================== #

@main.route('/', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'data_entry'])
def index():
    """Main dashboard with file management"""
    try:
        if request.method == 'POST':
            action = request.form.get('action')

            # Check for file upload first (before checking action)
            if request.files:
                return _handle_file_upload()
            elif action == 'create_delete_request':
                return _handle_delete_request()
            elif action == 'view_dates' and request.form.get('filename'):
                return _handle_view_dates()
            elif action == 'delete_all':
                return _handle_delete_all()
            elif action == 'delete_dates':
                return _handle_delete_dates()
            elif 'agent' in request.form:
                return _handle_agent_update()
        
        # GET request - prepare index data
        context = file_service.prepare_index_context(current_user)
        return render_template('index.html', **context)
        
    except Exception as e:
        flash(f"❌ Error: {str(e)}", 'error')
        # Return a simple error page instead of redirecting to avoid infinite loop
        return f"<h1>Error</h1><p>{str(e)}</p><p><a href='/'>Go back to main page</a></p>"

def _handle_delete_request():
    """Handle delete request creation"""
    filename = request.form.get('filename')
    delete_option = request.form.get('delete_option', 'entire')
    reason = request.form.get('reason', '').strip()
    selected_dates = request.form.getlist('selected_dates')
    
    success, message = file_service.create_delete_request(
        filename, delete_option, reason, selected_dates, current_user
    )
    flash(message, 'success' if success else 'error')
    return redirect(url_for('main.index'))

def _handle_view_dates():
    """Handle date viewing request"""
    selected_file = request.form.get('filename')
    dates = file_service.get_raw_dates(selected_file) if selected_file else []
    
    context = file_service.prepare_index_context(current_user)
    context.update({'selected_file': selected_file, 'dates': dates})
    return render_template('index.html', **context)

def _handle_delete_all():
    """Handle bulk deletion"""
    selected_file = request.form.get('filename')
    success, message = file_service.delete_all_data(selected_file, current_user)
    flash(message, 'success' if success else 'error')
    return redirect(url_for('main.index'))

def _handle_delete_dates():
    """Handle date-based deletion"""
    selected_file = request.form.get('filename')
    selected_dates = request.form.getlist('selected_dates')
    reason = request.form.get('reason', '').strip()
    
    success, message = file_service.delete_dates_data(
        selected_file, selected_dates, reason, current_user
    )
    flash(message, 'success' if success else 'error')
    return redirect(url_for('main.index'))

from flask import request, redirect, url_for, flash
from flask_login import current_user
from app.updater import update_agent_data  # import your updater

def _handle_agent_update():
    """Handle agent designation, role, group and TM updates"""

    agent = request.form.get('agent', '').strip()
    date = request.form.get('date', '')
    designation = request.form.get('designation', '').strip()
    role = request.form.get('role', '').strip()
    group_name = request.form.get('group_name', '').strip() or None
    tm_name = request.form.get('tm_name', '').strip() or None  # ✅ if available in form

    # ✅ Pass current user's username to ActivityLog
    username = getattr(current_user, "username", "System")

    success = update_agent_data(
        agent_name=agent,
        designation=designation,
        role=role,
        from_date=date,
        group_name=group_name,
        tm_name=tm_name,
        updated_by=username  # 👈 Important addition
    )

    if success:
        msg = f"✅ {agent} updated successfully!"
        if group_name:
            msg += f" (Group: {group_name})"
        if tm_name and designation.lower() != "team manager":
            msg += f" (TM: {tm_name})"
        flash(msg, "success")
    else:
        flash(f"❌ No records found for {agent}.", "error")

    return redirect(url_for("main.index"))


def _handle_file_upload():
    """Handle file upload from main index page"""
    # Try different possible file field names
    file = request.files.get('file') or request.files.get('upload_file') or request.files.get('csv_file')
    
    if not file or file.filename == '':
        flash('❌ No file selected.', 'error')
        return redirect(url_for('main.index'))
    
    success, result = file_service.handle_file_upload(file, current_user)
    
    if success:
        flash(result.get('message', '✅ File uploaded successfully.'), 'success')
    else:
        flash(result.get('message', '❌ File upload failed.'), 'error')
    
    return redirect(url_for('main.index'))

@main.route('/upload', methods=['POST'])
@login_required
@role_required(['admin', 'data_entry'])
def upload():
    """File upload endpoint"""
    file = request.files.get('file')
    if not file or file.filename == '':
        flash('❌ No file selected.', 'error')
        return redirect(url_for('main.index'))
    
    success, result = file_service.handle_file_upload(file, current_user)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': success,
            'message': result.get('message', 'File processed successfully' if success else 'File processing failed')
        })
    
    flash(result['message'], 'success' if success else 'error')
    return redirect(url_for('main.index'))

@main.route('/upload/progress/<ingestion_id>')
@login_required
def upload_progress(ingestion_id):
    """Endpoint to get real-time ingestion progress"""
    progress_data = {
        'current_step': 'Processing data',
        'progress': 50,
        'message': 'Inserting records into database...',
        'rows_processed': 22500,
        'total_rows': 45000
    }
    return jsonify(progress_data)

# ==================== OTHER ROUTES ==================== #

@main.route('/delete-user/<int:user_id>', methods=['POST'])
@login_required
@role_required(['admin'])
def delete_user(user_id):
    """Delete user endpoint"""
    user = User.query.get(user_id)
    if not user:
        flash('User not found', 'danger')
        return redirect(url_for('main.index'))
    
    if user.id == current_user.id:
        flash('You cannot delete yourself', 'danger')
        return redirect(url_for('main.index'))

    try:
        db.session.delete(user)
        db.session.commit()
        flash(f'User {user.username} deleted', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting user: {str(e)}', 'danger')
    
    return redirect(url_for('main.index'))

@main.route('/get_dates', methods=['POST'])
@login_required
def get_dates():
    """AJAX endpoint to get dates for a filename"""
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify(success=False, message='Invalid request'), 400
    
    filename = request.form.get('filename')
    if not filename:
        return jsonify(success=False, message='No filename provided'), 400
    
    try:
        dates = file_service.get_raw_dates(filename)
        return jsonify(success=True, dates=dates)
    except Exception as e:
        return jsonify(success=False, message=f'Error retrieving dates: {str(e)}'), 500

@main.route('/approve_delete/<int:req_id>', methods=['POST'])
@login_required
@role_required(['admin'])
def approve_delete(req_id):
    """Approve deletion request"""
    req = DeleteRequest.query.get_or_404(req_id)
    
    try:
        if req.date_range:
            dates = req.date_range.split(',')
            for date_str in dates:
                # REPLACED: pd.to_datetime with datetime.strptime
                date_start = datetime.strptime(date_str, "%Y-%m-%d")
                # REPLACED: pd.Timedelta with timedelta
                date_end = date_start + timedelta(days=1)

                db.session.query(RawCallLog).filter(
                    RawCallLog.source_file == req.filename,
                    RawCallLog.log_time >= date_start,
                    RawCallLog.log_time < date_end
                ).delete(synchronize_session=False)

                db.session.query(UpdatedCallLog).filter(
                    UpdatedCallLog.source_file == req.filename,
                    UpdatedCallLog.log_time >= date_start,
                    UpdatedCallLog.log_time < date_end
                ).delete(synchronize_session=False)
        else:
            db.session.query(RawCallLog).filter(RawCallLog.source_file == req.filename).delete(synchronize_session=False)
            db.session.query(UpdatedCallLog).filter(UpdatedCallLog.source_file == req.filename).delete(synchronize_session=False)

        req.status = 'approved'
        req.processed_by = current_user.username
        req.processed_at = datetime.utcnow()
        db.session.commit()
        return jsonify({'success': True, 'message': 'Deletion approved and executed'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error approving deletion: {str(e)}'}), 500

@main.route('/deny_delete/<int:req_id>', methods=['POST'])
@login_required
@role_required(['admin'])
def deny_delete(req_id):
    """Deny deletion request"""
    req = DeleteRequest.query.get_or_404(req_id)
    try:
        req.status = 'denied'
        req.processed_by = current_user.username
        req.processed_at = datetime.utcnow()
        db.session.commit()
        return jsonify({'success': True, 'message': 'Deletion request denied'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error denying request: {str(e)}'}), 500

@main.route('/logs')
@login_required
@role_required(['admin'])
def view_processed():
    """Log viewing endpoint - route to service - ADMIN ONLY"""
    
    selected_date = request.args.get("date")
    selected_user = request.args.get("user")
    
    # Get logs context from service
    context = log_service.prepare_logs_context(current_user, selected_date, selected_user)
    
    # Add admin-specific data
    context.update({
        'users_admin': User.query.options(db.joinedload(User.roles)).all(),
        'roles': Role.query.order_by(Role.name).all(),
        'team_managers': TeamManager.query.order_by(TeamManager.name).all(),
        'team_leaders': TeamLeader.query.order_by(TeamLeader.name).all(),
        'agents': Agent.query.order_by(Agent.name).all(),
        'pending_requests': DeleteRequest.query.filter_by(status='pending')
            .order_by(DeleteRequest.created_at.desc()).all()
    })
    
    return render_template("logs.html", **context)


from flask import jsonify
from app.models import ActivityLog   # apna actual log model import karo

@main.route('/logs/clear', methods=['POST'])
@login_required
@role_required(['admin'])
def clear_logs():
    """Clear all logs - ADMIN ONLY"""
    try:
        num_deleted = ActivityLog.query.delete()   # ✅ clear all logs
        db.session.commit()
        return jsonify({"success": True, "message": f"Cleared {num_deleted} log entries successfully."})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"Error clearing logs: {str(e)}"})

@main.route("/update-agent-status", methods=["POST"])
@login_required
@role_required(['admin', 'tm'])   # ✅ Only Admin and TM allowed
def update_agent_status():
    from app.services.distribution_service import DistributionService

    agent_name = request.form.get("agent_name")
    status = request.form.get("status")
    effective_date = request.form.get("effective_date")

    service = DistributionService()
    success, message = service.update_agent_status(agent_name, status, effective_date)

    flash(message, "success" if success else "danger")
    return redirect(url_for("main.distribution"))





# ================= TM Wise =================
@main.route('/api/get_tm_agents/<tm_name>')
@login_required
@role_required(['admin', 'tm', 'tl'])
def get_tm_agents(tm_name):
    """
    API endpoint for Team Manager agents
    - Returns latest records with joined/moved notes + status
    - Removes duplicates
    """
    agents = distribution_service.get_agents_with_history_by_tm(tm_name)

    seen = set()
    response = []
    for a in agents:
        if a["agent_name"] not in seen:  # ✅ skip duplicates
            response.append({
                "agent_name": a["agent_name"],
                "designation": a.get("designation", ""),
                "role": a.get("role", ""),
                "status": a.get("status", "Employee"),  # ✅ include status
                "tm_name": tm_name,
                "group_name": a.get("group_name", ""),
                "tl_name": a.get("tl_name", ""),
                "moved_note": a.get("moved_note", ""),
                "joined_note": a.get("joined_note", ""),
                "from_tm": a.get("from_tm", ""),
                "joined_date": a.get("joined_date", "")
            })
            seen.add(a["agent_name"])
    return jsonify(response)


# ================= Group Wise =================
@main.route('/api/get_group_agents/<group_name>')
@login_required
@role_required(['admin', 'tm', 'tl'])
def get_group_agents(group_name):
    """
    API endpoint for Group agents
    - Returns latest records with joined/moved notes + status
    - Removes duplicates
    """
    agents = distribution_service.get_agents_with_history_by_group(group_name)

    seen = set()
    response = []
    for a in agents:
        if a["agent_name"] not in seen:  # ✅ skip duplicates
            response.append({
                "agent_name": a["agent_name"],
                "designation": a.get("designation", ""),
                "role": a.get("role", ""),
                "status": a.get("status", "Employee"),  # ✅ include status
                "group_name": group_name,
                "tm_name": a.get("tm_name", ""),
                "tl_name": a.get("tl_name", ""),
                "moved_note": a.get("moved_note", ""),
                "joined_note": a.get("joined_note", ""),
                "from_group": a.get("from_group", ""),
                "joined_date": a.get("joined_date", "")
            })
            seen.add(a["agent_name"])
    return jsonify(response)


# ================= TL Wise =================
@main.route('/api/get_tl_agents/<tl_name>')
@login_required
@role_required(['admin', 'tm', 'tl'])
def get_tl_agents(tl_name):
    """
    API endpoint for Team Leader agents
    - Returns latest records with joined/moved notes + status
    - Removes duplicates
    """
    agents = distribution_service.get_agents_with_history_by_tl(tl_name)

    seen = set()
    response = []
    for a in agents:
        if a["agent_name"] not in seen:  # ✅ skip duplicates
            response.append({
                "agent_name": a["agent_name"],
                "designation": a.get("designation", ""),
                "role": a.get("role", ""),
                "status": a.get("status", "Employee"),  # ✅ include status
                "tl_name": tl_name,
                "group_name": a.get("group_name", ""),
                "tm_name": a.get("tm_name", ""),
                "moved_note": a.get("moved_note", ""),
                "joined_note": a.get("joined_note", ""),
                "from_tl": a.get("from_tl", ""),
                "joined_date": a.get("joined_date", "")
            })
            seen.add(a["agent_name"])
    return jsonify(response)



@main.route('/logout')
@login_required
def logout():
    """Logout endpoint"""
    logout_user()
    flash("✅ Logged out successfully.", 'success')
    return redirect(url_for('auth.login'))
    
