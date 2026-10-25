/* Existing page navigation and clinical charts remain owned by portal.js. */
(() => {
  'use strict';
  let handles = [];
  function mount() {
    if (handles.length || !window.KZMotion) return;
    document.querySelectorAll('.kpi,.finding').forEach(el => el.setAttribute('data-kz-light', ''));
    handles = [KZMotion.mountField(document), KZMotion.mountTilt(document)];
  }
  function dispose() {
    handles.forEach(handle => handle.dispose());
    handles = [];
  }
  window.addEventListener('pagehide', dispose);
  window.addEventListener('pageshow', mount);
  mount();
})();
