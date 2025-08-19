
document.addEventListener('DOMContentLoaded', async () => {
    setupFilters();

    initTabs('.dashboard-tabs .tab-btn', '.dashboard-content .tab-content', '.dashboard-tabs .tab-indicator', {
        onTabChange: (tabId) => {
            if (tabId === 'logs') {
                loadLogs();
            } 
            else if (tabId === 'users') {
                loadUsers();
            }
            else if (tabId === 'user-requests') {
                loadRequests();
            }
        },
        saveToLocalStorage: 'generalActiveTab',
    });

    initTabs('#user-details-modal .tab-btn', '#user-details-modal .tab-content', '#user-details-modal .tab-indicator', {
        saveToLocalStorage: 'modalDetailsActiveTab',
    });
});

let filtersVisiblelogs = false;
let filtersVisibleUsers = false;
let filtersVisibleRequests = false;

let currentFiltersLogs = {
    action_type: '',
    page: 1,
    perPage: 20
};

let currentFiltersUsers = {
    page: 1,
    perPage: 20
};

let currentFiltersRequests = {
    page: 1,
    perPage: 20
}

let searchQueries = {
    logs: '',
    users: '',
    requests: ''
};

async function loadLogs(page = currentFiltersLogs.page) {
    currentFiltersLogs.page = page;
    const container = document.querySelector('.logs-list');
    
    if (!container) return;
    
    container.innerHTML = `
        <div class="loading-row">
            <i class="fas fa-spinner fa-spin"></i> Загрузка логов...
        </div>
    `;

    initActionTypeSelector("status-filter");
    
    try {
        const params = new URLSearchParams();
        
        if (currentFiltersLogs.action_type !== 'all') {
            params.append('action_type', currentFiltersLogs.action_type);
        }
        
        if (searchQueries.logs) {
            params.append('search', searchQueries.logs);
        }
        
        params.append('page', currentFiltersLogs.page);
        params.append('per_page', currentFiltersLogs.perPage);
        
        const response = await fetch(`/dashboard/admin/general/logs?${params.toString()}`, {
            credentials: 'include'
        });
        
        if (!response.ok) {
            throw new Error('Ошибка загрузки логов');
        }
        
        const data = await response.json();
        console.log(data);
        renderLogs(data);
    } catch (error) {
        container.innerHTML = `
            <div class="no-logs">Ошибка загрузки: ${error.message}</div>
        `;
    }
}

function renderLogs(data) {
    const container = document.querySelector('.logs-list');
    
    if (!data.logs || data.logs.length === 0) {
        container.innerHTML = '<div class="no-logs">Логов не найдено</div>';
        return;
    }
    
    let html = '';
    
    data.logs.forEach(log => {
        const date = new Date(log.created_at).toLocaleString();
        const user = log.user;
        
        html += `
            <div class="log-entry">
                <div class="log-header">
                    <span class="log-type">${log.action_type}</span>
                    ${user ? `
                    <div class="log-user">
                        <div class="log-user-avatar">${user.username.charAt(0).toUpperCase()}</div>
                        <span>${user.username} (${user.role?.name || 'нет роли'})</span>
                    </div>
                    ` : '<div class="log-user">Гость</div>'}
                </div>
                <div class="log-details">
                    ${log.action_details}
                </div>
                <div class="log-footer">
                    <span class="log-ip">IP: ${log.ip_address}</span>
                    <span class="log-date">${date}</span>
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
    
    console.log('Pagination data:', {
        containerId: 'logs-pagination',
        currentPage: data.page,
        totalPages: data.total_pages,
        perPage: data.per_page
    });

    renderPagination(
        'logs-pagination',
        data.page, 
        data.total,
        data.per_page,
        loadLogs
    );
}

async function loadUsers(page = currentFiltersUsers.page) {
    currentFiltersUsers.page = page;
    const container = document.querySelector('#users-tab .users-list');
    
    if (!container) return;
    
    container.innerHTML = `
        <div class="loading-row">
            <i class="fas fa-spinner fa-spin"></i> Загрузка пользователей...
        </div>
    `;
    
    try {
        const params = new URLSearchParams();
        params.append('page', currentFiltersUsers.page);
        params.append('per_page', currentFiltersUsers.perPage);
        
        if (searchQueries.users) {
            params.append('search', searchQueries.users);
        }
        
        const response = await fetch(`/dashboard/admin/general/users?${params.toString()}`, {
            credentials: 'include'
        });
        
        if (!response.ok) {
            throw new Error('Ошибка загрузки пользователей');
        }
        
        const data = await response.json();
        renderUsers(data);
    } catch (error) {
        container.innerHTML = `
            <div class="no-data">Ошибка загрузки: ${error.message}</div>
        `;
    }
}

function renderUsers(data) {
    const container = document.querySelector('#users-tab .users-list');
    
    if (!data.users || data.users.length === 0) {
        container.innerHTML = '<div class="no-data">Пользователи не найдены</div>';
        renderPagination(
            'users-pagination',
            1,
            0,
            data.per_page || usersPerPage,
            loadUsers
        );
        return;
    }
    
    let html = '';
    
    data.users.forEach(user => {
        const createdDate = new Date(user.created_at).toLocaleDateString();
        const lastLogin = user.last_login ? 
            new Date(user.last_login).toLocaleString() : 'Никогда';
        const isActive = user.last_login ? 
            (new Date() - new Date(user.last_login) < 30 * 24 * 60 * 60 * 1000) : false;
        
        html += `
            <div class="user-card" data-id="${user.id}">
                <div class="user-info">
                    <div class="user-name">
                        ${user.username}
                        <span class="user-id">ID: ${user.id}</span>
                    </div>
                    <div class="user-details">
                        <div class="user-detail">
                            <i class="fas fa-envelope"></i> ${user.email}
                        </div>
                        <div class="user-detail">
                            <i class="fas fa-calendar-alt"></i> ${createdDate}
                        </div>
                        <div class="user-detail">
                            <i class="fas fa-sign-in-alt"></i> ${lastLogin}
                        </div>
                    </div>
                </div>
                <span class="user-role">${user.role}</span>
            </div>
        `;
    });
    
    container.innerHTML = html;
    
    document.querySelectorAll('.user-card').forEach(card => {
        card.addEventListener('click', () => {
            const userId = card.getAttribute('data-id');
            showUserDetails(userId);
        });
    });

    renderPagination(
        'users-pagination',
        data.page,
        data.total,
        data.per_page,
        loadUsers
    );
}

async function showUserDetails(userId, page = 1, perPage = 5) {
    const modal = document.getElementById('user-details-modal');
    showModal(modal.id);

    try {
        const response = await fetch(`/dashboard/admin/general/users/${userId}?page=${page}&per_page=${perPage}`, {
            credentials: 'include'
        });
        
        if (!response.ok) {
            throw new Error('Ошибка загрузки данных пользователя');
        }
        
        const data = await response.json();
        renderUserDetails(data, page, perPage);
    } catch (error) {
        console.error('Failed to load user details:', error);
        showNotification(`Ошибка: ${error.message}`, 'error');
    }
}

function renderUserDetails(data, currentPage = 1, perPage = 5) {
    const user = data.user;
    
    // Основная информация
    document.getElementById('user-id').textContent = user.id;
    document.getElementById('user-username').textContent = user.username;
    document.getElementById('user-email').textContent = user.email;
    document.getElementById('user-role').textContent = user.role;
    document.getElementById('user-created').textContent = new Date(user.created_at).toLocaleString();
    document.getElementById('user-last-login').textContent = user.last_login ? new Date(user.last_login).toLocaleString() : 'Никогда';
    
    // История изменений
    const historyList = document.getElementById('user-history-list');
    const historyData = data.history.items;
    
    if (historyData.length > 0) {
        historyList.innerHTML = historyData.slice(0, 3).map(h => `
            <div class="history-item">
                <div class="history-header">
                    <span>${getHistoryTypeName(h.change_type)}</span>
                    <span class="history-date">${new Date(h.changed_at).toLocaleString()}</span>
                </div>
                <div class="history-change">
                    ${h.old_value ? `<span class="old">${h.old_value}</span> → ` : ''}
                    <span class="new">${h.new_value || ''}</span>
                </div>
            </div>
        `).join('');
        
        // Пагинация для истории
        renderPagination(
            'user-history-pagination',
            currentPage,
            data.history.total,
            perPage,
            (page) => showUserDetails(user.id, page, perPage)
        );
    } else {
        historyList.innerHTML = '<div class="no-data">Нет данных об изменениях</div>';
    }
    
    // Обращения пользователя
    const appealsSection = document.getElementById('user-created-appeals-section');
    const appealsList = document.getElementById('user-created-appeals');
    const appealsData = data.appeals.items;
    
    if (appealsData.length > 0) {
        appealsSection.classList.remove('hidden');
        appealsList.innerHTML = appealsData.map(a => `
            <div class="appeal-item">
                <div class="appeal-header">
                    <span>${getTypeName(a.type)} (${getStatusName(a.status)})</span>
                    <span class="appeal-date">${new Date(a.created_at).toLocaleString()}</span>
                </div>
                <div>ID: ${a.id}</div>
            </div>
        `).join('');
        
        // Пагинация для обращений
        renderPagination(
            'created-appeals-pagination',
            currentPage,
            data.appeals.total,
            perPage,
            (page) => showUserDetails(user.id, page, perPage)
        );
    } else {
        appealsList.innerHTML = '<div class="no-data">Пользователь не создавал обращений</div>';
    }
    
    // Рассмотренные обращения (для модераторов)
    const moderatorSection = document.getElementById('moderator-appeals-section');
    const assignedAppealsList = document.getElementById('user-assigned-appeals');
    const assignedData = data.assigned_appeals.items;
    
    if (user.role_level >= 2 && assignedData.length > 0) {
        moderatorSection.classList.remove('hidden');
        assignedAppealsList.innerHTML = assignedData.map(a => `
            <div class="appeal-item">
                <div class="appeal-header">
                    <span>${getTypeName(a.type)} (${getStatusName(a.status)})</span>
                    <span class="appeal-date">Назначено: ${new Date(a.assigned_at).toLocaleString()}</span>
                </div>
                <div>ID: ${a.appeal_id}</div>
            </div>
        `).join('');
        
        // Пагинация для назначенных обращений
        renderPagination(
            'assigned-appeals-pagination',
            currentPage,
            data.assigned_appeals.total,
            perPage,
            (page) => showUserDetails(user.id, page, perPage)
        );
    } else {
        moderatorSection.classList.add('hidden');
    }
    
    // Заявки пользователя
    const requestsSection = document.getElementById('user-requests-tab');
    const requestsList = document.getElementById('modal-user-requests-list');
    const requestsData = data.requests.items;
    
    if (requestsData.length > 0) {
        requestsSection.classList.remove('hidden');
        requestsList.innerHTML = requestsData.map(request => `
            <div class="request-card" data-id="${request.id}">
                <div class="request-header">
                    <span class="request-type">${getRequestTypeName(request.request_type)}</span>
                    <span class="request-status ${getStatusClass(request.status)}">${getStatusName(request.status)}</span>
                </div>
                <div class="request-details">
                    ${Object.entries(request.request_data).map(([key, val]) =>
                        `<div><strong>${key}</strong>: ${val}</div>`).join('')}
                </div>
                <div class="request-footer">
                    <span class="request-date">${new Date(request.created_at).toLocaleString()}</span>
                </div>
            </div>
        `).join('');
        
        // Пагинация для заявок
        renderPagination(
            'modal-requests-pagination',
            currentPage,
            data.requests.total,
            perPage,
            (page) => showUserDetails(user.id, page, perPage)
        );
    } else {
        requestsList.innerHTML = '<div class="no-data">Пользователь не отправлял заявок</div>';
    }

    const banBtn = document.getElementById('ban-user-btn');
    if (user.is_active) {
        banBtn.textContent = 'Заблокировать';
        banBtn.className = 'secondary-btn';
        banBtn.onclick = async () => {
            const reason = prompt('Укажите причину блокировки пользователя:');
            if (!reason) {
                alert('Блокировка отменена: причина не указана.');
                return;
            }
            try {
                await banUser(user.id, reason);
                showNotification('Пользователь успешно заблокирован', 'success');
                hideModal('user-details-modal');
                loadUsers();
            } catch (error) {
                showNotification(`Ошибка: ${error.message}`, 'error');
            }
        };
    } else {
        banBtn.textContent = 'Разблокировать';
        banBtn.className = 'secondary-btn';
        banBtn.onclick = async () => {
            try {
                await unbanUser(user.id);
                showNotification('Пользователь успешно разблокирован', 'success');
                hideModal('user-details-modal');
                loadUsers();
            } catch (error) {
                showNotification(`Ошибка: ${error.message}`, 'error');
            }
        };
    }

    if (currentUser.role.level >= 6) {
        const roleSelect = document.createElement('select');
        roleSelect.id = 'user-role-select';
        roleSelect.className = 'role-select';
        
        // Загружаем список ролей
        loadRoles().then(roles => {
            const currentRole = roles.find(r => r.name === user.role);
            if (currentRole) {
                const option = document.createElement('option');
                option.value = currentRole.id;
                option.textContent = currentRole.name;
                option.selected = true;
                roleSelect.appendChild(option);
                
                const divider = document.createElement('option');
                divider.disabled = true;
                divider.textContent = '──────────';
                roleSelect.appendChild(divider);
            }
            
            roles.forEach(role => {
                if (role.id !== user.role.id && role.level <= currentUser.role.level) {
                    const option = document.createElement('option');
                    option.value = role.id;
                    option.textContent = role.name;
                    roleSelect.appendChild(option);
                }
            });
            if (currentRole) {
                roleSelect.value = currentRole.id;
            };
        });
        
        const roleContainer = document.getElementById('user-role');
        roleContainer.innerHTML = '';
        roleContainer.appendChild(roleSelect);
        
        roleSelect.addEventListener('change', async () => {
            try {
                await updateUserRole(user.id, roleSelect.value);
                showUserDetails(user.id); 
            } catch (error) {
                console.error('Failed to update role:', error);
            }
        });
    }
}

async function loadRoles() {
    try {
        const response = await fetch('/dashboard/admin/general/roles', {
            credentials: 'include'
        });
        
        if (!response.ok) {
            throw new Error('Ошибка загрузки ролей');
        }
        
        return await response.json();
    } catch (error) {
        showNotification(`Ошибка загрузки ролей: ${error.message}`, 'error');
        return [];
    }
}

async function updateUserRole(userId, newRoleId) {
    try {
        const response = await fetch(`/dashboard/admin/general/users/${userId}/role?role_id=${encodeURIComponent(newRoleId)}`, {
            method: 'POST',
            credentials: 'include'
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Ошибка при изменении роли');
        }
        
        return await response.json();
    } catch (error) {
        console.error('Failed to update user role:', error);
        throw error;
    }
}

async function banUser(userId, reason) {
    if (currentUser.id === userId) {
        throw new Error('Вы не можете заблокировать себя');
    }
    
    try {
        const response = await fetch(`/dashboard/admin/general/users/${userId}/ban?reason=${encodeURIComponent(reason)}`, {
            method: 'POST',
            credentials: 'include'
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Ошибка при блокировке пользователя');
        }
        
        return await response.json();
    } catch (error) {
        console.error('Failed to ban user:', error);
        throw error;
    }
}

async function unbanUser(userId) {
    try {
        const response = await fetch(`/dashboard/admin/general/users/${userId}/unban`, {
            method: 'POST',
            credentials: 'include'
        });
        
        if (!response.ok) {
            throw new Error('Ошибка при разблокировке пользователя');
        }
        
        return await response.json();
    } catch (error) {
        console.error('Failed to unban user:', error);
        throw error;
    }
}

async function loadRequests(page = currentFiltersRequests.page) {
    currentFiltersRequests.page = page

    const container = document.getElementById('user-requests-list');
    if (!container) return;
    
    container.innerHTML = `
        <div class="loading-row">
            <i class="fas fa-spinner fa-spin"></i> Загрузка заявок...
        </div>
    `;
    
    try {
        const response = await fetch(`/dashboard/admin/general/requests?page=${page}`, {
            credentials: 'include'
        });
        
        if (!response.ok) {
            throw new Error('Ошибка загрузки заявок');
        }
        
        const data = await response.json();
        renderRequests(data);
    } catch (error) {
        container.innerHTML = `
            <div class="no-data">Ошибка загрузки: ${error.message}</div>
        `;
    }
}

function renderRequests(data) {
    const container = document.getElementById('user-requests-list');
    const paginationInfo = document.getElementById('requests-pagination-info');
    
    if (!data.requests || data.requests.length === 0) {
        container.innerHTML = '<div class="no-data">Нет заявок на рассмотрении</div>';
        paginationInfo.textContent = '';
        return;
    }
    
    let html = '';
    
    data.requests.forEach(request => {
        const date = new Date(request.created_at).toLocaleString();
        let details = '';
        
        if (request.request_type === 'username_change') {
            details = `Смена никнейма с "${request.request_data.old_username}" на "${request.request_data.new_username}"`;
        } else if (request.request_type === 'account_deletion') {
            details = 'Запрос на удаление аккаунта';
        }
        
        html += `
            <div class="request-card" data-id="${request.id}">
                <div class="request-header">
                    <span class="request-user">${request.user_name}</span>
                    <span class="request-type">${getRequestTypeName(request.request_type)}</span>
                </div>
                <div class="request-details">${details}</div>
                <div class="request-footer">
                    <span class="request-date">${date}</span>
                    <div class="request-actions">
                        <button class="action-btn reject-btn" data-id="${request.id}">
                            <i class="fas fa-times"></i> Отклонить
                        </button>
                        <button class="action-btn approve-btn" data-id="${request.id}">
                            <i class="fas fa-check"></i> Одобрить
                        </button>
                    </div>
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
    paginationInfo.textContent = `Страница ${data.page} из ${data.total_pages}`;
    
    // Добавляем обработчики для кнопок
    document.querySelectorAll('.approve-btn').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            e.stopPropagation();
            const requestId = btn.getAttribute('data-id');
            try {
                await approveRequest(requestId);
                showNotification('Заявка одобрена', 'success');
                loadRequests();
            } catch (error) {
                showNotification(`Ошибка: ${error.message}`, 'error');
            }
        });
    });
    
    document.querySelectorAll('.reject-btn').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            e.stopPropagation();
            const requestId = btn.getAttribute('data-id');
            try {
                await rejectRequest(requestId);
                showNotification('Заявка отклонена', 'success');
                loadRequests();
            } catch (error) {
                showNotification(`Ошибка: ${error.message}`, 'error');
            }
        });
    });
    
    renderPagination(
        'requests-pagination',
        data.page,
        data.total_pages,
        data.per_page,
        loadRequests
    );
}

async function approveRequest(requestId) {
    const response = await fetch(`/dashboard/admin/general/requests/${requestId}/approve`, {
        method: 'POST',
        credentials: 'include'
    });
    
    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Ошибка одобрения заявки');
    }
}

async function rejectRequest(requestId) {
    const response = await fetch(`/dashboard/admin/general/requests/${requestId}/reject`, {
        method: 'POST',
        credentials: 'include'
    });
    
    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Ошибка отклонения заявки');
    }
}


async function handleRequestAction(requestId, action) {
    try {
        const response = await fetch(`/dashboard/admin/requests/${requestId}/${action}`, {
            method: 'POST',
            credentials: 'include'
        });
        
        if (!response.ok) {
            throw new Error('Ошибка при обработке заявки');
        }
        
        showNotification(`Заявка успешно ${action === 'approved' ? 'одобрена' : 'отклонена'}`, 'success');
        
        // Обновляем данные
        const userId = document.querySelector('#user-details-modal').getAttribute('data-user-id');
        showUserDetails(userId);
        
    } catch (error) {
        showNotification(`Ошибка: ${error.message}`, 'error');
    }
}

function renderPagination(containerId, currentPage, totalItems, perPage, callback) {
    const container = document.getElementById(containerId);
    
    const totalPages = Math.ceil(totalItems / perPage);
    
    if (totalPages <= 1) {
        container.innerHTML = '';
        return;
    }
    
    let html = '';
    const maxVisiblePages = 5;

    if (currentPage > 1) {
        html += `<button class="page-btn prev-btn" data-page="${currentPage - 1}">← Назад</button>`;
    }
    
    if (currentPage > Math.floor(maxVisiblePages / 2) + 1) {
        html += `<button class="page-btn" data-page="1">1</button>`;
        if (currentPage > Math.floor(maxVisiblePages / 2) + 2) {
            html += `<span class="page-dots">...</span>`;
        }
    }
    
    const startPage = Math.max(1, currentPage - Math.floor(maxVisiblePages / 2));
    const endPage = Math.min(totalPages, startPage + maxVisiblePages - 1);
    
    for (let i = startPage; i <= endPage; i++) {
        html += `<button class="page-btn ${i === currentPage ? 'active' : ''}" data-page="${i}">${i}</button>`;
    }
    
    if (currentPage < totalPages - Math.floor(maxVisiblePages / 2)) {
        if (currentPage < totalPages - Math.floor(maxVisiblePages / 2) - 1) {
            html += `<span class="page-dots">...</span>`;
        }
        html += `<button class="page-btn" data-page="${totalPages}">${totalPages}</button>`;
    }
    
    if (currentPage < totalPages) {
        html += `<button class="page-btn next-btn" data-page="${currentPage + 1}">Далее →</button>`;
    }
    
    container.innerHTML = html;
    
    container.querySelectorAll('.page-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const page = parseInt(btn.getAttribute('data-page'));
            callback(page);
        });
    });
}

function setupFilters() {
    // Добавлю обработчики для поиска
    document.getElementById('filter-toggle').addEventListener('click', toggleFiltersLogs);
    document.getElementById('apply-filters').addEventListener('click', applyFiltersLogs);
    document.getElementById('reset-filters').addEventListener('click', resetFiltersLogs);

    // Обработчик поиска по логам
    const logsSearch = document.querySelector('#logs-tab .search-box');
    logsSearch.querySelector('button').addEventListener('click', () => {
        searchQueries.logs = logsSearch.querySelector('input').value.trim();
        loadLogs();
    });
    logsSearch.querySelector('input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            searchQueries.logs = logsSearch.querySelector('input').value.trim();
            loadLogs();
        }
    });

    // Обработчик поиска по пользователям
    const usersSearch = document.querySelector('#users-tab .search-box');
    usersSearch.querySelector('button').addEventListener('click', () => {
        searchQueries.users = usersSearch.querySelector('input').value.trim();
        loadUsers();
    });
    usersSearch.querySelector('input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            searchQueries.users = usersSearch.querySelector('input').value.trim();
            loadUsers();
        }
    });
}

function toggleFiltersLogs() {
    const filtersPanel = document.getElementById('filters-panel');
    filtersVisiblelogs = !filtersVisiblelogs;
    
    if (filtersVisiblelogs) {
        filtersPanel.classList.add('show');
    } else {
        filtersPanel.classList.remove('show');
    }
}

function applyFiltersLogs() {
    const statusFilter = document.getElementById('status-filter');
    
    currentFiltersLogs = {
        action_type: statusFilter.value,
        page: 1,
        perPage: 20
    };
    
    loadLogs();
    toggleFiltersLogs();
}

function resetFiltersLogs() {
    document.getElementById('status-filter').value = 'all';
    
    currentFiltersLogs = {
        action_type: 'all',
        page: 1,
        perPage: 20
    };
    
    searchQueries.logs = '';
    document.getElementById('complaints-search-input').value = '';
    loadLogs();
    toggleFiltersLogs();
}


// Вспомогательные функции
function getHistoryTypeName(type) {
    const types = {
        'username': 'Смена имени',
        'password': 'Смена пароля',
        'email': 'Смена email',
        'role': 'Смена роли'
    };
    return types[type] || type;
}

function getRequestTypeName(type) {
    const types = {
        'account_deletion': 'Удаление аккаунта',
        'username_change': 'Смена имени',
    };
    return types[type] || type;
}

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
        'approved': 'Одобренно',
        'resolved': 'Решено',
        'rejected': 'Отклонено'
    };
    return statuses[status] || status;
}

function getStatusClass(status) {
    switch (status) {
        case 'approved': return 'status-completed'
        case 'rejected': return 'status-rejected';
        default: return 'status-pending';
    }
}

function initActionTypeSelector(selectId) {
    const actionTypes = {
        create_appeal: "Создание обращения",
        appeal_progress: "Обращение на рассмотрении",
        appeal_closed: "Обращение закрыто",
        register_user: "Регистрация пользователя",
        user_login: "Вход пользователя",
        update_role_user: "Изменение роли",
        account_deletion_requested: "Запрос на удаление аккаунта",
        delete_account: "Удаление аккаунта",
        add_account_deletion: "Учёт удалённых аккаунтов",
        update_stats_user: "Изменение статистики",
        reassigning_appeal: "Переназначение обращения",
        banned_user: "Блокировка аккаунта",
        unbanned_user: "Разблокировка аккаунта",
        approved_request: "Одобрение заявки",
        rejected_request: "Отклонение заявки",
        password_changed: "Смена пароля",
        username_change_request: "Запрос на смену ника"
    };

    const select = document.getElementById(selectId);
    if (!select) {
        console.error(`Селектор #${selectId} не найден`);
        return;
    }

    select.innerHTML = '<option value="all">Все</option>';

    Object.entries(actionTypes).forEach(([value, label]) => {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = label;
        select.appendChild(option);
    });
}
