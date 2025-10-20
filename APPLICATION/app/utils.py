"""
Utility functions for the Agent Management System.
See DOCUMENTATION.txt for detailed function descriptions.
"""

import re
from werkzeug.security import generate_password_hash
from app.models import ActivityLog, DeleteRequest, db
from datetime import datetime
from flask import current_app


def hash_password(password):
    """Hash password using Werkzeug's secure hashing"""
    return generate_password_hash(password)


def normalize_name(name):
    """Normalize name to title case"""
    return name.strip().title() if name else ""


def clean_agent_name(raw_name: str):
    """
    Clean agent names by removing:
    - Text inside parentheses e.g. (deleted), (temp)
    - '-P', '_P', or ' P' suffix for part-timers (case-insensitive)
    - Extra spaces, underscores, hyphens

    Detect role:
        - 'Part-Timer' if any marker found (-P, _P, space P)
        - 'Full-Timer' otherwise

    Examples:
    - 'Abshamyawer-P (deleted)' -> ('Abshamyawer', 'Part-Timer')
    - 'John Doe-P'              -> ('John Doe', 'Part-Timer')
    - 'Sajad_p'                 -> ('Sajad', 'Part-Timer')
    - 'usman'                   -> ('Usman', 'Full-Timer')
    - 'Hamza (temp)'            -> ('Hamza', 'Full-Timer')
    """
    if not raw_name:
        return "", "Full-Timer"

    name = str(raw_name).strip()

    # Remove anything inside parentheses e.g. (deleted), (temp)
    name = re.sub(r"\(.*?\)", "", name, flags=re.IGNORECASE).strip()

    role = "Full-Timer"

    # Detect part-timer markers (-P, _P, or ' P' at end)
    if re.search(r"(-P|_P|\sP)$", name, re.IGNORECASE):
        role = "Part-Timer"
        # Remove those markers
        name = re.sub(r"(-P|_P|\sP)$", "", name, flags=re.IGNORECASE)

    # Cleanup: remove trailing underscores, hyphens, spaces
    name = re.sub(r"[-_\s]+$", "", name).strip()

    # Normalize case (title case)
    name = name.title()

    return name, role


def detect_role(name):
    """Detect if agent is part-time or full-time based on '-P' marker"""
    return "Part-Timer" if name and "-P" in name else "Full-Timer"


def log_activity(user, message):
    """Log activity to both memory and database"""
    # In-memory log for frontend
    if not hasattr(current_app, "activity_logs"):
        current_app.activity_logs = []
    current_app.activity_logs.append({
        "user": user,
        "msg": message,
        "date": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    })

    # Database log for persistence
    db_log = ActivityLog(user=user, msg=message)
    db.session.add(db_log)
    db.session.commit()


def get_pending_delete_requests():
    """Fetch all pending delete requests"""
    return DeleteRequest.query.filter_by(status='pending').all()
