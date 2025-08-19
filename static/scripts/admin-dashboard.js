document.addEventListener('DOMContentLoaded', async () => {
    initTabs('.tab-btn', '.tab-content', '.tab-indicator');
    await initFilters();

    document.querySelectorAll('#search-input').forEach(input => {
        input.addEventListener('keyup', function(e) {
            if (e.key === 'Enter') {
                const tabContent = this.closest('.tab-content');
                if (tabContent) {
                    const tabId = tabContent.id.replace('-tab', '');
                    loadAppeals(tabId);
                }
            }
        });
    });

    document.querySelectorAll('.search-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const tabContent = this.closest('.tab-content');
            if (tabContent) {
                const tabId = tabContent.id.replace('-tab', '');
                loadAppeals(tabId);
            }
        });
    });
    
    document.getElementById('add-deleted-account-btn')?.addEventListener('click', () => {
        showModal('add-deleted-account-modal');
    });

    document.getElementById('add-another-account-btn')?.addEventListener('click', () => {
        const container = document.getElementById('deleted-accounts-container');
        const newInput = document.createElement('div');
        newInput.className = 'deleted-account-input';
        newInput.innerHTML = `
            <input type="text" class="account-url" placeholder="https://forum.majestic-rp.ru/members/username.123456/">
            <button class="remove-account-btn"><i class="fas fa-times"></i></button>
        `;
        container.appendChild(newInput);
        
        // Добавляем обработчик для кнопки удаления
        newInput.querySelector('.remove-account-btn').addEventListener('click', (e) => {
            e.preventDefault();
            container.removeChild(newInput);
        });
    });

    document.getElementById('submit-add-account')?.addEventListener('click', async () => {
        const mainAccountUrl = document.getElementById('main-account-url').value.trim();
        const accountInputs = document.querySelectorAll('.account-url');
        
        if (!mainAccountUrl) {
            showNotification('Введите ссылку на основной аккаунт', 'error');
            return;
        }
        
        const deletedAccounts = [];
        let hasErrors = false;
        
        accountInputs.forEach(input => {
            const url = input.value.trim();
            if (url) {
                // Проверяем базовую структуру URL перед отправкой
                if (!url.startsWith('https://forum.majestic-rp.ru/members/')) {
                    input.style.borderColor = 'var(--status-rejected-text)';
                    hasErrors = true;
                } else {
                    input.style.borderColor = '';
                    deletedAccounts.push({
                        url: url,
                        name: url.split('/').pop().split('.')[0],
                        id: parseInt(url.split('/').pop().split('.')[1])
                    });
                }
            }
        });
        
        if (hasErrors) {
            showNotification('Некоторые ссылки имеют неверный формат', 'error');
            return;
        }
        
        if (deletedAccounts.length === 0) {
            showNotification('Добавьте хотя бы один удаляемый аккаунт', 'error');
            return;
        }
        
        try {
            const response = await fetch('/dashboard/admin/deleted-accounts', {
                method: 'POST',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: new URLSearchParams({
                    'main_account_url': mainAccountUrl,
                    'deleted_accounts': JSON.stringify(deletedAccounts)
                })
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Ошибка сервера');
            }
            
            showNotification('Данные успешно добавлены', 'success');
            hideModal('add-deleted-account-modal');
            loadDeletedAccounts(); 
        } catch (error) {
            showNotification(`Ошибка: ${error.message}`, 'error');
        }
    });
});

let currentFilters = {
    type: 'all',
    status: 'all',
    assignedToMe: false,
    tabId: null
};

async function loadFiltersFromStorage() {
    const savedFilters = localStorage.getItem('appealsFilters');
    if (savedFilters) {
        currentFilters = JSON.parse(savedFilters);
        document.getElementById('type-filter').value = currentFilters.type;
        document.getElementById('status-filter').value = currentFilters.status;
        document.getElementById('assigned-to-me').checked = currentFilters.assignedToMe;

        if (currentFilters.tabId) {
            const tabElement = document.querySelector(`[data-tab="${currentFilters.tabId}"]`);
            if (tabElement) {
                tabElement.click();
            } else {
                await loadAppeals(currentFilters.tabId);
            }
        }
    }
}

function saveFiltersToStorage() {
    localStorage.setItem('appealsFilters', JSON.stringify(currentFilters));
}

function initTabs(tabButtonsSelector, tabContentsSelector, indicatorSelector) {
    const tabBtns = document.querySelectorAll(tabButtonsSelector);
    const tabContents = document.querySelectorAll(tabContentsSelector);
    const tabIndicator = document.querySelector(indicatorSelector);
    const dropdownBtn = document.getElementById('appeals-dropdown');
    const dropdown = dropdownBtn?.closest('.dropdown');
    const dropdownItems = document.querySelectorAll('.dropdown-item');
    
    const isMobileScreen = () => window.innerWidth <= 768;
    
    // Удаляем старые обработчики и добавляем новые
    tabBtns.forEach(btn => {
        btn.removeEventListener('click', handleTabClick);
        btn.addEventListener('click', handleTabClick);
    });

    function handleTabClick() {
        const tabId = this.getAttribute('data-tab');
        activateTab(tabId, this);
    }
    
    function activateTab(tabId, element = null) {
        const currentActiveTab = document.querySelector(`${tabButtonsSelector}.active`);
        
        if (currentActiveTab === (element || document.querySelector(`${tabButtonsSelector}[data-tab="${tabId}"]`))) {
            return;
        }
        
        tabBtns.forEach(b => b.classList.remove('active'));
        dropdownItems.forEach(item => item.classList.remove('active'));
        
        if (element) {
            element.classList.add('active');
            
            if (element.classList.contains('dropdown-item')) {
                dropdownBtn.innerHTML = element.textContent + 
                    `<svg class="dropdown-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M6 9L12 15L18 9" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>`;
            }
        } else {
            const dropdownItem = document.querySelector(`.dropdown-item[data-tab="${tabId}"]`);
            if (dropdownItem) dropdownItem.classList.add('active');
        }
        
        if (!isMobileScreen()) {
            const targetElement = element || document.querySelector(`${tabButtonsSelector}[data-tab="${tabId}"]`);
            if (targetElement) {
                tabIndicator.style.display = 'block';
                let leftPosition = targetElement.offsetLeft;
                let width = targetElement.offsetWidth;
                
                if (element && element.classList.contains('dropdown-item')) {
                    leftPosition += 5;
                    width -= 10;
                }
                
                tabIndicator.style.width = `${width}px`;
                tabIndicator.style.left = `${leftPosition}px`;
            }
        } else {
            tabIndicator.style.display = 'none';
        }
        
        tabContents.forEach(content => {
            content.classList.remove('active');
            if(content.id === `${tabId}-tab`) {
                content.classList.add('active');
                
                if (tabId === 'appeals-active' || tabId === 'appeals-closed') {
                    loadAppeals(tabId);
                } else if (tabId === 'deleted-accounts') {
                    loadDeletedAccounts();
                }
            }
        });
    }
    
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const tabId = btn.getAttribute('data-tab');
            activateTab(tabId, btn);
        });
    });
    
    if (dropdownBtn) {
        dropdownBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            dropdown.classList.toggle('active');
        });
        
        dropdownItems.forEach(item => {
            item.addEventListener('click', function() {
                const tabId = this.getAttribute('data-tab');
                activateTab(tabId, this);
                dropdown.classList.remove('active');
            });
        });
    }

    document.addEventListener('click', function() {
        if (dropdown) dropdown.classList.remove('active');
    });
    
    window.addEventListener('resize', () => {
        if (isMobileScreen()) {
            if (tabIndicator) {
                tabIndicator.style.display = 'none';
            }
        } else {
            const activeTab = document.querySelector(`${tabButtonsSelector}.active`) || 
                            document.querySelector('.dropdown-item.active');
            if (activeTab && activeTab.getAttribute('data-tab') !== 'settings') {
                tabIndicator.style.display = 'block';
                tabIndicator.style.width = `${activeTab.offsetWidth}px`;
                tabIndicator.style.left = `${activeTab.offsetLeft}px`;
            }
        }
    });
    
    const defaultTab = document.querySelector('.dropdown-item[data-tab="appeals-active"]');
    if (defaultTab) {
        defaultTab.click();
    } else if (tabBtns.length > 0) {
        tabBtns[0].click();
    } else if (dropdownItems.length > 0) {
        dropdownItems[0].click();
    }
}

async function loadAppeals(tabId, page = 1) {
    const tabContent = document.getElementById(`${tabId}-tab`);
    if (!tabContent) return;

    const appealsListContainer = tabContent.querySelector('.appeals-list');
    if (!appealsListContainer) return;

    // Показываем индикатор загрузки только если контейнер пуст
    if (!appealsListContainer.querySelector('.appeal-card')) {
        appealsListContainer.innerHTML = `
            <div class="loading-row">
                <i class="fas fa-spinner fa-spin"></i> Загрузка обращений...
            </div>
        `;
    }

    try {
        let statuses = tabId.includes('active') ? ['pending', 'in_progress'] : ['resolved', 'rejected'];
        
        if (currentFilters.status !== 'all' && tabId.includes('active')) {
            statuses = [currentFilters.status];
        }
        
        const params = new URLSearchParams();
        statuses.forEach(s => params.append('status', s));
        
        if (currentFilters.type !== 'all') {
            params.append('type', currentFilters.type);
        }
        
        if (currentFilters.assignedToMe) {
            params.append('assigned_to_me', 'true');
        }
        
        // Добавляем поисковый запрос
        const searchInput = tabContent.querySelector('#search-input');
        if (searchInput && searchInput.value.trim()) {
            params.append('search', searchInput.value.trim());
        }
        
        params.append('page', page);
        
        const response = await fetch(`/dashboard/admin/appeals?${params.toString()}`, {
            credentials: 'include'
        });

        if (!response.ok) {
            if (response.status === 403) {
                const error = await response.json();
                appealsListContainer.innerHTML = `
                    <div class="no-appeals">${error.detail}</div>
                `;
                return;
            }
            throw new Error('Ошибка загрузки');
        }

        const data = await response.json();
        renderAppeals(appealsListContainer, data.appeals, tabId, data.total_pages, page);
    } catch (error) {
        appealsListContainer.innerHTML = `
            <div class="no-appeals">Ошибка загрузки: ${error.message}</div>
        `;
    }
}

function renderAppeals(container, appeals, tabId, total_pages = 1, currentPage = 1) {
    if (!appeals || appeals.length === 0) {
        container.innerHTML = '<div class="no-appeals">Нет обращений</div>';
        return;
    }

    let html = '';

    appeals.forEach(appeal => {
        const date = new Date(appeal.created_at).toLocaleString();

        html += `
            <div class="appeal-card" data-id="${appeal.id}">
                <div class="appeal-header">
                    <div class="group-appeal-header">
                        <span class="appeal-type">${getTypeName(appeal.type)}</span>
                        <span class="appeal-id">ID: ${appeal.id}</span>
                    </div>
                    <span class="activity-status ${getStatusClass(appeal.status)}">${getStatusName(appeal.status)}</span>
                </div>
                <div class="appeal-user">
                    <strong>Пользователь:</strong> ${appeal.user_name}
                </div>
                <div class="appeal-message">
                    ${appeal.description}
                </div>
                <div class="appeal-footer">
                    <span class="appeal-date">${date}</span>
                    <div class="appeal-actions">
                        <button class="action-btn secondary-action take-btn" data-id="${appeal.id}">
                            Открыть
                        </button>
                    </div>
                </div>
            </div>
        `;
    });

    if (total_pages > 1) {
        html += renderPagination(currentPage, total_pages);
    }
    
    container.innerHTML = html;
    initAppealActions();
    
    document.querySelectorAll('.page-btn:not(.disabled)').forEach(btn => {
        btn.addEventListener('click', () => {
            const page = btn.getAttribute('data-page');
            loadAppeals(tabId, parseInt(page));
        });
    });
}

async function loadDeletedAccounts(page = 1) {
    const container = document.getElementById('deleted-accounts-list');
    if (!container) return;

    container.innerHTML = `
        <div class="loading-row">
            <i class="fas fa-spinner fa-spin"></i> Загрузка данных...
        </div>
    `;

    try {
        const response = await fetch(`/dashboard/admin/deleted-accounts?page=${page}`, {
            credentials: 'include'
        });

        if (!response.ok) {
            throw new Error('Ошибка загрузки');
        }

        const data = await response.json();
        renderDeletedAccounts(container, data.accounts, data.total_pages, page);
    } catch (error) {
        container.innerHTML = `
            <div class="no-appeals">Ошибка загрузки: ${error.message}</div>
        `;
    }
}

function renderDeletedAccounts(container, accounts, totalPages = 1, currentPage = 1) {
    if (!accounts || accounts.length === 0) {
        container.innerHTML = '<div class="no-appeals">Нет данных об удаленных аккаунтах</div>';
        return;
    }

    let html = '';

    accounts.forEach(account => {
        const date = new Date(account.created_at).toLocaleString();
        
        html += `
            <div class="deleted-account-card">
                <div class="deleted-account-header">
                    <div class="main-account">
                        <span>Основной аккаунт:</span>
                        <a href="${account.main_account.url}" target="_blank" class="main-account-link">
                            ${account.main_account.name} (ID: ${account.main_account.id})
                        </a>
                    </div>
                </div>
                
                <div class="deleted-accounts-list">
                    ${account.deleted_accounts.map(deleted => `
                        <div class="deleted-account-item">
                            <a href="${deleted.url}" target="_blank" class="deleted-account-link">
                                ${deleted.name} (ID: ${deleted.id}) удаленный аккаунт
                            </a>
                        </div>
                    `).join('')}
                </div>
                
                <div class="deleted-account-date">Добавлено: ${date}</div>
            </div>
        `;
    });

    if (totalPages > 1) {
        html += renderPagination(currentPage, totalPages, 'deleted-accounts');
    }
    
    container.innerHTML = html;
    
    document.querySelectorAll('#deleted-accounts-list .page-btn:not(.disabled)').forEach(btn => {
        btn.addEventListener('click', () => {
            const page = btn.getAttribute('data-page');
            loadDeletedAccounts(parseInt(page));
        });
    });
}

async function initFilters() {
    await loadFiltersFromStorage();
    const filterBtn = document.querySelector('.filter-btn');
    const dropdown = filterBtn?.closest('.dropdown');
    const applyBtn = document.querySelector('.apply-filters-btn');
    
    if (filterBtn && dropdown) {
        filterBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            dropdown.classList.toggle('active');
        });
    }
    
    if (applyBtn) {
        applyBtn.addEventListener('click', () => {
            const activeTab = document.querySelector('.tab-content.active');
            if (activeTab && activeTab.id.includes('appeals')) {
                dropdown?.classList.remove('active');
                const tabId = activeTab.id.replace('-tab', '');
                currentFilters = {
                    type: document.getElementById('type-filter').value,
                    status: document.getElementById('status-filter').value,
                    assignedToMe: document.getElementById('assigned-to-me').checked,
                    tabId: tabId
                };
                saveFiltersToStorage();
                loadAppeals(tabId);
            }
        });
    }
    
    // Закрытие dropdown при клике вне его
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.dropdown')) {
            document.querySelectorAll('.dropdown').forEach(d => d.classList.remove('active'));
        }
    });
}

function renderPagination(currentPage, totalPages) {
    let html = '<div class="pagination">';

    if (currentPage > 1) {
        html += `<button class="page-btn prev-btn" data-page="${currentPage - 1}">← Назад</button>`;
    } else {
        html += `<button class="page-btn prev-btn disabled" disabled>← Назад</button>`;
    }

    for (let i = 1; i <= totalPages; i++) {
        html += `<button class="page-btn ${i === currentPage ? 'active' : ''}" data-page="${i}">${i}</button>`;
    }

    if (currentPage < totalPages) {
        html += `<button class="page-btn next-btn" data-page="${currentPage + 1}">Далее →</button>`;
    } else {
        html += `<button class="page-btn next-btn disabled" disabled>Далее →</button>`;
    }

    html += '</div>';
    return html;
}

// Вспомогательные функции
function getTypeName(type) {
    const types = {
        'help': 'Помощь',
        'complaint': 'Жалоба',
        'amnesty': 'Амнистия'
    };
    return types[type] || type;
}

function getStatusName(status) {
    const statuses = {
        'pending': 'Ожидает',
        'in_progress': 'В работе',
        'resolved': 'Решено',
        'rejected': 'Отклонено'
    };
    return statuses[status] || status;
}

function getStatusClass(status) {
    switch (status) {
        case 'in_progress': return 'status-progress';
        case 'resolved': return 'status-completed'
        case 'rejected': return 'status-rejected';
        default: return 'status-pending';
    }
}