
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

    document.querySelectorAll('#user-details-modal .tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const tabName = btn.getAttribute('data-tab');
            if (currentUserDetails) {
                loadUserDetailsTab(tabName, userDetailsPagination[tabName].page);
            }
        });
    });

    document.getElementById('confirmRoleForm')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        if (currentRoleChangeData) {
            try {
                await updateUserRole(currentRoleChangeData.userId, currentRoleChangeData.newRoleId);
                hideModal('confirmRoleModal');
                showNotification('Роль пользователя успешно изменена', 'success');
                loadUserDetailsTab('user-info', userDetailsPagination['user-info'].page);
                loadUsers();
            } catch (error) {
                showNotification(`Ошибка: ${error.message}`, 'error');
            }
        }
    });
    
    document.getElementById('confirmBanForm')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        if (currentBanActionData) {
            try {
                if (currentBanActionData.action === 'ban') {
                    const reason = document.getElementById('ban-reason').value.trim();
                    if (!reason) {
                        showNotification('Пожалуйста, укажите причину блокировки', 'error');
                        return;
                    }
                    await banUser(currentBanActionData.user.id, reason);
                    showNotification('Пользователь успешно заблокирован', 'success');
                } else {
                    await unbanUser(currentBanActionData.user.id);
                    showNotification('Пользователь успешно разблокирован', 'success');
                }
                hideModal('confirmBanModal');
                loadUserDetailsTab('user-info', userDetailsPagination['user-info'].page);
                loadUsers();
            } catch (error) {
                showNotification(`Ошибка: ${error.message}`, 'error');
            }
        }
    });
    
    document.getElementById('confirmRestoreForm')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        if (currentRestoreActionData) {
            try {
                await restoreUser(currentRestoreActionData.id);
                showNotification('Пользователь успешно восстановлен', 'success');
                hideModal('confirmRestoreModal');
                loadUserDetailsTab('user-info', userDetailsPagination['user-info'].page);
                loadUsers();
            } catch (error) {
                showNotification(`Ошибка: ${error.message}`, 'error');
            }
        }
    });

    document.querySelectorAll('.cancel-confirm-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            const modal = btn.closest('.modal');
            hideModal(modal.id);
        });
    });

});

let filtersVisiblelogs = false;
let filtersVisibleUsers = false;
let filtersVisibleRequests = false;
let currentUserDetails = null;
let currentRoleChangeData = null;
let currentBanActionData = null;
let currentRestoreActionData = null;

let userDetailsPagination = {
    'user-info': { page: 1, perPage: 5 },
    'user-appeals': { page: 1, perPage: 5 },
    'user-requests': { page: 1, perPage: 5 }
};

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

        renderPagination(
            'logs-pagination',
            1,
            0,
            data.per_page || 0,
            loadLogs
        );
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

async function showUserDetails(userId, page = 1, perPage = 5, activeTab = 'user-info') {
    const modal = document.getElementById('user-details-modal');
    
    showLoadingIndicator();
    currentUserDetails = userId;

    try {
        const response = await fetch(`/dashboard/admin/general/users/${userId}?page=${page}&per_page=${perPage}`, {
            credentials: 'include'
        });
        
        if (!response.ok) {
            throw new Error('Ошибка загрузки данных пользователя');
        }
        
        const data = await response.json();
        userDetailsPagination[activeTab] = { page, perPage };
        switchToUserDetailsTab(activeTab);

        showModal(modal.id);
        renderUserDetails(data, activeTab);
    } catch (error) {
        console.error('Failed to load user details:', error);
        showNotification(`Ошибка: ${error.message}`, 'error');
        hideModal('user-details-modal');
    }
}

function showLoadingIndicator() {
    const modalContent = document.querySelector('#user-details-modal .modal-content');
    const loadingHtml = `
        <div class="loading-overlay">
            <i class="fas fa-spinner fa-spin"></i>
            <p>Загрузка данных пользователя...</p>
        </div>
    `;
    
    modalContent.insertAdjacentHTML('beforeend', loadingHtml);
}

function switchToUserDetailsTab(tabName) {
    const tabButtons = document.querySelectorAll('#user-details-modal .tab-btn');
    const tabContents = document.querySelectorAll('#user-details-modal .tab-content');
    
    tabButtons.forEach(btn => btn.classList.remove('active'));
    tabContents.forEach(content => content.classList.remove('active'));
    
    const targetTabBtn = document.querySelector(`#user-details-modal .tab-btn[data-tab="${tabName}"]`);
    const targetTabContent = document.querySelector(`#user-details-modal #${tabName}-tab`);
    
    if (targetTabBtn && targetTabContent) {
        targetTabBtn.classList.add('active');
        targetTabContent.classList.add('active');
        
        // Обновляем индикатор вкладок
        const tabIndicator = document.querySelector('#user-details-modal .tab-indicator');
        if (tabIndicator) {
            const btnRect = targetTabBtn.getBoundingClientRect();
            const containerRect = targetTabBtn.parentElement.getBoundingClientRect();
            
            tabIndicator.style.width = `${btnRect.width}px`;
            tabIndicator.style.left = `${btnRect.left - containerRect.left}px`;
        }
    }
}

async function loadUserDetailsTab(tabName, page) {
    if (!currentUserDetails) return;
    
    userDetailsPagination[tabName].page = page;

    const perPage = userDetailsPagination[tabName].perPage;
    
    try {
        const response = await fetch(`/dashboard/admin/general/users/${currentUserDetails}?page=${page}&per_page=${perPage}`, {
            credentials: 'include'
        });
        
        if (!response.ok) {
            throw new Error('Ошибка загрузки данных пользователя');
        }
        
        const data = await response.json();
        
        switchToUserDetailsTab(tabName);
        renderUserDetails(data, tabName);

    } catch (error) {
        console.error('Failed to load user details:', error);
        showNotification(`Ошибка: ${error.message}`, 'error');
    }
}

function renderUserDetails(data, activeTab = 'user-info') {
    const user = data.user;

    const loadingOverlay = document.querySelector('.loading-overlay');
    if (loadingOverlay) {
        loadingOverlay.remove();
    }
    
    document.getElementById('user-id').textContent = user.id;
    document.getElementById('user-username').textContent = user.username;
    document.getElementById('user-email').textContent = user.email;
    document.getElementById('user-role').textContent = user.role;
    document.getElementById('user-created').textContent = new Date(user.created_at).toLocaleString();
    document.getElementById('user-last-login').textContent = user.last_login ? new Date(user.last_login).toLocaleString() : 'Никогда';

    // Статус пользователя
    const statusBadge = document.getElementById('user-status-badge');
    if (!user.is_active) {
        if (user.username && user.username.includes('deleted_')) {
            statusBadge.textContent = 'Деактивирован';
            statusBadge.className = 'user-status-badge deactivated';
        } else {
            statusBadge.textContent = 'Заблокирован';
            statusBadge.className = 'user-status-badge banned';
        }
    } else {
        statusBadge.textContent = 'Активен';
        statusBadge.className = 'user-status-badge active';
    }

    // История изменений
    const historyList = document.getElementById('user-history-list');
    const historyData = data.history.items;
    
    if (historyData.length > 0) {
        historyList.innerHTML = historyData.map(h => `
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
            userDetailsPagination['user-info'].page,
            data.history.total,
            userDetailsPagination['user-info'].perPage,
            (page) => loadUserDetailsTab('user-info', page)
        );
    } else {
        historyList.innerHTML = '<div class="no-data">Нет данных об изменениях</div>';
    }
    
    // Обращения пользователя
    const appealsSection = document.getElementById('user-created-appeals-section');
    const appealsContainer = document.getElementById('user-created-appeals');
    const appealsData = data.appeals.items;
    
    if (appealsData.length > 0) {
        appealsSection.classList.remove('hidden');
        appealsContainer.innerHTML = appealsData.map(a => `
            <div class="appeal-card" data-id="${a.id}">
                <div class="appeal-header">
                    <span class="appeal-type">${getTypeName(a.type)}</span>
                    <span class="appeal-status ${a.status}">${getStatusName(a.status)}</span>
                </div>
                <div class="appeal-details">
                    <span class="appeal-id">ID: ${a.id.substring(0, 8)}...</span>
                    <span class="appeal-date">${new Date(a.created_at).toLocaleDateString()}</span>
                </div>
            </div>
        `).join('');
        
        // Пагинация для обращений
        renderPagination(
            'created-appeals-pagination',
            userDetailsPagination['user-appeals'].page,
            data.appeals.total,
            userDetailsPagination['user-appeals'].perPage,
            (page) => loadUserDetailsTab('user-appeals', page)
        );
    } else {
        appealsContainer.innerHTML = '<div class="no-data">Пользователь не создавал обращений</div>';
    }
    
    // Рассмотренные обращения
    const moderatorSection = document.getElementById('moderator-appeals-section');
    const assignedAppealsContainer = document.getElementById('user-assigned-appeals');
    const assignedData = data.assigned_appeals.items;
    
    if (user.role_level >= 2 && assignedData.length > 0) {
        moderatorSection.classList.remove('hidden');
        assignedAppealsContainer.innerHTML = assignedData.map(a => `
            <div class="appeal-card" data-id="${a.appeal_id}">
                <div class="appeal-header">
                    <span class="appeal-type">${getTypeName(a.type)}</span>
                    <span class="appeal-status ${a.status}">${getStatusName(a.status)}</span>
                </div>
                <div class="appeal-details">
                    <span class="appeal-id">ID: ${a.appeal_id.substring(0, 8)}...</span>
                    <span class="appeal-date">Назначено: ${new Date(a.assigned_at).toLocaleDateString()}</span>
                </div>
            </div>
        `).join('');
        
        // Пагинация для назначенных обращений
        renderPagination(
            'assigned-appeals-pagination',
            userDetailsPagination['user-appeals'].page,
            data.assigned_appeals.total,
            userDetailsPagination['user-appeals'].perPage,
            (page) => loadUserDetailsTab('user-appeals', page)
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
            userDetailsPagination['user-requests'].page,
            data.requests.total,
            userDetailsPagination['user-requests'].perPage,
            (page) => loadUserDetailsTab('user-requests', page)
        );
    } else {
        requestsList.innerHTML = '<div class="no-data">Пользователь не отправлял заявок</div>';
    }

    const banBtn = document.getElementById('ban-user-btn');
    if (!user.is_active && user.username && user.username.includes('deleted_')) {
        banBtn.textContent = 'Восстановить аккаунт';
        banBtn.className = 'primary-btn';
        banBtn.onclick = () => showConfirmRestore(user);
    } else if (user.is_active) {
        banBtn.textContent = 'Заблокировать';
        banBtn.className = 'secondary-btn';
        banBtn.onclick = () => showConfirmBan(user, 'ban');
    } else {
        banBtn.textContent = 'Разблокировать';
        banBtn.className = 'secondary-btn';
        banBtn.onclick = () => showConfirmBan(user, 'unban');
    }

    if (currentUser.role.level >= 6) {
        const roleContainer = document.getElementById('user-role');
        roleContainer.innerHTML = '';
        
        const roleSelectContainer = document.createElement('div');
        roleSelectContainer.className = 'role-select-container';
        
        const roleSelect = document.createElement('select');
        roleSelect.id = 'user-role-select';
        roleSelect.className = 'role-select';
        
        const confirmButton = document.createElement('button');
        confirmButton.className = 'primary-btn confirm-role-btn';
        confirmButton.textContent = 'Подтвердить';
        confirmButton.style.display = 'none';
        confirmButton.onclick = () => showConfirmRoleChange(user.id, roleSelect.value);
        
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
                if (role.id !== user.role.id && role.level < currentUser.role.level) {
                    const option = document.createElement('option');
                    option.value = role.id;
                    option.textContent = role.name;
                    roleSelect.appendChild(option);
                }
            });
            
            if (currentRole) {
                roleSelect.value = currentRole.id;
            }
            
            roleSelect.addEventListener('change', () => {
                const selectedRole = roles.find(r => r.id === roleSelect.value);
                if (selectedRole && selectedRole.name !== user.role) {
                    confirmButton.style.display = 'block';
                } else {
                    confirmButton.style.display = 'none';
                }
            });
        });
        
        roleSelectContainer.appendChild(roleSelect);
        roleSelectContainer.appendChild(confirmButton);
        roleContainer.appendChild(roleSelectContainer);
    } else {
        document.getElementById('user-role').textContent = user.role;
    }

    document.querySelectorAll('.appeal-card').forEach(card => {
    card.addEventListener('click', (e) => {
        e.stopPropagation();
        const appealId = card.getAttribute('data-id');
        openAppealChat(appealId);
    });
});
}

async function openAppealChat(appealId) {
    try {
        hideModal('user-details-modal');
        
        const chatContainer = document.getElementById('appeal-chat-container');
        if (chatContainer) {
            chatContainer.style.display = 'flex';
            document.querySelector('.dashboard-content').classList.add('chat-open');
        }
        
        await loadAppealChat(appealId);
        
    } catch (error) {
        console.error('Ошибка открытия чата:', error);
        showNotification('Не удалось открыть чат обращения', 'error');
    }
}

function closeAppealChatAndReturnToUser() {
    hideAppealChat();
    
    if (currentUserDetails) {
        setTimeout(() => {
            showModal('user-details-modal');
        }, 300);
    }
}

function hideAppealChat() {
    const dashboardContent = document.querySelector('.dashboard-content');
    const chatContainer = document.getElementById('appeal-chat-container');
    
    dashboardContent.classList.remove('chat-open');
    chatContainer.style.display = 'none';
}

async function loadAppealChat(appealId) {
    try {
        const response = await fetch(`/messanger/appeals/${appealId}/chat`, {
            credentials: 'include'
        });
        
        if (!response.ok) {
            throw new Error('Ошибка загрузки чата');
        }
        
        const data = await response.json();
        renderAppealChat(data, appealId);
        
    } catch (error) {
        console.error('Ошибка загрузки чата:', error);
        showNotification('Не удалось загрузить чат обращения', 'error');
    }
}

function renderAppealChat(data, appealId) {
    const messagesContainer = document.getElementById('appeal-messages');
    const appealType = document.getElementById('appeal-type');
    const appealIdElement = document.getElementById('appeal-id');
    
    appealType.textContent = getTypeName(data.appeal.type);
    appealIdElement.textContent = `ID: ${data.appeal.id}`;
    
    messagesContainer.innerHTML = '';
    
    data.messages.forEach(message => {
        const messageElement = document.createElement('div');
        messageElement.className = message.is_system ? 'message system-message' : 
                                message.user_id === data.appeal.user_id ? 'message user-message' : 'message admin-message';
        
        // Создаем HTML для вложений
        let attachmentsHtml = '';
        if (message.attachments && message.attachments.length > 0) {
            attachmentsHtml = '<div class="message-attachments">';
            
            message.attachments.forEach((attachment, index) => {
                if (!attachment) return;
                
                const imageUrl = `/messanger/appeals/${message.appeal_id}/files/${attachment}`;
                
                if (index === 0) {
                    attachmentsHtml += `
                        <div class="main-attachment">
                            <img src="${imageUrl}" 
                                alt="Прикрепленное изображение"
                                onerror="this.style.display='none'"
                        </div>`;
                } else {
                    if (index === 1) attachmentsHtml += '<div class="attachment-thumbnails">';
                    attachmentsHtml += `
                        <div class="thumbnail">
                            <img src="${imageUrl}" 
                                alt="Прикрепленное изображение"
                                onerror="this.style.display='none'"
                        </div>`;
                }
            });
            
            if (message.attachments.length > 1) attachmentsHtml += '</div>';
            attachmentsHtml += '</div>';
        }
        
        messageElement.innerHTML = `
            <div class="message-header">
                <strong>${message.username || 'Система'}</strong>
                <span class="message-date">${new Date(message.created_at).toLocaleString()}</span>
            </div>
            ${message.message ? `<div class="message-content">${message.message}</div>` : ''}
            ${attachmentsHtml}
        `;
        
        messagesContainer.appendChild(messageElement);
    });
    
    // Прокручиваем к последнему сообщению
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function showConfirmRoleChange(userId, newRoleId) {
    const roleSelect = document.getElementById('user-role-select');
    const selectedOption = roleSelect.options[roleSelect.selectedIndex];
    const currentRole = document.getElementById('user-role-select').options[0].text;
    
    currentRoleChangeData = { userId, newRoleId, currentRole, newRole: selectedOption.text };
    
    document.getElementById('current-role-name').textContent = currentRole;
    document.getElementById('new-role-name').textContent = selectedOption.text;
    
    showModal('confirmRoleModal');
}

function showConfirmBan(user, action) {
    currentBanActionData = { user, action };
    
    const modal = document.getElementById('confirmBanModal');
    const confirmText = document.getElementById('ban-confirm-text');
    const reasonContainer = document.getElementById('ban-reason-container');
    const reasonInput = document.getElementById('ban-reason');
    
    if (action === 'ban') {
        confirmText.textContent = `Вы уверены, что хотите заблокировать пользователя ${user.username}?`;
        reasonContainer.style.display = 'block';
        reasonInput.required = true; 
    } else if (action === 'unban') {
        confirmText.textContent = `Вы уверены, что хотите разблокировать пользователя ${user.username}?`;
        reasonContainer.style.display = 'none';
        reasonInput.required = false;
        reasonInput.value = ''; 
    }
    
    showModal('confirmBanModal');
}

function showConfirmRestore(user) {
    currentRestoreActionData = user;

    const modal = document.getElementById('confirmRestoreModal');
    const confirmText = document.getElementById('restore-confirm-text');
    
    confirmText.textContent = `Вы уверены, что хотите восстановить аккаунт пользователя ${user.username}?`;
    
    showModal('confirmRestoreModal');
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
        
        const confirmBtn = document.querySelector('.confirm-role-btn');
        if (confirmBtn) {
            confirmBtn.style.display = 'none';
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
    const infoContainer = document.getElementById(containerId + '-info');
    
    const totalPages = Math.ceil(totalItems / perPage);
    
    if (infoContainer) {
        infoContainer.textContent = `Страница ${currentPage} из ${totalPages} (всего: ${totalItems})`;
    }
    
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
            
            // Определяем активную вкладку
            const activeTab = document.querySelector('#user-details-modal .tab-btn.active');
            const tabName = activeTab ? activeTab.getAttribute('data-tab') : 'user-info';
            
            callback(page, tabName);
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

async function restoreUser(userId) {
    try {
        const response = await fetch(`/dashboard/admin/general/users/${userId}/restore`, {
            method: 'POST',
            credentials: 'include'
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Ошибка при восстановлении пользователя');
        }
        
        showNotification('Пользователь успешно восстановлен', 'success');
        return await response.json();
    } catch (error) {
        console.error('Failed to restore user:', error);
        showNotification(`Ошибка: ${error.message}`, 'error');
        throw error;
    }
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
