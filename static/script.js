// --- Global variable to store our raw data from the API ---
let allAthleteData = [];

// --- Helper Functions (KEEP - No changes) ---

function formatDate(date) {
    const options = { month: 'short', day: 'numeric', year: 'numeric' };
    return date.toLocaleDateString('en-US', options);
}
        
function getWeekStart(date = new Date()) {
    const d = new Date(date);
    const day = d.getDay();
    const diff = d.getDate() - day + (day === 0 ? -6 : 1); // Adjust when day is Sunday
    
    // --- FIX ---
    // Create a new Date object *and* set its time to midnight
    const weekStartDate = new Date(d.setDate(diff));
    weekStartDate.setHours(0, 0, 0, 0); // Set to 00:00:00.000
    return weekStartDate;
}
        
function formatDateForAPI(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

// --- NEW HELPER ---
// Gets the day name (e.g., "Monday") from a Date object
function getDayName(date) {
    // Note: getDay() returns 0 for Sunday, 1 for Monday, etc.
    const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    return days[date.getDay()];
}

// --- NEW "TRANSLATION" FUNCTION ---
// Takes the raw data and processes it for a specific week
function processDataForWeek(weekStart) {
    // The /data endpoint returns a *list* of athletes.
    // This UI is for one athlete. Try to find Tori, otherwise use the last athlete added.
    let athlete = allAthleteData.find(a => 
        (a.first_name && a.first_name.toLowerCase() === 'tori') || 
        (a.first_name && a.last_name && `${a.first_name} ${a.last_name}`.toLowerCase().includes('tori'))
    );
    
    // If Tori not found, use the last athlete (most recently added)
    if (!athlete && allAthleteData.length > 0) {
        athlete = allAthleteData[allAthleteData.length - 1];
    }
    
    if (!athlete) {
        // Return an empty structure if no data
        return { goal: 0, daily_mileage: {}, total: 0, remaining: 0 };
    }

    const goal = athlete.mileage_goal || 0;
    const weeklyRuns = {
        'Monday': 0, 'Tuesday': 0, 'Wednesday': 0, 'Thursday': 0,
        'Friday': 0, 'Saturday': 0, 'Sunday': 0
    };
    let total = 0;

    // Calculate the end of the selected week
    const weekEnd = new Date(weekStart);
    weekEnd.setDate(weekEnd.getDate() + 6); // 6 days after Monday is Sunday

    // Filter all the athlete's mileage for runs in this week
    athlete.mileage.forEach(run => {
        // Add 'T00:00:00' to the date string to avoid timezone issues
        const runDate = new Date(run.date + 'T00:00:00');
        
        // Check if the run date is within the selected week
        if (runDate >= weekStart && runDate <= weekEnd) {
            const dayName = getDayName(runDate);
            weeklyRuns[dayName] += run.distance;
            total += run.distance;
        }
    });

    const remaining = Math.max(0, goal - total);

    // Return the *exact* data structure that populateTable expects
    return {
        goal: goal,
        daily_mileage: weeklyRuns,
        total: total,
        remaining: remaining
    };
}
        
// --- RENAMED & REWRITTEN ---
// This function NO LONGER fetches. It just triggers the UI update.
function displaySelectedWeek() {
    const status = document.getElementById('status');
    const weekSelect = document.getElementById('weekSelect');
    const selectedValue = weekSelect.value;
    
    // Hide status (loading is already done)
    status.style.display = 'none';
    
    try {
        let weekStart;
        if (selectedValue === 'current') {
            weekStart = getWeekStart();
        } else {
            // Parse the date from the dropdown's value
            weekStart = new Date(selectedValue + 'T00:00:00');
        }
        
        // 1. "Translate" the raw data into a weekly summary
        const weeklyData = processDataForWeek(weekStart);
        
        // 2. Populate the table with that summary
        populateTable(weeklyData, weekStart);
        
    } catch (error) {
        status.className = 'status error';
        status.style.display = 'block';
        status.textContent = `Error displaying week data: ${error.message}.`;
    }
}
        
// --- KEEP (No changes) ---
// This function is perfect as-is, since we feed it the
// exact data structure it expects.
function populateTable(data, weekStart) {
    const tableBody = document.getElementById('mileageTableBody');
    const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
    const dailyMileage = data.daily_mileage || {};
    
    let total = 0;
    
    // Update each day row
    days.forEach((day, index) => {
        const row = tableBody.rows[index];
        const date = new Date(weekStart);
        date.setDate(date.getDate() + index);
        
        row.cells[1].textContent = formatDate(date);
        
        const mileage = dailyMileage[day] || 0;
        const mileageCell = row.cells[2];
        
        if (mileage > 0) {
            mileageCell.textContent = mileage.toFixed(2);
            mileageCell.className = 'mileage-value';
            total += mileage;
        } else {
            mileageCell.textContent = '--';
            mileageCell.className = 'mileage-value empty';
        }
    });
    
    // Update total row
    const totalCell = document.getElementById('totalMileage');
    totalCell.textContent = total.toFixed(2);
    
    // Update summary cards
    const goal = data.goal || 0;
    document.getElementById('goalValue').textContent = goal.toFixed(2);
    document.getElementById('goalDisplay').textContent = goal.toFixed(2);
    document.getElementById('completedMileage').textContent = total.toFixed(2);
    
    const remaining = Math.max(0, goal - total);
    document.getElementById('remainingMileage').textContent = remaining.toFixed(2);
}

// --- REWRITTEN ---
// This is the new main function that runs on page load.
async function initializePage() {
    const status = document.getElementById('status');
    const weekSelect = document.getElementById('weekSelect');

    // Show loading status
    status.className = 'status loading';
    status.style.display = 'block';
    status.textContent = 'Loading athlete data from /data...';

    try {
        // 1. Fetch ALL data from the *correct* endpoint
        const response = await fetch('/data'); // This is your real endpoint
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        allAthleteData = await response.json(); // Store it globally
        
        // Check if we got any data
        if (!allAthleteData || allAthleteData.length === 0) {
            throw new Error("No athlete data found from /data endpoint.");
        }

        // 2. Populate week dropdown (same as before)
        const currentWeekStart = getWeekStart();
        for (let i = 1; i <= 4; i++) {
            const weekDate = new Date(currentWeekStart);
            weekDate.setDate(weekDate.getDate() - (7 * i));
            const option = document.createElement('option');
            option.value = formatDateForAPI(weekDate);
            option.textContent = `Week of ${formatDate(weekDate)}`;
            weekSelect.appendChild(option);
        }
        
        // 3. Add event listener
        weekSelect.addEventListener('change', displaySelectedWeek);

        // 4. Load the data for the current week (using the data we just fetched)
        displaySelectedWeek();

    } catch (error) {
        status.className = 'status error';
        status.style.display = 'block';
        status.textContent = `Error loading data: ${error.message}. Is the backend server running?`;
    }
}

// Start everything when the page loads
window.addEventListener('DOMContentLoaded', initializePage);