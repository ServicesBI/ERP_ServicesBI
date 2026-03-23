/**
 * ERP ServicesBI - Core JavaScript
 */

// Toggle submenu - Alterna entre aberto/fechado
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

// Salvar estado dos submenus abertos
function saveSidebarState() {
    const openMenus = [];
    document.querySelectorAll('.erp-sidebar__item').forEach((item, index) => {
        if (item.classList.contains('open')) {
            openMenus.push(index);
        }
    });
    localStorage.setItem('sidebarOpenMenus', JSON.stringify(openMenus));
}

// Restaurar estado dos submenus
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

// Toggle sidebar mobile
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');
    sidebar.classList.toggle('open');
    overlay.classList.toggle('open');
}

// Fechar alerts automaticamente
document.addEventListener('DOMContentLoaded', function() {
    const alerts = document.querySelectorAll('.erp-alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.opacity = '0';
            alert.style.transition = 'opacity 0.5s';
            setTimeout(() => alert.remove(), 500);
        }, 5000);
    });
    
    // Restaurar estado dos submenus
    restoreSidebarState();
});

// Confirmar exclusões
document.addEventListener('DOMContentLoaded', function() {
    const deleteButtons = document.querySelectorAll('[data-confirm]');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            if (!confirm(this.dataset.confirm || 'Tem certeza que deseja excluir?')) {
                e.preventDefault();
            }
        });
    });
});