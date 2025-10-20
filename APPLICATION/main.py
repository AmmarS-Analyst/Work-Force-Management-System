from app import create_app, db
from app.services.user_service import UserService
from app.distributor import DistributionManager
from app.loader import load_raw_data
from app.updater import update_agent_data

# Create Flask application instance
app = create_app()

with app.app_context():
    from app.models import User, Role
    admin = User.query.filter_by(username='admin').first()
    if admin:
        print("Admin user exists")
    else:
        print("Admin user does not exist")
    # Database initialization
    print("Database initialized")
    
    # Initialize roles and admin user using UserService
    user_service = UserService()
    user_service.init_roles()
    user_service.init_admin_user()
    print("Roles and admin user initialized")

@app.route('/load_data')
def load_data():
    """Endpoint to load and process agent data"""
    try:
        print("Loading latest raw data from DB...")
        df = load_raw_data()  

        print("Updating agent information...")
        updated_df = update_agent_data(df)

        print("Assigning Group and TM Name...")
        distributor = DistributionManager()
        
        print("Data successfully updated in database!")
        return "Data loaded and updated successfully"
        
    except Exception as e:
        print(f"Error in load_data: {str(e)}")
        return f"Error: {str(e)}"

if __name__ == '__main__':
    app.run("0.0.0.0",debug=True)