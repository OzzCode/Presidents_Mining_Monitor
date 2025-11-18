// Lightweight DOM diffing helpers to enable flicker-free updates
// This file attaches a DomUtils namespace on window for use by non-module scripts.
// Usage:
//   DomUtils.morphChildrenByKey(container, dataArray, keyFn, renderFn)
//     - keyFn(item) -> unique key string
//     - renderFn(item, existingNode?) -> HTMLElement (can reuse existingNode)

(function (global) {
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

  global.DomUtils = { preserveScroll, morphChildrenByKey, setTextSafe, createSerialExecutor };
})(window);
