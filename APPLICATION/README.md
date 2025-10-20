# 🏢 Agent Management System

A comprehensive Flask-based web application for managing call center agents, team hierarchies, and performance tracking with role-based access control.

## 🚀 Features

### 👥 **User Management**
- **Role-based Access Control**: Admin, Data Entry, Team Manager, Team Leader, Agent roles
- **Secure Authentication**: Flask-Login with strong session protection
- **User Creation & Management**: Admin panel for user administration
- **Password Security**: Hashed passwords with secure authentication

### 📊 **Agent Management**
- **Agent Designation**: Cold Caller, Team Leader, Team Manager designations
- **Team Hierarchy**: TM → TL → Agent structure
- **Performance Tracking**: Call log analysis and reporting
- **Bulk Data Processing**: High-performance CSV ingestion (5000+ rows/second)

### 📈 **Distribution Management**
- **Team Assignment**: Assign agents to Team Leaders and Team Managers
- **Request System**: TLs can request agent transfers
- **Approval Workflow**: TM approval for distribution changes
- **Activity Logging**: Complete audit trail of all changes

### 📁 **File Management**
- **CSV Upload**: Bulk agent data import
- **Data Processing**: Automated data cleaning and validation
- **File History**: Track uploaded files and their processing status
- **Delete Requests**: Secure file deletion with approval workflow

### 🔐 **Security Features**
- **CSRF Protection**: Cross-site request forgery prevention
- **Session Security**: Strong session protection with configurable timeouts
- **Role-based Permissions**: Granular access control
- **Secure File Handling**: Validated file uploads with size limits

## 🏗️ Architecture

### **Backend Structure**
```
app/
├── __init__.py          # Flask app factory
├── config.py            # Centralized configuration
├── models.py            # Database models
├── routes.py            # Main application routes
├── admin.py             # Admin-specific routes
├── auth.py              # Authentication routes
├── decorators.py        # Security decorators
├── distributor.py       # Distribution business logic
├── data_ingestion.py    # CSV processing engine
├── services/            # Business logic layer
│   ├── user_service.py
│   ├── file_service.py
│   ├── distribution_service.py
│   └── log_service.py
├── templates/           # Jinja2 templates
└── static/             # CSS, JS, images
```

### **Database Models**
- **User**: Authentication and role management
- **Role**: Permission system
- **TeamManager**: Team management hierarchy
- **TeamLeader**: Team leadership structure
- **Agent**: Agent information and assignments
- **RawCallLog**: Original call data
- **UpdatedCallLog**: Processed call data
- **ActivityLog**: Audit trail
- **DistributionRequest**: Transfer requests

## 🛠️ Installation & Setup

### **Prerequisites**
- Python 3.9+
- PostgreSQL 12+
- pip (Python package manager)

### **1. Clone Repository**
```bash
git clone <repository-url>
cd agent-management-system
```

### **2. Create Virtual Environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### **3. Install Dependencies**
```bash
pip install -r requirements.txt
```

### **4. Environment Configuration**
Create a `.env` file in the root directory:
```bash
# Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/agent_management

# Security
SECRET_KEY=your-super-secret-key-here

# Session Settings
SESSION_COOKIE_SECURE=False  # Set to True for HTTPS
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax

# Application Settings
FLASK_ENV=development
FLASK_DEBUG=True
```

### **5. Database Setup**
```bash
# Create database
createdb agent_management

# Run migrations
flask db upgrade

# Initialize roles and admin user
python main.py
```

### **6. Run Application**
```bash
python main.py
```

The application will be available at `http://127.0.0.1:5000`

## 👤 Default Login

**Admin User:**
- Username: `admin`
- Password: `admin123` (change in production!)

## 🔧 Configuration

All configuration is centralized in `app/config.py`:

```python
class Config:
    # Core settings
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev123')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    
    # Session settings
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)
    SESSION_PROTECTION = 'strong'
    
    # File upload settings
    MAX_CONTENT_LENGTH = 200 * 1024 * 1024  # 200MB
    
    # Default values
    DEFAULT_DESIGNATION = 'Cold Caller'
    DEFAULT_ROLE = 'Full-Timer'
```

## 🚀 Production Deployment

### **1. Environment Variables**
Set production environment variables:
```bash
export SECRET_KEY="your-production-secret-key"
export DATABASE_URL="postgresql://user:pass@host:port/db"
export FLASK_ENV="production"
export FLASK_DEBUG="False"
```

### **2. Update config.py**
Uncomment production settings:
```python
SESSION_COOKIE_SECURE = True
SESSION_PROTECTION = 'strong'
SECRET_KEY = os.getenv('SECRET_KEY')  # Must be set
```

### **3. WSGI Server**
```bash
# Install Gunicorn
pip install gunicorn

# Run with Gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 main:app
```

### **4. Reverse Proxy (Nginx)**
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location /static {
        alias /path/to/app/static;
    }
}
```

## 📊 Performance Features

### **High-Speed Data Processing**
- **Memory-mapped CSV loading** for large files
- **Bulk database operations** with connection pooling
- **Optimized queries** with proper indexing
- **Chunked processing** for files >50MB

### **Database Optimization**
- **Connection pooling** (15 connections, 25 overflow)
- **Query optimization** with proper joins
- **Indexed columns** for fast lookups
- **Batch operations** for bulk updates

## 🔒 Security Features

### **Authentication & Authorization**
- **Flask-Login** integration
- **Role-based access control**
- **Session management** with strong protection
- **Password hashing** with Werkzeug

### **Request Security**
- **CSRF protection** on all forms
- **Input validation** and sanitization
- **File upload security** with type validation
- **SQL injection prevention** with SQLAlchemy ORM

## 📝 API Endpoints

### **Authentication**
- `GET /auth/login` - Login page
- `POST /auth/login` - User authentication
- `GET /auth/logout` - User logout

### **Main Application**
- `GET /` - Dashboard (Admin/Data Entry)
- `GET /distribution` - Distribution page (TM/TL)
- `POST /` - File operations and agent updates

### **Admin Panel**
- `GET /admin/` - Admin dashboard
- `POST /admin/create-user` - Create new user
- `POST /admin/create-team-manager` - Create TM
- `POST /admin/create-team-leader` - Create TL
- `POST /admin/delete-*` - Delete operations

## 🧪 Testing

### **Manual Testing Checklist**
- [ ] User authentication and logout
- [ ] Role-based access control
- [ ] Admin panel functionality
- [ ] Team management operations
- [ ] Agent assignment and transfers
- [ ] File upload and processing
- [ ] Activity logging
- [ ] Session management

### **Security Testing**
- [ ] CSRF protection
- [ ] SQL injection prevention
- [ ] XSS protection
- [ ] File upload validation
- [ ] Session security

## 📈 Monitoring & Logging

### **Activity Logging**
- All user actions are logged
- Database changes tracked
- File operations recorded
- Distribution changes audited

### **Error Handling**
- Graceful error handling
- User-friendly error messages
- Database rollback on errors
- Comprehensive logging

## 🤝 Contributing

### **Development Setup**
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

### **Code Standards**
- Follow PEP 8 style guidelines
- Add docstrings to functions
- Use type hints where appropriate
- Write meaningful commit messages

## 📄 License

This project is proprietary software developed for internal use.

## 🆘 Support

For technical support or questions:
- Create an issue in the repository
- Contact the development team
- Check the documentation

## 🔄 Version History

### **v1.0.0** - Current
- Initial release
- Complete agent management system
- Role-based access control
- High-performance data processing
- Production-ready security

---

**Built with ❤️ using Flask, SQLAlchemy, and modern web technologies**