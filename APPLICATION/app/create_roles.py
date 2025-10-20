from app import db
from app.models import Role

def create_roles():
    roles_permissions = {
        'admin': ['upload_agent_data', 'view_distribution', 'manage_users', 'update_team_data'],
        'data_entry': ['upload_agent_data', 'update_team_data'],
        'tm': ['view_distribution'],
    }

    for role_name, permissions in roles_permissions.items():
        role = Role.query.filter_by(name=role_name).first()
        if not role:
            role = Role(name=role_name, permissions=permissions)
            db.session.add(role)
        else:
            role.permissions = permissions
    db.session.commit()
    print("Roles and permissions created/updated successfully.")

if __name__ == '__main__':
    create_roles()
