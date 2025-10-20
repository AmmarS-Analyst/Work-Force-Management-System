import pandas as pd
from datetime import datetime
from app import db
from app.models import UpdatedCallLog, Agent, TeamManager, TeamLeader, ActivityLog


def update_agent_data(agent_name, designation=None, role=None, from_date=None, group_name=None,
                      tm_name=None, tl_name=None, updated_by="System"):
    """
    Update agent data in all relevant tables (UpdatedCallLog, Agent, TeamManager/Leader).
    Handles edge cases for promoting agent to TL, preserving existing group/TM unless overridden.
    Also ensures TeamLeader table is updated when TM/group are assigned AFTER TL creation.
    Additionally logs all updates to ActivityLog.
    """
    from_date_dt = pd.to_datetime(from_date, errors="coerce") if from_date else None

    # === 1) Get all affected UpdatedCallLog records ===
    query = UpdatedCallLog.query.filter(UpdatedCallLog.agent_name == agent_name)
    if from_date_dt:
        query = query.filter(UpdatedCallLog.log_time >= from_date_dt)
    records = query.all()
    if not records:
        print(f"[Updater] ⚠️ No matching records found for agent: {agent_name}")
        return False

    # === 2) Pull latest UpdatedCallLog for fallback ===
    latest_log = (
        UpdatedCallLog.query.filter_by(agent_name=agent_name)
        .order_by(UpdatedCallLog.log_time.desc())
        .first()
    )

    # Use existing values if new ones are not provided
    final_group = group_name or (latest_log.group_name if latest_log and latest_log.group_name else "Unassigned")
    final_tm_name = tm_name or (latest_log.tm_name if latest_log and latest_log.tm_name else "Unassigned")

    # === 3) Update UpdatedCallLog rows ===
    for rec in records:
        if designation:
            rec.designation = designation
            if designation.lower() == "team manager":
                rec.tm_name = "Self"
                rec.tl_name = "N/A"
                rec.group_name = final_group
            elif designation.lower() == "team leader":
                rec.tl_name = "Self"
                rec.group_name = final_group
                rec.tm_name = final_tm_name

        if role:
            rec.role = role
        if group_name:
            rec.group_name = group_name
        if tm_name:
            rec.tm_name = tm_name
        if tl_name:
            rec.tl_name = tl_name

    # === 4) Update Agent table ===
    agent = Agent.query.filter_by(name=agent_name).first()
    if agent:
        if designation:
            agent.designation = designation
        if role:
            agent.role = role
        agent.group_name = group_name if group_name is not None else final_group
        agent.tm_name = tm_name if tm_name is not None else final_tm_name

    # === 5) Maintain Team Manager / Team Leader tables ===
    if designation:
        if designation.lower() == "team manager":
            tm = TeamManager.query.filter_by(name=agent_name).first()
            if not tm:
                tm = TeamManager(
                    name=agent_name,
                    group_name=final_group,
                    is_active=True,
                    created_date=datetime.utcnow(),
                )
                db.session.add(tm)
            else:
                tm.group_name = final_group
                tm.is_active = True

        elif designation.lower() == "team leader":
            tm_obj = None
            if final_tm_name and final_tm_name != "Unassigned":
                tm_obj = TeamManager.query.filter_by(name=final_tm_name).first()
                if not tm_obj:
                    tm_obj = TeamManager(
                        name=final_tm_name,
                        group_name=final_group,
                        is_active=True,
                        created_date=datetime.utcnow(),
                    )
                    db.session.add(tm_obj)
                    db.session.flush()
            tm_id_val = tm_obj.id if tm_obj else None

            tl = TeamLeader.query.filter_by(name=agent_name).first()
            if not tl:
                tl = TeamLeader(
                    name=agent_name,
                    tm_name=final_tm_name,
                    group_name=final_group,
                    tm_id=tm_id_val,
                    is_active=True,
                    created_date=datetime.utcnow(),
                )
                db.session.add(tl)
            else:
                tl.group_name = final_group
                tl.tm_name = final_tm_name
                tl.tm_id = tm_id_val
                tl.is_active = True
                if tl_name:
                    for rec in records:
                        rec.tl_name = tl_name

    # === 6) EXTRA SYNC: Update existing TL if TM/group later assigned ===
    existing_tl = TeamLeader.query.filter_by(name=agent_name).first()
    if existing_tl:
        need_update = False
        new_group_for_tl = existing_tl.group_name
        new_tm_name_for_tl = existing_tl.tm_name
        new_tm_id_for_tl = existing_tl.tm_id

        if group_name:
            new_group_for_tl = group_name
            need_update = True
        elif (existing_tl.group_name in (None, "", "Unassigned")) and (latest_log and latest_log.group_name):
            new_group_for_tl = latest_log.group_name
            need_update = True

        if tm_name:
            new_tm_name_for_tl = tm_name
            need_update = True
        elif (existing_tl.tm_name in (None, "", "Unassigned")) and (latest_log and latest_log.tm_name):
            new_tm_name_for_tl = latest_log.tm_name
            need_update = True

        if new_tm_name_for_tl and new_tm_name_for_tl != "Unassigned":
            tm_obj = TeamManager.query.filter_by(name=new_tm_name_for_tl).first()
            if not tm_obj:
                tm_obj = TeamManager(
                    name=new_tm_name_for_tl,
                    group_name=new_group_for_tl or "Unassigned",
                    is_active=True,
                    created_date=datetime.utcnow(),
                )
                db.session.add(tm_obj)
                db.session.flush()
            new_tm_id_for_tl = tm_obj.id
            need_update = True

        if need_update:
            existing_tl.group_name = new_group_for_tl or existing_tl.group_name
            existing_tl.tm_name = new_tm_name_for_tl or existing_tl.tm_name
            existing_tl.tm_id = new_tm_id_for_tl or existing_tl.tm_id
            existing_tl.is_active = True

    # === 7) Commit all DB updates ===
    db.session.commit()
    print(f"[Updater] ✅ Updated {len(records)} rows for agent: {agent_name} + synced to Agent/TM/TL tables")

    # === 8) Log the update in ActivityLog ===
    try:
        log_entry = ActivityLog(
            user=updated_by,
            msg=(
                f"🔄 Agent '{agent_name}' updated — "
                f"Designation: {designation or '-'}, "
                f"Role: {role or '-'}, "
                f"Group: {group_name or '-'}, "
                f"TM: {tm_name or '-'}, "
                f"TL: {tl_name or '-'}"
            ),
            date=datetime.utcnow()
        )
        db.session.add(log_entry)
        db.session.commit()
        print(f"[Updater] 🪵 Activity logged for {agent_name} by {updated_by}")
    except Exception as log_err:
        print(f"[Updater] ⚠️ Failed to log activity: {log_err}")

    return True
