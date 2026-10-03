(function () {
  'use strict';

  const STORAGE_KEY = 'my4d.theme';
  const VALID = new Set(['auto', 'light', 'dark']);
  const media = window.matchMedia('(prefers-color-scheme: dark)');

  function savedPreference() {
    try {
      const value = localStorage.getItem(STORAGE_KEY);
      return VALID.has(value) ? value : 'auto';
    } catch (_) {
      return 'auto';
    }
  }

  function applyTheme(preference) {
    const resolved = preference === 'auto' ? (media.matches ? 'dark' : 'light') : preference;
    document.documentElement.dataset.themePreference = preference;
    document.documentElement.dataset.theme = resolved;
    document.documentElement.style.colorScheme = resolved;
  }

  function savePreference(preference) {
    try {
      if (preference === 'auto') localStorage.removeItem(STORAGE_KEY);
      else localStorage.setItem(STORAGE_KEY, preference);
    } catch (_) {}
    applyTheme(preference);
  }

  applyTheme(savedPreference());

  function mountControl() {
    if (document.querySelector('[data-theme-control]')) return;
    const label = document.createElement('label');
    label.className = 'theme-control';
    label.dataset.themeControl = '';
    label.innerHTML = '<span>Theme</span><select aria-label="Colour theme"><option value="auto">System</option><option value="light">Light</option><option value="dark">Dark</option></select>';
    const select = label.querySelector('select');
    select.value = savedPreference();
    select.addEventListener('change', () => savePreference(select.value));
    document.body.appendChild(label);
  }

  function ensureLocale() {
    if (window.SiteLocale || document.querySelector('script[data-site-locale-loader]')) return;
    const script = document.createElement('script');
    script.src = '/assets/site-locale.js?v=20261003r1';
    script.dataset.siteLocaleLoader = '';
    document.head.appendChild(script);
  }

  const systemChanged = () => {
    if (savedPreference() === 'auto') applyTheme('auto');
  };
  if (typeof media.addEventListener === 'function') media.addEventListener('change', systemChanged);
  else if (typeof media.addListener === 'function') media.addListener(systemChanged);

  function boot() { mountControl(); ensureLocale(); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
