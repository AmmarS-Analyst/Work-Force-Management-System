"""
Database models for the Agent Management System.
See DOCUMENTATION.txt for detailed model descriptions and relationships.
"""

from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import db

# Association table for many-to-many relationship between users and roles
user_roles = db.Table(
    'user_roles',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id')),
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id'))
)

# ------------------------
# Team Manager Model
# ------------------------

class TeamManager(db.Model):
    """Team Manager model - manages team leaders and agents"""
    __tablename__ = 'team_managers'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    group_name = db.Column(db.String(100), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    end_date = db.Column(db.DateTime, nullable=True)
    replaced_by_id = db.Column(db.Integer, db.ForeignKey('team_managers.id'), nullable=True)

    # Relationships
    users = db.relationship('User', backref='team_manager_ref', lazy=True)
    team_leaders = db.relationship('TeamLeader', backref='team_manager', lazy=True)

    # Self-referential relationship
    replaced_by = db.relationship('TeamManager', remote_side=[id],
                                  backref=db.backref('replaced', lazy=True))

    def __repr__(self):
        return f'<TeamManager {self.name} - {self.group_name}>'

# ------------------------
# Team Leader Model
# ------------------------

class TeamLeader(db.Model):
    __tablename__ = 'team_leaders'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    group_name = db.Column(db.String(100), nullable=False)
    tm_id = db.Column(db.Integer, db.ForeignKey('team_managers.id'), nullable=True)
    tm_name = db.Column(db.String(100), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    end_date = db.Column(db.DateTime, nullable=True)
    replaced_by_id = db.Column(db.Integer, db.ForeignKey('team_leaders.id'), nullable=True)

    # Relationships
    agents = db.relationship('Agent', backref='team_leader', lazy=True)

    replaced_by = db.relationship('TeamLeader', remote_side=[id],
                                  backref=db.backref('replaced', lazy=True))

    def __repr__(self):
        return f'<TeamLeader {self.name} - {self.group_name} (TM: {self.tm_name})>'
    
# ------------------------
# Agents List
# ------------------------

class AgentList(db.Model):
    _tablename_ = 'agent_list'
    
    id = db.Column(db.Integer, primary_key=True)
    agent_name = db.Column(db.String(100), unique=True, nullable=False)
    
    def _repr_(self):
        return f'<AgentList {self.agent_name}>'

# ------------------------
# Agent Model
# ------------------------

class Agent(db.Model):
    __tablename__ = 'agents'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    group_name = db.Column(db.String(100), nullable=False)
    tl_id = db.Column(db.Integer, db.ForeignKey('team_leaders.id'), nullable=True)
    tm_id = db.Column(db.Integer, db.ForeignKey('team_managers.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    end_date = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f'<Agent {self.name} - {self.group_name}>'

# ------------------------
# User Model
# ------------------------

class User(UserMixin, db.Model):
    """User model with authentication and role management"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_active = db.Column(db.Boolean, default=True)

    # Foreign keys for team associations
    tm_id = db.Column(db.Integer, db.ForeignKey('team_managers.id'), nullable=True)
    tl_id = db.Column(db.Integer, db.ForeignKey('team_leaders.id'), nullable=True)

    roles = db.relationship('Role', secondary=user_roles, backref=db.backref('users', lazy='dynamic'))
    delete_requests = db.relationship('DeleteRequest', backref='requester', lazy=True)

    # In the User class, add this method:
    def has_permission(self, permission):
        """Check if user has specific permission - uses existing PermissionSystem"""
        from app.permissions import PermissionSystem
        permission_system = PermissionSystem()
        return permission_system.has_permission(self, permission)

    # ------------------ Password ------------------ #
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # ------------------ Roles ------------------ #
    def has_role(self, role_name):
        return any(role.name.lower() == role_name.strip().lower() for role in self.roles)

    # ------------------ Static Helpers ------------------ #
    @staticmethod
    def get(user_id):
        return User.query.get(int(user_id))

    @staticmethod
    def validate(username, password):
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            return user
        return None

# ------------------------
# Role Model
# ------------------------

class Role(db.Model):
    __tablename__ = 'roles'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    permissions = db.Column(db.PickleType, nullable=False)

    def __repr__(self):
        return f'<Role {self.name}>'

# ------------------------
# Call Logs
# ------------------------

class RawCallLog(db.Model):
    __tablename__ = 'raw_call_logs'

    id = db.Column(db.Integer, primary_key=True)
    agent_name = db.Column(db.String(100))
    profile_id = db.Column(db.String(50))
    call_log_id = db.Column(db.String(50))
    log_time = db.Column(db.DateTime)
    log_type = db.Column(db.String(50))
    state = db.Column(db.String(50))
    call_type = db.Column(db.String(50))
    original_campaign = db.Column(db.String(100))
    current_campaign = db.Column(db.String(100))
    ember = db.Column(db.String(50))
    source_file = db.Column(db.String(255))
    uploaded_at = db.Column(db.DateTime, server_default=db.func.now())

class UpdatedCallLog(db.Model):
    __tablename__ = 'updated_call_logs'

    id = db.Column(db.Integer, primary_key=True)
    agent_name = db.Column(db.String(100))
    profile_id = db.Column(db.String(50))
    call_log_id = db.Column(db.String(50))
    log_time = db.Column(db.DateTime)
    log_type = db.Column(db.String(50))
    state = db.Column(db.String(50))
    call_type = db.Column(db.String(50))
    original_campaign = db.Column(db.String(100))
    current_campaign = db.Column(db.String(100))
    ember = db.Column(db.String(50))

    designation = db.Column(db.String(50))   # Agent / TL / TM
    role = db.Column(db.String(50))          # role from roles table
    group_name = db.Column(db.String(100))
    tm_name = db.Column(db.String(100))
    tl_name = db.Column(db.String(100))
    source_file = db.Column(db.String(255))
    updated_at = db.Column(db.DateTime, server_default=db.func.now())
    status = db.Column(
    db.String(50),
    nullable=False,
    server_default="employee"
)

# ------------------------
# Delete Request
# ------------------------

class DeleteRequest(db.Model):
    __tablename__ = 'delete_requests'

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    requested_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    requested_by_username = db.Column(db.String(100), nullable=False)
    reason = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending')  # pending, approved, denied
    date_range = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    processed_by = db.Column(db.String(100))
    processed_at = db.Column(db.DateTime)

    def __repr__(self):
        return f'<DeleteRequest {self.filename} - {self.status}>'

# ------------------------
# Agent Assignment Request
# ------------------------

class AgentAssignmentRequest(db.Model):
    __tablename__ = 'agent_assignment_requests'

    id = db.Column(db.Integer, primary_key=True)
    agent_name = db.Column(db.String(100), nullable=False)
    action = db.Column(db.String(20), nullable=False)  # add, remove, replace
    effective_date = db.Column(db.Date, nullable=True)
    requesting_tl_id = db.Column(db.Integer, db.ForeignKey('team_leaders.id'), nullable=False)
    current_tl_id = db.Column(db.Integer, db.ForeignKey('team_leaders.id'), nullable=True)
    tm_id = db.Column(db.Integer, db.ForeignKey('team_managers.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, approved, denied
    reason = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    processed_at = db.Column(db.DateTime, nullable=True)

    requesting_tl = db.relationship('TeamLeader', foreign_keys=[requesting_tl_id])
    current_tl = db.relationship('TeamLeader', foreign_keys=[current_tl_id])
    tm = db.relationship('TeamManager', backref='assignment_requests')

    def __repr__(self):
        return f'<AgentAssignmentRequest {self.agent_name} - {self.status}>'

# ------------------------
# Activity Log
# ------------------------

class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'

    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.String(100), nullable=False)
    msg = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<ActivityLog {self.user} - {self.msg[:50]}>'

class DistributionRequest(db.Model):
    __tablename__ = 'distribution_requests'

    id = db.Column(db.Integer, primary_key=True)

    # Request details
    agent_name = db.Column(db.String(100), nullable=False)
    action = db.Column(db.String(50), nullable=False)  # e.g., 'swap', 'shift_change'
    effective_date = db.Column(db.Date, nullable=False)
    swap_with_tl = db.Column(db.String(100), nullable=True)
    swap_with_agent = db.Column(db.String(100), nullable=True)
    reason = db.Column(db.Text, nullable=True)

    # Status tracking
    status = db.Column(db.String(20), default='pending')  # 'pending', 'approved', 'rejected'

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(100), nullable=False)

    approved_by = db.Column(db.String(100), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f"<DistributionRequest {self.agent_name} - {self.action} - {self.status}>"




# ------------------------
# Agent Info
# ------------------------

from datetime import datetime
from app import db

class AgentInfo(db.Model):
    __tablename__ = 'agent_info'

    id = db.Column(db.Integer, primary_key=True)
    agent_name = db.Column(db.String, unique=True, nullable=False)
    tm_name = db.Column(db.String, nullable=True)
    tl_name = db.Column(db.String, nullable=True)
    group_name = db.Column(db.String, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<AgentInfo {self.agent_name}>"
