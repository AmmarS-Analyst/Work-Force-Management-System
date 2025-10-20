// Mobile sidebar functionality
document.addEventListener('DOMContentLoaded', function() {
    // Mobile sidebar toggle (for responsive design)
    const initMobileSidebar = () => {
        const sidebar = document.querySelector('.sidebar');
        const menuToggle = document.getElementById('mobileMenuToggle');
        
        // Create mobile menu toggle if it doesn't exist
        if (!menuToggle && window.innerWidth < 992) {
            const toggleBtn = document.createElement('button');
            toggleBtn.id = 'mobileMenuToggle';
            toggleBtn.className = 'btn btn-primary mobile-menu-toggle';
            toggleBtn.innerHTML = '<i class="fas fa-bars"></i>';
            toggleBtn.style.position = 'fixed';
            toggleBtn.style.top = '70px';
            toggleBtn.style.left = '10px';
            toggleBtn.style.zIndex = '1001';
            
            toggleBtn.addEventListener('click', function() {
                sidebar.classList.toggle('mobile-open');
            });
            
            document.body.appendChild(toggleBtn);
        }
    };
    
    // Initialize mobile sidebar
    initMobileSidebar();
    
    // Re-init on window resize
    window.addEventListener('resize', initMobileSidebar);
    
    // Close sidebar when clicking outside on mobile
    document.addEventListener('click', function(e) {
        const sidebar = document.querySelector('.sidebar');
        const menuToggle = document.getElementById('mobileMenuToggle');
        
        if (window.innerWidth < 992 && 
            sidebar.classList.contains('mobile-open') &&
            !sidebar.contains(e.target) && 
            (!menuToggle || !menuToggle.contains(e.target))) {
            sidebar.classList.remove('mobile-open');
        }
    });
});