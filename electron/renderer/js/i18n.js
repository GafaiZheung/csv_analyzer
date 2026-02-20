/**
 * i18n.js – Internationalization module.
 *
 * Usage:
 *   await I18n.init('zh-CN');  // load locale
 *   I18n.t('sidebar.dataSources') => '数据源'
 *   I18n.t('pagination.rows', '100') => '100 行'
 *
 * Adding a new language:
 *   1. Create a new JSON file in locales/ (e.g., locales/ja.json)
 *   2. Add the locale key to I18n.SUPPORTED_LOCALES
 *   3. Done!
 */
const I18n = (() => {
  /**
   * Supported locales: key → display label.
   * To add a new language, add an entry here and create the corresponding JSON file.
   */
  const SUPPORTED_LOCALES = {
    'zh-CN': '中文',
    'en':    'English',
  };

  const DEFAULT_LOCALE = 'zh-CN';

  let _locale = DEFAULT_LOCALE;
  let _messages = {};
  let _fallback = {};  // fallback to default locale

  /**
   * Initialize i18n with the given locale.
   * Loads the JSON file from locales/<locale>.json
   */
  async function init(locale) {
    locale = locale || DEFAULT_LOCALE;
    if (!SUPPORTED_LOCALES[locale]) locale = DEFAULT_LOCALE;
    _locale = locale;

    try {
      _messages = await _loadLocale(locale);
    } catch (e) {
      console.error(`Failed to load locale "${locale}":`, e);
      _messages = {};
    }

    // Load fallback if not default
    if (locale !== DEFAULT_LOCALE) {
      try {
        _fallback = await _loadLocale(DEFAULT_LOCALE);
      } catch { _fallback = {}; }
    } else {
      _fallback = _messages;
    }
  }

  async function _loadLocale(locale) {
    const resp = await fetch(`locales/${locale}.json`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    return resp.json();
  }

  /**
   * Get a translated string by dot-separated key.
   * Supports simple placeholder substitution: {0}, {1}, etc.
   *
   * @param {string} key  e.g. 'sidebar.dataSources'
   * @param {...string} args  replacement values for {0}, {1}, etc.
   * @returns {string}
   */
  function t(key, ...args) {
    let val = _resolve(_messages, key) ?? _resolve(_fallback, key) ?? key;
    // Replace placeholders
    for (let i = 0; i < args.length; i++) {
      val = val.replace(`{${i}}`, args[i]);
    }
    return val;
  }

  function _resolve(obj, path) {
    const parts = path.split('.');
    let cur = obj;
    for (const p of parts) {
      if (cur == null || typeof cur !== 'object') return undefined;
      cur = cur[p];
    }
    return typeof cur === 'string' ? cur : undefined;
  }

  /** Current locale code */
  function locale() { return _locale; }

  /** Get supported locales map */
  function locales() { return { ...SUPPORTED_LOCALES }; }

  /**
   * Apply translations to all elements with data-i18n attribute.
   * <span data-i18n="sidebar.dataSources"></span>
   * Also supports data-i18n-title, data-i18n-placeholder.
   */
  function applyToDOM() {
    document.querySelectorAll('[data-i18n]').forEach(el => {
      const key = el.getAttribute('data-i18n');
      el.textContent = t(key);
    });
    document.querySelectorAll('[data-i18n-title]').forEach(el => {
      el.title = t(el.getAttribute('data-i18n-title'));
    });
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
      el.placeholder = t(el.getAttribute('data-i18n-placeholder'));
    });
  }

  return { init, t, locale, locales, applyToDOM, SUPPORTED_LOCALES, DEFAULT_LOCALE };
})();
