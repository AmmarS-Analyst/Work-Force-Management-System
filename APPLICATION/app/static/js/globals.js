// Global utilities and theme management
document.addEventListener('DOMContentLoaded', function() {
    initializeThemeToggle();
    initializeToastNotifications();
});

// Theme switching functionality
function initializeThemeToggle() {
    const themeToggle = document.getElementById('themeToggle');
    const themeIcon = themeToggle?.querySelector('i');
    
    if (!themeToggle || !themeIcon) return;
    
    // Check for saved theme preference or respect OS preference
    const savedTheme = localStorage.getItem('theme');
    const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    
    // Set initial theme
    if (savedTheme === 'dark' || (!savedTheme && systemPrefersDark)) {
        document.documentElement.setAttribute('data-theme', 'dark');
        themeIcon.className = 'fas fa-sun';
    } else {
        document.documentElement.setAttribute('data-theme', 'light');
        themeIcon.className = 'fas fa-moon';
    }
    
    // Theme toggle button event listener
    themeToggle.addEventListener('click', function() {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        if (currentTheme === 'light') {
            document.documentElement.setAttribute('data-theme', 'dark');
            themeIcon.className = 'fas fa-sun';
            localStorage.setItem('theme', 'dark');
        } else {
            document.documentElement.setAttribute('data-theme', 'light');
            themeIcon.className = 'fas fa-moon';
            localStorage.setItem('theme', 'light');
        }
    });
}

// Toast Notification System
class IngestionNotifier {
    constructor() {
        this.toastContainer = document.getElementById('toastContainer');
        this.activeToasts = new Map();
    }

    createToast(id, title, message, type = 'info') {
        const toastId = id || `toast-${Date.now()}`;
        const toast = document.createElement('div');
        toast.className = `ingestion-toast ${type}`;
        toast.id = toastId;
        toast.innerHTML = `
            <div class="toast-progress" id="progress-${toastId}"></div>
            <div class="toast-header">
                <div class="toast-title">
                    <i class="fas ${this.getIcon(type)}"></i>
                    ${title}
                </div>
                <button class="close-toast" onclick="notifier.removeToast('${toastId}')">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <div class="toast-body">
                <div class="toast-message">${message}</div>
                <div class="toast-details" id="details-${toastId}"></div>
            </div>
        `;
        
        this.toastContainer.appendChild(toast);
        this.activeToasts.set(toastId, toast);
        
        // Auto-remove after 10 seconds for non-progress toasts
        if (!id.includes('progress')) {
            setTimeout(() => this.removeToast(toastId), 10000);
        }
        
        return toastId;
    }

    updateToast(toastId, message, details = null) {
        const toast = this.activeToasts.get(toastId);
        if (toast) {
            const messageEl = toast.querySelector('.toast-message');
            const detailsEl = toast.querySelector('.toast-details');
            
            if (message) messageEl.textContent = message;
            if (details) detailsEl.textContent = details;
        }
    }

    updateProgress(toastId, progress, message = null) {
        const progressBar = document.getElementById(`progress-${toastId}`);
        if (progressBar) {
            progressBar.style.width = `${progress}%`;
        }
        if (message) {
            this.updateToast(toastId, message);
        }
    }

    removeToast(toastId) {
        const toast = this.activeToasts.get(toastId);
        if (toast) {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(100%)';
            setTimeout(() => {
                toast.remove();
                this.activeToasts.delete(toastId);
            }, 300);
        }
    }

    getIcon(type) {
        const icons = {
            'info': 'fa-info-circle',
            'success': 'fa-check-circle',
            'warning': 'fa-exclamation-triangle',
            'error': 'fa-exclamation-circle'
        };
        return icons[type] || 'fa-info-circle';
    }
}

// Initialize toast notifications
function initializeToastNotifications() {
    window.notifier = new IngestionNotifier();
}

// Utility functions
function showAlert(message, type = 'info') {
    if (window.Swal) {
        Swal.fire({
            title: type.charAt(0).toUpperCase() + type.slice(1),
            text: message,
            icon: type,
            confirmButtonText: 'OK',
            confirmButtonColor: type === 'success' ? '#34a853' : type === 'error' ? '#ea4335' : '#4285f4'
        });
    } else {
        alert(message);
    }
}

// CSRF token utility
function getCSRFToken() {
    return document.querySelector('body').getAttribute('data-csrf-token');
}

// User role utility
function getUserRoles() {
    const rolesData = document.querySelector('body').getAttribute('data-user-roles');
    try {
        return JSON.parse(rolesData) || [];
    } catch {
        return [];
    }
}

// Check if user has admin role
function isAdmin() {
    const isAdminData = document.querySelector('body').getAttribute('data-is-admin');
    return isAdminData === 'true';
}