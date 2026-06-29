document.getElementById('nav-toggle')?.addEventListener('click', () => {
  document.getElementById('nav-links')?.classList.toggle('open');
});

const path = location.pathname.replace(/\/$/, '') || '/';
document.querySelectorAll('.nav-links a[data-nav]').forEach((a) => {
  const href = (a.getAttribute('href') || '').replace(/\/$/, '') || '/';
  if (href === path || (href !== '/' && path.startsWith(href))) {
    a.classList.add('active');
  }
});