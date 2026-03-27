/**
 * ERP ServicesBI - Core JavaScript
 * Funções: Sidebar, Submenus, Dark/Light Theme, Alerts
 */

/* ============================================================
   TEMA DARK / LIGHT
   ============================================================ */

function toggleTheme() {
    var html = document.documentElement;
    var current = html.getAttribute('data-theme');
    var next = (current === 'dark') ? 'light' : 'dark';

    html.setAttribute('data-theme', next);
    localStorage.setItem('erp-theme', next);
    updateThemeIcon(next);

    // Dispara evento para que gráficos possam se reinicializar
    window.dispatchEvent(new CustomEvent('themeChanged', { detail: { theme: next } }));
}

function updateThemeIcon(theme) {
    var icon = document.getElementById('themeIcon');
    if (icon) {
        icon.textContent = (theme === 'dark') ? '☀️' : '🌙';
    }
}

function initTheme() {
    var saved = localStorage.getItem('erp-theme');
    // Se não tiver salvo, verifica preferência do SO
    if (!saved) {
        saved = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }
    document.documentElement.setAttribute('data-theme', saved);
    updateThemeIcon(saved);
}

/* ============================================================
   SIDEBAR - TOGGLE SUBMENU
   ============================================================ */

function toggleSubmenu(element) {
    if (event) event.preventDefault();
    var item = element.parentElement;

    if (item.classList.contains('open')) {
        item.classList.remove('open');
    } else {
        item.classList.add('open');
    }

    saveSidebarState();
}

function saveSidebarState() {
    var openMenus = [];
    document.querySelectorAll('.erp-sidebar__item').forEach(function(item, index) {
        if (item.classList.contains('open')) {
            openMenus.push(index);
        }
    });
    localStorage.setItem('sidebarOpenMenus', JSON.stringify(openMenus));
}

function restoreSidebarState() {
    var saved = localStorage.getItem('sidebarOpenMenus');
    if (saved) {
        try {
            var openMenus = JSON.parse(saved);
            var allItems = document.querySelectorAll('.erp-sidebar__item');

            openMenus.forEach(function(index) {
                if (allItems[index]) {
                    allItems[index].classList.add('open');
                }
            });
        } catch (e) {
            // ignora erro de parse
        }
    }
}

/* ============================================================
   SIDEBAR MOBILE - TOGGLE
   ============================================================ */

function toggleSidebar() {
    var sidebar = document.getElementById('sidebar');
    var overlay = document.getElementById('sidebarOverlay');
    if (sidebar) sidebar.classList.toggle('open');
    if (overlay) overlay.classList.toggle('open');
}

/* ============================================================
   ALERTS - FECHAR AUTOMATICAMENTE
   ============================================================ */

function initAlerts() {
    var alerts = document.querySelectorAll('.erp-alert');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            alert.style.opacity = '0';
            alert.style.transition = 'opacity 0.5s';
            setTimeout(function() { alert.remove(); }, 500);
        }, 5000);
    });
}

/* ============================================================
   CONFIRMAÇÃO DE EXCLUSÃO
   ============================================================ */

function initDeleteConfirmations() {
    var deleteButtons = document.querySelectorAll('[data-confirm]');
    deleteButtons.forEach(function(button) {
        button.addEventListener('click', function(e) {
            if (!confirm(this.dataset.confirm || 'Tem certeza que deseja excluir?')) {
                e.preventDefault();
            }
        });
    });
}

/* ============================================================
   INIT - TUDO JUNTO
   ============================================================ */

document.addEventListener('DOMContentLoaded', function() {
    initTheme();
    restoreSidebarState();
    initAlerts();
    initDeleteConfirmations();
});