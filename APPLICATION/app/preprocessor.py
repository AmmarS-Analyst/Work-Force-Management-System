import pandas as pd
from app import db
from app.models import RawCallLog, UpdatedCallLog

DEFAULT_DESIGNATION = "Agent"

def clean_agent_name(name: str) -> str:
    return name.replace("-P", "").strip()

def detect_role(name: str) -> str:
    return "Part timer" if "-P" in name else "Full timer"

def process_dataframe(df: pd.DataFrame, source_filename: str):
    """Process a single raw dataframe and insert directly into DB"""
    
    if 'Agent name' not in df.columns or 'Log Time' not in df.columns:
        print(f"[Processor] ❌ Skipped '{source_filename}' (missing columns)")
        return
    
    df['Agent name'] = df['Agent name'].astype(str)
    df['Role'] = df['Agent name'].apply(detect_role)
    df['Agent name'] = df['Agent name'].apply(clean_agent_name)
    df['Designation'] = DEFAULT_DESIGNATION
    df['Group Name'] = ''
    df['TM Name'] = ''
    df['Source File'] = source_filename
    df['Log Time'] = pd.to_datetime(df['Log Time'], errors='coerce')
    df.dropna(subset=['Log Time'], inplace=True)
    
    # Insert into RawCallLog
    raw_records = [
        RawCallLog(
            agent_name=row['Agent name'],
            profile_id=row.get('Profile ID', ''),
            call_log_id=row.get('Call Log ID', ''),
            log_time=row['Log Time'],
            log_type=row.get('Log Type', ''),
            state=row.get('State', ''),
            call_type=row.get('Call type', ''),
            original_campaign=row.get('Original campaign', ''),
            current_campaign=row.get('Current campaign', ''),
            ember=row.get('Ember', ''),
            source_file=source_filename
        )
        for _, row in df.iterrows()
    ]
    db.session.bulk_save_objects(raw_records)
    
    # Insert into UpdatedCallLog (example: with minimal processing)
    updated_records = [
        UpdatedCallLog(
            agent_name=row['Agent name'],
            profile_id=row.get('Profile ID', ''),
            call_log_id=row.get('Call Log ID', ''),
            log_time=row['Log Time'],
            log_type=row.get('Log Type', ''),
            state=row.get('State', ''),
            call_type=row.get('Call type', ''),
            original_campaign=row.get('Original campaign', ''),
            current_campaign=row.get('Current campaign', ''),
            ember=row.get('Ember', ''),
            designation=row['Designation'],
            role=row['Role'],
            group_name=row['Group Name'],
            tm_name=row['TM Name'],
            source_file=source_filename
        )
        for _, row in df.iterrows()
    ]
    db.session.bulk_save_objects(updated_records)
    
    db.session.commit()
    print(f"[Processor] ✅ Inserted {len(df)} records from '{source_filename}'")
