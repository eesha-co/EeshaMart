document.addEventListener('DOMContentLoaded', () => {
  const splash = document.getElementById('splash-screen');
  const mainContent = document.getElementById('main-content');
  
  setTimeout(() => {
    splash.style.opacity = '0';
    splash.style.transition = 'opacity 0.5s ease';
    setTimeout(() => {
      splash.style.display = 'none';
      mainContent.style.display = 'block';
    }, 500);
  }, 3000); // Splash duration
});