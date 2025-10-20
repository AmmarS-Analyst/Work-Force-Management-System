// Admin Panel functionality - Safe for all pages
document.addEventListener('DOMContentLoaded', function() {
    initializeAdminPanel();
    initializeHierarchyDropdowns();
});

// Initialize admin panel functionality
function initializeAdminPanel() {
    // Admin Panel Toggle
    const adminPanelToggle = document.getElementById('adminPanelToggle');
    const adminPanel = document.getElementById('adminPanel');
    const closeAdminPanel = document.getElementById('closeAdminPanel');
    
    // Only initialize if elements exist
    if (adminPanelToggle && adminPanel) {
        console.log('Initializing admin panel...');
        
        adminPanelToggle.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            adminPanel.classList.add('active');
            console.log('Admin panel opened');
        });
        
        if (closeAdminPanel) {
            closeAdminPanel.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                adminPanel.classList.remove('active');
                console.log('Admin panel closed');
            });
        }
        
        // Close admin panel when clicking outside
        document.addEventListener('click', function(e) {
            if (adminPanel.classList.contains('active') && 
                !adminPanel.contains(e.target) && 
                e.target !== adminPanelToggle) {
                adminPanel.classList.remove('active');
                console.log('Admin panel closed (outside click)');
            }
        });
        
        // Prevent clicks inside admin panel from closing it
        adminPanel.addEventListener('click', function(e) {
            e.stopPropagation();
        });
        
        // Initialize admin navigation
        initializeAdminNavigation();
        
        // Initialize form submissions
        initializeAdminForms();
    } else {
        if (!adminPanelToggle) console.log('Admin panel toggle not found');
        if (!adminPanel) console.log('Admin panel not found');
    }
}

// Initialize admin navigation
function initializeAdminNavigation() {
    const createUserBtn = document.getElementById('createUserBtn');
    const manageUsersBtn = document.getElementById('manageUsersBtn');
    const createTMBtn = document.getElementById('createTMBtn');
    const createTLBtn = document.getElementById('createTLBtn');
    
    const createUserSection = document.getElementById('createUserSection');
    const manageUsersSection = document.getElementById('manageUsersSection');
    const createTMSection = document.getElementById('createTMSection');
    const createTLSection = document.getElementById('createTLSection');
    
    // Create User section
    if (createUserBtn && createUserSection) {
        createUserBtn.addEventListener('click', function() {
            showSection(createUserSection, [manageUsersSection, createTMSection, createTLSection]);
            setActiveButton(createUserBtn, [manageUsersBtn, createTMBtn, createTLBtn]);
        });
    }
    
    // Manage Users section
    if (manageUsersBtn && manageUsersSection) {
        manageUsersBtn.addEventListener('click', function() {
            showSection(manageUsersSection, [createUserSection, createTMSection, createTLSection]);
            setActiveButton(manageUsersBtn, [createUserBtn, createTMBtn, createTLBtn]);
        });
    }
    
    // Create TM section
    if (createTMBtn && createTMSection) {
        createTMBtn.addEventListener('click', function() {
            showSection(createTMSection, [createUserSection, manageUsersSection, createTLSection]);
            setActiveButton(createTMBtn, [createUserBtn, manageUsersBtn, createTLBtn]);
        });
    }

    // Create TL section
    if (createTLBtn && createTLSection) {
        createTLBtn.addEventListener('click', function() {
            showSection(createTLSection, [createUserSection, manageUsersSection, createTMSection]);
            setActiveButton(createTLBtn, [createUserBtn, manageUsersBtn, createTMBtn]);
        });
    }

    // Agent creation removed
}

// Helper function to show a section and hide others
function showSection(sectionToShow, sectionsToHide) {
    if (sectionToShow) sectionToShow.style.display = 'block';
    sectionsToHide.forEach(section => {
        if (section) section.style.display = 'none';
    });
}

// Helper function to set active button state
function setActiveButton(buttonToActivate, buttonsToDeactivate) {
    if (buttonToActivate) buttonToActivate.classList.add('active');
    buttonsToDeactivate.forEach(button => {
        if (button) button.classList.remove('active');
    });
}

// Initialize admin forms
function initializeAdminForms() {
    // Create User Form Submission
    const createUserForm = document.getElementById('createUserForm');
    if (createUserForm) {
        createUserForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(createUserForm);
            
            fetch(createUserForm.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => {
                if (response.redirected) {
                    window.location.href = response.url;
                    return { success: true };
                }
                return response.json();
            })
            .then(data => {
                if (data && data.success) {
                    Swal.fire('Success', data.message || 'User created successfully', 'success');
                    createUserForm.reset();
                    // Refresh the users list if manage users section is visible
                    const manageUsersSection = document.getElementById('manageUsersSection');
                    if (manageUsersSection && manageUsersSection.style.display === 'block') {
                        setTimeout(() => {
                            location.reload();
                        }, 1500);
                    }
                } else if (data && data.error) {
                    Swal.fire('Error', data.error, 'error');
                }
            })
            .catch(error => {
                Swal.fire('Error', 'Failed to create user', 'error');
                console.error('Error:', error);
            });
        });
    }

    // Create Team Manager Form Submission
    const createTMForm = document.getElementById('createTMForm');
    if (createTMForm) {
        createTMForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(createTMForm);
            
            fetch(createTMForm.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => {
                if (response.redirected) {
                    window.location.href = response.url;
                    return { success: true };
                }
                return response.json();
            })
            .then(data => {
                if (data && data.success) {
                    Swal.fire('Success', data.message || 'Team Manager created successfully', 'success');
                    createTMForm.reset();
                    setTimeout(() => {
                        location.reload();
                    }, 1500);
                } else if (data && data.error) {
                    Swal.fire('Error', data.error, 'error');
                }
            })
            .catch(error => {
                Swal.fire('Error', 'Failed to create Team Manager', 'error');
                console.error('Error:', error);
            });
        });
    }

    // Create Team Leader Form Submission
    const createTLForm = document.getElementById('createTLForm');
    if (createTLForm) {
        createTLForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(createTLForm);
            
            fetch(createTLForm.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => {
                if (response.redirected) {
                    window.location.href = response.url;
                    return { success: true };
                }
                return response.json();
            })
            .then(data => {
                if (data && data.success) {
                    Swal.fire('Success', data.message || 'Team Leader created successfully', 'success');
                    createTLForm.reset();
                    setTimeout(() => {
                        location.reload();
                    }, 1500);
                } else if (data && data.error) {
                    Swal.fire('Error', data.error, 'error');
                }
            })
            .catch(error => {
                Swal.fire('Error', 'Failed to create Team Leader', 'error');
                console.error('Error:', error);
            });
        });
    }

    // Create Agent Form Submission
    // Agent creation removed
}

// Initialize hierarchy dropdowns functionality
function initializeHierarchyDropdowns() {
    const roleSelect = document.getElementById('roleSelect');
    const agentTmSelect = document.getElementById('agentTmSelect');
    
    if (roleSelect) {
        // Set initial state
        toggleHierarchyDropdowns();
        
        // Add change listener
        roleSelect.addEventListener('change', toggleHierarchyDropdowns);
    }

    // Agent TL dropdown logic removed
}

// Function to show/hide hierarchy dropdowns based on selected role
function toggleHierarchyDropdowns() {
    const roleSelect = document.getElementById('roleSelect');
    const tmDropdownContainer = document.getElementById('tmDropdownContainer');
    const tlDropdownContainer = document.getElementById('tlDropdownContainer');
    const agentDropdownContainer = document.getElementById('agentDropdownContainer');
    
    const tmSelect = document.getElementById('tmSelect');
    const tlSelect = document.getElementById('tlSelect');
    const agentSelect = document.getElementById('agentSelect');
    
    if (roleSelect) {
        const selectedRole = roleSelect.value.toLowerCase();
        
        // Hide all dropdowns first
        if (tmDropdownContainer) tmDropdownContainer.style.display = 'none';
        if (tlDropdownContainer) tlDropdownContainer.style.display = 'none';
        if (agentDropdownContainer) agentDropdownContainer.style.display = 'none';
        
        // Remove required attributes
        if (tmSelect) tmSelect.removeAttribute('required');
        if (tlSelect) tlSelect.removeAttribute('required');
        if (agentSelect) agentSelect.removeAttribute('required');
        
        // Reset selections
        if (tmSelect) tmSelect.value = '';
        if (tlSelect) tlSelect.value = '';
        if (agentSelect) agentSelect.value = '';
        
        // Show appropriate dropdown based on role
        if (selectedRole === 'tm') {
            if (tmDropdownContainer) tmDropdownContainer.style.display = 'block';
            if (tmSelect) tmSelect.setAttribute('required', 'required');
        } else if (selectedRole === 'tl') {
            if (tlDropdownContainer) tlDropdownContainer.style.display = 'block';
            if (tlSelect) tlSelect.setAttribute('required', 'required');
        } else if (selectedRole === 'agent') {
            if (agentDropdownContainer) agentDropdownContainer.style.display = 'block';
            if (agentSelect) agentSelect.setAttribute('required', 'required');
        }
    }
}

// Function to update agent TL dropdown based on selected TM
// Agent TL dropdown function removed

// Make functions available globally
window.toggleHierarchyDropdowns = toggleHierarchyDropdowns;
// window.updateAgentTLDropdown removed
window.initializeAdminPanel = initializeAdminPanel;