from datetime import datetime
from flask import render_template, flash, redirect, url_for
from sqlalchemy import func
from app.models import (
    DistributionRequest,
    ActivityLog,
    TeamManager,
    TeamLeader,
    UpdatedCallLog,
    User,
    Role,
    Agent
)
import pandas as pd
from app.distributor import DistributionManager
from app.services.log_service import LogService
from app.updater import update_agent_data
from app import db

from datetime import datetime
from flask_login import current_user as flask_current_user


class DistributionService:
    """Service layer for distribution operations"""

    def __init__(self):
        self.distributor = DistributionManager()
        self.log_service = LogService()

    # ------------------ Convenience name helpers ------------------ #
    def get_tm_names(self, all_data=False):
        if all_data:
            return [tm.name for tm in TeamManager.query.order_by(TeamManager.name).all()]
        # default: active TMs only
        return [tm.name for tm in TeamManager.query.filter_by(is_active=True).order_by(TeamManager.name).all()]

    def get_group_names(self):
        tms = TeamManager.query.order_by(TeamManager.group_name).all()
        names = sorted(list({tm.group_name for tm in tms if tm.group_name}))
        return names

    def get_team_leaders(self, all_data=False):
        if all_data:
            return TeamLeader.query.order_by(TeamLeader.name).all()
        return TeamLeader.query.filter_by(is_active=True).order_by(TeamLeader.name).all()

    # ==============================================================
    # DISTRIBUTION PAGE RENDERING
    # ==============================================================

    def get_distribution_page(self, current_user):
        """Render the Distribution page with all required context."""
        try:
            # Base data from DistributionManager
            context = self.distributor.prepare_distribution_context(current_user)

            # ========================
            # 🔹 Fetch Team Managers
            # ========================
            tm_objects = TeamManager.query.order_by(TeamManager.name).all()

            # ========================
            # 🔹 Fetch Team Leaders (role-based)
            # ========================
            if current_user.has_role("admin"):
                # Admin sees all TLs
                tl_objects = TeamLeader.query.order_by(TeamLeader.name).all()

            elif current_user.has_role("tm"):
                # TM sees TLs under them
                tl_objects = TeamLeader.query.filter_by(
                    tm_name=current_user.username
                ).order_by(TeamLeader.name).all()

            elif current_user.has_role("tl"):
                # TL sees only TLs under same TM
                current_tl = TeamLeader.query.filter_by(name=current_user.username).first()
                if current_tl and current_tl.tm_name:
                    tl_objects = TeamLeader.query.filter(
                        TeamLeader.tm_name == current_tl.tm_name
                    ).order_by(TeamLeader.name).all()
                else:
                    tl_objects = [current_tl] if current_tl else []

            else:
                tl_objects = []

            # ========================
            # 🔹 Prepare structured context
            # ========================
            context["tm_data"] = [
                {"name": tm.name, "group_name": tm.group_name or "Unassigned"}
                for tm in tm_objects
            ]

            context["tl_data"] = [
                {
                    "name": tl.name,
                    "group_name": tl.group_name or "Unassigned",
                    "tm_name": tl.tm_name or "Unassigned",
                }
                for tl in tl_objects
            ]

            # ✅ FIX: Admin panel compatibility — ensures TM/TL names always appear
            context["teamManagers"] = tm_objects
            context["teamLeaders"] = tl_objects

            # ✅ Finally render the page
            return render_template("distribution.html", **context)

        except Exception as e:
            return render_template(
                "distribution.html",
                error=f"❌ Error loading distribution page: {str(e)}"
            )


    # ================= TL HANDLERS ================= #
    def handle_tl_request(self, agent, date, swap_tl, reason, current_user):
        success, message, log_message = self.distributor.create_tl_distribution_request(
            agent, date, swap_tl, reason, current_user
        )
        if success:
            self.log_service.log_activity(
                current_user.username,
                log_message
                or f"📝 TL request submitted: Agent '{agent}' on {date or 'N/A'} "
                   f"requested to swap under TL '{swap_tl}'. Reason: {reason or 'N/A'}"
            )
        return success, message

    def get_tl_agents(self, tl_name, selected_date=None):
        return self.get_agents_with_history_by_tl(tl_name, selected_date)

    def assign_tl_directly(self, agent, tl_id, date, current_user):
        success, message, log_message = self.distributor.assign_tl_directly(
            agent, tl_id, date, current_user
        )
        if success:
            self.log_service.log_activity(
                current_user.username,
                log_message
                or f"👤 Agent '{agent}' directly assigned to TL ID {tl_id} effective {date}"
            )
        return success, message

    def create_tl_assignment_request(
        self, agent, action, date, reason, swap_tl, swap_agent, current_user
    ):
        success, message, log_message = self.distributor.create_tl_assignment_request(
            agent, action, date, reason, swap_tl, swap_agent, current_user
        )
        if success:
            details = f"Action: {action}, Swap TL: {swap_tl or 'N/A'}, Swap Agent: {swap_agent or 'N/A'}"
            self.log_service.log_activity(
                current_user.username,
                log_message
                or f"📌 TL assignment request created for '{agent}' on {date or 'N/A'} - {details}. Reason: {reason or 'N/A'}"
            )
        return success, message

    # ================= TM / ADMIN HANDLERS ================= #
    def handle_admin_tm_update(self, agent, date, group, tm_name, tl_name, current_user):
        success, message, log_message = self.distributor.update_distribution_directly(
            agent, date, group, tm_name, tl_name, current_user
        )
        if success:
            self.log_service.log_activity(
                current_user.username,
                log_message
                or f"⚡ Direct distribution update by {current_user.username}: "
                   f"Agent '{agent}' assigned → TM: {tm_name or 'N/A'}, TL: {tl_name or 'N/A'}, Group: {group or 'N/A'}"
            )
        return success, message

    def handle_tm_assignment(
        self, agent, action, date, reason, replace_tl, request_tl, current_user
    ):
        success, message, log_message = self.distributor.handle_tm_assignment(
            agent, action, date, reason, replace_tl, request_tl, current_user
        )
        if success:
            self.log_service.log_activity(
                current_user.username,
                log_message
                or f"🔄 TM assignment: Agent '{agent}' | Action: {action} | "
                   f"Replace TL: {replace_tl or 'N/A'} → Request TL: {request_tl or 'N/A'} "
                   f"| Date: {date or 'N/A'} | Reason: {reason or 'N/A'}"
            )
        return success, message

    # ================= REQUEST APPROVAL ================= #
    def handle_request_decision(self, request_id, action, current_user):
        success, message, log_message = self.distributor.handle_distribution_request(
            request_id, action, current_user
        )
        if success:
            self.log_service.log_activity(
                current_user.username,
                log_message
                or f"✅ Request {action} for request ID {request_id} by {current_user.username}"
            )
        return success, message

    # ================= AGENT DESIGNATION ================= #
    def update_agent_designation(
        self,
        agent,
        date,
        designation,
        role,
        current_user,
        group_name=None,
        tm_name=None,
        tl_name=None
    ):
        try:
            success = update_agent_data(
                agent_name=agent,
                designation=designation,
                role=role,
                from_date=date,
                group_name=group_name,
                tm_name=tm_name,
                tl_name=tl_name
            )

            if success:
                log_message = (
                    f"✏️ Agent '{agent}' designation updated to '{designation}' "
                    f"with role '{role}' effective {date or 'N/A'}"
                )
                if group_name:
                    log_message += f" (assigned to group '{group_name}')"
                if tm_name and designation.lower() != "team manager":
                    log_message += f" under TM '{tm_name}'"
                if tl_name:
                    log_message += f" under TL '{tl_name}'"

                self.log_service.log_activity(current_user.username, log_message)
                return True, f"✅ {agent} updated successfully!", log_message
            else:
                return False, f"❌ No records found for {agent}", None

        except Exception as e:
            return False, f"❌ Error updating agent: {str(e)}", None

    # ================= AGENT SEARCH (SMART PREVIOUS RECORD) ================= #
    def search_agent_records(self, agent_name, selected_date=None):
        try:
            query = UpdatedCallLog.query.filter(
                UpdatedCallLog.agent_name.ilike(f"%{agent_name}%")
            )

            if selected_date:
                try:
                    date_obj = pd.to_datetime(selected_date).date()
                    query = query.filter(func.date(UpdatedCallLog.log_time) == date_obj)
                except Exception:
                    pass

                records = query.order_by(UpdatedCallLog.log_time.desc()).all()
                return {
                    "mode": "date_filter",
                    "records": [
                        {
                            "agent_name": r.agent_name,
                            "designation": r.designation,
                            "role": r.role,
                            "group_name": r.group_name,
                            "tm_name": r.tm_name,
                            "tl_name": r.tl_name,
                            "status": r.status,
                            "log_time": r.log_time.strftime("%Y-%m-%d %H:%M:%S")
                        } for r in records
                    ],
                    "dates": []
                }

            records = query.order_by(UpdatedCallLog.log_time.desc()).all()
            if not records:
                return {"mode": "default", "records": [], "dates": []}

            all_dates = sorted(
                list({r.log_time.strftime("%Y-%m-%d") for r in records}),
                reverse=True
            )

            latest_record = records[0]
            previous_record = None
            for r in records[1:]:
                if (
                    r.designation != latest_record.designation or
                    r.role != latest_record.role or
                    r.group_name != latest_record.group_name or
                    r.tm_name != latest_record.tm_name or
                    r.tl_name != latest_record.tl_name
                ):
                    previous_record = r
                    break

            final_records = [latest_record]
            if previous_record:
                final_records.append(previous_record)

            return {
                "mode": "default",
                "records": [
                    {
                        "agent_name": r.agent_name,
                        "designation": r.designation,
                        "role": r.role,
                        "group_name": r.group_name,
                        "tm_name": r.tm_name,
                        "tl_name": r.tl_name,
                        "status": r.status,
                        "log_time": r.log_time.strftime("%Y-%m-%d %H:%M:%S")
                    } for r in final_records
                ],
                "dates": all_dates
            }

        except Exception as e:
            print("❌ Error in search_agent_records:", e)
            return {"mode": "error", "records": [], "dates": []}


    def update_agent_status(self, agent_name, status, effective_date, current_user=None):
        """
        Update status on UpdatedCallLog records for agent_name from effective_date onward,
        and record an activity log entry via LogService.

        Params:
            agent_name (str): agent identifier
            status (str): new status (e.g. "Employee", "Long Leave", etc.)
            effective_date (str): "YYYY-MM-DD"
            current_user (optional): user object (if omitted, flask_login.current_user is used)

        Returns:
            (bool, str) -- success flag and message
        """

        if not agent_name or not status or not effective_date:
            return False, "⚠ Agent name, status, and effective date are required."

        # prefer explicitly passed current_user, else use flask_login's current_user if available
        actor = None
        try:
            actor = current_user.username if current_user and hasattr(current_user, "username") else None
        except Exception:
            actor = None

        if not actor:
            try:
                actor = flask_current_user.username if flask_current_user and hasattr(flask_current_user, "username") else "system"
            except Exception:
                actor = "system"

        try:
            # parse effective_date
            effective_dt = datetime.strptime(effective_date, "%Y-%m-%d")

            # perform the update; this returns number of rows updated only for some DB backends
            q = db.session.query(UpdatedCallLog).filter(
                UpdatedCallLog.agent_name == agent_name,
                UpdatedCallLog.log_time >= effective_dt
            )

            rows_updated = q.update({"status": status}, synchronize_session=False)
            db.session.commit()

            # Compose and write a log entry
            log_message = (
                f"⚙️ Status update: Agent '{agent_name}' set to '{status}' "
                f"effective from {effective_dt.date()}. "
                f"Rows affected: {rows_updated}."
            )
            try:
                # Use your LogService to persist activity (keeps consistency with other handlers)
                self.log_service.log_activity(actor, log_message)
            except Exception as log_exc:
                # If logging fails, don't break the main operation — just print for debugging
                print("⚠ Failed to write activity log:", log_exc)

            return True, f"✅ Status for {agent_name} updated to {status} from {effective_dt.date()} onwards."

        except Exception as e:
            db.session.rollback()
            err_msg = f"⚠ Error updating status: {str(e)}"
            # Optional: record failed attempt in logs
            try:
                self.log_service.log_activity(actor, f"⚠ Failed status update for '{agent_name}' to '{status}' on {effective_date}: {str(e)}")
            except Exception:
                pass
            return False, err_msg

    # ================= LATEST / HISTORY HELPERS ================= #
    def _latest_records_map(self, up_to_date=None):
        q = db.session.query(
            UpdatedCallLog.agent_name,
            func.max(UpdatedCallLog.log_time).label("latest_time")
        )
        if up_to_date:
            if isinstance(up_to_date, str):
                up_to_date = datetime.strptime(up_to_date, "%Y-%m-%d").date()
            q = q.filter(func.date(UpdatedCallLog.log_time) <= up_to_date)

        subq = q.group_by(UpdatedCallLog.agent_name).subquery()

        latest_rows = db.session.query(UpdatedCallLog).join(
            subq,
            (UpdatedCallLog.agent_name == subq.c.agent_name) &
            (UpdatedCallLog.log_time == subq.c.latest_time)
        ).all()

        return {r.agent_name: r for r in latest_rows}

    # ================= TM helpers ================= #
    def get_latest_agents_by_tm(self, tm_name, selected_date=None):
        latest_map = self._latest_records_map(up_to_date=selected_date)
        return [
            {
                "agent_name": r.agent_name,
                "designation": r.designation,
                "role": r.role,
                "group_name": r.group_name,
                "tm_name": r.tm_name,
                "tl_name": r.tl_name,
                "status": r.status,
                "log_time": r.log_time.strftime("%Y-%m-%d %H:%M:%S")
            }
            for r in latest_map.values() if r.tm_name == tm_name
        ]

    def get_agents_with_history_by_tm(self, tm_name, selected_date=None):
        latest_map = self._latest_records_map(up_to_date=selected_date)

        agent_rows = (
            db.session.query(UpdatedCallLog.agent_name)
            .filter(UpdatedCallLog.tm_name == tm_name)
            .distinct()
            .all()
        )

        results = []

        for (name,) in agent_rows:
            # Latest record for this TM
            display_rec = (
                db.session.query(UpdatedCallLog)
                .filter(
                    UpdatedCallLog.agent_name == name,
                    UpdatedCallLog.tm_name == tm_name
                )
                .order_by(UpdatedCallLog.log_time.desc())
                .first()
            )
            if not display_rec:
                continue

            latest_global = latest_map.get(name)
            moved_note = ""
            if latest_global and latest_global.tm_name != tm_name:
                moved_note = f"(Moved on {latest_global.log_time.strftime('%Y-%m-%d')} to {latest_global.tm_name})"

            # ✅ Find the most recent record before this TM
            prev_tm_rec = (
                db.session.query(UpdatedCallLog)
                .filter(
                    UpdatedCallLog.agent_name == name,
                    UpdatedCallLog.log_time < display_rec.log_time,
                    UpdatedCallLog.tm_name.isnot(None),
                    UpdatedCallLog.tm_name != tm_name
                )
                .order_by(UpdatedCallLog.log_time.desc())
                .first()
            )

            # If previous TM exists → came from there
            from_tm = prev_tm_rec.tm_name if prev_tm_rec else "N/A"

            # ✅ Get the actual first entry date in this TM (the join date)
            first_in_this_tm = (
                db.session.query(UpdatedCallLog)
                .filter(
                    UpdatedCallLog.agent_name == name,
                    UpdatedCallLog.tm_name == tm_name
                )
                .order_by(UpdatedCallLog.log_time.asc())
                .first()
            )

            if first_in_this_tm:
                joined_date = first_in_this_tm.log_time.strftime("%Y-%m-%d")
            else:
                # fallback if no specific first record found
                joined_date = display_rec.log_time.strftime("%Y-%m-%d")

            results.append({
                "agent_name": display_rec.agent_name,
                "designation": display_rec.designation,
                "role": display_rec.role,
                "group_name": display_rec.group_name,
                "tm_name": display_rec.tm_name,
                "tl_name": display_rec.tl_name,
                "status": display_rec.status,
                "log_time": display_rec.log_time.strftime("%Y-%m-%d %H:%M:%S"),
                "moved_note": moved_note,
                "from_tm": from_tm,
                "joined_date": joined_date
            })

        results.sort(key=lambda x: x["agent_name"].lower())
        return results


    # ================= GROUP helpers ================= #
    def get_latest_agents_by_group(self, group_name, selected_date=None):
        latest_map = self._latest_records_map(up_to_date=selected_date)
        return [
            {
                "agent_name": r.agent_name,
                "designation": r.designation,
                "role": r.role,
                "group_name": r.group_name,
                "tm_name": r.tm_name,
                "tl_name": r.tl_name,
                "status": r.status,
                "log_time": r.log_time.strftime("%Y-%m-%d %H:%M:%S")
            }
            for r in latest_map.values() if r.group_name == group_name
        ]

    # ================= GROUP helpers ================= #
    def get_agents_with_history_by_group(self, group_name, selected_date=None):
        latest_map = self._latest_records_map(up_to_date=selected_date)

        agent_rows = (
            db.session.query(UpdatedCallLog.agent_name)
            .filter(UpdatedCallLog.group_name == group_name)
            .distinct()
            .all()
        )

        results = []

        for (name,) in agent_rows:
            # Latest record for this group
            display_rec = (
                db.session.query(UpdatedCallLog)
                .filter(
                    UpdatedCallLog.agent_name == name,
                    UpdatedCallLog.group_name == group_name
                )
                .order_by(UpdatedCallLog.log_time.desc())
               .first()
            )
            if not display_rec:
                continue

            latest_global = latest_map.get(name)
            moved_note = ""
            if latest_global and latest_global.group_name != group_name:
                moved_note = f"(Moved on {latest_global.log_time.strftime('%Y-%m-%d')} to {latest_global.group_name})"

            # ✅ Find the most recent record before this group (to detect from where the agent came)
            prev_group_rec = (
                db.session.query(UpdatedCallLog)
                .filter(
                    UpdatedCallLog.agent_name == name,
                    UpdatedCallLog.log_time < display_rec.log_time,
                    UpdatedCallLog.group_name.isnot(None),
                    UpdatedCallLog.group_name != group_name
                )
                .order_by(UpdatedCallLog.log_time.desc())
                .first()
            )

            # ✅ Set 'from' group
            from_group = prev_group_rec.group_name if prev_group_rec else "N/A"

            # ✅ Get actual first join date in this group
            first_in_this_group = (
                db.session.query(UpdatedCallLog)
                .filter(
                    UpdatedCallLog.agent_name == name,
                    UpdatedCallLog.group_name == group_name
                )
                .order_by(UpdatedCallLog.log_time.asc())
                .first()
            )

            joined_date = (
                first_in_this_group.log_time.strftime("%Y-%m-%d")
                if first_in_this_group
                else display_rec.log_time.strftime("%Y-%m-%d")
            )

            results.append({
                "agent_name": display_rec.agent_name,
                "designation": display_rec.designation,
                "role": display_rec.role,
                "group_name": display_rec.group_name,
                "tm_name": display_rec.tm_name,
                "tl_name": display_rec.tl_name,
                "status": display_rec.status,
                "log_time": display_rec.log_time.strftime("%Y-%m-%d %H:%M:%S"),
                "moved_note": moved_note,
                "from_group": from_group,
                "joined_date": joined_date
            })

        results.sort(key=lambda x: x["agent_name"].lower())
        return results

    # ================= TL helpers ================= #
    def get_latest_agents_by_tl(self, tl_name, selected_date=None):
        latest_map = self._latest_records_map(up_to_date=selected_date)
        return [
            {
                "agent_name": r.agent_name,
                "designation": r.designation,
                "role": r.role,
                "group_name": r.group_name,
                "tm_name": r.tm_name,
                "tl_name": r.tl_name,
                "status": r.status,
               "log_time": r.log_time.strftime("%Y-%m-%d %H:%M:%S")
            }
            for r in latest_map.values() if r.tl_name == tl_name
        ]


    def get_agents_with_history_by_tl(self, tl_name, selected_date=None):
        latest_map = self._latest_records_map(up_to_date=selected_date)

        agent_rows = (
            db.session.query(UpdatedCallLog.agent_name)
            .filter(UpdatedCallLog.tl_name == tl_name)
            .distinct()
            .all()
        )

        results = []

        for (name,) in agent_rows:
            # 🔹 Get the latest record for this TL
            display_rec = (
                db.session.query(UpdatedCallLog)
                .filter(
                    UpdatedCallLog.agent_name == name,
                    UpdatedCallLog.tl_name == tl_name
                )
                .order_by(UpdatedCallLog.log_time.desc())
                .first()
            )
            if not display_rec:
                continue

            latest_global = latest_map.get(name)
            moved_note = ""
            if latest_global and latest_global.tl_name != tl_name:
                moved_note = f"(Moved on {latest_global.log_time.strftime('%Y-%m-%d')} to {latest_global.tl_name})"

            # 🔹 Find previous record (different TL)
            prev_tl_rec = (
                db.session.query(UpdatedCallLog)
                .filter(
                    UpdatedCallLog.agent_name == name,
                    UpdatedCallLog.log_time < display_rec.log_time,
                    UpdatedCallLog.tl_name.isnot(None),
                    UpdatedCallLog.tl_name != tl_name
                )
                .order_by(UpdatedCallLog.log_time.desc())
                .first()
            )

            # ✅ Determine "From TL"
            from_tl = prev_tl_rec.tl_name if prev_tl_rec else "N/A"

            # ✅ Get the first time this agent joined this TL (actual join date)
            first_in_this_tl = (
                db.session.query(UpdatedCallLog)
                .filter(
                    UpdatedCallLog.agent_name == name,
                    UpdatedCallLog.tl_name == tl_name
                )
                .order_by(UpdatedCallLog.log_time.asc())
                .first()
            )

            joined_date = (
                first_in_this_tl.log_time.strftime("%Y-%m-%d")
                if first_in_this_tl
                else display_rec.log_time.strftime("%Y-%m-%d")
            )

            results.append({
                "agent_name": display_rec.agent_name,
                "designation": display_rec.designation,
                "role": display_rec.role,
                "group_name": display_rec.group_name,
                "tm_name": display_rec.tm_name,
                "tl_name": display_rec.tl_name,
                "status": display_rec.status,
                "log_time": display_rec.log_time.strftime("%Y-%m-%d %H:%M:%S"),
                "moved_note": moved_note,
                "from_tl": from_tl,
               "joined_date": joined_date
            })

        results.sort(key=lambda x: x["agent_name"].lower())
        return results
