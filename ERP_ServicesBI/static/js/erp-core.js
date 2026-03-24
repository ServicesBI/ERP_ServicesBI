/**
 * ERP ServicesBI - Core JavaScript
 * Gerencia tema, sidebar e interações do sistema
 */

// ========================================================================
// TEMA (Dark/Light Mode)
// ========================================================================

/**
 * Toggle entre tema escuro e claro
 * Salva preferência no localStorage
 */
function toggleTheme() {
    const html = document.documentElement;
    const currentTheme = html.getAttribute('data-theme') || 'light';
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    
    // Atualiza atributo
    html.setAttribute('data-theme', newTheme);
    
    // Salva preferência
    localStorage.setItem('theme', newTheme);
    
    // Atualiza ícone do botão
    updateThemeIcon(newTheme);
    
    // Log para debug
    console.log('Tema alterado para:', newTheme);
}

/**
 * Atualiza ícone do botão de tema
 */
function updateThemeIcon(theme) {
    const icon = document.getElementById('themeIcon');
    if (icon) {
        icon.textContent = theme === 'dark' ? '☀️' : '🌙';
    }
}

/**
 * Carrega tema salvo ou usa preferência do sistema
 */
function loadTheme() {
    let theme = localStorage.getItem('theme');
    
    // Se não houver tema salvo, detecta preferência do SO
    if (!theme) {
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        theme = prefersDark ? 'dark' : 'light';
    }
    
    // Aplica tema
    document.documentElement.setAttribute('data-theme', theme);
    updateThemeIcon(theme);
}

// ========================================================================
// SIDEBAR
// ========================================================================

/**
 * Toggle submenu - Alterna entre aberto/fechado
 */
function toggleSubmenu(element) {
    event.preventDefault();
    const item = element.parentElement;
    
    // Se já está aberto, fecha. Se está fechado, abre.
    if (item.classList.contains('open')) {
        item.classList.remove('open');
    } else {
        item.classList.add('open');
    }
    
    saveSidebarState();
}

/**
 * Salvar estado dos submenus abertos
 */
function saveSidebarState() {
    const openMenus = [];
    document.querySelectorAll('.erp-sidebar__item').forEach((item, index) => {
        if (item.classList.contains('open')) {
            openMenus.push(index);
        }
    });
    localStorage.setItem('sidebarOpenMenus', JSON.stringify(openMenus));
}

/**
 * Restaurar estado dos submenus
 */
function restoreSidebarState() {
    const saved = localStorage.getItem('sidebarOpenMenus');
    if (saved) {
        const openMenus = JSON.parse(saved);
        const allItems = document.querySelectorAll('.erp-sidebar__item');
        
        // Limpa todos primeiro
        allItems.forEach(item => {
            item.classList.remove('open');
        });
        
        // Abre apenas os que estavam salvos
        openMenus.forEach(index => {
            if (allItems[index]) {
                allItems[index].classList.add('open');
            }
        });
    }
}

/**
 * Toggle sidebar mobile
 */
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');
    
    if (sidebar) {
        sidebar.classList.toggle('open');
    }
    if (overlay) {
        overlay.classList.toggle('open');
    }
}

// ========================================================================
// ALERTS
// ========================================================================

/**
 * Fechar alerts automaticamente
 */
function setupAlerts() {
    const alerts = document.querySelectorAll('.erp-alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.opacity = '0';
            alert.style.transition = 'opacity 0.5s';
            setTimeout(() => alert.remove(), 500);
        }, 5000);
    });
}

// ========================================================================
// CONFIRMAÇÕES
// ========================================================================

/**
 * Confirmar exclusões
 */
function setupDeleteConfirmation() {
    const deleteButtons = document.querySelectorAll('[data-confirm]');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            if (!confirm(this.dataset.confirm || 'Tem certeza que deseja excluir?')) {
                e.preventDefault();
            }
        });
    });
}

// ========================================================================
// INICIALIZAÇÃO
// ========================================================================

document.addEventListener('DOMContentLoaded', function() {
    console.log('📦 ERP Core JS - Inicializando...');
    
    // Carrega tema salvo
    loadTheme();
    
    // Restaura estado dos submenus
    restoreSidebarState();
    
    // Setup alerts
    setupAlerts();
    
    // Setup delete confirmation
    setupDeleteConfirmation();
    
    // Fechar sidebar ao clicar em link no mobile
    const sidebarLinks = document.querySelectorAll('.erp-sidebar__link, .erp-sidebar__submenu-link');
    sidebarLinks.forEach(link => {
        link.addEventListener('click', function() {
            const sidebar = document.getElementById('sidebar');
            const overlay = document.getElementById('sidebarOverlay');
            
            // Se tiver classe 'href' real (não for preventDefault), fecha sidebar
            if (this.href && !this.href.includes('#')) {
                if (sidebar) sidebar.classList.remove('open');
                if (overlay) overlay.classList.remove('open');
            }
        });
    });
    
    console.log('✅ ERP Core JS - Pronto!');
});

// ========================================================================
// ESCUTA MUDANÇA DE TEMA DO SO
// ========================================================================

// Escuta mudança de preferência de cor do SO
if (window.matchMedia) {
    window.matchMedia('(prefers-color-scheme: dark)').addListener(e => {
        if (!localStorage.getItem('theme')) {
            // Se não houver preferência salva, usa a do SO
            const theme = e.matches ? 'dark' : 'light';
            document.documentElement.setAttribute('data-theme', theme);
            updateThemeIcon(theme);
        }
    });
}