(function(){
  const STORAGE_KEY = 'ui.theme'; // 'light' | 'dark' | ''
  const root = document.documentElement;

  function getSystemPref(){
    return (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) ? 'dark' : 'light';
  }

  function applyTheme(theme){
    if (theme === 'light' || theme === 'dark') {
      root.setAttribute('data-theme', theme);
    } else {
      root.removeAttribute('data-theme'); // fall back to system via @media
    }
  }

  function currentStored(){
    try { return localStorage.getItem(STORAGE_KEY) || ''; } catch { return ''; }
  }

  function saveTheme(theme){
    try {
      if (theme) localStorage.setItem(STORAGE_KEY, theme);
      else localStorage.removeItem(STORAGE_KEY);
    } catch {}
  }

  function init(){
    const stored = currentStored();
    applyTheme(stored || '');

    // Keep button state optional
    const btn = document.getElementById('themeToggle');
    if (btn) {
      btn.addEventListener('click', () => {
        // Determine next theme: toggle between explicit light/dark
        const explicit = root.getAttribute('data-theme');
        const next = explicit === 'dark' ? 'light' : (explicit === 'light' ? 'dark' : (getSystemPref()==='dark' ? 'light' : 'dark'));
        applyTheme(next);
        saveTheme(next);
      });
    }

    // Also react if system changes and no explicit theme selected
    if (window.matchMedia) {
      const mq = window.matchMedia('(prefers-color-scheme: dark)');
      mq.addEventListener?.('change', () => {
        if (!root.getAttribute('data-theme')) {
          applyTheme('');
        }
      });
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
