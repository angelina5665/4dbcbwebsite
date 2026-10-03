(function () {
  'use strict';

  const SPONSOR_LINKS = Object.freeze([
    'https://bcb88j.com/RFAA8723385',
    'https://2bvbx.com/RFMY4D.BVBX',
    'https://v12luck.com/RFMY4D.V12',
    'https://3x44my.com/RFMY4D.X44',
    'https://ttbet.fun/RFAA9570A03'
  ]);
  const notices = {
    en: 'Payout and How to Bet buttons have a 50% chance of opening one randomly selected sponsored partner.',
    ms: 'Butang Jadual Bayaran dan Cara Bertaruh mempunyai peluang 50% untuk membuka satu rakan tajaan yang dipilih secara rawak.',
    zh: '点击奖金表或如何下注按钮时，有 50% 的机会前往一个随机选择的赞助合作伙伴。'
  };

  function eligible(event) {
    return event.isTrusted && !event.defaultPrevented && event.button === 0 &&
      !event.ctrlKey && !event.metaKey && !event.shiftKey && !event.altKey;
  }

  function guideReferralClick(event) {
    if (!eligible(event) || Math.random() >= 0.50) return;
    const index = Math.floor(Math.random() * SPONSOR_LINKS.length);
    event.preventDefault();
    window.location.assign(SPONSOR_LINKS[index]);
  }

  function translateNotices() {
    const lang = document.documentElement.lang?.toLowerCase().startsWith('zh') ? 'zh' :
      document.documentElement.lang?.toLowerCase().startsWith('ms') ? 'ms' : 'en';
    document.querySelectorAll('[data-guide-referral-notice]').forEach(element => {
      element.textContent = notices[lang];
    });
  }

  function boot() {
    document.querySelectorAll('[data-guide-referral]').forEach(element => {
      element.addEventListener('click', guideReferralClick);
    });
    translateNotices();
    document.addEventListener('site-language-change', translateNotices);
  }

  if (!document.readyState || document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
}());
