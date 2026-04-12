/**
 * ERP-CORE.JS - VERSÃO LIMPA E OTIMIZADA
 * Sidebar responsivo, Tema, Submenu, Link Ativo
 */

document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    initSidebar();
    initSubmenu();
    initActiveLinks();
    attachEventListeners();
});

// ==========================================
//  TEMA (DARK/LIGHT MODE)
// ==========================================

function initTheme() {
    const savedTheme = localStorage.getItem('erp-theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    
    let isDark = savedTheme === 'dark' || (savedTheme === null && prefersDark);
    applyTheme(isDark);
}

function applyTheme(isDark) {
    const body = document.body;
    const html = document.documentElement;
    const themeIcon = document.getElementById('theme-icon');
    const themeText = document.getElementById('theme-text');
    
    if (isDark) {
        body.classList.remove('light-mode');
        if (themeIcon) themeIcon.textContent = '🌙';
        if (themeText) themeText.textContent = 'Dark';
    } else {
        body.classList.add('light-mode');
        if (themeIcon) themeIcon.textContent = '☀️';
        if (themeText) themeText.textContent = 'Light';
    }
    
    localStorage.setItem('erp-theme', isDark ? 'dark' : 'light');
    html.setAttribute('data-theme', isDark ? 'dark' : 'light');
}

function toggleTheme() {
    const isDarkMode = document.body.classList.contains('light-mode') === false;
    applyTheme(!isDarkMode);
}

// ==========================================
//  SIDEBAR RESPONSIVO
// ==========================================

function initSidebar() {
    const sidebar = document.getElementById('sidebar');
    const toggleBtn = document.querySelector('.toggle-sidebar');
    
    if (!sidebar) return;
    
    // Handler do botao hamburger
    if (toggleBtn) {
        toggleBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            toggleSidebar();
        });
    }
    
    // Fechar ao clicar fora (mobile)
    document.addEventListener('click', (e) => {
        const isClickInsideSidebar = sidebar.contains(e.target);
        const isClickOnToggle = toggleBtn && toggleBtn.contains(e.target);
        
        if (!isClickInsideSidebar && !isClickOnToggle && isMobileView()) {
            if (!sidebar.classList.contains('collapsed')) {
                closeSidebar();
            }
        }
    });
    
    // Fechar ao clicar em link (mobile)
    const sidebarLinks = sidebar.querySelectorAll('a[href]');
    sidebarLinks.forEach(link => {
        link.addEventListener('click', () => {
            if (isMobileView()) {
                closeSidebar();
            }
        });
    });
    
    // Ajustar ao redimensionar
    window.addEventListener('resize', () => {
        if (!isMobileView()) {
            openSidebar();
        }
    });
}

function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const main = document.getElementById('main');
    
    if (!sidebar) return;
    
    sidebar.classList.toggle('collapsed');
    if (main) main.classList.toggle('sidebar-collapsed');
}

function openSidebar() {
    const sidebar = document.getElementById('sidebar');
    const main = document.getElementById('main');
    
    if (!sidebar) return;
    
    sidebar.classList.remove('collapsed');
    if (main) main.classList.remove('sidebar-collapsed');
}

function closeSidebar() {
    const sidebar = document.getElementById('sidebar');
    const main = document.getElementById('main');
    
    if (!sidebar) return;
    
    sidebar.classList.add('collapsed');
    if (main) main.classList.add('sidebar-collapsed');
}

function isMobileView() {
    return window.innerWidth <= 768;
}

// ==========================================
//  SUBMENU EXPANSIVEL
// ==========================================

function initSubmenu() {
    const sidebar = document.getElementById('sidebar');
    if (!sidebar) return;
    
    const hasSubmenuItems = sidebar.querySelectorAll('.sidebar-item.has-submenu');
    
    hasSubmenuItems.forEach(item => {
        const link = item.querySelector('.sidebar-link');
        
        if (!link) return;
        
        link.addEventListener('click', (e) => {
            e.preventDefault();
            toggleSubmenu(item);
        });
    });
}

function toggleSubmenu(item) {
    const sidebar = document.getElementById('sidebar');
    if (!sidebar) return;
    
    const allSubmenuItems = sidebar.querySelectorAll('.sidebar-item.has-submenu');
    
    allSubmenuItems.forEach(otherItem => {
        if (otherItem !== item) {
            otherItem.classList.remove('open');
        }
    });
    
    item.classList.toggle('open');
}

// ==========================================
//  LINK ATIVO
// ==========================================

function initActiveLinks() {
    const currentPath = window.location.pathname;
    const sidebar = document.getElementById('sidebar');
    
    if (!sidebar) return;
    
    const allLinks = sidebar.querySelectorAll('a[href]');
    
    allLinks.forEach(link => {
        const href = link.getAttribute('href');
        
        if (!href) return;
        
        const linkPath = href.replace(/\/$/, '');
        const cleanCurrentPath = currentPath.replace(/\/$/, '');
        
        if (cleanCurrentPath === linkPath || cleanCurrentPath.includes(linkPath)) {
            link.classList.add('active');
            
            const parentSubmenu = link.closest('.sidebar-item.has-submenu');
            if (parentSubmenu) {
                parentSubmenu.classList.add('open');
            }
        } else {
            link.classList.remove('active');
        }
    });
}

// ==========================================
//  EVENT LISTENERS
// ==========================================

function attachEventListeners() {
    // Theme toggle
    const themeBtn = document.querySelector('.theme-toggle');
    if (themeBtn) {
        themeBtn.addEventListener('click', toggleTheme);
    }
    
    // Detectar mudanca de tema do sistema
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
        if (!localStorage.getItem('erp-theme')) {
            applyTheme(e.matches);
        }
    });
    
    // Fechar sidebar com ESC (mobile)
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && isMobileView()) {
            const sidebar = document.getElementById('sidebar');
            if (sidebar && !sidebar.classList.contains('collapsed')) {
                closeSidebar();
            }
        }
    });
}

// ==========================================
//  UTILIDADES
// ==========================================

function formatCurrency(value) {
    if (value === null || value === undefined) return 'R$ 0,00';
    return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    }).format(value);
}

function formatDate(dateString) {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleDateString('pt-BR');
}

function formatDateTime(dateString) {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleString('pt-BR');
}

function copyToClipboard(text) {
    if (!text) {
        console.warn('Nenhum texto para copiar');
        return;
    }
    
    navigator.clipboard.writeText(text).then(() => {
        console.log('Copiado para clipboard!');
    }).catch(err => {
        console.error('Erro ao copiar:', err);
    });
}

function confirmDelete(message = 'Tem certeza que deseja deletar? Esta acao nao pode ser desfeita.') {
    return confirm(message);
}

function showNotification(message, type = 'info', duration = 3000) {
    const alertDiv = document.createElement('div');
    alertDiv.className = 'alert alert-' + type;
    alertDiv.textContent = message;
    alertDiv.style.animation = 'slideIn 0.3s ease';
    
    const main = document.getElementById('main');
    if (main) {
        main.insertBefore(alertDiv, main.firstChild);
        
        setTimeout(() => {
            alertDiv.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => alertDiv.remove(), 300);
        }, duration);
    }
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction() {
        const args = arguments;
        const later = () => {
            clearTimeout(timeout);
            func.apply(this, args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// ==========================================
//  EXPORTAR PARA GLOBAL
// ==========================================

window.toggleTheme = toggleTheme;
window.toggleSidebar = toggleSidebar;
window.openSidebar = openSidebar;
window.closeSidebar = closeSidebar;
window.formatCurrency = formatCurrency;
window.formatDate = formatDate;
window.formatDateTime = formatDateTime;
window.copyToClipboard = copyToClipboard;
window.confirmDelete = confirmDelete;
window.showNotification = showNotification;
window.debounce = debounce;