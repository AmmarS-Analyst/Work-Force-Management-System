// Notification functionality
document.addEventListener('DOMContentLoaded', function() {
    initializeNotifications();
});

function initializeNotifications() {
    // Request approval/denial functionality
    document.addEventListener('click', function(e) {
        const btn = e.target.closest('.approve-btn, .deny-btn');
        if (!btn) return;
        
        const action = btn.classList.contains('approve-btn') ? 'approve' : 'deny';
        const reqId = btn.dataset.id;
        
        if (!reqId) return;
        
        // Show confirmation dialog
        const actionText = action === 'approve' ? 'approve' : 'deny';
        const confirmText = action === 'approve' ? 
            'Are you sure you want to approve this deletion request?' : 
            'Are you sure you want to deny this deletion request?';
        
        if (!confirm(confirmText)) return;
        
        // Send AJAX request
        const csrfToken = getCSRFToken();
        
        fetch(`/${action}_delete/${reqId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: new URLSearchParams({
                'csrf_token': csrfToken
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Remove the request item from both dropdown and sidebar
                const requestItem = document.getElementById(`request-${reqId}`);
                if (requestItem) {
                    requestItem.remove();
                }
                
                // Update notification counts
                updateNotificationCounts();
                
                // Show success message
                showAlert(`Request ${actionText}d successfully`, 'success');
                
                // Check if no more requests
                checkEmptyRequests();
            } else {
                showAlert(data.message || `Failed to ${actionText} request`, 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showAlert(`Failed to ${actionText} request`, 'error');
        });
    });
}

function updateNotificationCounts() {
    const pendingCount = document.getElementById('pending-count');
    const pendingCountSidebar = document.getElementById('pending-count-sidebar');
    
    if (pendingCount) {
        const currentCount = parseInt(pendingCount.textContent) || 0;
        pendingCount.textContent = Math.max(0, currentCount - 1);
    }
    
    if (pendingCountSidebar) {
        const currentCount = parseInt(pendingCountSidebar.textContent) || 0;
        pendingCountSidebar.textContent = Math.max(0, currentCount - 1);
    }
}

function checkEmptyRequests() {
    const requestsList = document.getElementById('requests-list');
    const notificationBody = document.querySelector('.notification-body');
    
    // Check dropdown
    if (requestsList && requestsList.children.length === 0) {
        requestsList.innerHTML = '<div class="alert alert-info mb-0"><i class="fas fa-check-circle"></i> No pending requests</div>';
    }
    
    // Check sidebar
    if (notificationBody && notificationBody.children.length === 0) {
        notificationBody.innerHTML = '<div class="alert alert-info"><i class="fas fa-check-circle"></i> No pending requests</div>';
    }
}

// Auto-refresh notifications (optional)
function startNotificationRefresh() {
    // Refresh notifications every 30 seconds
    setInterval(() => {
        refreshNotifications();
    }, 30000);
}

function refreshNotifications() {
    // Only refresh if user is on a page with notifications
    const notificationToggle = document.getElementById('notificationToggle');
    if (!notificationToggle) return;
    
    fetch('/api/notifications', {
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            updateNotificationCounts();
            // You could also update the notification list here
        }
    })
    .catch(error => {
        console.error('Failed to refresh notifications:', error);
    });
}

// Initialize auto-refresh if needed
// startNotificationRefresh();