"""
User management service for the Agent Management System.
See DOCUMENTATION.txt for detailed service descriptions.
"""

from flask import current_app
from sqlalchemy import func
from app import db
from app.models import User, Role, TeamManager, TeamLeader, Agent, ActivityLog,UpdatedCallLog
from datetime import datetime
from app.permissions import PermissionSystem

class UserService:
    """Service for all user, role, and team management operations"""
    
    def __init__(self):
        self.permission_system = PermissionSystem()
    
    def init_roles(self):
        """Initializes all system roles with permissions"""
        roles_to_create ={
            'admin': self.permission_system.get_default_permissions('admin'),
            'data_entry': self.permission_system.get_default_permissions('data_entry'),
            'tm': self.permission_system.get_default_permissions('tm'),
            'tl': self.permission_system.get_default_permissions('tl'),
        }

        for role_name, permissions in roles_to_create.items():
            role = Role.query.filter_by(name=role_name).first()
            if not role:
                role = Role(name=role_name, permissions=permissions)
                db.session.add(role)
            else:
                role.permissions = permissions

        db.session.commit()
        return True
    
    def init_admin_user(self):
        """Initialize admin user with admin role"""
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(username='admin')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()


        admin_role = Role.query.filter_by(name='admin').first()
        if admin_role and admin_role not in admin.roles:
            admin.roles.append(admin_role)
            db.session.commit()

        return
   
    def create_user(self, username, password, role_name, current_user, tm_id=None, tl_id=None):
        """Create a new user with specified role and team associations"""
        try:
            # Validate inputs
            if not all([username, password, role_name]):
                return False, "❌ All fields are required"
        
            # Check for existing user
            if User.query.filter_by(username=username).first():
                return False, "⚠️ Username already exists"
        
            # Ensure role exists
            role = Role.query.filter_by(name=role_name).first()
            if not role:
                role = self._create_role(role_name)
        
            # Extra info for logging
            association_info = ""

            if role_name == "tm":
                if tm_id:
                    tm = TeamManager.query.get(tm_id)
                    if not tm:
                        return False, f"❌ Team Manager with ID {tm_id} not found"
                    association_info = f"(Team Manager: {tm.name})"
                else:
                    return False, "⚠️ Please select a Team Manager for TM role"
        
            elif role_name == "tl":
                if tl_id:
                    tl = TeamLeader.query.get(tl_id)
                    if not tl:
                        return False, f"❌ Team Leader with ID {tl_id} not found"
                    tm_id = tl.tm_id
                    association_info = f"(Team Leader: {tl.name}, TM: {tl.tm_name})"
                else:
                    return False, "⚠️ Please select a Team Leader for TL role"
        
            # Create user
            new_user = User(username=username.lower(), tm_id=tm_id, tl_id=tl_id)
            new_user.set_password(password)
            new_user.roles.append(role)
        
            db.session.add(new_user)
            db.session.commit()
        
            # ✅ Only include role names of the current user, not the username twice
            current_roles = ", ".join([r.name for r in current_user.roles])
        
            log_message = (
                f"created user '{username}' "
                f"with role '{role_name}' {association_info}"
            )
            self._log_activity(current_user, log_message)
        
            return True, f"✅ Successfully created user '{username}' with role '{role_name}' {association_info}"
        
        except Exception as e:
            db.session.rollback()
            return False, f"❌ Error creating user: {str(e)}"


    def delete_user(self, user_id, current_user):
        """Delete a user with validation and logging"""
        try:
            user = User.query.get(user_id)
            if not user:
                return False, "❌ User not found"
        
            if user.id == current_user.id:
                return False, "❌ You cannot delete yourself"
        
            # ✅ Capture roles of the user being deleted before deletion
            roles = [role.name for role in user.roles] if user.roles else ["N/A"]
            role_list = ", ".join(roles)

            username = user.username

            # Delete the user
            db.session.delete(user)
            db.session.commit()
        
            # ✅ Build detailed log message with roles
            current_roles = ", ".join([r.name for r in current_user.roles])
            log_message = (
                f"deleted user '{username}' (Role: {role_list})"
            )

            # Log activity
            self._log_activity(current_user, log_message)
        
            return True, f"✅ User '{username}' (Role: {role_list}) deleted successfully"
        
        except Exception as e:
            db.session.rollback()
            return False, f"❌ Error deleting user: {str(e)}"

    
    def create_team_manager(self, name, group_name, current_user):
        """Create a new team manager and update agent/logs if exists"""
        try:
            if not all([name, group_name]):
                return False, "Name and group name are required"

            if TeamManager.query.filter_by(name=name).first():
                return False, "Team Manager already exists"

            # === 1) Create TeamManager record ===
            new_tm = TeamManager(
                name=name,
                group_name=group_name,
                created_date=datetime.utcnow(),
                is_active=True
            )
            db.session.add(new_tm)

            # === 2) Update Agent if exists ===
            agent = Agent.query.filter_by(name=name).first()
            if agent:
                agent.designation = "Team Manager"
                agent.group_name = group_name
                agent.tm_name = "Self"  # ✅ TM khud ka TM hota hai

            # === 3) Update UpdatedCallLog if exists ===
            logs = UpdatedCallLog.query.filter_by(agent_name=name).all()
            for log in logs:
                log.designation = "Team Manager"
                log.tm_name = "Self"
                log.tl_name = "N/A"  # ✅ TM ke liye TL N/A
                log.group_name = group_name

            db.session.commit()

            # === 4) Log Activity ===
            self._log_activity(
                current_user,
                f"created Team Manager '{name}' with group '{group_name}'"
            )

            return True, f"✅ Successfully created Team Manager '{name}' in group '{group_name}'."

        except Exception as e:
            db.session.rollback()
            return False, f"❌ Error creating team manager: {str(e)}"

    
    def create_team_leader(self, name, tm_id, tm_name, group_name, current_user):
        """Create a new Team Leader and update agent/logs if exists"""
        try:
            if not all([name, tm_id, tm_name, group_name]):
                return False, "Name, TM, and Group are required"

            if TeamLeader.query.filter_by(name=name).first():
                return False, "Team Leader already exists"

            # === 1) Create TL record ===
            new_tl = TeamLeader(
                name=name,
                tm_id=tm_id,
                tm_name=tm_name,
                group_name=group_name,
                created_date=datetime.utcnow()
            )
            db.session.add(new_tl)

            # === 2) Update Agent if exists ===
            agent = Agent.query.filter_by(name=name).first()
            if agent:
                agent.designation = "Team Leader"
                agent.group_name = group_name
                agent.tm_name = tm_name

            # === 3) Update UpdatedCallLog if exists ===
            logs = UpdatedCallLog.query.filter_by(agent_name=name).all()
            for log in logs:
                log.designation = "Team Leader"
                log.tl_name = "Self"
                log.tm_name = tm_name
                log.group_name = group_name

            db.session.commit()

            # === 4) Activity Log ===
            self._log_activity(
                current_user,
                f"created Team Leader '{name}' under TM '{tm_name}' in group '{group_name}'"
            )

            return True, f"✅ Successfully created Team Leader '{name}' under TM '{tm_name}'."

        except Exception as e:
            db.session.rollback()
            return False, f"❌ Error creating team leader: {str(e)}"

    
    def delete_team_leader(self, tl_id, current_user):
        """Delete a team leader with validation and logging"""
        try:
            tl = TeamLeader.query.get(tl_id)
            if not tl:
                return False, "Team Leader not found"
            
            # Check if TL has associated agents
            agents_count = Agent.query.filter_by(tl_id=tl_id).count()
            if agents_count > 0:
                return False, f"Cannot delete Team Leader '{tl.name}' - has {agents_count} associated agents"
            
            # Delete associated user if exists
            user = User.query.filter_by(tl_id=tl_id).first()
            if user:
                db.session.delete(user)
            
            # Delete the team leader
            tl_name = tl.name
            db.session.delete(tl)
            db.session.commit()
            
            self._log_activity(
                current_user,
                f"deleted Team Leader '{tl_name}'"
            )
            
            return True, f"Team Leader '{tl_name}' deleted successfully"
            
        except Exception as e:
            db.session.rollback()
            return False, f"Error deleting team leader: {str(e)}"
    
    def delete_team_manager(self, tm_id, current_user):
        """Delete a team manager with validation and logging"""
        try:
            tm = TeamManager.query.get(tm_id)
            if not tm:
                return False, "Team Manager not found"
            
            # Check if TM has associated team leaders
            tls_count = TeamLeader.query.filter_by(tm_id=tm_id).count()
            if tls_count > 0:
                return False, f"Cannot delete Team Manager '{tm.name}' - has {tls_count} associated team leaders"
            
            # Check if TM has associated agents
            agents_count = Agent.query.filter_by(tm_id=tm_id).count()
            if agents_count > 0:
                return False, f"Cannot delete Team Manager '{tm.name}' - has {agents_count} associated agents"
            
            # Delete associated users if exist
            users = User.query.filter_by(tm_id=tm_id).all()
            for user in users:
                db.session.delete(user)
            
            # Delete the team manager
            tm_name = tm.name
            db.session.delete(tm)
            db.session.commit()
            
            self._log_activity(
                current_user,
                f"deleted Team Manager '{tm_name}'"
            )
            
            return True, f"Team Manager '{tm_name}' deleted successfully"
            
        except Exception as e:
            db.session.rollback()
            return False, f"Error deleting team manager: {str(e)}"
    
    def deactivate_team_manager(self, tm_id, current_user):
        """Deactivate a team manager"""
        try:
            tm = TeamManager.query.get(tm_id)
            if not tm:
                return False, "Team Manager not found"
            
            if not tm.is_active:
                return False, f"Team Manager '{tm.name}' is already inactive"
            
            tm.is_active = False
            tm.end_date = datetime.utcnow()
            db.session.commit()
            
            self._log_activity(
                current_user,
                f"deactivated Team Manager '{tm.name}'"
            )
            
            return True, f"Team Manager '{tm.name}' deactivated successfully"
            
        except Exception as e:
            db.session.rollback()
            return False, f"Error deactivating team manager: {str(e)}"
    
    def replace_team_manager(self, old_tm_id, new_name, new_group_name, effective_date, current_user, keep_old_tm=True):
        """Replace an existing team manager with a new one"""
        try:
            if not all([old_tm_id, new_name, new_group_name]):
                return False, "All fields are required"
            
            old_tm = TeamManager.query.get(old_tm_id)
            if not old_tm:
                return False, "Team Manager not found"
            
            # Check if new name already exists
            if TeamManager.query.filter_by(name=new_name).first():
                return False, "Team Manager with this name already exists"
            
            # Create new team manager
            new_tm = TeamManager(
                name=new_name,
                group_name=new_group_name,
                is_active=True,
                created_date=datetime.utcnow()
            )
            db.session.add(new_tm)
            db.session.flush()  # Get the ID
            
            # Update all team leaders under the old TM
            team_leaders = TeamLeader.query.filter_by(tm_id=old_tm_id).all()
            for tl in team_leaders:
                tl.tm_id = new_tm.id
                tl.tm_name = new_name
                tl.group_name = new_group_name
            
            # Update all agents under the old TM
            agents = Agent.query.filter_by(tm_id=old_tm_id).all()
            for agent in agents:
                agent.tm_id = new_tm.id
                agent.tm_name = new_name
                agent.group_name = new_group_name
            
            # Update all users under the old TM
            users = User.query.filter_by(tm_id=old_tm_id).all()
            for user in users:
                user.tm_id = new_tm.id
            
            # Handle old team manager based on keep_old_tm setting
            if keep_old_tm:
                # Deactivate old team manager but keep in database
                old_tm.is_active = False
                old_tm.end_date = datetime.utcnow()
                old_tm.replaced_by_id = new_tm.id
            else:
                # Delete old team manager completely
                db.session.delete(old_tm)
            
            db.session.commit()
            
            self._log_activity(
                current_user,
                f"replaced Team Manager '{old_tm.name}' with '{new_name}'"
            )
            
            return True, f"Successfully replaced Team Manager '{old_tm.name}' with '{new_name}'"
            
        except Exception as e:
            db.session.rollback()
            return False, f"Error replacing team manager: {str(e)}"
    
    def _create_role(self, role_name):
        """Create a new role with default permissions"""
        permissions = self.permission_system.get_default_permissions(role_name)
        role = Role(name=role_name, permissions=permissions)
        db.session.add(role)
        db.session.commit()
        return role
    
    def _log_activity(self, user, message):
        """Helper for activity logging"""
        log_msg = f"{user.username} (Admin) {message}"
        log_entry = ActivityLog(user=user.username, msg=log_msg, date=datetime.utcnow())
        db.session.add(log_entry)
        db.session.commit()
        
        if hasattr(current_app, "activity_logs"):
            current_app.activity_logs.append({
                "msg": log_msg,
                "date": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                "user": user.username
            })