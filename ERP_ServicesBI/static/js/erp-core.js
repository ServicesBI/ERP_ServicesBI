/**
 * ERP ServicesBI - Core JavaScript (CORRIGIDO)
 * Funções: Sidebar, Submenus, Dark/Light Theme, Alerts
 * 
 * SINCRONIZADO COM erp-theme.css que usa: body.light-mode
 */

/* ============================================================
   TEMA DARK / LIGHT - CORRIGIDO
   ============================================================ */

function toggleTheme() {
    var body = document.body;
    var isLightMode = body.classList.contains('light-mode');
    
    if (isLightMode) {
        // Estava em light, voltar para dark
        body.classList.remove('light-mode');
        localStorage.setItem('erp-theme', 'dark');
        updateThemeIcon('dark');
    } else {
        // Estava em dark, ir para light
        body.classList.add('light-mode');
        localStorage.setItem('erp-theme', 'light');
        updateThemeIcon('light');
    }
    
    // Dispara evento para que gráficos possam se reinicializar
    window.dispatchEvent(new CustomEvent('themeChanged', { 
        detail: { theme: isLightMode ? 'dark' : 'light' } 
    }));
}

function updateThemeIcon(theme) {
    var icon = document.getElementById('themeIcon');
    if (icon) {
        icon.textContent = (theme === 'dark') ? '🌙' : '☀️';
    }
}

function initTheme() {
    var saved = localStorage.getItem('erp-theme');
    
    // Se não tiver salvo, verifica preferência do SO
    if (!saved) {
        saved = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }
    
    var body = document.body;
    
    if (saved === 'light') {
        body.classList.add('light-mode');
        updateThemeIcon('light');
    } else {
        body.classList.remove('light-mode');
        updateThemeIcon('dark');
    }
}

/* ============================================================
   SIDEBAR - TOGGLE SUBMENU
   ============================================================ */

function toggleSubmenu(element) {
    if (event) {
        event.preventDefault();
    }
    
    var item = element.closest('.erp-sidebar__item');
    
    if (item.classList.contains('open')) {
        item.classList.remove('open');
    } else {
        item.classList.add('open');
    }
    
    saveSidebarState();
}

function saveSidebarState() {
    var openMenus = [];
    var items = document.querySelectorAll('.erp-sidebar__item');
    
    items.forEach(function(item, index) {
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
            console.error('Erro ao restaurar sidebar:', e);
        }
    }
}

/* ============================================================
   SIDEBAR MOBILE - TOGGLE COM OVERLAY
   ============================================================ */

function toggleSidebar() {
    var sidebar = document.getElementById('sidebar');
    var overlay = document.getElementById('sidebarOverlay');
    
    if (sidebar) {
        sidebar.classList.toggle('open');
    }
    
    if (overlay) {
        overlay.classList.toggle('open');
    }
}

/* ============================================================
   FECHAR SIDEBAR AO CLICAR EM LINK (MOBILE)
   ============================================================ */

function closeSidebarOnLinkClick() {
    if (window.innerWidth < 768) {
        var links = document.querySelectorAll('.erp-sidebar__submenu-link, .erp-sidebar__link');
        
        links.forEach(function(link) {
            link.addEventListener('click', function() {
                var sidebar = document.getElementById('sidebar');
                var overlay = document.getElementById('sidebarOverlay');
                
                if (sidebar) {
                    sidebar.classList.remove('open');
                }
                if (overlay) {
                    overlay.classList.remove('open');
                }
            });
        });
    }
}

/* ============================================================
   ALERTS - FECHAR AUTOMATICAMENTE
   ============================================================ */

function initAlerts() {
    var alerts = document.querySelectorAll('.erp-alert, .alert');
    
    alerts.forEach(function(alert) {
        // Se não tiver classe 'alert-persistent', fechar automaticamente
        if (!alert.classList.contains('alert-persistent')) {
            setTimeout(function() {
                alert.style.opacity = '0';
                alert.style.transition = 'opacity 0.5s ease';
                
                setTimeout(function() {
                    alert.remove();
                }, 500);
            }, 5000); // 5 segundos
        }
    });
}

/* ============================================================
   CONFIRMAÇÃO DE EXCLUSÃO
   ============================================================ */

function initDeleteConfirmations() {
    var deleteButtons = document.querySelectorAll('[data-confirm]');
    
    deleteButtons.forEach(function(button) {
        button.addEventListener('click', function(e) {
            var message = this.dataset.confirm || 'Tem certeza que deseja excluir?';
            
            if (!confirm(message)) {
                e.preventDefault();
                e.stopPropagation();
            }
        });
    });
}

/* ============================================================
   AUTO-FECHAR SIDEBAR EM RESIZE
   ============================================================ */

function initResponsiveSidebar() {
    window.addEventListener('resize', function() {
        var sidebar = document.getElementById('sidebar');
        var overlay = document.getElementById('sidebarOverlay');
        
        if (window.innerWidth >= 768) {
            // Desktop: remover classes de aberto
            if (sidebar) {
                sidebar.classList.remove('open');
            }
            if (overlay) {
                overlay.classList.remove('open');
            }
        }
    });
}

/* ============================================================
   INIT - EXECUTAR TUDO QUANDO DOCUMENT ESTIVER PRONTO
   ============================================================ */

document.addEventListener('DOMContentLoaded', function() {
    // Temas
    initTheme();
    
    // Sidebar
    restoreSidebarState();
    closeSidebarOnLinkClick();
    initResponsiveSidebar();
    
    // Alerts e confirmações
    initAlerts();
    initDeleteConfirmations();
    
    console.log('✅ ERP Core JS inicializado com sucesso!');
});

/* ============================================================
   EVENT LISTENER PARA REINICIAR ALERTS (AJAX, etc)
   ============================================================ */

document.addEventListener('contentUpdated', function() {
    initAlerts();
    initDeleteConfirmations();
});