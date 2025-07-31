const REFRESH_INTERVAL = 30; // seconds

/**
 * Fetch the list of discovered miner IPs and render them in the DOM.
 */
async function fetchMiners() {
    try {
        const response = await fetch('/api/miners');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const {miners} = await response.json();
        const listEl = document.getElementById('miner-list');
        listEl.innerHTML = '';
        miners.forEach(ip => {
            const li = document.createElement('li');
            li.textContent = ip;
            listEl.appendChild(li);
        });
    } catch (error) {
        console.error('Failed to fetch miners:', error);
    }
}

// Initialize on DOM load and set up periodic refresh
window.addEventListener('DOMContentLoaded', () => {
    fetchMiners();
    setInterval(fetchMiners, REFRESH_INTERVAL * 1000);
});