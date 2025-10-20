// Upload functionality
document.addEventListener('DOMContentLoaded', function() {
    initializeUpload();
    initializeFileManagement();
});

function initializeUpload() {
    const uploadForm = document.getElementById('uploadForm');
    if (!uploadForm) return;
    
    uploadForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const formData = new FormData(uploadForm);
        const fileInput = document.getElementById('fileUpload');
        const filename = fileInput.files[0]?.name;
        
        if (!filename) {
            showAlert('Please select a file first', 'error');
            return;
        }
        
        // Create progress toast
        const toastId = window.notifier.createToast(
            `progress-${Date.now()}`,
            'CSV Ingestion Started',
            `Processing ${filename}...`,
            'info'
        );
        
        // Disable upload button during processing
        const uploadBtn = document.getElementById('uploadBtn');
        const originalText = uploadBtn.innerHTML;
        uploadBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
        uploadBtn.disabled = true;
        
        // Simulate progress updates
        let progress = 0;
        const progressInterval = setInterval(() => {
            if (progress < 95) {
                progress += 5;
                window.notifier.updateProgress(toastId, progress);
                
                const messages = [
                    'Loading CSV with memory mapping...',
                    'Minimal data processing...',
                    'Fetching previous records...',
                    'Inserting into database...',
                    'Finalizing ingestion...'
                ];
                
                const messageIndex = Math.floor(progress / 20);
                if (messageIndex < messages.length) {
                    window.notifier.updateToast(toastId, messages[messageIndex]);
                }
            }
        }, 500);
        
        fetch(uploadForm.action, {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            clearInterval(progressInterval);
            window.notifier.updateProgress(toastId, 100);
            
            // Debug logging
            console.log('Upload response:', data);
            console.log('Success flag:', data.success);
            console.log('Message:', data.message);
            
            // Handle response format - check for success flag or message content
            const isSuccess = data.success === true || (data.message && data.message.includes('✅'));
            
            if (isSuccess) {
                window.notifier.updateToast(
                    toastId, 
                    'Ingestion Complete!', 
                    `✅ ${data.message || `Processed ${filename} successfully`}`
                );
                document.getElementById(toastId).classList.add('success');
                showAlert(data.message || 'File processed successfully!', 'success');
            } else {
                window.notifier.updateToast(
                    toastId, 
                    'Ingestion Failed', 
                    `❌ ${data.message || 'Failed to process file'}`
                );
                document.getElementById(toastId).classList.add('error');
                showAlert(data.message || 'Failed to process file', 'error');
            }
        })
        .catch(error => {
            clearInterval(progressInterval);
            window.notifier.updateProgress(toastId, 100);
            window.notifier.updateToast(
                toastId, 
                'Upload Error', 
                `❌ ${error.message || 'Failed to process file'}`
            );
            document.getElementById(toastId).classList.add('error');
            showAlert('Failed to upload file. Please try again.', 'error');
        })
        .finally(() => {
            uploadBtn.innerHTML = originalText;
            uploadBtn.disabled = false;
            fileInput.value = '';
        });
    });
}

function initializeFileManagement() {
    // File selection change handler
    const fileSelect = document.getElementById('fileSelect');
    if (fileSelect) {
        fileSelect.addEventListener('change', function() {
            // Clear any existing dates when file changes
            const datesCheckboxes = document.getElementById('datesCheckboxes');
            const datesSection = document.getElementById('datesSection');
            
            if (datesCheckboxes) datesCheckboxes.innerHTML = '';
            if (datesSection) datesSection.style.display = 'none';
            
            const deleteEntire = document.getElementById('deleteEntire');
            if (deleteEntire) deleteEntire.checked = true;
        });
    }

    // Show dates button with AJAX
    const showDatesBtn = document.getElementById('showDatesBtn');
    if (showDatesBtn) {
        showDatesBtn.addEventListener('click', async function(e) {
            e.preventDefault();
            const fileSelect = document.getElementById('fileSelect');
            if (!fileSelect || !fileSelect.value) {
                showAlert('Please select a file first', 'warning');
                return;
            }
            
            // Show loading state
            const originalText = showDatesBtn.innerHTML;
            showDatesBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i> Loading...';
            showDatesBtn.disabled = true;
            
            try {
                const csrfToken = getCSRFToken();
                const response = await fetch("/get_dates", {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    body: new URLSearchParams({
                        'csrf_token': csrfToken,
                        'filename': fileSelect.value
                    })
                });

                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                const data = await response.json();
                
                if (data.success && data.dates && data.dates.length > 0) {
                    const datesContainer = document.getElementById('datesCheckboxes');
                    if (datesContainer) {
                        datesContainer.innerHTML = '';
                        
                        data.dates.forEach((date, index) => {
                            const dateItem = document.createElement('div');
                            dateItem.className = 'form-check';
                            dateItem.innerHTML = `
                                <input class="form-check-input" type="checkbox" 
                                       name="selected_dates" 
                                       value="${date}" 
                                       id="date-${index}">
                                <label class="form-check-label" for="date-${index}">
                                    ${date}
                                </label>
                            `;
                            datesContainer.appendChild(dateItem);
                        });
                        
                        const datesSection = document.getElementById('datesSection');
                        const deleteDates = document.getElementById('deleteDates');
                        if (datesSection) datesSection.style.display = 'block';
                        if (deleteDates) deleteDates.checked = true;
                    }
                } else {
                    showAlert('No dates found in the selected file', 'info');
                }
            } catch (error) {
                console.error('Error loading dates:', error);
                showAlert('Failed to load dates from the selected file', 'error');
            } finally {
                showDatesBtn.innerHTML = originalText;
                showDatesBtn.disabled = false;
            }
        });
    }

    // Form submission validation
    const fileManagementForm = document.getElementById('fileManagementForm');
    if (fileManagementForm) {
        fileManagementForm.addEventListener('submit', function(e) {
            const actionButton = document.activeElement;
            const action = actionButton ? actionButton.value : '';
            const deleteOption = document.querySelector('input[name="delete_option"]:checked');
            
            // Validate deletion requests
            if (action === 'create_delete_request') {
                const reason = document.getElementById('deleteReason');
                if (!reason || !reason.value.trim()) {
                    e.preventDefault();
                    showAlert('Please provide a reason for deletion', 'error');
                    return;
                }                        
                
                if (deleteOption && deleteOption.value === 'dates') {
                    const checkedDates = document.querySelectorAll('#datesSection input[type="checkbox"]:checked');
                    if (checkedDates.length === 0) {
                        e.preventDefault();
                        showAlert('Please select at least one date', 'error');
                        return;
                    }
                }
                
                if (!confirm('Submit this deletion request for admin approval?')) {
                    e.preventDefault();
                }
            }
        });
    }
}

// Toggle date selection visibility
function toggleDatesSection(show) {
    const datesSection = document.getElementById('datesSection');
    if (!datesSection) return;
    
    datesSection.style.display = show ? 'block' : 'none';
    
    if (!show) {
        const checkboxes = document.querySelectorAll('#datesSection input[type="checkbox"]');
        checkboxes.forEach(checkbox => {
            checkbox.checked = false;
        });
    }
}

// Make function available globally
window.toggleDatesSection = toggleDatesSection;