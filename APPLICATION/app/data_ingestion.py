# """
# High-performance CSV data ingestion for the Agent Management System.
# See DOCUMENTATION.txt for detailed data processing descriptions.
# """

# import pandas as pd
# from datetime import datetime
# import io
# import csv
# from sqlalchemy import text
# from app.models import TeamLeader
# from app.config import Config
# from app.utils import clean_agent_name


# class DataIngestionManager:
#     """OOP class for extreme speed CSV ingestion with hierarchy + status preservation"""
    
#     def __init__(self):
#         pass
    
#     def ingest_csv(self, file_path, source_filename, date_range=None):
#         """
#         REAL EXTREME SPEED CSV ingestion - Targeting 5,000+ rows/second
#         Preserves agent status + hierarchy and syncs AgentInfo
#         """
#         from app import db
        
#         try:
#             start_time = datetime.now()
            
#             # Step 1: Load CSV fast
#             df = pd.read_csv(
#                 file_path, 
#                 low_memory=False,
#                 encoding="utf-8-sig",   # ✅ Fix BOM/encoding issues
#                 dtype={col: 'string' for col in [
#                     'Agent name', 'Profile ID', 'Call Log ID', 'Log Type', 
#                     'State', 'Call type', 'Original campaign', 'Current campaign', 'Ember'
#                 ]},
#                 engine='c'
#             )
#             total_rows = len(df)

#             # Validate required columns
#             required_columns = [
#                 'Agent name', 'Profile ID', 'Call Log ID', 'Log Time',
#                 'Log Type', 'State', 'Call type', 'Original campaign',
#                 'Current campaign', 'Ember'
#             ]
#             missing_columns = set(required_columns) - set(df.columns)
#             if missing_columns:
#                 raise ValueError(f"CSV missing required columns: {missing_columns}")

#             # Step 2: Normalize data
#             for col in required_columns:
#                 if col in df.columns:
#                     df[col] = df[col].astype('string').str.strip()
            
#             df['Log Time'] = pd.to_datetime(df['Log Time'], errors='coerce')
#             df['Cleaned Name'] = df['Agent name'].str.replace(r'-[Pp]$', '', regex=True).str.strip()
            
#             # Step 3: Get previous records WITH DATE CONTEXT (includes status)
#             unique_agents = df['Cleaned Name'].unique().tolist()
            
#             file_min_date = df['Log Time'].min()
#             previous_records = self._fetch_previous_records_with_date_context(
#                 unique_agents, file_min_date, db
#             )
            
#             # Step 4: Ultra-fast COPY inserts
#             raw_conn = db.engine.raw_connection()
#             try:
#                 with raw_conn.cursor() as cursor:
#                     # Disable triggers for speed
#                     try:
#                         cursor.execute("ALTER TABLE raw_call_logs DISABLE TRIGGER ALL;")
#                         cursor.execute("ALTER TABLE updated_call_logs DISABLE TRIGGER ALL;")
#                         print("✅ Triggers disabled")
#                     except Exception as trigger_error:
#                         print(f"⚠ Could not disable triggers: {trigger_error}")
                    
#                     # Insert raw data
#                     print("➡ Inserting raw_call_logs...")
#                     raw_csv_data = self._create_raw_csv_data(df, source_filename)
#                     self._insert_raw_copy(cursor, raw_csv_data)
#                     print(f"✅ Raw data inserted: {len(df):,} rows")
                    
#                     # Insert updated data
#                     print("➡ Inserting updated_call_logs...")
#                     updated_csv_data = self._create_updated_csv_data(df, source_filename, previous_records)
#                     self._insert_updated_copy(cursor, updated_csv_data)
#                     print(f"✅ Updated data inserted: {len(df):,} rows")
                    
#                     # Re-enable triggers
#                     try:
#                         cursor.execute("ALTER TABLE raw_call_logs ENABLE TRIGGER ALL;")
#                         cursor.execute("ALTER TABLE updated_call_logs ENABLE TRIGGER ALL;")
#                         print("✅ Triggers re-enabled")
#                     except Exception as trigger_error:
#                         print(f"⚠ Could not re-enable triggers: {trigger_error}")
                
#                 raw_conn.commit()
                
#             finally:
#                 raw_conn.close()
            
#             # Step 5: Preserve TL info
#             self._preserve_team_leader_info()
            
#             # Step 6: Update AgentInfo table (SYNC HERE)
#             self._update_agent_info()
            
#             elapsed = (datetime.now() - start_time).total_seconds()
#             print(f"🚀 Ingestion completed in {elapsed:.2f} seconds")
#             return True

#         except Exception as e:
#             # Ensure proper cleanup on error
#             try:
#                 raw_conn = db.engine.raw_connection()
#                 with raw_conn.cursor() as cursor:
#                     cursor.execute("ALTER TABLE raw_call_logs ENABLE TRIGGER ALL;")
#                     cursor.execute("ALTER TABLE updated_call_logs ENABLE TRIGGER ALL;")
#                 raw_conn.commit()
#                 raw_conn.close()
#             except:
#                 pass
            
#             db.session.rollback()
#             raise ValueError(f"Failed to ingest CSV: {str(e)}")

#     # -------------------- AgentInfo Sync --------------------
#     def _update_agent_info(self):
#         """Sync AgentInfo with updated_call_logs whenever hierarchy info changes"""
#         from app import db
#         from app.models import UpdatedCallLog, AgentInfo
#         from datetime import datetime

#         try:
#             latest_agents = db.session.query(
#                 UpdatedCallLog.agent_name,
#                 UpdatedCallLog.tm_name,
#                 UpdatedCallLog.tl_name,
#                 UpdatedCallLog.group_name
#             ).distinct().all()

#             new_count = 0
#             updated_count = 0

#             for agent_name, tm_name, tl_name, group_name in latest_agents:
#                 existing = AgentInfo.query.filter_by(agent_name=agent_name).first()
#                 now = datetime.utcnow()

#                 if not existing:
#                     # Insert new agent
#                     db.session.add(AgentInfo(
#                         agent_name=agent_name,
#                         tm_name=tm_name,
#                         tl_name=tl_name,
#                         group_name=group_name,
#                         updated_at=now
#                     ))
#                     new_count += 1
#                 else:
#                     # Update only if any info changed
#                     has_changes = False
#                     if existing.tm_name != tm_name:
#                         existing.tm_name = tm_name
#                         has_changes = True
#                     if existing.tl_name != tl_name:
#                         existing.tl_name = tl_name
#                         has_changes = True
#                     if existing.group_name != group_name:
#                         existing.group_name = group_name
#                         has_changes = True
#                     if has_changes:
#                         existing.updated_at = now
#                         updated_count += 1

#             db.session.commit()
#             print(f"✅ AgentInfo synced. {new_count} new agents added, {updated_count} agents updated.")
#         except Exception as e:
#             db.session.rollback()
#             print(f"⚠ Failed to update AgentInfo: {e}")

#     # -------------------- Fetching Previous Records --------------------
#     def _fetch_previous_records_with_date_context(self, unique_agents, current_file_min_date, db):
#         """Fetch previous records (with status preserved)"""
#         if not unique_agents or current_file_min_date is None:
#             return {}
        
#         previous_records = {}
        
#         try:
#             if isinstance(current_file_min_date, pd.Timestamp):
#                 current_file_min_date = current_file_min_date.to_pydatetime()
            
#             batch_size = 500
#             for i in range(0, len(unique_agents), batch_size):
#                 batch_agents = unique_agents[i:i + batch_size]
                
#                 query = text("""
#                     SELECT agent_name, designation, role, group_name, tm_name, tl_name, status, log_time
#                     FROM updated_call_logs 
#                     WHERE agent_name IN :agents
#                     AND log_time < :cutoff_date
#                     ORDER BY log_time DESC
#                 """)
                
#                 agents_tuple = tuple(batch_agents)
                
#                 result = db.session.execute(query, {
#                     'agents': agents_tuple,
#                     'cutoff_date': current_file_min_date
#                 }).fetchall()
                
#                 for row in result:
#                     agent_name = row[0]
#                     if agent_name not in previous_records:
#                         previous_records[agent_name] = {
#                             'designation': row[1] or 'Agent',
#                             'role': row[2] or 'Full-Timer',
#                             'group_name': row[3] or '',
#                             'tm_name': row[4] or '',
#                             'tl_name': row[5] or '',
#                             'status': row[6] or 'Employee',
#                             'last_seen': row[7]
#                         }
                        
#         except Exception as e:
#             print(f"❌ Error fetching previous records: {e}")
#             previous_records = self._fetch_previous_records_simple(unique_agents, db)
        
#         return previous_records
    
#     def _fetch_previous_records_simple(self, unique_agents, db):
#         """Fallback fetch (includes status)"""
#         if not unique_agents:
#             return {}
        
#         previous_records = {}
        
#         try:
#             batch_size = 1000
#             for i in range(0, len(unique_agents), batch_size):
#                 batch_agents = unique_agents[i:i + batch_size]
                
#                 query = text("""
#                     SELECT DISTINCT ON (agent_name) 
#                         agent_name, 
#                         COALESCE(designation, 'Agent') as designation,
#                         COALESCE(role, 'Full-Timer') as role,
#                         COALESCE(group_name, '') as group_name,
#                         COALESCE(tm_name, '') as tm_name,
#                         COALESCE(tl_name, '') as tl_name,
#                         COALESCE(status, 'Employee') as status
#                     FROM updated_call_logs 
#                     WHERE agent_name = ANY(:agents)
#                     ORDER BY agent_name, log_time DESC
#                 """)
                
#                 result = db.session.execute(query, {'agents': batch_agents})
                
#                 for row in result:
#                     previous_records[row['agent_name']] = {
#                         'designation': row['designation'],
#                         'role': row['role'],
#                         'group_name': row['group_name'],
#                         'tm_name': row['tm_name'],
#                         'tl_name': row['tl_name'],
#                         'status': row['status']
#                     }
                    
#         except Exception as e:
#             print(f"⚠ Could not fetch some previous records: {e}")
        
#         return previous_records

#     # -------------------- CSV Builders --------------------
#     def _create_raw_csv_data(self, df, source_filename):
#         """Create CSV data for raw_call_logs"""
#         output = io.StringIO()
#         writer = csv.writer(output)
        
#         rows_processed = 0
#         for _, row in df.iterrows():
#             log_time = row['Log Time'].isoformat() if pd.notnull(row['Log Time']) else ""
#             writer.writerow([
#                 str(row['Agent name']).strip(),
#                 str(row['Profile ID']).strip(),
#                 str(row['Call Log ID']).strip(),
#                 log_time,
#                 str(row['Log Type']).strip(),
#                 str(row['State']).strip(),
#                 str(row['Call type']).strip(),
#                 str(row['Original campaign']).strip(),
#                 str(row['Current campaign']).strip(),
#                 str(row['Ember']).strip(),
#                 source_filename
#             ])
#             rows_processed += 1
#             if rows_processed % 50000 == 0:
#                 print(f"   Processed {rows_processed:,} raw rows...")
        
#         output.seek(0)
#         return output

#     def _create_updated_csv_data(self, df, source_filename, previous_records):
#         """Create CSV data for updated_call_logs with hierarchy + status preservation"""
#         output = io.StringIO()
#         writer = csv.writer(output)

#         rows_processed = 0
#         part_timer_count = 0

#         for _, row in df.iterrows():
#             raw_name = str(row['Agent name']).strip()
#             agent, role = clean_agent_name(raw_name)
#             if role == "Part-Timer":
#                 part_timer_count += 1

#             prev_data = previous_records.get(agent, {})
#             log_time = row['Log Time'].isoformat() if pd.notnull(row['Log Time']) else ""

#             # Hierarchy info
#             team_leader = TeamLeader.query.filter_by(name=agent).first()
#             if team_leader:
#                 designation = "TL"
#                 tl_name = "Self"
#                 tm_name = team_leader.tm_name or prev_data.get('tm_name', '')
#                 group_name = team_leader.group_name or prev_data.get('group_name', '')
#             else:
#                 designation = prev_data.get('designation', Config.DEFAULT_DESIGNATION)
#                 tl_name = prev_data.get('tl_name', '')
#                 tm_name = prev_data.get('tm_name', '')
#                 group_name = prev_data.get('group_name', '')
#                 if designation == "TL":
#                     tl_name = "Self"
#                 elif designation == Config.DEFAULT_DESIGNATION:
#                     tl_name = prev_data.get('tl_name', '')
#                 elif designation == "TM":
#                     tl_name = ""

#             status = prev_data.get('status', 'Employee')

#             writer.writerow([
#                 agent,
#                 str(row['Profile ID']).strip(),
#                 str(row['Call Log ID']).strip(),
#                 log_time,
#                 str(row['Log Type']).strip(),
#                 str(row['State']).strip(),
#                 str(row['Call type']).strip(),
#                 str(row['Original campaign']).strip(),
#                 str(row['Current campaign']).strip(),
#                 str(row['Ember']).strip(),
#                 designation,
#                 role,
#                 group_name,
#                 tm_name,
#                 tl_name,
#                 source_filename,
#                 status
#             ])

#             rows_processed += 1
#             if rows_processed % 50000 == 0:
#                 print(f"   Processed {rows_processed:,} updated rows...")

#         print(f"   Detected {part_timer_count} part-timer records")
#         output.seek(0)
#         return output

#     # -------------------- COPY to DB --------------------
#     def _insert_raw_copy(self, cursor, csv_data):
#         cursor.copy_expert("""
#             COPY raw_call_logs (agent_name, profile_id, call_log_id, log_time, 
#                               log_type, state, call_type, original_campaign, 
#                               current_campaign, ember, source_file) 
#             FROM STDIN WITH (FORMAT CSV)
#         """, csv_data)
    
#     def _insert_updated_copy(self, cursor, csv_data):
#         cursor.copy_expert("""
#             COPY updated_call_logs (agent_name, profile_id, call_log_id, log_time, 
#                                   log_type, state, call_type, original_campaign, 
#                                   current_campaign, ember, designation, role, 
#                                   group_name, tm_name, tl_name, source_file, status) 
#             FROM STDIN WITH (FORMAT CSV)
#         """, csv_data)

#     # -------------------- Preserve TeamLeader Info --------------------
#     def _preserve_team_leader_info(self):
#         try:
#             from app.models import TeamLeader, UpdatedCallLog
#             from app import db
#             team_leaders = TeamLeader.query.filter(TeamLeader.is_active == True).all()
            
#             for tl in team_leaders:
#                 latest_record = UpdatedCallLog.query.filter(
#                     UpdatedCallLog.agent_name == tl.name,
#                     UpdatedCallLog.designation == 'TL'
#                 ).order_by(UpdatedCallLog.log_time.desc()).first()
                
#                 if latest_record:
#                     update_values = {}
#                     if tl.tm_name:
#                         update_values['tm_name'] = tl.tm_name
#                     elif latest_record.tm_name:
#                         update_values['tm_name'] = latest_record.tm_name
                    
#                     if tl.group_name:
#                         update_values['group_name'] = tl.group_name
#                     elif latest_record.group_name:
#                         update_values['group_name'] = latest_record.group_name
                    
#                     if update_values:
#                         UpdatedCallLog.query.filter(
#                             UpdatedCallLog.agent_name == tl.name,
#                             UpdatedCallLog.designation == 'TL'
#                         ).update(update_values)
#                         print(f"✅ Preserved TL '{tl.name}': TM='{update_values.get('tm_name', 'N/A')}', Group='{update_values.get('group_name', 'N/A')}'")
            
#             db.session.commit()
#             print("✅ TeamLeader info preserved")
#         except Exception as e:
#             from app import db
#             db.session.rollback()
#             print(f"⚠ Could not preserve TeamLeader info: {e}")



















"""
High-performance CSV data ingestion for the Agent Management System.
Combines hierarchy, status, and AgentInfo/AgentList synchronization logic.
See DOCUMENTATION.txt for detailed data processing descriptions.
"""

import pandas as pd
from datetime import datetime
import io
import csv
import os
import re
from sqlalchemy import text
from app.models import TeamLeader
from app.config import Config
from app.utils import clean_agent_name
from app import db  # ✅ add this here (global import)


class DataIngestionManager:
    """OOP class for extreme speed CSV ingestion with hierarchy + status preservation + sync"""

    def __init__(self):
        pass

    def ingest_csv(self, file_path, source_filename, date_range=None):
        """
        EXTREME SPEED CSV ingestion (5,000+ rows/sec)
        ✅ Preserves agent status
        ✅ Handles hierarchy and TL relationships
        ✅ Syncs AgentInfo + AgentList after ingestion
        """
        from app import db

        try:
            start_time = datetime.now()

            # Step 1: Load CSV (optimized)
            df = pd.read_csv(
                file_path,
                low_memory=False,
                encoding="utf-8-sig",
                dtype={
                    'Agent name': 'string',
                    'Profile ID': 'string',
                    'Call Log ID': 'string',
                    'Log Type': 'string',
                    'State': 'string',
                    'Call type': 'string',
                    'Original campaign': 'string',
                    'Current campaign': 'string',
                    'Ember': 'string'
                },
                engine='c'
            )
            total_rows = len(df)

            # Validate required columns
            required_columns = [
                'Agent name', 'Profile ID', 'Call Log ID', 'Log Time',
                'Log Type', 'State', 'Call type', 'Original campaign',
                'Current campaign', 'Ember'
            ]
            missing_columns = set(required_columns) - set(df.columns)
            if missing_columns:
                raise ValueError(f"CSV missing required columns: {missing_columns}")

            # Step 2: Normalize/clean data
            for col in required_columns:
                if col in df.columns:
                    df[col] = df[col].astype('string').str.strip()

            df['Log Time'] = pd.to_datetime(df['Log Time'], errors='coerce')
            df['Cleaned Name'] = df['Agent name'].str.replace(r'-[Pp]$', '', regex=True).str.strip()

            # Step 3: Fetch previous records for inheritance
            unique_agents = df['Cleaned Name'].unique().tolist()
            file_min_date = df['Log Time'].min()

            previous_records = self._fetch_previous_records_with_date_context(
                unique_agents, file_min_date, db
            )

            # Step 4: Bulk COPY to PostgreSQL (fast ingestion)
            raw_conn = db.engine.raw_connection()
            try:
                with raw_conn.cursor() as cursor:
                    # Disable triggers for performance
                    try:
                        cursor.execute("ALTER TABLE raw_call_logs DISABLE TRIGGER ALL;")
                        cursor.execute("ALTER TABLE updated_call_logs DISABLE TRIGGER ALL;")
                        print("✅ Triggers disabled for maximum speed")
                    except Exception as trigger_error:
                        print(f"⚠ Could not disable triggers: {trigger_error}")

                    # Insert into raw_call_logs
                    print("➡ Inserting raw_call_logs...")
                    raw_csv_data = self._create_raw_csv_data(df, source_filename)
                    self._insert_raw_copy(cursor, raw_csv_data)
                    print(f"✅ Raw data inserted: {len(df):,} rows")

                    # Insert into updated_call_logs
                    print("➡ Inserting updated_call_logs...")
                    updated_csv_data = self._create_updated_csv_data(df, source_filename, previous_records)
                    self._insert_updated_copy(cursor, updated_csv_data)
                    print(f"✅ Updated data inserted: {len(df):,} rows")

                    # Re-enable triggers
                    try:
                        cursor.execute("ALTER TABLE raw_call_logs ENABLE TRIGGER ALL;")
                        cursor.execute("ALTER TABLE updated_call_logs ENABLE TRIGGER ALL;")
                        print("✅ Triggers re-enabled")
                    except Exception as trigger_error:
                        print(f"⚠ Could not re-enable triggers: {trigger_error}")

                raw_conn.commit()

            finally:
                raw_conn.close()

            # Step 5: Preserve TL info
            self._preserve_team_leader_info()

            # Step 6: Sync AgentInfo (from file 1)
            self._update_agent_info()

            # Step 7: Sync AgentList (from file 2)
            self._sync_agent_list()

            elapsed = (datetime.now() - start_time).total_seconds()
            print(f"🚀 Ingestion completed in {elapsed:.2f} seconds")
            return True

        except Exception as e:
            try:
                raw_conn = db.engine.raw_connection()
                with raw_conn.cursor() as cursor:
                    cursor.execute("ALTER TABLE raw_call_logs ENABLE TRIGGER ALL;")
                    cursor.execute("ALTER TABLE updated_call_logs ENABLE TRIGGER ALL;")
                raw_conn.commit()
                raw_conn.close()
            except:
                pass

            db.session.rollback()
            raise ValueError(f"Failed to ingest CSV: {str(e)}")

    # -------------------- AgentInfo Sync (from File 1) --------------------
    def _update_agent_info(self):
        """Sync AgentInfo with updated_call_logs whenever hierarchy info changes"""
        from app import db
        from app.models import UpdatedCallLog, AgentInfo

        try:
            latest_agents = db.session.query(
                UpdatedCallLog.agent_name,
                UpdatedCallLog.tm_name,
                UpdatedCallLog.tl_name,
                UpdatedCallLog.group_name
            ).distinct().all()

            new_count = 0
            updated_count = 0
            now = datetime.utcnow()

            for agent_name, tm_name, tl_name, group_name in latest_agents:
                existing = AgentInfo.query.filter_by(agent_name=agent_name).first()

                if not existing:
                    db.session.add(AgentInfo(
                        agent_name=agent_name,
                        tm_name=tm_name,
                        tl_name=tl_name,
                        group_name=group_name,
                        updated_at=now
                    ))
                    new_count += 1
                else:
                    has_changes = False
                    if existing.tm_name != tm_name:
                        existing.tm_name = tm_name
                        has_changes = True
                    if existing.tl_name != tl_name:
                        existing.tl_name = tl_name
                        has_changes = True
                    if existing.group_name != group_name:
                        existing.group_name = group_name
                        has_changes = True
                    if has_changes:
                        existing.updated_at = now
                        updated_count += 1

            db.session.commit()
            print(f"✅ AgentInfo synced. {new_count} new, {updated_count} updated.")

        except Exception as e:
            db.session.rollback()
            print(f"⚠ Failed to update AgentInfo: {e}")

    # -------------------- AgentList Sync (from File 2) --------------------
    def _sync_agent_list(self):
        """Sync new agents from UpdatedCallLog to AgentList table"""
        try:
            from app.models import AgentList
            from app import db
            from sqlalchemy import text

            existing_agents = {agent.agent_name for agent in AgentList.query.all()}

            if not existing_agents:
                result = db.session.execute(text("""
                    SELECT DISTINCT agent_name 
                    FROM updated_call_logs 
                    WHERE agent_name IS NOT NULL
                """))
            else:
                result = db.session.execute(text("""
                    SELECT DISTINCT agent_name 
                    FROM updated_call_logs 
                    WHERE agent_name IS NOT NULL 
                    AND agent_name NOT IN :existing_agents
                """), {'existing_agents': tuple(existing_agents)})

            new_agents = [row[0] for row in result if row[0] not in existing_agents]

            if new_agents:
                from app.models import AgentList
                agents_to_add = [AgentList(agent_name=a) for a in new_agents]
                db.session.bulk_save_objects(agents_to_add)
                db.session.commit()
                print(f"✅ Synced {len(new_agents)} new agents to AgentList")
            else:
                print("ℹ No new agents to sync")

        except Exception as e:
            db.session.rollback()
            print(f"⚠ AgentList sync failed: {e}")

    # -------------------- Fetch Previous Records --------------------
    def _fetch_previous_records_with_date_context(self, unique_agents, current_file_min_date, db):
        """Fetch previous records (with status + hierarchy context)"""
        if not unique_agents or current_file_min_date is None:
            return {}

        previous_records = {}
        try:
            if isinstance(current_file_min_date, pd.Timestamp):
                current_file_min_date = current_file_min_date.to_pydatetime()

            batch_size = 500
            for i in range(0, len(unique_agents), batch_size):
                batch_agents = unique_agents[i:i + batch_size]

                query = text("""
                    SELECT agent_name, designation, role, group_name, tm_name, tl_name, status, log_time
                    FROM updated_call_logs 
                    WHERE agent_name IN :agents
                    AND log_time < :cutoff_date
                    ORDER BY log_time DESC
                """)

                result = db.session.execute(query, {
                    'agents': tuple(batch_agents),
                    'cutoff_date': current_file_min_date
                }).fetchall()

                for row in result:
                    agent_name = row[0]
                    if agent_name not in previous_records:
                        previous_records[agent_name] = {
                            'designation': row[1] or 'Agent',
                            'role': row[2] or 'Full-Timer',
                            'group_name': row[3] or '',
                            'tm_name': row[4] or '',
                            'tl_name': row[5] or '',
                            'status': row[6] or 'Employee',
                            'last_seen': row[7]
                        }

        except Exception as e:
            print(f"❌ Error fetching previous records: {e}")
            previous_records = self._fetch_previous_records_simple(unique_agents, db)

        return previous_records

    def _fetch_previous_records_simple(self, unique_agents, db):
        """Fallback previous record fetch"""
        if not unique_agents:
            return {}

        previous_records = {}
        try:
            batch_size = 1000
            for i in range(0, len(unique_agents), batch_size):
                batch_agents = unique_agents[i:i + batch_size]

                query = text("""
                    SELECT DISTINCT ON (agent_name) 
                        agent_name, 
                        COALESCE(designation, 'Agent') as designation,
                        COALESCE(role, 'Full-Timer') as role,
                        COALESCE(group_name, '') as group_name,
                        COALESCE(tm_name, '') as tm_name,
                        COALESCE(tl_name, '') as tl_name,
                        COALESCE(status, 'Employee') as status
                    FROM updated_call_logs 
                    WHERE agent_name = ANY(:agents)
                    ORDER BY agent_name, log_time DESC
                """)

                result = db.session.execute(query, {'agents': batch_agents})

                for row in result:
                    previous_records[row['agent_name']] = {
                        'designation': row['designation'],
                        'role': row['role'],
                        'group_name': row['group_name'],
                        'tm_name': row['tm_name'],
                        'tl_name': row['tl_name'],
                        'status': row['status']
                    }

        except Exception as e:
            print(f"⚠ Could not fetch previous records: {e}")

        return previous_records

    # -------------------- CSV Builders --------------------
    def _create_raw_csv_data(self, df, source_filename):
        """Prepare CSV buffer for raw_call_logs COPY"""
        output = io.StringIO()
        writer = csv.writer(output)

        for _, row in df.iterrows():
            log_time = ""
            if pd.notnull(row['Log Time']):
                try:
                    log_time = row['Log Time'].isoformat()
                except Exception:
                    log_time = ""

            writer.writerow([
                str(row['Agent name']).strip(),
                str(row['Profile ID']).strip(),
                str(row['Call Log ID']).strip(),
                log_time,
                str(row['Log Type']).strip(),
                str(row['State']).strip(),
                str(row['Call type']).strip(),
                str(row['Original campaign']).strip(),
                str(row['Current campaign']).strip(),
                str(row['Ember']).strip(),
                source_filename
            ])

        output.seek(0)
        return output

    def _create_updated_csv_data(self, df, source_filename, previous_records):
        """Prepare CSV buffer for updated_call_logs COPY"""
        output = io.StringIO()
        writer = csv.writer(output)

        part_timer_count = 0

        for _, row in df.iterrows():
            raw_name = str(row['Agent name']).strip()
            agent, role = clean_agent_name(raw_name)
            if role == "Part-Timer":
                part_timer_count += 1

            prev_data = previous_records.get(agent, {})
            log_time = ""
            if pd.notnull(row['Log Time']):
                try:
                    log_time = row['Log Time'].isoformat()
                except Exception:
                    log_time = ""

            team_leader = TeamLeader.query.filter_by(name=agent).first()

            if team_leader:
                designation = "TL"
                tl_name = "Self"
                tm_name = team_leader.tm_name or prev_data.get('tm_name', '')
                group_name = team_leader.group_name or prev_data.get('group_name', '')
            else:
                designation = prev_data.get('designation', Config.DEFAULT_DESIGNATION)
                tl_name = prev_data.get('tl_name', '')
                tm_name = prev_data.get('tm_name', '')
                group_name = prev_data.get('group_name', '')
                if designation == "TL":
                    tl_name = "Self"
                elif designation == Config.DEFAULT_DESIGNATION:
                    tl_name = prev_data.get('tl_name', '')
                elif designation == "TM":
                    tl_name = ""

            status = prev_data.get('status', 'Employee')

            writer.writerow([
                agent,
                str(row['Profile ID']).strip(),
                str(row['Call Log ID']).strip(),
                log_time,
                str(row['Log Type']).strip(),
                str(row['State']).strip(),
                str(row['Call type']).strip(),
                str(row['Original campaign']).strip(),
                str(row['Current campaign']).strip(),
                str(row['Ember']).strip(),
                designation,
                role,
                group_name,
                tm_name,
                tl_name,
                source_filename,
                status
            ])

        print(f"   Detected {part_timer_count} part-timer records")
        output.seek(0)
        return output

    # -------------------- COPY commands --------------------
    def _insert_raw_copy(self, cursor, csv_data):
        cursor.copy_expert("""
            COPY raw_call_logs (agent_name, profile_id, call_log_id, log_time, 
                              log_type, state, call_type, original_campaign, 
                              current_campaign, ember, source_file) 
            FROM STDIN WITH (FORMAT CSV)
        """, csv_data)

    def _insert_updated_copy(self, cursor, csv_data):
        cursor.copy_expert("""
            COPY updated_call_logs (agent_name, profile_id, call_log_id, log_time, 
                                  log_type, state, call_type, original_campaign, 
                                  current_campaign, ember, designation, role, 
                                  group_name, tm_name, tl_name, source_file, status) 
            FROM STDIN WITH (FORMAT CSV)
        """, csv_data)

    # -------------------- Preserve TL Info --------------------
    def _preserve_team_leader_info(self):
        """Preserve TeamLeader TM/Group info after upload"""
        try:
            from app.models import TeamLeader, UpdatedCallLog
            from app import db
            team_leaders = TeamLeader.query.filter(TeamLeader.is_active == True).all()

            for tl in team_leaders:
                latest_record = UpdatedCallLog.query.filter(
                    UpdatedCallLog.agent_name == tl.name,
                    UpdatedCallLog.designation == 'TL'
                ).order_by(UpdatedCallLog.log_time.desc()).first()

                if latest_record:
                    update_values = {}
                    if tl.tm_name:
                        update_values['tm_name'] = tl.tm_name
                    elif latest_record.tm_name:
                        update_values['tm_name'] = latest_record.tm_name

                    if tl.group_name:
                        update_values['group_name'] = tl.group_name
                    elif latest_record.group_name:
                        update_values['group_name'] = latest_record.group_name

                    if update_values:
                        UpdatedCallLog.query.filter(
                            UpdatedCallLog.agent_name == tl.name,
                            UpdatedCallLog.designation == 'TL'
                        ).update(update_values)
                        print(f"✅ Preserved TL '{tl.name}': TM='{update_values.get('tm_name', 'N/A')}', Group='{update_values.get('group_name', 'N/A')}'")

            db.session.commit()
            print("✅ TeamLeader info preserved")

        except Exception as e:
            from app import db
            db.session.rollback()
            print(f"⚠ Could not preserve TeamLeader info: {e}")
