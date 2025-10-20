class PermissionSystem:
    """Centralized permission management system"""
    
    # Permission constants
    UPLOAD_AGENT_DATA = "upload_agent_data"
    UPDATE_TEAM_DATA = "update_team_data"
    VIEW_DISTRIBUTION = "view_distribution"
    MANAGE_TEAM_LEADERS = "manage_team_leaders"
    MANAGE_AGENTS = "manage_agents"
    FULL_ACCESS = "full_access"
    
    def __init__(self):
        self.role_permissions = self._initialize_role_permissions()
    
    def _initialize_role_permissions(self):
        """Initialize role permission mappings"""
        return {
            'admin': [
                self.UPLOAD_AGENT_DATA, self.UPDATE_TEAM_DATA, self.VIEW_DISTRIBUTION,
                self.MANAGE_TEAM_LEADERS, self.MANAGE_AGENTS, self.FULL_ACCESS
            ],
            'data_entry': [self.UPLOAD_AGENT_DATA],
            'tm': [self.VIEW_DISTRIBUTION, self.MANAGE_TEAM_LEADERS, self.MANAGE_AGENTS],
            'tl': [self.VIEW_DISTRIBUTION]
        }
    
    def get_default_permissions(self, role_name):
        """Get default permissions for a role"""
        return self.role_permissions.get(role_name.lower(), [])
    
    def has_permission(self, user, permission):
        """Check if user has specific permission"""
        if not user or not user.roles:
            return False
        
        user_permissions = set()
        for role in user.roles:
            perms = self.role_permissions.get(role.name.lower(), [])
            user_permissions.update(perms)
        
        return permission in user_permissions
    
    def get_user_permissions(self, user):
        """Get all permissions for a user"""
        if not user or not user.roles:
            return []
        
        permissions = set()
        for role in user.roles:
            perms = self.role_permissions.get(role.name.lower(), [])
            permissions.update(perms)
        
        return list(permissions)