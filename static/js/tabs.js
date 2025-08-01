// Simple tab switching
const tabs = document.querySelectorAll('.tab');
const panels = document.querySelectorAll('.tab-content');
tabs.forEach(t => t.addEventListener('click', () => {
    tabs.forEach(x => x.classList.remove('active'));
    panels.forEach(p => p.classList.add('hidden'));
    t.classList.add('active');
    document.getElementById(t.dataset.tab).classList.remove('hidden');
}));