// Distribution page functionality
document.addEventListener('DOMContentLoaded', function() {
    // Check if distributionData is available
    if (typeof window.distributionData !== 'undefined') {
        initializeDistributionPage();
    } else {
        console.error('Distribution data not loaded');
        // Show error message to user
        const searchResults = document.getElementById('search-results');
        if (searchResults) {
            searchResults.innerHTML = '<div class="alert alert-danger">Distribution data failed to load. Please refresh the page.</div>';
        }
    }
});

function initializeDistributionPage() {
    // Set today's date as default
    const today = new Date().toISOString().split('T')[0];
    const dateInput = document.getElementById('date');
    if (dateInput) {
        dateInput.value = today;
    }
    
    // Initialize viewer functionality
    initViewer();
    
    // Initialize suggestion functionality
    initSuggestions();
    
    // Initialize search functionality
    initSearch();
}

// Initialize the viewer
function initViewer() {
    const tabs = document.querySelectorAll('.viewer-tab');
    const tmSelect = document.getElementById('tm-select');
    const groupSelect = document.getElementById('group-select');
    const tlSelect = document.getElementById('tl-select');
    
    // Handle tab switching
    tabs.forEach(tab => {
        tab.addEventListener('click', function() {
            const tabName = this.getAttribute('data-tab');
            
            // Update active tab
            tabs.forEach(t => t.classList.remove('active'));
            this.classList.add('active');
            
            // Show appropriate content
            document.querySelectorAll('.viewer-content').forEach(content => {
                content.classList.remove('active');
            });
            document.getElementById(tabName + '-viewer').classList.add('active');
        });
    });
    
    // Handle TM selection change
    if (tmSelect) {
        tmSelect.addEventListener('change', function() {
            loadTmData(this.value);
        });
        
        // Load initial data if a TM is already selected
        if (tmSelect.value) {
            loadTmData(tmSelect.value);
        }
    }
    
    // Handle Group selection change
    if (groupSelect) {
        groupSelect.addEventListener('change', function() {
            loadGroupData(this.value);
        });
        
        // Load initial data if a Group is already selected
        if (groupSelect.value) {
            loadGroupData(groupSelect.value);
        }
    }
    
    // Handle TL selection change
    if (tlSelect) {
        tlSelect.addEventListener('change', function() {
            loadTlData(this.value);
        });
        
        // Load initial data if a TL is already selected
        if (tlSelect.value) {
            loadTlData(tlSelect.value);
        }
    }
}

// Initialize suggestion functionality
function initSuggestions() {
    const agentInput = document.getElementById('agent');
    const agentSuggestions = document.getElementById('agent-suggestions');
    const searchInput = document.getElementById('agent-search');
    const searchSuggestions = document.getElementById('search-suggestions');
    
    // Agent input suggestions
    if (agentInput && agentSuggestions && window.distributionData.allAgentNames) {
        agentInput.addEventListener('input', function() {
            showSuggestions(this, agentSuggestions, window.distributionData.allAgentNames, this.value);
        });
    }
    
    // Search input suggestions
    if (searchInput && searchSuggestions && window.distributionData.allAgentNames) {
        searchInput.addEventListener('input', function() {
            showSuggestions(this, searchSuggestions, window.distributionData.allAgentNames, this.value);
        });
    }
    
    // Hide suggestions when clicking outside
    document.addEventListener('click', function(e) {
        if (agentInput && agentSuggestions && !agentInput.contains(e.target) && !agentSuggestions.contains(e.target)) {
            agentSuggestions.style.display = 'none';
        }
        if (searchInput && searchSuggestions && !searchInput.contains(e.target) && !searchSuggestions.contains(e.target)) {
            searchSuggestions.style.display = 'none';
        }
    });
}

// Initialize search functionality
function initSearch() {
    const searchBtn = document.getElementById('search-btn');
    const agentSearch = document.getElementById('agent-search');
    
    if (searchBtn) {
        searchBtn.addEventListener('click', function() {
            searchAgent();
        });
    }
    
    if (agentSearch) {
        agentSearch.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                searchAgent();
            }
        });
    }
}

// Show suggestions for an input field
function showSuggestions(inputElement, suggestionsElement, items, query) {
    if (!query || !items || !Array.isArray(items)) {
        if (suggestionsElement) suggestionsElement.style.display = 'none';
        return;
    }
    
    const suggestions = fuzzySearch(query, items, 0.5);
    
    if (suggestions.length === 0) {
        if (suggestionsElement) suggestionsElement.style.display = 'none';
        return;
    }
    
    suggestionsElement.innerHTML = '';
    suggestions.forEach(suggestion => {
        const div = document.createElement('div');
        div.className = 'suggestion-item';
        div.textContent = suggestion;
        div.addEventListener('click', () => {
            inputElement.value = suggestion;
            suggestionsElement.style.display = 'none';
        });
        suggestionsElement.appendChild(div);
    });
    
    suggestionsElement.style.display = 'block';
}

// Fuzzy search function
function fuzzySearch(query, items, threshold = 0.7) {
    if (!query || !items || !Array.isArray(items)) return [];
    
    const results = [];
    const lowercaseQuery = query.toLowerCase();
    
    // First check for exact matches
    const exactMatch = items.find(item => 
        item && item.toLowerCase() === lowercaseQuery
    );
    
    if (exactMatch) {
        return [exactMatch];
    }
    
    // Then check for partial matches
    items.forEach(item => {
        if (!item) return;
        
        const lowercaseItem = item.toLowerCase();
        
        // Check if query is a substring of item
        if (lowercaseItem.includes(lowercaseQuery)) {
            results.push(item);
            return;
        }
        
        // Check if item is a substring of query (for very short queries)
        if (lowercaseQuery.includes(lowercaseItem) && lowercaseItem.length > 2) {
            results.push(item);
            return;
        }
        
        // Calculate similarity using Levenshtein distance
        const similarity = calculateSimilarity(lowercaseQuery, lowercaseItem);
        if (similarity >= threshold) {
            results.push(item);
        }
    });
    
    // Sort by relevance (exact matches first, then by similarity)
    return results.sort((a, b) => {
        const aLower = a.toLowerCase();
        const bLower = b.toLowerCase();
        
        // Exact matches first
        if (aLower === lowercaseQuery) return -1;
        if (bLower === lowercaseQuery) return 1;
        
        // Then by substring matches
        const aIsSubstring = aLower.includes(lowercaseQuery);
        const bIsSubstring = bLower.includes(lowercaseQuery);
        
        if (aIsSubstring && !bIsSubstring) return -1;
        if (!aIsSubstring && bIsSubstring) return 1;
        
        // Then by similarity score
        const aSimilarity = calculateSimilarity(lowercaseQuery, aLower);
        const bSimilarity = calculateSimilarity(lowercaseQuery, bLower);
        
        return bSimilarity - aSimilarity;
    });
}

// Calculate similarity between two strings (0 to 1)
function calculateSimilarity(str1, str2) {
    if (!str1 || !str2) return 0;
    
    const longer = str1.length > str2.length ? str1 : str2;
    const shorter = str1.length > str2.length ? str2 : str1;
    
    // If the shorter string is empty, return 0
    if (shorter.length === 0) return 0;
    
    // Check for exact match
    if (longer === shorter) return 1;
    
    // Check if one string is contained within the other
    if (longer.includes(shorter)) {
        return shorter.length / longer.length;
    }
    
    // Use Levenshtein distance for more complex comparisons
    const distance = levenshteinDistance(str1, str2);
    return 1 - (distance / Math.max(str1.length, str2.length));
}

// Levenshtein distance algorithm
function levenshteinDistance(str1, str2) {
    if (!str1 || !str2) return Math.max(str1 ? str1.length : 0, str2 ? str2.length : 0);
    
    const matrix = [];
    
    // Initialize matrix
    for (let i = 0; i <= str1.length; i++) {
        matrix[i] = [i];
    }
    for (let j = 0; j <= str2.length; j++) {
        matrix[0][j] = j;
    }
    
    // Fill matrix
    for (let i = 1; i <= str1.length; i++) {
        for (let j = 1; j <= str2.length; j++) {
            if (str1.charAt(i-1) === str2.charAt(j-1)) {
                matrix[i][j] = matrix[i-1][j-1];
            } else {
                matrix[i][j] = Math.min(
                    matrix[i-1][j-1] + 1, // substitution
                    matrix[i][j-1] + 1,   // insertion
                    matrix[i-1][j] + 1    // deletion
                );
            }
        }
    }
    
    return matrix[str1.length][str2.length];
}

// Load TM data
function loadTmData(tmName) {
    const infoHeader = document.getElementById('tm-viewer-info');
    const agentGrid = document.getElementById('tm-agent-grid');
    const searchResults = document.getElementById('search-results');
    
    // Clear previous results
    if (searchResults) {
        searchResults.innerHTML = '';
    }
    
    if (!tmName) {
        if (infoHeader) infoHeader.innerHTML = '';
        if (agentGrid) agentGrid.innerHTML = '<div class="no-agents">Select a TM to view assigned agents</div>';
        return;
    }
    
    // Get agents for this TM
    const agents = window.distributionData.tmToAgents && window.distributionData.tmToAgents[tmName] || [];
    
    if (agents.length === 0) {
        if (infoHeader) infoHeader.innerHTML = '';
        if (agentGrid) agentGrid.innerHTML = '<div class="no-agents">No agents found for this TM</div>';
        return;
    }
    
    // Get the group for this TM
    const groupName = window.distributionData.tmToGroup && window.distributionData.tmToGroup[tmName] || 'Not assigned';
    
    // Display info header
    if (infoHeader) {
        infoHeader.innerHTML = `
            <div class="info-header">
                <i class="fas fa-user-tie"></i> Team Manager: ${tmName}
                <span style="float: right;">
                    <i class="fas fa-people-group"></i> Group: ${groupName}
                </span>
            </div>
        `;
    }
    
    // Display agents in a grid
    if (agentGrid) {
        let html = '';
        agents.forEach(agent => {
            html += `<div class="agent-item">${agent}</div>`;
        });
        agentGrid.innerHTML = html;
    }
}

// Load Group data
function loadGroupData(groupName) {
    const infoHeader = document.getElementById('group-viewer-info');
    const agentGrid = document.getElementById('group-agent-grid');
    const searchResults = document.getElementById('search-results');
    
    // Clear previous results
    if (searchResults) {
        searchResults.innerHTML = '';
    }
    
    if (!groupName) {
        if (infoHeader) infoHeader.innerHTML = '';
        if (agentGrid) agentGrid.innerHTML = '<div class="no-agents">Select a Group to view assigned agents</div>';
        return;
    }
    
    // Get agents for this Group
    const agents = window.distributionData.groupToAgents && window.distributionData.groupToAgents[groupName] || [];
    
    if (agents.length === 0) {
        if (infoHeader) infoHeader.innerHTML = '';
        if (agentGrid) agentGrid.innerHTML = '<div class="no-agents">No agents found for this Group</div>';
        return;
    }
    
    // Get the TM for this Group
    const tmName = window.distributionData.groupToTm && window.distributionData.groupToTm[groupName] || 'Not assigned';
    
    // Display info header
    if (infoHeader) {
        infoHeader.innerHTML = `
            <div class="info-header">
                <i class="fas fa-people-group"></i> Group: ${groupName}
                <span style="float: right;">
                    <i class="fas fa-user-tie"></i> Team Manager: ${tmName}
                </span>
            </div>
        `;
    }
    
    // Display agents in a grid
    if (agentGrid) {
        let html = '';
        agents.forEach(agent => {
            html += `<div class="agent-item">${agent}</div>`;
        });
        agentGrid.innerHTML = html;
    }
}

// Search for a specific agent
function searchAgent() {
    const agentSearch = document.getElementById('agent-search');
    const searchResults = document.getElementById('search-results');
    
    if (!agentSearch || !searchResults) return;
    
    const searchTerm = agentSearch.value.trim();
    
    if (!searchTerm) {
        searchResults.innerHTML = '<div class="alert alert-warning">Please enter an agent name to search</div>';
        return;
    }
    
    // Find exact match first
    let agentInfo = window.distributionData.agentToInfo && window.distributionData.agentToInfo[searchTerm];
    
    // If no exact match, try fuzzy search
    if (!agentInfo) {
        const suggestions = fuzzySearch(searchTerm, window.distributionData.allAgentNames, 0.6);
        
        if (suggestions.length > 0) {
            const bestMatch = suggestions[0];
            agentInfo = window.distributionData.agentToInfo && window.distributionData.agentToInfo[bestMatch];
            
            if (agentInfo) {
                searchResults.innerHTML = `
                    <div class="alert alert-info">
                        <i class="fas fa-info-circle"></i> No exact match found for "${searchTerm}". 
                        Did you mean <strong>${bestMatch}</strong>?
                    </div>
                    <div class="search-results">
                        <h5><i class="fas fa-user"></i> Agent Details: ${bestMatch}</h5>
                        <div class="agent-detail-item">
                            <i class="fas fa-user-tie"></i>
                            <span><strong>Team Manager:</strong> ${agentInfo.tm || 'Not assigned'}</span>
                        </div>
                        <div class="agent-detail-item">
                            <i class="fas fa-user-shield"></i>
                            <span><strong>Team Leader:</strong> ${agentInfo.tl || 'Not assigned'}</span>
                        </div>
                        <div class="agent-detail-item">
                            <i class="fas fa-people-group"></i>
                            <span><strong>Group:</strong> ${agentInfo.group || 'Not assigned'}</span>
                        </div>
                        <div class="agent-detail-item">
                            <i class="fas fa-id-card"></i>
                            <span><strong>Role:</strong> ${agentInfo.role || 'Not specified'}</span>
                        </div>
                        <div class="agent-detail-item">
                            <i class="fas fa-briefcase"></i>
                            <span><strong>Designation:</strong> ${agentInfo.designation || 'Not specified'}</span>
                        </div>
                    </div>
                `;
            } else {
                searchResults.innerHTML = `
                    <div class="alert alert-warning">
                        <i class="fas fa-circle-exclamation"></i> No information found for agent: ${searchTerm}
                    </div>
                `;
            }
            return;
        }
    }
    
    if (!agentInfo) {
        searchResults.innerHTML = `
            <div class="alert alert-warning">
                <i class="fas fa-circle-exclamation"></i> No information found for agent: ${searchTerm}
            </div>
        `;
        return;
    }
    
    searchResults.innerHTML = `
        <div class="search-results">
            <h5><i class="fas fa-user"></i> Agent Details: ${searchTerm}</h5>
            <div class="agent-detail-item">
                <i class="fas fa-user-tie"></i>
                <span><strong>Team Manager:</strong> ${agentInfo.tm || 'Not assigned'}</span>
            </div>
            <div class="agent-detail-item">
                <i class="fas fa-user-shield"></i>
                <span><strong>Team Leader:</strong> ${agentInfo.tl || 'Not assigned'}</span>
            </div>
            <div class="agent-detail-item">
                <i class="fas fa-people-group"></i>
                <span><strong>Group:</strong> ${agentInfo.group || 'Not assigned'}</span>
            </div>
            <div class="agent-detail-item">
                <i class="fas fa-id-card"></i>
                <span><strong>Role:</strong> ${agentInfo.role || 'Not specified'}</span>
            </div>
            <div class="agent-detail-item">
                <i class="fas fa-briefcase"></i>
                <span><strong>Designation:</strong> ${agentInfo.designation || 'Not specified'}</span>
            </div>
        </div>
    `;
}

// Load TL data
function loadTlData(tlName) {
    const infoHeader = document.getElementById('tl-viewer-info');
    const agentGrid = document.getElementById('tl-agent-grid');
    const searchResults = document.getElementById('search-results');
    
    // Clear previous results
    if (searchResults) {
        searchResults.innerHTML = '';
    }
    
    if (!tlName) {
        if (infoHeader) infoHeader.innerHTML = '';
        if (agentGrid) agentGrid.innerHTML = '<div class="no-agents">Select a TL to view assigned agents</div>';
        return;
    }
    
    // Get agents for this TL
    const agents = window.distributionData.tlToAgents && window.distributionData.tlToAgents[tlName] || [];
    
    if (agents.length === 0) {
        if (infoHeader) infoHeader.innerHTML = '';
        if (agentGrid) agentGrid.innerHTML = '<div class="no-agents">No agents found for this TL</div>';
        return;
    }
    
    // Get the TM and group for this TL
    let tmName = 'Not assigned';
    let groupName = 'Not assigned';
    
    if (agents.length > 0) {
        const firstAgent = window.distributionData.agentToInfo && window.distributionData.agentToInfo[agents[0]];
        if (firstAgent) {
            tmName = firstAgent.tm || 'Not assigned';
            groupName = firstAgent.group || 'Not assigned';
        }
    }
    
    // Display info header
    if (infoHeader) {
        infoHeader.innerHTML = `
            <div class="info-header">
                <i class="fas fa-user-shield"></i> Team Leader: ${tlName}
                <span style="float: right;">
                    <i class="fas fa-user-tie"></i> TM: ${tmName} | 
                    <i class="fas fa-people-group"></i> Group: ${groupName}
                </span>
            </div>
        `;
    }
    
    // Display agents in a grid
    if (agentGrid) {
        let html = '';
        agents.forEach(agent => {
            html += `<div class="agent-item">${agent}</div>`;
        });
        agentGrid.innerHTML = html;
    }
}