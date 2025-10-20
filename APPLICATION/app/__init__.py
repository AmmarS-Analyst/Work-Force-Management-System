"""
Flask application factory for the Agent Management System.
See DOCUMENTATION.txt for detailed architecture descriptions.
"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf import CSRFProtect
from dotenv import load_dotenv
from app.config import Config

load_dotenv()

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
csrf = CSRFProtect()

def create_app():
    app = Flask(
        __name__,
        template_folder=Config.TEMPLATE_FOLDER,
        static_folder=Config.STATIC_FOLDER
    )

    # Load configuration from centralized config
    app.config.from_object(Config)
    
    # Set Flask-Login specific settings
    login_manager.login_view = Config.LOGIN_VIEW
    login_manager.session_protection = Config.SESSION_PROTECTION

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    
    # Add services to app context AFTER app is created
    from app.services.log_service import LogService
    app.log_service = LogService()
    
    # Flask-Login user loader
    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return User.query.get(int(user_id))

    # Register Blueprints
    from app.auth import auth_bp
    from app.routes import main as main_blueprint
    from app.admin import admin_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(main_blueprint)
    app.register_blueprint(admin_bp, url_prefix='/admin')

    # Create DB tables and initialize roles/admin user
    with app.app_context():
        # Import all models to ensure they're registered with SQLAlchemy
        from app.models import User, Role, RawCallLog, UpdatedCallLog, DeleteRequest
        db.create_all()

        # REMOVE THIS LINE COMPLETELY - it's causing the error
        # from app.models import init_roles, init_admin_user
        
        # Use UserService for initialization instead
        from app.services.user_service import UserService
        user_service = UserService()
        user_service.init_roles()
        user_service.init_admin_user()

        # Ensure optional columns exist (idempotent)
        try:
            db.session.execute(
                "ALTER TABLE updated_call_logs ADD COLUMN IF NOT EXISTS tl_name VARCHAR(100)"
            )
            db.session.commit()
        except Exception:
            db.session.rollback()

        # Normalize designations: default to configured default designation except explicit 'Team Leader'
        try:
            db.session.execute(
                f"""
                UPDATE updated_call_logs
                SET designation = '{Config.DEFAULT_DESIGNATION}'
                WHERE designation IS NULL OR TRIM(designation) = '' OR LOWER(designation) NOT IN ('team leader')
                """
            )
            db.session.commit()
        except Exception:
            db.session.rollback()

    return app