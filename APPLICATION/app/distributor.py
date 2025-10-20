"""
Distribution management for the Agent Management System.
See DOCUMENTATION.txt for detailed business logic descriptions.
"""

from datetime import datetime
from sqlalchemy import func
from app import db
from app.models import (
    UpdatedCallLog,
    TeamManager,
    TeamLeader,
    DistributionRequest,
    ActivityLog,
    User,
    Role,
    Agent
)


class DistributionManager:
    """Core distribution business logic - OOP backend"""

    # ========================= PAGE CONTEXT ========================= #
    def prepare_distribution_context(self, current_user):
        """Prepare context for distribution.html"""

        # Base context
        context = {
            "agent_names": self._get_agent_names(current_user),
            "group_names": self._get_group_names(),
            "tm_names": self._get_tm_names(),
            "tl_names": self._get_tl_names(current_user),
            "swap_tl_names": self._get_swap_tl_names(current_user),
            "agent_data": self._get_agent_data(),
            "current_user": current_user,
            "tm_counts": self._get_tm_counts(current_user),
            "pending_requests": self._get_pending_requests(current_user),
            "team_managers": TeamManager.query.filter_by(is_active=True)
                .order_by(TeamManager.name)
                .all(),
            "team_leaders": TeamLeader.query.filter_by(is_active=True)
                .order_by(TeamLeader.name)
                .all(),
        }

        # Admins see extra context
        if current_user.has_role("admin"):
            context.update({
                "users_admin": User.query.options(db.joinedload(User.roles)).all(),
                "roles": Role.query.order_by(Role.name).all(),
                "agents": Agent.query.order_by(Agent.name).all(),
                "admin_pending_requests": DistributionRequest.query.filter_by(status="pending").all(),
            })

        return context

    # ========================= TL DISTRIBUTION ========================= #
    def create_tl_distribution_request(self, agent, date, swap_tl, swap_agent, reason, current_user):
        """TL creates a Swap Request for TM approval"""
        try:
            # 1️⃣ Required fields check
            if not agent or not date or not swap_tl or not swap_agent:
                return False, "❌ Agent, Swap TL, and Swap Agent are required.", None

            # 2️⃣ Ensure TL can only act on their own agents
            if not self._validate_tl_ownership(agent, current_user):
                return False, "❌ You can only manage agents under you.", None

            # 3️⃣ Verify that swap TL exists
            swap_tl_obj = TeamLeader.query.filter_by(name=swap_tl).first()
            if not swap_tl_obj:
                return False, f"❌ Swap TL '{swap_tl}' does not exist.", None

            # 4️⃣ Verify that swap agent exists under swap TL
            swap_agent_obj = Agent.query.filter_by(name=swap_agent, tl_id=swap_tl_obj.id).first()
            if not swap_agent_obj:
                return False, f"❌ Swap Agent '{swap_agent}' does not belong to TL '{swap_tl}'.", None

            # 5️⃣ Parse date
            try:
                effective_date = datetime.strptime(date, "%Y-%m-%d").date()
            except ValueError:
                return False, "❌ Invalid date format. Use YYYY-MM-DD.", None

            # 6️⃣ Create new distribution request
            new_request = DistributionRequest(
                agent_name=agent,
                effective_date=effective_date,
                action="swap",
                swap_with_tl=swap_tl,
                swap_with_agent=swap_agent,
                created_by=current_user.username,
                status="pending",
                reason=reason,
            )

            db.session.add(new_request)
            db.session.commit()

            return True, "🔔 Request sent to TM for approval.", (
                f"Created swap request: '{agent}' ↔ '{swap_agent}' "
                f"(Between TL '{current_user.username}' and TL '{swap_tl}')"
            )

        except Exception as e:
            db.session.rollback()
            return False, f"❌ Failed to create request: {str(e)}", None


    # ========================= DIRECT UPDATE ========================= #
    def update_distribution_directly(self, agent, date, group, tm_name, tl_name, current_user):
        """Admin/TM can directly change an agent’s TM/TL/Group"""
        try:
            if not agent or not date:
                return False, "❌ Agent and Date are required.", None

            updated_rows = UpdatedCallLog.query.filter(
                UpdatedCallLog.agent_name == agent,
                func.date(UpdatedCallLog.log_time) >= datetime.strptime(date, "%Y-%m-%d").date()
            ).all()

            if not updated_rows:
                return False, "⚠ No matching records found.", None

            # Snapshot old state
            old_tm = updated_rows[0].tm_name or "N/A"
            old_group = updated_rows[0].group_name or "N/A"
            old_tl = updated_rows[0].tl_name or "N/A"

            # TM lookup
            tm_info = TeamManager.query.filter_by(name=tm_name).first() if tm_name else None

            for row in updated_rows:
                if group:
                    row.group_name = group
                if tm_name:
                    row.tm_name = tm_name
                if tl_name:
                    row.tl_name = tl_name
                elif row.designation and row.designation.strip().lower() in ["team leader", "tl"]:
                    row.tl_name = "Self"

            # Update TeamLeader record if necessary
            if tm_name and tm_info:
                if any(row.designation and row.designation.strip().lower() in ["team leader", "tl"] for row in updated_rows):
                    team_leader = TeamLeader.query.filter_by(name=agent).first()
                    if team_leader:
                        team_leader.tm_id = tm_info.id
                        team_leader.tm_name = tm_name
                        team_leader.group_name = group or tm_info.group_name
                    else:
                        new_tl = TeamLeader(
                            name=agent,
                            tm_id=tm_info.id,
                            tm_name=tm_name,
                            group_name=group or tm_info.group_name,
                            is_active=True,
                            created_date=datetime.utcnow(),
                        )
                        db.session.add(new_tl)

            db.session.commit()

            new_tm = updated_rows[0].tm_name or "N/A"
            new_group = updated_rows[0].group_name or "N/A"
            new_tl = updated_rows[0].tl_name or "N/A"

            log_message = (
                f"Updated distribution for '{agent}': "
                f"[Before → TM: {old_tm}, Group: {old_group}, TL: {old_tl}] → "
                f"[After → TM: {new_tm}, Group: {new_group}, TL: {new_tl}]"
            )

            return True, f"✅ Distribution updated for {agent}.", log_message

        except Exception as e:
            db.session.rollback()
            return False, f"❌ Error: {str(e)}", None

    # ========================= REQUEST HANDLING ========================= #
    def handle_distribution_request(self, request_id, action, current_user):
        """TM approves or denies a TL request"""
        try:
            request = DistributionRequest.query.get_or_404(request_id)
            if request.status != "pending":
                return False, "⚠ Request already processed.", None

            # ✅ Normalize TM → TL validation
            if current_user.has_role("tm"):
                # Find the TM object for this user
                tm_obj = TeamManager.query.filter(
                    func.lower(TeamManager.name) == func.lower(current_user.username)
                ).first()

                if tm_obj:
                    allowed_tls = [
                        tl.name.lower()
                        for tl in TeamLeader.query.filter_by(tm_name=tm_obj.name, is_active=True).all()
                    ]

                    # ✅ Case-insensitive check for TL ownership
                    if (
                        request.swap_with_tl.lower() not in allowed_tls
                        and request.created_by.lower() not in allowed_tls
                    ):
                        return False, "❌ You can only handle requests from your own TLs.", None
                else:
                    return False, "❌ No matching Team Manager record found for you.", None

            # ✅ Continue with normal request handling
            if action == "approve":
                return self._approve_request(request, current_user)
            elif action == "deny":
                return self._deny_request(request, current_user)
            else:
                return False, "❌ Invalid action.", None

        except Exception as e:
            db.session.rollback()
            return False, f"❌ Error: {str(e)}", None


    # ========================= TL AGENTS ========================= #
    def get_tl_agents(self, tl_name):
        """List all agents under a specific TL"""
        agents = UpdatedCallLog.query.filter_by(tl_name=tl_name).distinct().all()
        return [a.agent_name for a in agents if a.agent_name]

    # ========================= DIRECT TL ASSIGNMENT ========================= #
    def assign_tl_directly(self, agent, tl_id, date, current_user):
        """Direct TL assignment by TM/Admin"""
        try:
            if not agent or not tl_id:
                return False, "❌ Agent and TL required.", None

            tl = TeamLeader.query.get(tl_id)
            if not tl:
                return False, "❌ TL not found.", None

            # Validate permissions
            if not current_user.has_role("admin"):
                if current_user.has_role("tm"):
                    if not self._validate_tm_ownership(agent, current_user):
                        return False, "❌ You can only manage agents in your team.", None
                    if not self._validate_tl_access(tl.name, current_user):
                        return False, "❌ You can only assign to your own TLs.", None
                else:
                    return False, "❌ Insufficient permissions.", None

            q = UpdatedCallLog.query.filter(UpdatedCallLog.agent_name == agent)
            if date:
                q = q.filter(func.date(UpdatedCallLog.log_time) >= date)

            tm = TeamManager.query.get(tl.tm_id) if tl.tm_id else None
            for row in q.all():
                row.tl_name = tl.name
                if tm:
                    row.tm_name = tm.name
                    row.group_name = tm.group_name

            db.session.commit()
            return True, "✅ Agent assigned to TL successfully.", f"Assigned '{agent}' → TL '{tl.name}'"

        except Exception as e:
            db.session.rollback()
            return False, f"❌ Error: {str(e)}", None

    # ========================= TL REQUEST CREATION ========================= #
    def create_tl_assignment_request(self, agent, action, date, reason, swap_tl, swap_agent, current_user):
        """TL requests to remove or swap an agent"""
        try:
            if not agent or action not in ["remove", "swap"]:
                return False, "❌ Invalid request data.", None

            current_tl = TeamLeader.query.get(current_user.tl_id) if current_user.tl_id else None
            if not current_tl:
                return False, "❌ You must be assigned to a TL.", None

            owns_agent = db.session.query(UpdatedCallLog.id).filter(
                UpdatedCallLog.agent_name == agent,
                UpdatedCallLog.tl_name == current_tl.name
            ).first()

            if not owns_agent:
                return False, "❌ You can only manage agents assigned to you.", None

            if action == "swap" and (not swap_tl or not swap_agent):
                return False, "❌ Please specify both TL and Agent for swap.", None

            new_req = DistributionRequest(
                agent_name=agent,
                action=action,
                effective_date=datetime.strptime(date, "%Y-%m-%d").date() if date else None,
                swap_with_tl=swap_tl,
                swap_with_agent=swap_agent,
                reason=reason,
                status="pending",
                created_by=current_user.username,
            )

            db.session.add(new_req)
            db.session.commit()
            return True, "✅ Request submitted to TM for approval.", f"Created TL assignment request for '{agent}'."

        except Exception as e:
            db.session.rollback()
            return False, f"❌ Failed: {str(e)}", None
        
    def handle_tm_assignment(self, agent, action, date, reason, replace_tl, request_tl, current_user):
        """  TM to Directly Manage Agents on their own team """
        try:
            if not agent or action not in ['add', 'remove', 'replace']:
                return False, 'Invalid request data', None
            
            if action == 'replace' and not replace_tl:
                return False, 'Please specify which TL to replace with', None
            
            # Validate access control
            if not current_user.has_role('admin') and not current_user.has_role('tm'):
                return False, 'Insufficient permissions', None
            
            tm = TeamManager.query.get(current_user.tm_id) if current_user.tm_id else None
            if not tm and not current_user.has_role('admin'):
                return False, 'You must be assigned to a TM', None
            
            # For non-admin users, validate ownership
            if not current_user.has_role('admin'):
                if not self._validate_tm_ownership(agent, current_user):
                    return False, 'You can only manage agents in your team', None
            
            if action == 'replace' and replace_tl:
                if not current_user.has_role('admin'):
                    replace_tl_obj = TeamLeader.query.filter_by(name=replace_tl, tm_id=tm.id).first()
                    if not replace_tl_obj:
                        return False, 'Selected replacement TL not found in your team', None
                else:
                    replace_tl_obj = TeamLeader.query.filter_by(name=replace_tl).first()
                    if not replace_tl_obj:
                        return False, 'Selected replacement TL not found', None
            
            self._ensure_tl_name_column()
            q = UpdatedCallLog.query.filter(UpdatedCallLog.agent_name == agent)
            if date:
                q = q.filter(func.date(UpdatedCallLog.log_time) >= date)
            
            if action == 'add' and request_tl:
                if not current_user.has_role('admin'):
                    requesting_tl = TeamLeader.query.filter_by(name=request_tl, tm_id=tm.id).first()
                else:
                    requesting_tl = TeamLeader.query.filter_by(name=request_tl).first()
                if requesting_tl:
                    for row in q.all():
                        row.tl_name = requesting_tl.name
                        if tm:
                            row.tm_name = tm.name
                            row.group_name = tm.group_name
            elif action == 'remove':
                for row in q.all():
                    row.tl_name = None
                    if tm:
                        row.tm_name = tm.name
                        row.group_name = tm.group_name
            elif action == 'replace' and replace_tl:
                for row in q.all():
                    row.tl_name = replace_tl
                    if tm:
                        row.tm_name = tm.name
                        row.group_name = tm.group_name
            
            db.session.commit()
            log_message = f"Performed {action} action on agent '{agent}'"
            return True, f'✅ Agent {action} action completed successfully', log_message
            
        except Exception as e:
            db.session.rollback()
            return False, f'❌ Error: {str(e)}', None
    
    def update_agent_designation(self, agent, date, designation, role, current_user):
        """Core logic for updating agent designation and role"""
        try:
            if not agent or not date:
                return False, "❌ Agent and Date are required.", None

            updated_rows = UpdatedCallLog.query.filter(
                UpdatedCallLog.agent_name == agent,
                func.date(UpdatedCallLog.log_time) >= datetime.strptime(date, "%Y-%m-%d").date()
            ).all()
            
            if not updated_rows:
                return False, "⚠️ No matching records found.", None
            

            # Get old designation & role for logging
            old_designation = updated_rows[0].designation
            old_role = updated_rows[0].role

            # If designation changed to Team Leader, ensure TL exists
            inferred_tm = None
            if designation.strip().lower() in ['team leader', 'tl']:
                sample_row = updated_rows[0]
                inferred_tm = TeamManager.query.filter_by(name=sample_row.tm_name).first() if sample_row.tm_name else None
                
                # Create TeamLeader if doesn't exist
                existing_tl = TeamLeader.query.filter_by(name=agent).first()
                if not existing_tl:
                    try:
                        # Create TeamLeader record - TM info will be updated later when assigned
                        new_tl = TeamLeader(
                            name=agent,
                            group_name=(inferred_tm.group_name if inferred_tm else sample_row.group_name or 'Unassigned'),
                            tm_id=(inferred_tm.id if inferred_tm else None),
                            tm_name=(inferred_tm.name if inferred_tm else None),
                            is_active=True,
                            created_date=datetime.utcnow()
                        )
                        db.session.add(new_tl)
                        db.session.flush()
                    except Exception as e:
                        db.session.rollback()
                        return False, f"❌ Failed to create Team Leader record: {str(e)}", None

            # Update all matching records
            for row in updated_rows:
                row.designation = designation
                row.role = role
                
                if designation.strip().lower() in ['team leader', 'tl']:
                    row.tl_name = 'Self'
                    if inferred_tm:
                        row.tm_name = inferred_tm.name
                        row.group_name = inferred_tm.group_name
                else:
                    # Non-TL designation becomes default designation
                    from app.config import Config
                    row.designation = Config.DEFAULT_DESIGNATION
                    row.tl_name = None  # Clear TL assignment

            db.session.commit()
            
            log_message = (
            f"Updated designation/role for '{agent}' from {date} onwards | "
            f"Designation: '{old_designation}' → '{designation}', "
            f"Role: '{old_role}' → '{role}'"
        )
            return True, "✅ Designation and Role updated successfully.", log_message

        except Exception as e:
            db.session.rollback()
            return False, f"❌ Error: {str(e)}", None
    
    # ========== PRIVATE METHODS ==========
    
    def _get_agent_names(self, current_user):
        """ Fetch the list of agent names user allowed to see """
        if current_user.has_role("admin"):
            return [a[0] for a in db.session.query(UpdatedCallLog.agent_name)
                   .filter(UpdatedCallLog.agent_name.isnot(None), UpdatedCallLog.agent_name != '').distinct() if a[0]]
        elif current_user.has_role("tm"):
            tm = TeamManager.query.get(current_user.tm_id)
            return [a[0] for a in db.session.query(UpdatedCallLog.agent_name)
                   .filter(UpdatedCallLog.tm_name == tm.name, 
                          UpdatedCallLog.agent_name.isnot(None), UpdatedCallLog.agent_name != '').distinct() if a[0]] if tm else []
        elif current_user.has_role("tl"):
            tl = TeamLeader.query.get(current_user.tl_id)
            return [a[0] for a in db.session.query(UpdatedCallLog.agent_name)
                   .filter(UpdatedCallLog.tl_name == tl.name,
                          UpdatedCallLog.agent_name.isnot(None), UpdatedCallLog.agent_name != '').distinct() if a[0]] if tl else []
        return []
    
    def _get_group_names(self):
        """Get group names"""
        return [g[0] for g in db.session.query(TeamManager.group_name)
                .filter(TeamManager.group_name.isnot(None), TeamManager.group_name != '').distinct() if g[0]]
    
    def _get_tm_names(self):
        """Get TM names"""
        return [t[0] for t in db.session.query(TeamManager.name)
                .filter(TeamManager.name.isnot(None), TeamManager.name != '').distinct() if t[0]]
    
    def _get_tl_names(self, current_user):
        """ Get a list of TL names I'm allowed to see """
        if current_user.has_role("admin"):
            return [t[0] for t in db.session.query(TeamLeader.name)
                    .filter(TeamLeader.is_active == True, TeamLeader.name.isnot(None), TeamLeader.name != '').distinct() if t[0]]
        elif current_user.has_role("tm"):
            tm = TeamManager.query.get(current_user.tm_id)
            return [t[0] for t in db.session.query(TeamLeader.name)
                    .filter(TeamLeader.tm_id == tm.id, TeamLeader.is_active == True, 
                           TeamLeader.name.isnot(None), TeamLeader.name != '').distinct()] if tm else []
        elif current_user.has_role("tl"):
            tl = TeamLeader.query.get(current_user.tl_id)
            return [t[0] for t in db.session.query(TeamLeader.name)
                    .filter(TeamLeader.tm_id == tl.tm_id, TeamLeader.is_active == True,
                           TeamLeader.name.isnot(None), TeamLeader.name != '').distinct()] if tl else []
        return []
    
    def _get_swap_tl_names(self, current_user):
        """ Get a list of TLs I'm allowed to swap agents with """
        query = db.session.query(TeamLeader.name).filter(
            TeamLeader.is_active == True,
            TeamLeader.name.isnot(None),
            TeamLeader.name != ''
        ).order_by(TeamLeader.name)
        
        if current_user.has_role("tm"):
            tm = TeamManager.query.get(current_user.tm_id)
            query = query.filter(TeamLeader.tm_id == tm.id) if tm else query.filter(False)
        elif current_user.has_role("tl"):
            tl = TeamLeader.query.get(current_user.tl_id)
            query = query.filter(TeamLeader.tm_id == tl.tm_id, TeamLeader.id != tl.id) if tl else query.filter(False)
        
        return [t[0] for t in query.all()]
    
    def _get_agent_data(self):
        """ Get detailed info about all agents """
        agent_data = db.session.query(
            UpdatedCallLog.agent_name,
            UpdatedCallLog.tm_name,
            UpdatedCallLog.group_name,
            UpdatedCallLog.role,
            UpdatedCallLog.designation,
            UpdatedCallLog.tl_name
        ).distinct().all()
        
        return [dict(agent_name=a.agent_name, tm_name=a.tm_name, group_name=a.group_name,
                    role=a.role, designation=a.designation, tl_name=a.tl_name)
                for a in agent_data if a.agent_name]
    
    def _get_tm_counts(self, current_user):
        """ Count how many TLs and agents a TM has """
        if not current_user.has_role('tm') or not current_user.tm_id:
            return {}
        
        tm = TeamManager.query.get(current_user.tm_id)
        if not tm:
            return {}
        
        return {
            'tl_count': TeamLeader.query.filter_by(tm_id=tm.id, is_active=True).count(),
            'agent_count': db.session.query(UpdatedCallLog.agent_name).filter(
                UpdatedCallLog.tm_name == tm.name).distinct().count(),
            'idle_agents': db.session.query(UpdatedCallLog.agent_name).filter(
                UpdatedCallLog.tm_name == tm.name,
                (UpdatedCallLog.tl_name.is_(None) | (UpdatedCallLog.tl_name == ''))).distinct().count(),
            'tm_name': tm.name
        }
    
    def _get_pending_requests(self, current_user):
        """ Get all requests waiting for my review - filtered by TM's team """
        # Admin can see all requests
        if current_user.has_role('admin'):
            return DistributionRequest.query.filter_by(status='pending').order_by(
                DistributionRequest.created_at.desc()).all()
        
        # TM can only see requests from their own TLs
        if current_user.has_role('tm') and current_user.tm_id:
            tm = TeamManager.query.get(current_user.tm_id)
            if tm:
                # Get usernames of users who are TLs under this TM
                tl_usernames = [user.username for user in User.query.filter(
                    User.tl_id.in_([tl.id for tl in TeamLeader.query.filter_by(tm_id=tm.id, is_active=True).all()])
                ).all()]
                # Filter requests to only show those from TLs under this TM
                return DistributionRequest.query.filter(
                    DistributionRequest.status == 'pending',
                    DistributionRequest.created_by.in_(tl_usernames)
                ).order_by(DistributionRequest.created_at.desc()).all()
        return []
    
    def _validate_tl_ownership(self, agent_name, current_user):
        """ Check if this agent actually belongs to me """
        if not current_user.tl_id:
            return False
        
        tl = TeamLeader.query.get(current_user.tl_id)
        if not tl:
            return False
        
        return db.session.query(UpdatedCallLog.id).filter(
            UpdatedCallLog.agent_name == agent_name,
            UpdatedCallLog.tl_name == tl.name
        ).first() is not None
    
    def _validate_tm_ownership(self, agent_name, current_user):
        """ Check if this agent belongs to my team """
        if not current_user.tm_id:
            return False
        
        tm = TeamManager.query.get(current_user.tm_id)
        if not tm:
            return False
        
        return db.session.query(UpdatedCallLog.id).filter(
            UpdatedCallLog.agent_name == agent_name,
            UpdatedCallLog.tm_name == tm.name
        ).first() is not None
    
    def _validate_tl_access(self, tl_name, current_user):
        """ Check if user can access this TL """
        if current_user.has_role("admin"):
            return True
        
        if current_user.has_role("tm"):
            tm = TeamManager.query.get(current_user.tm_id)
            if not tm:
                return False
            tl = TeamLeader.query.filter_by(name=tl_name, tm_id=tm.id).first()
            return tl is not None
        
        if current_user.has_role("tl"):
            tl = TeamLeader.query.get(current_user.tl_id)
            if not tl:
                return False
            return tl.tm_id == TeamLeader.query.filter_by(name=tl_name).first().tm_id if TeamLeader.query.filter_by(name=tl_name).first() else False
        
        return False
    
    def _ensure_tl_name_column(self):
        """ Make sure the database has a place to store the TL's name """
        try:
            db.session.execute(
                "ALTER TABLE updated_call_logs ADD COLUMN IF NOT EXISTS tl_name VARCHAR(100)"
            )
            db.session.commit()
        except Exception:
            db.session.rollback()
    
    def _approve_request(self, request, current_user):
        """Approve request (Swap / Remove)"""
        try:
            effective_date = datetime.combine(request.effective_date, datetime.min.time())

            if request.action == 'swap' and request.swap_with_tl and request.swap_with_agent:
                # --- Find old TL for both agents ---
                agent_row = UpdatedCallLog.query.filter(
                    UpdatedCallLog.agent_name == request.agent_name,
                    UpdatedCallLog.log_time >= effective_date
                ).first()
                agent_old_tl = agent_row.tl_name if agent_row else "N/A"

                swap_agent_row = UpdatedCallLog.query.filter(
                    UpdatedCallLog.agent_name == request.swap_with_agent,
                    UpdatedCallLog.log_time >= effective_date
                ).first()
                swap_agent_old_tl = swap_agent_row.tl_name if swap_agent_row else "N/A"

                # --- Perform Swap ---
                UpdatedCallLog.query.filter(
                    UpdatedCallLog.agent_name == request.agent_name,
                    UpdatedCallLog.log_time >= effective_date
                ).update({UpdatedCallLog.tl_name: swap_agent_old_tl})

                UpdatedCallLog.query.filter(
                    UpdatedCallLog.agent_name == request.swap_with_agent,
                    UpdatedCallLog.log_time >= effective_date
                ).update({UpdatedCallLog.tl_name: agent_old_tl})

                log_message = (
                    f"✅ Swap Approved: "
                    f"'{request.agent_name}' (from TL '{agent_old_tl}') → TL '{swap_agent_old_tl}', "
                    f"'{request.swap_with_agent}' (from TL '{swap_agent_old_tl}') → TL '{agent_old_tl}'"
                )

            elif request.action == 'remove':
                # --- Find agent's old TL ---
                agent_row = UpdatedCallLog.query.filter(
                    UpdatedCallLog.agent_name == request.agent_name,
                    UpdatedCallLog.log_time >= effective_date
                ).first()
                agent_old_tl = agent_row.tl_name if agent_row else "N/A"

                # --- Remove agent from TL (set TL to None / Unassigned) ---
                UpdatedCallLog.query.filter(
                    UpdatedCallLog.agent_name == request.agent_name,
                    UpdatedCallLog.log_time >= effective_date
                ).update({UpdatedCallLog.tl_name: None})

                log_message = (
                    f"🗑️ Remove Approved: "
                    f"'{request.agent_name}' removed from TL '{agent_old_tl}'"
                )

            else:
                log_message = f"Approved request for {request.agent_name}"

            # --- Mark as approved ---
            request.status = 'approved'
            request.approved_by = current_user.username
            request.approved_at = datetime.utcnow()
            db.session.commit()

            return True, "✅ Request approved successfully.", log_message

        except Exception as e:
            db.session.rollback()
            return False, f"❌ Error approving request: {str(e)}", None



    
    def _deny_request(self, request, current_user):
        """Deny request"""
        request.status = 'rejected'
        request.approved_by = current_user.username
        request.approved_at = datetime.utcnow()
        db.session.commit()
        
        log_message = f"Denied request for {request.agent_name}"
        return True, f"❌ Request denied for {request.agent_name}.", log_message