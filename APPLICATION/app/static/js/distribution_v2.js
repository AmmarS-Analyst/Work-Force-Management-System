// ==========================
// 1️⃣ Agent Search Functions
// ==========================
async function fetchAgentRecords(name, date = "") {
    let url = `/api/search-agent?name=${encodeURIComponent(name)}`;
    if (date) url += `&date=${date}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error("Failed to fetch agent records");
    return await res.json();
}

// Helper: Deduplicate records by date (keep latest only)
function deduplicateRecords(records) {
    const seen = new Map();
    records.forEach((r) => {
        const dateKey = new Date(r.log_time).toISOString().split("T")[0];
        if (!seen.has(dateKey)) {
            seen.set(dateKey, r);
        } else {
            const existing = seen.get(dateKey);
            if (new Date(r.log_time) > new Date(existing.log_time)) {
                seen.set(dateKey, r);
            }
        }
    });
    return Array.from(seen.values()).sort(
        (a, b) => new Date(b.log_time) - new Date(a.log_time)
    );
}

function renderRecords(records, title = "") {
    let html = title ? `<h5>${title}</h5>` : "";
    records.forEach((r, idx) => {
        html += `
            <div class="card mb-2 p-2 shadow-sm border">
                ${title === "" ? `<strong>${idx === 0 ? "Latest Record" : "Previous Record"}</strong><br>` : ""}
                <span><b>Agent:</b> ${r.agent_name}</span><br>
                <span><b>Designation:</b> ${r.designation || "-"}</span><br>
                <span><b>Role:</b> ${r.role || "-"}</span><br>
                <span><b>Group:</b> ${r.group_name || "-"}</span><br>
                <span><b>TM:</b> ${r.tm_name || "-"}</span><br>
                <span><b>TL:</b> ${r.tl_name || "-"}</span><br>
                <span><b>Status:</b> 
                    <span class="badge ${r.status === "Employee"
                        ? "bg-success"
                        : r.status === "Lay Off"
                        ? "bg-danger"
                        : r.status === "Long Leave"
                        ? "bg-warning text-dark"
                        : "bg-secondary"}">
                        ${r.status || "-"}
                    </span>
                </span><br>
                <small class="text-muted"><b>Updated:</b> ${r.log_time}</small>
            </div>
        `;
    });
    return html;
}

// Search button click
document.getElementById("search-btn").addEventListener("click", async () => {
    const name = document.getElementById("agent-search").value.trim();
    const searchResults = document.getElementById("search-results");
    const dateFilter = document.getElementById("date-filter");
    const searchDate = document.getElementById("search-date");

    if (!name) {
        searchResults.innerHTML = `<div class="alert alert-warning">⚠️ Please enter an agent name</div>`;
        dateFilter.style.display = "none";
        return;
    }

    try {
        const data = await fetchAgentRecords(name);
        if (!data || !data.records || !data.records.length) {
            searchResults.innerHTML = `<div class="alert alert-info">No records found.</div>`;
            dateFilter.style.display = "none";
            return;
        }

        const uniqueRecords = deduplicateRecords(data.records);
        searchResults.innerHTML = renderRecords(uniqueRecords);

        if (data.dates && data.dates.length) {
            searchDate.innerHTML = `<option value="">-- Select Date --</option>`;
            data.dates.forEach((d) => {
                searchDate.innerHTML += `<option value="${d}">${d}</option>`;
            });
            dateFilter.style.display = "block";
        } else {
            dateFilter.style.display = "none";
        }
    } catch (err) {
        console.error(err);
        searchResults.innerHTML = `<div class="alert alert-danger">❌ Error fetching results</div>`;
    }
});

// Date filter change
document.getElementById("search-date").addEventListener("change", async (e) => {
    const name = document.getElementById("agent-search").value.trim();
    const date = e.target.value;
    const searchResults = document.getElementById("search-results");
    if (!name || !date) return;

    try {
        const data = await fetchAgentRecords(name, date);
        if (!data || !data.records || !data.records.length) {
            searchResults.innerHTML = `<div class="alert alert-info">No records found for ${date}.</div>`;
            return;
        }

        const uniqueRecords = deduplicateRecords(data.records);
        searchResults.innerHTML = renderRecords(uniqueRecords, `Record(s) on ${date}:`);
    } catch (err) {
        console.error(err);
        searchResults.innerHTML = `<div class="alert alert-danger">❌ Error fetching date-specific results</div>`;
    }
});

// Trigger search on Enter key
document.getElementById("agent-search").addEventListener("keypress", (e) => {
    if (e.key === "Enter") {
        e.preventDefault();
        document.getElementById("search-btn").click();
    }
});

// ==========================
// 2️⃣ Distribution Viewer with Active/All Filter
// ==========================
function filterAgentList(agentList, filterType) {
    if (filterType === "active") {
        return agentList.filter(agent => agent.status === "Employee" && (!agent.moved_note || agent.moved_note.trim() === ""));
    }
    return agentList;
}

function renderAgents(agentList, containerId, currentContextType, currentContextValue) {
    const grid = document.getElementById(containerId);
    grid.innerHTML = "";

    if (!agentList || !agentList.length) {
        grid.innerHTML = '<div class="no-agents">No agents found</div>';
        return;
    }

    agentList.forEach(agent => {
        const div = document.createElement("div");
        div.classList.add("agent-card");

        // ✅ Active only if assigned and not moved
        let isActive = agent.status === "Employee" &&
                       ((currentContextType === "tm" && agent.tm_name === currentContextValue) ||
                        (currentContextType === "tl" && agent.tl_name === currentContextValue) ||
                        (currentContextType === "group" && agent.group_name === currentContextValue)) &&
                       (!agent.moved_note || agent.moved_note.trim() === "");

        // Apply CSS classes
        if (agent.moved_note && agent.moved_note.trim() !== "") {
            div.classList.add("moved");
        } else {
            div.classList.add(isActive ? "active" : "inactive");
        }

        // Status logic
        let statusColor = "green";
        let statusLabelText = agent.status || "Employee";
        if (agent.status === "Long Leave") statusColor = "gold";
        else if (agent.status === "Lay Off") { statusColor = "red"; isActive = false; }
        else if (agent.status === "Resigned") { statusColor = "gray"; isActive = false; }

        const activeLabel = isActive ? "Active" : "Inactive";

        let fromSource = agent.from_tm?.trim() && agent.from_tm !== "N/A"
            ? agent.from_tm
            : agent.from_tl?.trim() && agent.from_tl !== "N/A"
            ? agent.from_tl
            : agent.from_group?.trim() && agent.from_group !== "N/A"
            ? agent.from_group
            : "N/A";

        const statusLabel = `
            <span class="status-label" style="
                background-color:${statusColor};
                color:white;
                padding:2px 8px;
                border-radius:8px;
                font-size:0.8rem;
                margin-left:4px;
            ">
                ${statusLabelText}
            </span>
        `;

        div.innerHTML = `
            <strong>${agent.agent_name}</strong><br>
            <span>${activeLabel}</span> ${statusLabel}<br>
            <small>✅ Joined On: ${agent.joined_date || "Unknown"}</small><br>
            <small>📌 From: ${fromSource}</small>
            ${agent.moved_note ? `<br><small>Note: ${agent.moved_note}</small>` : ""}
        `;

        grid.appendChild(div);
    });
}

// ==========================
// Fetch agents dynamically with Active/All filter
// ==========================
["tm-select", "group-select", "tl-select"].forEach(selectId => {
    const gridMap = {
        "tm-select": "tm-agent-grid",
        "group-select": "group-agent-grid",
        "tl-select": "tl-agent-grid"
    };
    const filterMap = {
        "tm-select": "tm-filter",
        "group-select": "group-filter",
        "tl-select": "tl-filter"
    };

    async function loadAgents() {
        const val = document.getElementById(selectId).value;
        const filterType = document.getElementById(filterMap[selectId])?.value || "all";
        if (!val) return;

        try {
            const endpoint = selectId.includes("tm")
                ? `/api/get_tm_agents/${val}`
                : selectId.includes("group")
                ? `/api/get_group_agents/${val}`
                : `/api/get_tl_agents/${val}`;

            const res = await fetch(endpoint);
            const data = await res.json();
            const filteredData = filterAgentList(data, filterType);

            renderAgents(
                filteredData,
                gridMap[selectId],
                selectId.includes("tm") ? "tm" : selectId.includes("group") ? "group" : "tl",
                val
            );
        } catch (err) {
            console.error("Error fetching agents:", err);
        }
    }

    document.getElementById(selectId).addEventListener("change", loadAgents);
    document.getElementById(filterMap[selectId])?.addEventListener("change", loadAgents);
});

// ==========================
// Tab switching for viewer
// ==========================
document.addEventListener("DOMContentLoaded", function() {
    const tabs = document.querySelectorAll(".viewer-tab");
    const contents = document.querySelectorAll(".viewer-content");

    tabs.forEach(tab => {
        tab.addEventListener("click", function() {
            tabs.forEach(t => t.classList.remove("active"));
            contents.forEach(c => c.classList.remove("active"));

            tab.classList.add("active");
            document.getElementById(tab.dataset.tab + "-viewer").classList.add("active");
        });
    });
});

// ==========================
// 3️⃣ TM Form Toggle
// ==========================
function toggleTmReplaceFields() {
    const action = document.getElementById("tmAction").value;
    const replaceDiv = document.getElementById("tmReplaceWithTlDiv");
    const requestingDiv = document.getElementById("tmRequestingTlDiv");
    if (action === "replace") {
        replaceDiv.style.display = "block";
        requestingDiv.style.display = "none";
    } else if (action === "add") {
        replaceDiv.style.display = "none";
        requestingDiv.style.display = "block";
    } else {
        replaceDiv.style.display = "none";
        requestingDiv.style.display = "none";
    }
}

// ==========================
// 4️⃣ TL Swap Fields Toggle
// ==========================
function toggleTlFields() {
    const action = document.getElementById("tlAction").value;
    const swapTlDiv = document.getElementById("swapWithTlDiv");
    const swapAgentDiv = document.getElementById("swapWithAgentDiv");
    if (action === "swap") {
        swapTlDiv.style.display = "block";
        swapAgentDiv.style.display = "block";
    } else {
        swapTlDiv.style.display = "none";
        swapAgentDiv.style.display = "none";
    }
}

// Load TL agents dynamically
async function loadSwapAgents() {
    const selectedTl = document.getElementById("swapWithTl").value;
    const agentSelect = document.getElementById("swapWithAgent");
    agentSelect.innerHTML = '<option value="">-- Select agent to swap with --</option>';

    if (!selectedTl) return;

    try {
        const res = await fetch(`/api/get_tl_agents/${encodeURIComponent(selectedTl)}`);
        if (!res.ok) throw new Error("Failed to fetch agents");

        const data = await res.json();
        if (!Array.isArray(data) || !data.length) return;

        const agentNames = data.map(a => (typeof a === "string" ? a : a.agent_name));
        const uniqueNames = [...new Set(agentNames)];

        uniqueNames.forEach(name => {
            const option = document.createElement("option");
            option.value = name;
            option.textContent = name;
            agentSelect.appendChild(option);
        });
    } catch (err) {
        console.error("Error loading swap agents:", err);
    }
}

// ==========================
// 5️⃣ Flatpickr Date Picker
// ==========================
if (document.getElementById("effective-date")) {
    flatpickr("#effective-date", {
        dateFormat: "Y-m-d",
        altInput: true,
        altFormat: "F j, Y",
        defaultDate: "today",
        allowInput: true
    });
}
