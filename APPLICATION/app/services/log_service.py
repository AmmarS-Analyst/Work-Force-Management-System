"""
Activity logging service for the Agent Management System.
See DOCUMENTATION.txt for detailed service descriptions.
"""

from datetime import datetime
from flask import current_app


class LogService:
    """Service layer for activity log operations - ADMIN ONLY"""

    def log_activity(self, username, message):
        """Create a new activity log entry"""
        from app import db
        from app.models import ActivityLog

        try:
            log_entry = ActivityLog(
                user=username,
                msg=message,
                date=datetime.utcnow()
            )
            db.session.add(log_entry)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Failed to log activity: {str(e)}")
            return False

    def get_logs(self, filters=None):
        """Retrieve activity logs with optional filtering - ADMIN ONLY"""
        from app import db
        from app.models import ActivityLog

        try:
            query = ActivityLog.query.order_by(ActivityLog.date.desc())

            if filters:
                if filters.get("date"):
                    query = query.filter(db.func.date(ActivityLog.date) == filters["date"])
                if filters.get("user"):
                    query = query.filter(ActivityLog.user == filters["user"])
                if filters.get("search"):
                    search_term = f"%{filters['search']}%"
                    query = query.filter(ActivityLog.msg.ilike(search_term))

            return query.all()
        except Exception as e:
            current_app.logger.error(f"Failed to retrieve logs: {str(e)}")
            return []

    def get_available_dates(self):
        """Get distinct dates from activity logs - ADMIN ONLY"""
        from app import db
        from app.models import ActivityLog

        try:
            dates = (
                db.session.query(db.func.date(ActivityLog.date).label("log_date"))
                .distinct()
                .order_by(db.func.date(ActivityLog.date).desc())
                .all()
            )

            return [date.log_date.strftime("%Y-%m-%d") for date in dates if date.log_date]
        except Exception as e:
            current_app.logger.error(f"Failed to get available dates: {str(e)}")
            return []

    def get_available_users(self):
        """Get distinct users from activity logs - ADMIN ONLY"""
        from app.models import ActivityLog

        try:
            users = (
                ActivityLog.query.with_entities(ActivityLog.user)
                .distinct()
                .order_by(ActivityLog.user)
                .all()
            )
            return [user[0] for user in users if user[0]]
        except Exception as e:
            current_app.logger.error(f"Failed to get available users: {str(e)}")
            return []

    def prepare_logs_context(self, current_user, selected_date=None, selected_user=None):
        """Prepare context data for logs page - ADMIN ONLY ACCESS"""

        from app import db
        from app.models import User, Role, TeamManager, TeamLeader, Agent, DeleteRequest

        # Access check
        if not current_user.has_role("admin"):
            return {
                "error": "Access denied. Administrator role required to view activity logs.",
                "logs": [],
                "dates": [],
                "users": [],
                "selected_date": selected_date,
                "selected_user": selected_user,
                "access_denied": True,
            }

        filters = {}
        if selected_date:
            filters["date"] = selected_date
        if selected_user:
            filters["user"] = selected_user

        logs = self.get_logs(filters)

        # Format logs
        formatted_logs = [
            {
                "msg": log.msg,
                "user": log.user,
                "date": log.date.strftime("%Y-%m-%d %H:%M:%S"),
            }
            for log in logs
        ]

        # Include runtime logs (in-memory)
        formatted_logs.extend(getattr(current_app, "activity_logs", []))

        # Apply filters again
        if selected_date:
            formatted_logs = [
                log for log in formatted_logs if log["date"].startswith(selected_date)
            ]
        if selected_user:
            formatted_logs = [
                log for log in formatted_logs if log["user"] == selected_user
            ]

        # ✅ Include admin panel context here also
        return {
            "logs": formatted_logs,
            "dates": self.get_available_dates(),
            "users": self.get_available_users(),
            "selected_date": selected_date,
            "selected_user": selected_user,
            "access_denied": False,

            # Admin panel variables
            "users_admin": User.query.options(db.joinedload(User.roles)).all(),
            "roles": Role.query.order_by(Role.name).all(),
            "teamManagers": TeamManager.query.order_by(TeamManager.name).all(),
            "teamLeaders": TeamLeader.query.order_by(TeamLeader.name).all(),
            "agents": Agent.query.order_by(Agent.name).all(),
            "pending_requests": DeleteRequest.query.filter_by(status="pending")
            .order_by(DeleteRequest.created_at.desc())
            .all(),
        }

    def admin_required(self, current_user):
        """Check if current user has admin role"""
        return current_user.has_role("admin")

    def get_log_statistics(self, current_user):
        """Get log statistics - ADMIN ONLY"""
        from app import db
        from app.models import ActivityLog

        if not self.admin_required(current_user):
            return {}

        try:
            total_logs = ActivityLog.query.count()
            today = datetime.utcnow().date()
            today_logs = (
                ActivityLog.query.filter(db.func.date(ActivityLog.date) == today).count()
            )

            # Get most active users
            active_users = (
                db.session.query(
                    ActivityLog.user, db.func.count(ActivityLog.id).label("log_count")
                )
                .group_by(ActivityLog.user)
                .order_by(db.func.count(ActivityLog.id).desc())
                .limit(5)
                .all()
            )

            return {
                "total_logs": total_logs,
                "today_logs": today_logs,
                "active_users": [
                    {"user": user, "count": count} for user, count in active_users
                ],
            }
        except Exception as e:
            current_app.logger.error(f"Failed to get log statistics: {str(e)}")
            return {}
