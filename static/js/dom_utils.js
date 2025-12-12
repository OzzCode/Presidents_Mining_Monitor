// Lightweight DOM diffing helpers to enable flicker-free updates
// This file attaches a DomUtils namespace on window for use by non-module scripts.
// Usage:
//   DomUtils.morphChildrenByKey(container, dataArray, keyFn, renderFn)
//     - keyFn(item) -> unique key string
//     - renderFn(item, existingNode?) -> HTMLElement (can reuse existingNode)

(function (global) {
  // Wait for DOM to be fully loaded
  function onDocumentReady(callback) {
    if (document.readyState !== 'loading') {
      callback();
    } else {
      document.addEventListener('DOMContentLoaded', callback);
    }
  }

  // Mobile menu functionality
  function setupMobileMenu() {
    const menuToggle = document.getElementById('menuToggle');
    const primaryNav = document.querySelector('.primary-nav');
    
    if (!menuToggle || !primaryNav) return;
    
    // Toggle menu on button click
    menuToggle.addEventListener('click', function(e) {
      e.preventDefault();
      e.stopPropagation();
      
      const isExpanded = menuToggle.getAttribute('aria-expanded') === 'true';
      if (isExpanded) {
        primaryNav.classList.remove('open');
      } else {
        primaryNav.classList.add('open');
      }
      menuToggle.setAttribute('aria-expanded', String(!isExpanded));
    });
    
    // Close menu when clicking outside
    document.addEventListener('click', function(e) {
      if (!primaryNav.contains(e.target) && e.target !== menuToggle) {
        primaryNav.classList.remove('open');
        menuToggle.setAttribute('aria-expanded', 'false');
      }
    });
    
    // Close menu on Escape key
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape' && primaryNav.classList.contains('open')) {
        primaryNav.classList.remove('open');
        menuToggle.setAttribute('aria-expanded', 'false');
        menuToggle.focus();
      }
    });
    
    // Initialize ARIA attributes
    menuToggle.setAttribute('aria-expanded', 'false');
    menuToggle.setAttribute('aria-controls', 'primaryNav');
    menuToggle.setAttribute('aria-label', 'Toggle navigation menu');
  }

  // Dropdown functionality
  function setupDropdowns() {
    // Close all dropdowns when clicking outside
    document.addEventListener('click', function(e) {
      if (!e.target.closest('.dropdown')) {
        document.querySelectorAll('.dropdown').forEach(function(dropdown) {
          dropdown.classList.remove('open');
          const toggle = dropdown.querySelector('.dropdown-toggle');
          if (toggle) {
            toggle.setAttribute('aria-expanded', 'false');
          }
        });
      }
    });

    // Toggle dropdown on click
    document.addEventListener('click', function(e) {
      const toggle = e.target.closest('.dropdown-toggle');
      if (!toggle) return;
      
      e.preventDefault();
      e.stopPropagation();
      
      const dropdown = toggle.closest('.dropdown');
      if (!dropdown) return;
      
      const isExpanded = toggle.getAttribute('aria-expanded') === 'true';
      
      // Close all other dropdowns
      document.querySelectorAll('.dropdown').forEach(function(d) {
        if (d !== dropdown) {
          d.classList.remove('open');
          const otherToggle = d.querySelector('.dropdown-toggle');
          if (otherToggle) otherToggle.setAttribute('aria-expanded', 'false');
        }
      });
      
      // Toggle current dropdown
      if (isExpanded) {
        dropdown.classList.remove('open');
        toggle.setAttribute('aria-expanded', 'false');
      } else {
        dropdown.classList.add('open');
        toggle.setAttribute('aria-expanded', 'true');
      }
    });
    
    // Close dropdowns when clicking on a menu item (for mobile)
    document.querySelectorAll('.dropdown-menu a').forEach(menuItem => {
      menuItem.addEventListener('click', function() {
        const dropdown = this.closest('.dropdown');
        if (dropdown) {
          dropdown.classList.remove('open');
          const toggle = dropdown.querySelector('.dropdown-toggle');
          if (toggle) toggle.setAttribute('aria-expanded', 'false');
        }
      });
    });
  }
  
  function preserveScroll(element, fn) {
    if (!element) return fn();
    const top = element.scrollTop;
    const left = element.scrollLeft;
    const active = document.activeElement;
    const sel = active && active.closest ? active.closest('input,select,textarea,button,a') : null;
    fn();
    element.scrollTop = top;
    element.scrollLeft = left;
    if (sel && sel.focus) sel.focus();
  }

  function morphChildrenByKey(container, items, keyFn, renderFn) {
    if (!container) return;
    const doc = container.ownerDocument || document;
    const map = new Map();
    // build current index by key
    Array.from(container.children).forEach(node => {
      const k = node.getAttribute('data-key');
      if (k) map.set(k, node);
    });

    const frag = doc.createDocumentFragment();
    for (const it of items) {
      const key = String(keyFn(it));
      let node = map.get(key) || null;
      node = renderFn(it, node) || node;
      if (!node) {
        // renderFn must return a node
        node = doc.createElement('div');
        node.textContent = '';
      }
      node.setAttribute('data-key', key);
      frag.appendChild(node);
    }
    // apply with scroll preservation
    preserveScroll(container, () => {
      // only replace children, not the container itself
      container.innerHTML = '';
      container.appendChild(frag);
    });
  }

  function setTextSafe(el, text) {
    if (el && el.textContent !== text) el.textContent = text;
  }

  // Simple concurrency guard to avoid overlapping fetch -> render causing flashes
  function createSerialExecutor() {
    let current = Promise.resolve();
    return function enqueue(task) {
      current = current.then(() => task()).catch(() => {}).then(() => {});
      return current;
    };
  }

  onDocumentReady(function() {
    try {
      // Initialize mobile menu
      setupMobileMenu();
      
      // Initialize dropdowns
      setupDropdowns();
      
      // Make sure other scripts can access DomUtils
      global.DomUtils = { 
        preserveScroll, 
        morphChildrenByKey, 
        setTextSafe, 
        createSerialExecutor,
        setupDropdowns,
        setupMobileMenu
      };
      
      console.log('DOM Utils initialized successfully');
    } catch (error) {
      console.error('Error initializing DOM Utils:', error);
    }
  });
})(window);
