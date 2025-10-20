"""
File management service for the Agent Management System.
See DOCUMENTATION.txt for detailed service descriptions.
"""

from datetime import datetime
import os
import pandas as pd
from werkzeug.utils import secure_filename
from app import db
from app.models import DeleteRequest, ActivityLog, RawCallLog, UpdatedCallLog
from app.data_ingestion import DataIngestionManager
from app.loader import load_raw_data

class FileService:
    """Service layer for file operations"""
    
    def __init__(self):
        self.ingestion_manager = DataIngestionManager()
    
    def prepare_index_context(self, current_user):
        """Prepare context for index page"""
        context = {
            'agent_names': self._get_all_agent_names(),
            'filenames': self._get_all_filenames(),
            'pending_requests': self._get_pending_delete_requests(),
            'current_user': current_user,
            'users_admin': self._get_users_with_roles(),
            'roles': self._get_roles(),
            'teamManagers': self._get_team_managers(),
            'teamLeaders': self._get_team_leaders(),
            'agents': self._get_agents()
        }
        
        # Add legacy names for backward compatibility
        context['users'] = context['users_admin']
        context['team_managers'] = context['teamManagers']
        context['team_leaders'] = context['teamLeaders']
        
        return context
    
    def handle_file_upload(self, file, current_user):
        """Handle file upload and ingestion"""
        try:
            if not file or file.filename == '':
                return False, {'message': '❌ No file selected.', 'filename': ''}
            
            if not self._allowed_file(file.filename):
                return False, {'message': '❌ Only CSV files are allowed.', 'filename': ''}
            
            filename = secure_filename(file.filename)
            path = os.path.join('temp_uploads', filename)
            os.makedirs('temp_uploads', exist_ok=True)
            file.save(path)
            
            try:
                # Extract date range
                date_range = self._extract_date_range_from_file(path)
                
                # Log upload activity
                self._log_activity(current_user.username, f"uploaded file '{filename}'")
                
                # Ingest data
                success = self.ingestion_manager.ingest_csv(path, filename, date_range)
                
                if success:
                    return True, {
                        'message': f' File "{filename}" uploaded and ingested.',
                        'filename': filename,
                        'ingestion_id': f"ingest-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                    }
                else:
                    return False, {
                        'message': f'❌ Failed to ingest file "{filename}"',
                        'filename': filename
                    }
                        
            finally:
                os.remove(path)
                
        except Exception as e:
            return False, {'message': f'❌ Failed to process file: {str(e)}', 'filename': filename}
    
    def create_delete_request(self, filename, delete_option, reason, selected_dates, current_user):
        """Create deletion request"""
        try:
            if not filename:
                return False, "❌ Please select a file"
            
            request_entry = DeleteRequest(
                filename=filename,
                requested_by=current_user.id,
                requested_by_username=current_user.username,
                reason=reason,
                status='pending',
                date_range=','.join(selected_dates) if delete_option == 'dates' and selected_dates else None,
                created_at=datetime.utcnow()
            )
            
            db.session.add(request_entry)
            db.session.commit()
            
            self._log_activity(current_user.username, f"Submitted delete request for '{filename}'")
            return True, "🗃️ Deletion request submitted for admin approval"
            
        except Exception as e:
            db.session.rollback()
            return False, f"❌ Failed to create request: {str(e)}"
    
    def delete_all_data(self, filename, current_user):
        """Delete all data from file"""
        try:
            if not current_user.has_role('admin'):
                return False, "❌ Unauthorized"
            
            db.session.query(RawCallLog).filter(RawCallLog.source_file == filename).delete(synchronize_session=False)
            db.session.query(UpdatedCallLog).filter(UpdatedCallLog.source_file == filename).delete(synchronize_session=False)
            db.session.commit()
            
            self._log_activity(current_user.username, f"Deleted all data from '{filename}'")
            return True, f"✅ All data from '{filename}' deleted."
            
        except Exception as e:
            db.session.rollback()
            return False, f"❌ Failed to delete: {str(e)}"
    
    def delete_dates_data(self, filename, selected_dates, reason, current_user):
        """Delete data for specific dates"""
        try:
            if not current_user.has_role('admin'):
                return False, "❌ Unauthorized"
            
            if not selected_dates:
                return False, "⚠️ No dates selected."
            
            for date_str in selected_dates:
                date_start = pd.to_datetime(date_str)
                date_end = date_start + pd.Timedelta(days=1)

                db.session.query(RawCallLog).filter(
                    RawCallLog.source_file == filename,
                    RawCallLog.log_time >= date_start,
                    RawCallLog.log_time < date_end
                ).delete(synchronize_session=False)

                db.session.query(UpdatedCallLog).filter(
                    UpdatedCallLog.source_file == filename,
                    UpdatedCallLog.log_time >= date_start,
                    UpdatedCallLog.log_time < date_end
                ).delete(synchronize_session=False)

            db.session.commit()
            
            self._log_activity(current_user.username, f"Deleted dates {', '.join(selected_dates)} from '{filename}'")
            return True, f"✅ Selected dates deleted from '{filename}'."
            
        except Exception as e:
            db.session.rollback()
            return False, f"❌ Failed to delete: {str(e)}"
    
    def get_raw_dates(self, filename):
        """Get dates for a filename"""
        query = db.session.query(db.func.date(RawCallLog.log_time))
        if filename:
            query = query.filter(RawCallLog.source_file == filename)
        raw_dates = query.distinct().all()
        return sorted({r[0].strftime('%Y-%m-%d') for r in raw_dates if r[0]})
    
    # ========== PRIVATE METHODS ==========
    
    def _allowed_file(self, filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'csv'
    
    def _extract_date_range_from_file(self, file_path):
        """Extract date range from CSV file"""
        try:
            df = pd.read_csv(file_path, nrows=1000, 
                           usecols=['Log Time'] if 'Log Time' in pd.read_csv(file_path, nrows=1).columns else None)
            
            if 'Log Time' in df.columns:
                df['Log Time'] = pd.to_datetime(df['Log Time'], errors='coerce')
                valid_dates = df['Log Time'].dropna()
                
                if not valid_dates.empty:
                    min_date = valid_dates.min()
                    max_date = valid_dates.max()
                    return (min_date, max_date)
                    
        except Exception as e:
            print(f"❌ Error extracting date range: {e}")
        
        return (None, None)
    
    def _get_all_agent_names(self):
        agents = db.session.query(UpdatedCallLog.agent_name).distinct().all()
        return sorted([a[0] for a in agents if a[0]])
    
    def _get_all_filenames(self):
        filenames = db.session.query(RawCallLog.source_file).distinct().all()
        return sorted([f[0] for f in filenames if f[0]])
    
    def _get_pending_delete_requests(self):
        return DeleteRequest.query.filter_by(status='pending').order_by(DeleteRequest.created_at.desc()).all()
    
    def _get_users_with_roles(self):
        from app.models import User
        return User.query.options(db.joinedload(User.roles)).all()
    
    def _get_roles(self):
        from app.models import Role
        return Role.query.order_by(Role.name).all()
    
    def _get_team_managers(self):
        from app.models import TeamManager
        return TeamManager.query.order_by(TeamManager.name).all()
    
    def _get_team_leaders(self):
        from app.models import TeamLeader
        return TeamLeader.query.order_by(TeamLeader.name).all()
    
    def _get_agents(self):
        from app.models import Agent
        return Agent.query.order_by(Agent.name).all()
    
    def _log_activity(self, username, message):
        """Log activity"""
        from app.models import ActivityLog
        log_entry = ActivityLog(
            user=username,
            msg=message,
            date=datetime.utcnow()
        )
        db.session.add(log_entry)
        db.session.commit()