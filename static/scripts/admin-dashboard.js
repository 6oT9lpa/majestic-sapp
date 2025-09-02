document.addEventListener('DOMContentLoaded', async () => {
    initTabs('.tab-btn', '.tab-content', '.tab-indicator');
    await initFilters();

    const savedTab = localStorage.getItem('activeAdminTab');
    if (savedTab) {
        const tabElement = document.querySelector(`[data-tab="${savedTab}"]`);
        if (tabElement) {
            tabElement.click();
        }
    }

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
    
    document.getElementById('add-multi-account-btn')?.addEventListener('click', () => {
        showModal('add-multi-account-modal');
    });

    document.getElementById('add-another-account-btn')?.addEventListener('click', () => {
        const container = document.getElementById('accounts-container');
        const newInput = document.createElement('div');
        newInput.className = 'account-input';
        newInput.innerHTML = `
            <div class="account-input-wrapper">
                <input type="text" class="account-url" placeholder="https://forum.majestic-rp.ru/members/username.123456/">
                <select class="account-type">
                    <option value="multi">Мультиаккаунт</option>
                    <option value="bypass">Обход блокировки</option>
                </select>
                <button class="remove-account-btn"><i class="fas fa-times"></i></button>
            </div>
        `;
        container.appendChild(newInput);
        
        newInput.querySelector('.remove-account-btn').addEventListener('click', (e) => {
            e.preventDefault();
            container.removeChild(newInput);
        });
    });

    document.getElementById('submit-add-account')?.addEventListener('click', async () => {
        const mainAccountUrl = document.getElementById('main-account-url').value.trim();
        const comment = document.getElementById('account-comment').value.trim();
        const accountInputs = document.querySelectorAll('.account-input');
        
        if (!mainAccountUrl) {
            showNotification('Введите ссылку на основной аккаунт', 'error');
            return;
        }
        
        const accounts = [];
        let hasErrors = false;
        
        accountInputs.forEach(input => {
            const url = input.querySelector('.account-url').value.trim();
            const type = input.querySelector('.account-type').value;
            
            if (url) {
                if (!url.startsWith('https://forum.majestic-rp.ru/members/')) {
                    input.querySelector('.account-url').style.borderColor = 'var(--status-rejected-text)';
                    hasErrors = true;
                } else {
                    input.querySelector('.account-url').style.borderColor = '';
                    accounts.push({
                        url: url,
                        name: url.split('/').pop().split('.')[0],
                        id: parseInt(url.split('/').pop().split('.')[1]),
                        type: type
                    });
                }
            }
        });
        
        if (hasErrors) {
            showNotification('Некоторые ссылки имеют неверный формат', 'error');
            return;
        }
        
        if (accounts.length === 0) {
            showNotification('Добавьте хотя бы один аккаунт', 'error');
            return;
        }
        
        try {
            const response = await fetch('/dashboard/admin/multi-accounts', {
                method: 'POST',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: new URLSearchParams({
                    'main_account_url': mainAccountUrl,
                    'accounts': JSON.stringify(accounts),
                    'comment': comment
                })
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Ошибка сервера');
            }
            
            showNotification('Данные успешно добавлены', 'success');
            hideModal('add-multi-account-modal');
            loadMultiAccounts();
        } catch (error) {
            showNotification(`Ошибка: ${error.message}`, 'error');
        }
    });

    document.querySelectorAll('.close-modal').forEach(btn => {
        btn.addEventListener('click', function() {
            const modal = this.closest('.modal');
            if (modal.id === 'view-multi-account-modal') {
                removeDoubleClickHandlers();
                currentMultiAccountData = null;
                
                // Очищаем поле с ID
                document.getElementById('edit-account-id').value = '';
                
                // Очищаем список файлов
                document.getElementById('uploaded-files-list').innerHTML = '';
                document.getElementById('file-upload-input').value = '';
            }
            hideModal(modal.id);
        });
    });

    initAppealsListWebSocket();
    fetchAppealsCounters().then(updateCounters);
});

function removeUploadedFile(element) {
    element.closest('.uploaded-file').remove();
}

setInterval(() => {
    if (appealsListSocket && appealsListSocket.readyState === WebSocket.OPEN) {
        appealsListSocket.send('ping');
    }
}, 30000);

let currentFilters = {
    type: 'all',
    status: 'all',
    assignedToMe: false,
    tabId: null
};
let appealsListSocket = null;
let currentMultiAccountData = null;
let doubleClickHandlers = new Map();

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

function initAppealsListWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/messanger/appeals-list-ws`;
    
    appealsListSocket = new WebSocket(wsUrl);
    
    appealsListSocket.onopen = function() {
        console.log('WebSocket для списка обращений подключен');
        loadAppeals(currentFilters.tabId);
    };
    
    appealsListSocket.onmessage = async function(event) {
        try {
            if (event.data === 'pong') {
                return; 
            }
            
            const data = JSON.parse(event.data);
            
            if (data.type === 'counters_update') {
                updateCounters(data.counters);
            }
            else if (data.type === 'appeal_update' || 
                    data.type === 'appeal_status_changed' ||
                    data.type === 'appeal_closed' ||
                    data.type === 'appeal_reassigned' ||
                    data.type === 'appeal_reassigned' ||
                    data.type === 'appeal_created') { 
                
                const activeTab = document.querySelector('.tab-content.active');
                if (activeTab && activeTab.id.includes('appeals')) {
                    const tabId = activeTab.id.replace('-tab', '');
                    await loadAppeals(tabId);
                }
                
                const counters = await fetchAppealsCounters();
                updateCounters(counters);
                
                if (data.type === 'appeal_created') {
                    showNotification('Добавлено новое обращение', 'info');
                }
            }
            
        } catch (error) {
            if (event.data !== 'pong') {
                console.error('Ошибка обработки WebSocket сообщения:', error, event.data);
            }
        }
    };
    
    appealsListSocket.onclose = function() {
        console.log('WebSocket для списка обращений отключен, переподключение через 3 секунды...');
        setTimeout(initAppealsListWebSocket, 3000);
    };
    
    appealsListSocket.onerror = function(error) {
        console.error('WebSocket ошибка:', error);
    };
}

async function fetchAppealsCounters() {
    try {
        const response = await fetch('/dashboard/admin/appeals/counters', {
            credentials: 'include'
        });
        
        if (response.ok) {
            return await response.json();
        }
        return { pending: 0, user_assigned: 0 };
    } catch (error) {
        console.error('Ошибка получения счетчиков:', error);
        return { pending: 0, user_assigned: 0 };
    }
}

function updateCounters(counters) {
    const pendingCounter = document.getElementById('pending-counter-value');
    const assignedCounter = document.getElementById('assigned-counter-value');
    
    if (pendingCounter) {
        pendingCounter.textContent = counters.pending || 0;
    }
    
    if (assignedCounter) {
        assignedCounter.textContent = counters.user_assigned || 0;
    }
}

async function forceCloseAppeal(appealId) {
    const modal = document.getElementById('confirmModal');
    const closeReasonTextarea = document.getElementById('close-reason');
    const confirmBtn = document.querySelector('.confirm-btn');
    const cancelBtn = document.querySelector('.cancel-confirm-btn');
    
    closeReasonTextarea.value = '';
    
    modal.style.display = 'flex';
    modal.classList.remove('hidden');
    
    return new Promise((resolve) => {
        const confirmHandler = async () => {
            const reason = closeReasonTextarea.value.trim();
            
            if (!reason) {
                showNotification('Укажите причину закрытия', 'error');
                return;
            }
            
            try {
                const formData = new URLSearchParams();
                formData.append('reason', reason);
                
                const response = await fetch(`/dashboard/admin/appeals/${appealId}/force-close?${formData.toString()}`, {
                    method: 'POST',
                    credentials: 'include'
                });
                
                if (!response.ok) throw new Error('Ошибка закрытия');
                
                showNotification('Обращение принудительно закрыто', 'success');
                loadAppeals(currentFilters.tabId);
                
                modal.style.display = 'none';
                modal.classList.add('hidden');
                
                resolve(true);
            } catch (error) {
                showNotification(error.message, 'error');
                resolve(false);
            }
        };
        
        const cancelHandler = () => {
            modal.style.display = 'none';
            modal.classList.add('hidden');
            resolve(false);
        };
        
        confirmBtn.removeEventListener('click', confirmHandler);
        cancelBtn.removeEventListener('click', cancelHandler);
        document.querySelector('.close-modal').removeEventListener('click', cancelHandler);
        
        confirmBtn.addEventListener('click', confirmHandler);
        cancelBtn.addEventListener('click', cancelHandler);
        document.querySelector('.close-modal').addEventListener('click', cancelHandler);
        
        const outsideClickHandler = (e) => {
            if (e.target === modal) {
                cancelHandler();
            }
        };
        
        modal.removeEventListener('click', outsideClickHandler);
        modal.addEventListener('click', outsideClickHandler);
    });
}

async function showReassignToModal(appealId) {
    try {
        const response = await fetch('/dashboard/admin/moderators', {
            credentials: 'include'
        });
        
        if (!response.ok) throw new Error('Ошибка загрузки модераторов');
        
        const moderators = await response.json();
        
        const modal = document.getElementById('reassignModal');
        const moderatorSelect = document.getElementById('moderator-select');
        const confirmBtn = document.querySelector('.confirm-reassign-btn');
        const cancelBtn = document.querySelector('.cancel-reassign-btn');
        
        moderatorSelect.innerHTML = '<option value="">Выберите модератора</option>' +
            moderators.map(m => `<option value="${m.id}">${m.username} (${m.role_name})</option>`).join('');
        
        
        modal.style.display = 'flex';
        modal.classList.remove('hidden');
        
        return new Promise((resolve) => {
            const confirmHandler = async () => {
                const moderatorId = moderatorSelect.value;
                
                if (!moderatorId) {
                    showNotification('Выберите модератора', 'error');
                    return;
                }
                
                try {
                    const formData = new URLSearchParams();
                    formData.append('moderator_id', moderatorId);
                    
                    const response = await fetch(`/dashboard/admin/appeals/${appealId}/reassign-to?${formData.toString()}`, {
                        method: 'POST',
                        credentials: 'include'
                    });
                    
                    if (!response.ok) throw new Error('Ошибка переназначения');
                    
                    showNotification('Обращение переназначено', 'success');
                    
                    modal.style.display = 'none';
                    modal.classList.add('hidden');
                    
                    loadAppeals(currentFilters.tabId);
                    resolve(true);
                } catch (error) {
                    showNotification(error.message, 'error');
                    resolve(false);
                }
            };
            
            const cancelHandler = () => {
                modal.style.display = 'none';
                modal.classList.add('hidden');
                resolve(false);
            };
            
            confirmBtn.removeEventListener('click', confirmHandler);
            cancelBtn.removeEventListener('click', cancelHandler);
            document.querySelector('#reassignModal .close-modal').removeEventListener('click', cancelHandler);
            
            confirmBtn.addEventListener('click', confirmHandler);
            cancelBtn.addEventListener('click', cancelHandler);
            document.querySelector('#reassignModal .close-modal').addEventListener('click', cancelHandler);
            
            const outsideClickHandler = (e) => {
                if (e.target === modal) {
                    cancelHandler();
                }
            };
            
            modal.removeEventListener('click', outsideClickHandler);
            modal.addEventListener('click', outsideClickHandler);
        });
        
    } catch (error) {
        showNotification(error.message, 'error');
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
        localStorage.setItem('activeAdminTab', tabId);

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
                } else if (tabId === 'multi-accounts') {
                    loadMultiAccounts();
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
                    <div class="no-appeals">
                        <i class="fas fa-lock"></i>
                        <p>${error.detail || 'Нет доступа к данным обращениям'}</p>
                        <p class="small-text">Обратитесь к руководителю для получения прав доступа</p>
                    </div>
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

    // Сортируем обращения: сначала назначенные текущему пользователю, потом остальные
    appeals.sort((a, b) => {
        const aIsAssigned = a.assigned_to === currentUser.username;
        const bIsAssigned = b.assigned_to === currentUser.username;
        
        if (aIsAssigned && !bIsAssigned) return -1;
        if (!aIsAssigned && bIsAssigned) return 1;
        return new Date(b.created_at) - new Date(a.created_at);
    });

    appeals.forEach(appeal => {
        const date = new Date(appeal.created_at).toLocaleString();
        const canForceClose = currentUser.role.level >= 6;
        const isCompleted = ['resolved', 'rejected'].includes(appeal.status);
        const isActiveTab = tabId === 'appeals-active';
        const isAssignedToMe = appeal.assigned_to === currentUser.username;
        
        html += `
            <div class="appeal-card ${isAssignedToMe ? 'assigned-to-me' : ''}" data-id="${appeal.id}">
                ${isAssignedToMe ? '<div class="assigned-indicator"></div>' : ''}
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
                        ${canForceClose && isActiveTab && !isCompleted ? `
                        <button class="action-btn danger-action force-close-btn" data-id="${appeal.id}">
                            Принудительно закрыть
                        </button>
                        <button class="action-btn secondary-action reassign-to-btn" data-id="${appeal.id}">
                            Назначить
                        </button>
                        ` : ''}
                        <button class="action-btn secondary-action take-btn" data-id="${appeal.id}">
                            ${isCompleted ? 'Просмотреть' : 'Открыть'}
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

    // Добавляем обработчики только для активных обращений
    if (tabId === 'appeals-active') {
        document.querySelectorAll('.force-close-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const appealId = btn.getAttribute('data-id');
                forceCloseAppeal(appealId);
            });
        });
        
        document.querySelectorAll('.reassign-to-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const appealId = btn.getAttribute('data-id');
                showReassignToModal(appealId);
            });
        });
    }
}

async function loadMultiAccounts(page = 1) {
    const container = document.getElementById('multi-accounts-list');
    if (!container) return;

    container.innerHTML = `
        <div class="loading-row">
            <i class="fas fa-spinner fa-spin"></i> Загрузка данных...
        </div>
    `;

    try {
        const response = await fetch(`/dashboard/admin/multi-accounts?page=${page}`, {
            credentials: 'include'
        });

        if (!response.ok) {
            throw new Error('Ошибка загрузки');
        }

        const data = await response.json();
        renderMultiAccounts(container, data.accounts, data.total_pages, page);
    } catch (error) {
        container.innerHTML = `
            <div class="no-appeals">Ошибка загрузки: ${error.message}</div>
        `;
    }
}

function renderMultiAccounts(container, accounts, totalPages = 1, currentPage = 1) {
    if (!accounts || accounts.length === 0) {
        container.innerHTML = '<div class="no-appeals">Нет данных о мультиаккаунтах</div>';
        return;
    }

    let html = '';

    accounts.forEach(account => {
        const date = new Date(account.created_at).toLocaleString();
        
        html += `
            <div class="multi-account-card" data-id="${account.id}">
                <div class="multi-account-header">
                    <div class="main-account">
                        <span>Основной аккаунт:</span>
                        <a href="${account.main_account.url}" target="_blank" class="main-account-link">
                            ${account.main_account.name} (ID: ${account.main_account.id})
                        </a>
                    </div>
                    <span class="accounts-count">${account.accounts_count} аккаунтов</span>
                </div>
                
                ${account.comment_preview ? `
                <div class="account-comment-preview">
                    ${account.comment_preview}
                </div>
                ` : ''}
                
                <div class="multi-account-footer">
                    <span class="account-date">Добавлено: ${date}</span>
                    <button class="view-details-btn" data-id="${account.id}">
                        Подробнее
                    </button>
                </div>
            </div>
        `;
    });

    if (totalPages > 1) {
        html += renderPagination(currentPage, totalPages, 'multi-accounts');
    }
    
    container.innerHTML = html;
    
    // Добавляем обработчики для кнопок "Подробнее"
    document.querySelectorAll('.view-details-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const accountId = btn.getAttribute('data-id');
            showMultiAccountDetails(accountId);
        });
    });
    
    document.querySelectorAll('#multi-accounts-list .page-btn:not(.disabled)').forEach(btn => {
        btn.addEventListener('click', () => {
            const page = btn.getAttribute('data-page');
            loadMultiAccounts(parseInt(page));
        });
    });
}

async function loadMultiAccountFiles(multiAccountId) {
    try {
        const response = await fetch(`/dashboard/admin/multi-accounts/${multiAccountId}/files`, {
            credentials: 'include'
        });
        
        if (response.ok) {
            const files = await response.json();
            renderFilesList(files);
        }
    } catch (error) {
        console.error('Ошибка загрузки файлов:', error);
    }
}

function renderFilesList(files) {
    const filesList = document.getElementById('files-list');
    
    if (!files || files.length === 0) {
        filesList.innerHTML = '<div class="no-files">Нет прикрепленных файлов</div>';
        return;
    }
    
    let html = '';
    files.forEach(file => {
        html += `
            <div class="file-item">
                <a href="/dashboard/admin/multi-accounts/${currentMultiAccountData.account.id}/files/${file.id}/download" 
                    target="_blank" class="file-link">
                    <i class="fas fa-file"></i> ${file.filename}
                </a>
                <span class="file-size">${formatFileSize(file.file_size)}</span>
                <span class="file-date">${new Date(file.uploaded_at).toLocaleDateString()}</span>
            </div>
        `;
    });
    
    filesList.innerHTML = html;
}

async function showMultiAccountDetails(accountId) {
    try {
        const response = await fetch(`/dashboard/admin/multi-accounts/${accountId}`, {
            credentials: 'include'
        });

        if (!response.ok) {
            throw new Error('Ошибка загрузки деталей');
        }

        const data = await response.json();
        currentMultiAccountData = data;
        renderMultiAccountDetails(data);
        showModal('view-multi-account-modal');
        
        document.getElementById('edit-account-id').value = accountId;     
        addDoubleClickHandlers();
        
    } catch (error) {
        showNotification(error.message, 'error');
    }
}

function addDoubleClickHandlers() {
    removeDoubleClickHandlers(); // Сначала удаляем старые обработчики
    
    document.querySelectorAll('.account-type-badge').forEach(badge => {
        const handler = (e) => {
            e.preventDefault();
            e.stopPropagation();
            
            const accountItem = badge.closest('.detailed-account-item');
            const accountLink = accountItem.querySelector('.account-link');
            const accountUrl = accountLink.href;
            const accountId = extractAccountIdFromUrl(accountUrl);
            
            if (!accountId) {
                showNotification('Не удалось определить ID аккаунта из URL', 'error');
                return;
            }
            
            toggleAccountType(accountId, badge, accountUrl);
        };
        
        badge.addEventListener('dblclick', handler);
        doubleClickHandlers.set(badge, handler);
    });
    
    document.querySelectorAll('.set-main-btn:not(.active)').forEach(btn => {
        const handler = (e) => {
            e.preventDefault();
            e.stopPropagation();
            
            const accountItem = btn.closest('.detailed-account-item');
            const accountLink = accountItem.querySelector('.account-link');
            const accountUrl = accountLink.href;
            const accountId = extractAccountIdFromUrl(accountUrl);
            const accountName = extractUsernameFromUrl(accountUrl);
            
            if (!accountId || !accountName) {
                showNotification('Не удалось определить данные аккаунта из URL', 'error');
                return;
            }
            
            setAsMainAccount(accountId, accountUrl, accountName);
        };
        
        btn.addEventListener('click', handler);
        doubleClickHandlers.set(btn, handler);
    });
}

function removeDoubleClickHandlers() {
    doubleClickHandlers.forEach((handler, element) => {
        element.removeEventListener('dblclick', handler);
        element.removeEventListener('click', handler);
    });
    doubleClickHandlers.clear();
}

async function toggleAccountType(accountId, badgeElement, accountUrl) {
    try {
        const currentType = badgeElement.classList.contains('type-multi') ? 'multi' : 'bypass';
        const newType = currentType === 'multi' ? 'bypass' : 'multi';
        
        const response = await fetch('/dashboard/admin/multi-accounts/update-account-type', {
            method: 'POST',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                multi_account_id: document.getElementById('edit-account-id').value,
                account_id: accountId,
                account_url: accountUrl,
                new_type: newType
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Ошибка обновления типа аккаунта');
        }

        // Обновляем внешний вид
        badgeElement.classList.remove(`type-${currentType}`);
        badgeElement.classList.add(`type-${newType}`);
        badgeElement.textContent = newType === 'multi' ? 'Мультиаккаунт' : 'Обход блокировки';
        
        showNotification('Тип аккаунта успешно изменен', 'success');
        
    } catch (error) {
        showNotification(error.message, 'error');
    }
}

async function setAsMainAccount(accountId, accountUrl, accountName) {
    try {
        const multiAccountId = document.getElementById('edit-account-id').value;
        
        const response = await fetch('/dashboard/admin/multi-accounts/set-main-account', {
            method: 'POST',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                multi_account_id: multiAccountId,
                new_main_account_id: accountId,
                new_main_account_url: accountUrl,
                new_main_account_name: accountName
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Ошибка установки основного аккаунта');
        }

        showNotification('Основной аккаунт успешно изменен', 'success');
        
        // Перезагружаем данные
        showMultiAccountDetails(multiAccountId);
        
    } catch (error) {
        showNotification(error.message, 'error');
    }
}

function renderMultiAccountDetails(data) {
    const accountsList = document.getElementById('detailed-accounts-list');
    const logsList = document.getElementById('account-logs-list');

    let accountsHtml = '';
    
    // Основной аккаунт
    accountsHtml += `
        <div class="detailed-account-item account-main">
            <div class="account-info">
                <a href="${data.account.main_account.url}" target="_blank" class="account-link">
                    ${data.account.main_account.name} (ID: ${data.account.main_account.id})
                </a>
                <span class="main-badge">Основной аккаунт</span>
            </div>
        </div>
    `;
    
    // Остальные аккаунты
    data.account.accounts.forEach(account => {
        accountsHtml += `
            <div class="detailed-account-item">
                <div class="account-info">
                    <a href="${account.url}" target="_blank" class="account-link">
                        ${account.name} (ID: ${account.id})
                    </a>
                    <span class="account-type-badge type-${account.type}" title="Двойной клик для изменения типа">
                        ${account.type === 'multi' ? 'Мультиаккаунт' : 'Обход блокировки'}
                    </span>
                </div>
                <button class="set-main-btn" title="Сделать основным">Сделать основным</button>
            </div>
        `;
    });
    
    accountsList.innerHTML = accountsHtml;

    let logsHtml = '';
    data.logs.forEach(log => {
        logsHtml += `
            <div class="log-item">
                <div class="log-header">
                    <span class="log-type">${getLogTypeName(log.action_type)}</span>
                    <span class="log-date">${new Date(log.changed_at).toLocaleString('ru-RU')}</span>
                </div>
                <div class="log-details">${formatLogDetails(log.action_details)}</div>
                <div class="log-user">Изменено: ${log.user_name}</div>
            </div>
        `;
    });
    logsList.innerHTML = logsHtml;

    document.getElementById('account-comment-modal').value = data.account.comment || '[Нет комментария]';
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

function getLogTypeName(actionType) {
    const types = {
        'created': 'Создание',
        'account_type_changed': 'Изменение типа аккаунта',
        'main_account_changed': 'Изменение основного аккаунта',
        'comment_updated': 'Обновление комментария',
        'updated': 'Обновление',
        'deleted': 'Удаление',
        'add_multi_account': 'Добавление мультиаккаунта',
        'banned_user': 'Блокировка пользователя',
        'unbanned_user': 'Разблокировка пользователя',
        'update_role_user': 'Изменение роли',
        'user_restored': 'Восстановление пользователя',
        'approved_request': 'Одобрение заявки',
        'rejected_request': 'Отклонение заявки',
        'appeal_closed': 'Закрытие обращения',
        'reassigning_appeal': 'Переназначение обращения'
    };
    return types[actionType] || actionType;
}

function formatLogDetails(details) {
    if (typeof details === 'string') {
        try {
            const parsed = JSON.parse(details);
            return formatObjectDetails(parsed);
        } catch (e) {
            return details;
        }
    }
    
    if (typeof details === 'object') {
        return formatObjectDetails(details);
    }
    
    return String(details);
}

function formatObjectDetails(obj) {
    let result = '';
    
    if (obj.account_id) {
        result += `<strong>ID аккаунта:</strong> ${obj.account_id}<br>`;
    }
    
    if (obj.account_url) {
        result += `<strong>URL аккаунта:</strong> <a href="${obj.account_url}" target="_blank">${obj.account_url}</a><br>`;
    }
    
    if (obj.new_type) {
        result += `<strong>Новый тип:</strong> ${obj.new_type === 'multi' ? 'Мультиаккаунт' : 'Обход блокировки'}<br>`;
    }
    
    if (obj.action === 'main_account_changed') {
        result += `<strong>Действие:</strong> Изменение основного аккаунта<br>`;
        if (obj.new_main_account_id) {
            result += `<strong>Новый основной ID:</strong> ${obj.new_main_account_id}<br>`;
        }
        if (obj.new_main_account_name) {
            result += `<strong>Новое имя:</strong> ${obj.new_main_account_name}<br>`;
        }
    }
    
    if (obj.old_main_account) {
        result += `<strong>Старый основной:</strong> ${obj.old_main_account.name} (ID: ${obj.old_main_account.id})<br>`;
    }
    
    if (obj.new_main_account) {
        result += `<strong>Новый основной:</strong> ${obj.new_main_account.name} (ID: ${obj.new_main_account.id})<br>`;
    }

    if (obj.main_account) {
        result += `<strong>Основной аккаунт:</strong> ${obj.main_account}<br>`;
    }
    
    if (obj.accounts_count !== undefined) {
        result += `<strong>Количество аккаунтов:</strong> ${obj.accounts_count}<br>`;
    }
    
    if (obj.comment) {
        const commentPreview = obj.comment.length > 100 ? 
            obj.comment.substring(0, 100) + '...' : obj.comment;
        result += `<strong>Комментарий:</strong> ${commentPreview}<br>`;
    }
    
    if (obj.added_accounts) {
        result += `<strong>Добавленные аккаунты:</strong> ${obj.added_accounts.join(', ')}<br>`;
    }
    
    if (obj.removed_accounts) {
        result += `<strong>Удаленные аккаунты:</strong> ${obj.removed_accounts.join(', ')}<br>`;
    }
    
    if (obj.changed_accounts) {
        result += `<strong>Измененные аккаунты:</strong><br>`;
        obj.changed_accounts.forEach(change => {
            result += `- ${change.account}: ${change.changes.join(', ')}<br>`;
        });
    }
    
    return result || JSON.stringify(obj, null, 2);
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function extractAccountIdFromUrl(url) {
    try {
        const match = url.match(/members\/[^\/]+\.(\d+)/);
        return match ? parseInt(match[1]) : null;
    } catch (error) {
        console.error('Ошибка извлечения ID из URL:', error);
        return null;
    }
}

function extractUsernameFromUrl(url) {
    try {
        const match = url.match(/members\/([^\/]+)\.\d+/);
        return match ? match[1] : null;
    } catch (error) {
        console.error('Ошибка извлечения username из URL:', error);
        return null;
    }
}
