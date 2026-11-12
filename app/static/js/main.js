// Titan Fitness & Gym Management System - main.js

document.addEventListener('DOMContentLoaded', function () {
  // 1. Dark / Light Mode Toggle
  const themeToggleBtn = document.getElementById('themeToggleBtn');
  const themeIcon = document.getElementById('themeIcon');
  const htmlTag = document.documentElement;

  function applyTheme(theme) {
    htmlTag.setAttribute('data-bs-theme', theme);
    localStorage.setItem('gym_theme', theme);
    if (themeIcon) {
      if (theme === 'dark') {
        themeIcon.classList.remove('bi-moon-stars-fill');
        themeIcon.classList.add('bi-sun-fill');
      } else {
        themeIcon.classList.remove('bi-sun-fill');
        themeIcon.classList.add('bi-moon-stars-fill');
      }
    }
  }

  const savedTheme = localStorage.getItem('gym_theme') || 'light';
  applyTheme(savedTheme);

  if (themeToggleBtn) {
    themeToggleBtn.addEventListener('click', function () {
      const current = htmlTag.getAttribute('data-bs-theme') || 'light';
      applyTheme(current === 'light' ? 'dark' : 'light');
    });
  }

  // 2. Sidebar Toggle for Mobile / Tablets
  const sidebarToggle = document.getElementById('sidebarToggle');
  const sidebar = document.getElementById('sidebar');
  if (sidebarToggle && sidebar) {
    sidebarToggle.addEventListener('click', function () {
      sidebar.classList.toggle('show');
    });
  }

  // 3. Auto dismiss flash alerts after 6 seconds
  const alerts = document.querySelectorAll('.alert-dismissible');
  alerts.forEach(function (alert) {
    setTimeout(function () {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
      if (bsAlert) bsAlert.close();
    }, 6000);
  });

  // 4. Notifications Polling & Dropdown update
  const notifBadge = document.getElementById('notifBadge');
  const notifList = document.getElementById('notifList');

  function updateNotifications() {
    if (!notifBadge) return;
    fetch('/notifications/unread-count')
      .then(res => res.json())
      .then(data => {
        if (data.count > 0) {
          notifBadge.textContent = data.count;
          notifBadge.classList.remove('d-none');
        } else {
          notifBadge.classList.add('d-none');
        }

        if (notifList && data.notifications) {
          if (data.notifications.length === 0) {
            notifList.innerHTML = '<li class="p-3 text-center text-muted small">No new notifications</li>';
          } else {
            let html = '';
            data.notifications.forEach(n => {
              html += `
                <li class="p-2 border-bottom">
                  <div class="d-flex align-items-center">
                    <span class="badge bg-${n.type || 'primary'} me-2 p-1"><i class="bi bi-bell"></i></span>
                    <div class="flex-grow-1 small">
                      <div class="fw-bold">${n.title}</div>
                      <div class="text-secondary">${n.message}</div>
                      <div class="text-muted" style="font-size: 0.72rem;">${n.created_at}</div>
                    </div>
                  </div>
                </li>
              `;
            });
            notifList.innerHTML = html;
          }
        }
      })
      .catch(err => console.debug('Notif check:', err));
  }

  // Check notifications on load if logged in
  if (notifBadge) {
    updateNotifications();
  }
});
