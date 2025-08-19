document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('logout-btn').addEventListener('click', logout);
    document.getElementById('stats-period').addEventListener('change', loadStats);
    
    initDashboard();
    
    initTabs('.dashboard-tabs .tab-btn', '.dashboard-content .tab-content', '.dashboard-tabs .tab-indicator', {
        onTabChange: (tabId) => {
            if (tabId === 'appeals') {
                loadUserAppeals();
                hideAppealChat();
            } else if (tabId === 'stats') {
                loadStats();
                hideAppealChat();
            } else if (tabId === 'admin') {
                loadAdminPanel();
                hideAppealChat();
            }
        },
    });

    initTabs('#supportModal .tab-btn', '#supportModal .tab-content', '#supportModal .tab-indicator');
});

async function initDashboard() {
    try {
        if (!currentUser) {
            const response = await fetch('/dashboard/', {
                method: 'GET',
                credentials: 'include'
            });
            
            if (response.status === 401) {
                const refreshResponse = await fetch('/auth/refresh', {
                    method: 'POST',
                    credentials: 'include' 
                });
                
                if (refreshResponse.ok) {
                    return initDashboard();
                }
                
                window.location.href = '/';
                return;
            }
            
            if (!response.ok) throw new Error('Ошибка загрузки');
        }

        displayUserData(currentUser);
        await loadDashboardData();
        
    } catch (error) {
        console.error('Ошибка:', error);
    }
}

async function loadDashboardData() {
    try {
        // Получаем данные для dashboard
        const dashboardResponse = await fetch('/dashboard/data', {
            credentials: 'include'
        });
        
        if (!dashboardResponse.ok) {
            throw new Error('Ошибка загрузки данных');
        }
        
        const dashboardData = await dashboardResponse.json();
        
        // Получаем логи действий только для текущего пользователя
        const logsResponse = await fetch(`/dashboard/admin/general/logs?user_id=${currentUser.id}&per_page=30`, {
            credentials: 'include'
        });
        
        if (logsResponse.ok) {
            const logsData = await logsResponse.json();
            displayActivities(logsData.logs);
        } else {
            displayActivities(dashboardData.activities || []);
        }
        
        if (document.getElementById('appeals-tab').classList.contains('active')) {
            await loadUserAppeals();
        }
        
    } catch (error) {
        console.error('Ошибка загрузки данных dashboard:', error);
        showNotification('Ошибка загрузки данных', 'error');
    }
}

function displayUserData(user) {
    document.getElementById('user-nickname').textContent = user["username"];
    document.getElementById('user-email').textContent = user["email"];
    document.getElementById('user-role').textContent = user["role"]["name"];
    document.getElementById('user-id').textContent = user["id"];
    
    if (user.created_at) {
        document.getElementById('user-reg-date').textContent = new Date(user.created_at).toLocaleDateString();
    }
    
    const emailVerifiedBadge = document.getElementById('email-verified');
    if (user.is_active) {
        emailVerifiedBadge.textContent = 'Подтверждено';
        emailVerifiedBadge.classList.add('verified-badge');
    } else {
        emailVerifiedBadge.textContent = 'Не подтверждено';
        emailVerifiedBadge.style.backgroundColor = '#ff4757';
    }
}

function displayActivities(activities) {
    const container = document.getElementById('recent-activities');
    container.innerHTML = '';
    
    if (!activities || activities.length === 0) {
        container.innerHTML = '<div class="no-activities">Нет последних действий</div>';
        return;
    }
    
    // Фильтруем действия и ограничиваем количество
    const filteredActivities = activities
        .filter(activity => !['user_login', 'register_user'].includes(activity.action_type))
        .slice(0, 5); 
    
    if (filteredActivities.length === 0) {
        container.innerHTML = '<div class="no-activities">Нет последних действий</div>';
        return;
    }
    
    filteredActivities.forEach(activity => {
        const activityItem = document.createElement('div');
        activityItem.className = 'activity-item';
        
        const actionName = getActionName(activity.action_type);
        const actionIcon = getActionIcon(activity.action_type);
        
        activityItem.innerHTML = `
            <div class="activity-item-header">
                <span class="activity-icon">${actionIcon}</span>
                <span class="activity-type">${actionName}</span>
                <span class="activity-date">${formatDateTime(activity.created_at)}</span>
            </div>
            <div class="activity-description">${activity.action_details || ''}</div>
        `;
        
        container.appendChild(activityItem);
    });
}

async function loadUserAppeals() {
    try {
        const response = await fetch('/dashboard/appeals', {
            credentials: 'include'
        });
        
        if (!response.ok) {
            throw new Error('Ошибка загрузки обращений');
        }
        
        const appeals = await response.json();
        displayAppeals(appeals);
    } catch (error) {
        console.error('Ошибка загрузки обращений:', error);
        showNotification('Ошибка загрузки списка обращений', 'error');
    }
}

function displayAppeals(appeals) {
    const tableBody = document.getElementById('appeals-table-body');
    tableBody.innerHTML = '';
    
    if (!appeals || appeals.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="4" class="no-appeals">
                    У вас пока нет обращений
                </td>
            </tr>
        `;
        return;
    }
    
    appeals.forEach(appeal => {
        const row = document.createElement('tr');
        const statusClass = getStatusClass(appeal.status);
        
        row.innerHTML = `
            <td data-label="Тип">${getAppealTypeName(appeal.type)}</td>
            <td data-label="Дата">${formatDateTime(appeal.created_at)}</td>
            <td data-label="Статус"><span class="activity-status ${statusClass}">${getAppealStatusName(appeal.status)}</span></td>
            <td data-label="Действия">
                <button class="action-btn take-btn" data-id="${appeal.id}">
                    Открыть обращение
                </button>
            </td>
        `;
        
        tableBody.appendChild(row);
    });

    initAppealActions();
}

async function loadStats() {
    try {
        const response = await fetch(`/dashboard/admin/reports/user-stats?admin_name=${encodeURIComponent(currentUser["username"])}`, {
            credentials: 'include'
        });
        
        if (!response.ok) {
            throw new Error('Ошибка загрузки статистики');
        }
        
        const data = await response.json();
        
        if (!data.users || data.users.length === 0) {
            return;
        }

        displayStats(data);
    } catch (error) {
        console.error('Ошибка загрузки статистики:', error);
        showNotification('Ошибка загрузки статистики', 'error');
    }
}

function displayStats(stats) {
    if (!stats.users || stats.users.length === 0) return;
    
    const userStats = stats.users[0];
    
    // Основные показатели
    document.getElementById('resolved-count').textContent = 
        (userStats.complaints_resolved || 0) + (userStats.appeals_resolved || 0);
    document.getElementById('rejected-count').textContent = 
        (userStats.complaints_rejected || 0) + (userStats.appeals_rejected || 0);
    document.getElementById('pending-count').textContent = 0; // Нет данных о в работе
    
    // Детализация
    document.getElementById('complaints-resolved').textContent = userStats.complaints_resolved || 0;
    document.getElementById('appeals-resolved').textContent = userStats.appeals_resolved || 0;
    document.getElementById('delays-count').textContent = userStats.delays || 0;
    document.getElementById('bans-issued').textContent = userStats.bans_issued || 0;
    
    // Финансы
    document.getElementById('total-earned').textContent = (userStats.total || 0) + ' ₽';
    document.getElementById('total-fine').textContent = (userStats.fine || 0) + ' ₽';
    document.getElementById('total-payment').textContent = (userStats.total || 0) + ' ₽';
    
    // Статус платежа
    const paymentStatusElement = document.createElement('div');
    paymentStatusElement.className = `payment-status ${userStats.payment_status === 'Оплачено' ? 'paid' : 'unpaid'}`;
    paymentStatusElement.textContent = `Статус: ${userStats.payment_status || 'Ожидает'}`;
    
    const financeSection = document.querySelector('.stats-finance');
    const existingStatus = financeSection.querySelector('.payment-status');
    if (existingStatus) {
        financeSection.removeChild(existingStatus);
    }
    financeSection.appendChild(paymentStatusElement);
}

document.addEventListener('DOMContentLoaded', function() {
    initTabs('#settingsModal .tab-btn', '#settingsModal .tab-content', '#settingsModal .tab-indicator');
    
    document.querySelector('[data-tab="settings"]').addEventListener('click', function() {
        showModal('settingsModal');
    });
    
    document.getElementById('new-password')?.addEventListener('input', function() {
        const strengthBar = document.querySelector('.strength-bar');
        const strengthText = document.querySelector('.strength-text');
        const password = this.value;
        
        let strength = 0;
        if (password.length > 0) strength += 1;
        if (password.length >= 8) strength += 1;
        if (/[A-Z]/.test(password)) strength += 1;
        if (/[0-9]/.test(password)) strength += 1;
        if (/[^A-Za-z0-9]/.test(password)) strength += 1;
        
        const width = strength * 20;
        strengthBar.style.width = `${width}%`;
        
        if (strength <= 2) {
            strengthBar.style.backgroundColor = '#ff4757';
            strengthText.textContent = 'Сложность: слабый';
        } else if (strength === 3) {
            strengthBar.style.backgroundColor = '#ffa502';
            strengthText.textContent = 'Сложность: средний';
        } else {
            strengthBar.style.backgroundColor = '#2ed573';
            strengthText.textContent = 'Сложность: сильный';
        }
    });
    
    // Обработчики форм
    document.getElementById('change-username-form')?.addEventListener('submit', handleUsernameChange);
    document.getElementById('change-password-form')?.addEventListener('submit', handlePasswordChange);
    document.getElementById('delete-account-form')?.addEventListener('submit', handleAccountDeletion);
});

async function handleUsernameChange(e) {
    e.preventDefault();
    const form = e.target;
    const username = form.querySelector('#new-username').value.trim();
    
    if (!username || username.length < 3 || username.length > 20) {
        showNotification('Никнейм должен быть от 3 до 20 символов', 'error');
        return;
    }
    
    try {
        const response = await fetch('/dashboard/user/request-username-change', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                new_username: username
            })
        });

        const result = await response.json();
        
        if (!response.ok) {
            if (result.detail && Array.isArray(result.detail)) {
                const errorMsg = result.detail[0].msg;
                const cleanMsg = errorMsg.replace(/^Value error,\s*/i, '');
                showNotification(cleanMsg, 'error');
            } else if (result.detail) {
                showNotification(result.detail, 'error');
            } else {
                showNotification(result.message || 'Ошибка отправки заявки', 'error');
            }
            return;
        }
        
        showNotification('Заявка на изменение никнейма отправлена на рассмотрение');
        hideModal('settingsModal');
    } catch (error) {
        showNotification(error.message, 'error');
    }
}

async function handlePasswordChange(e) {
    e.preventDefault();
    const form = e.target;
    const currentPassword = form.querySelector('#current-password').value;
    const newPassword = form.querySelector('#new-password').value;
    const confirmPassword = form.querySelector('#confirm-password').value;
    
    if (newPassword !== confirmPassword) {
        showNotification('Пароли не совпадают', 'error');
        return;
    }
    
    if (newPassword.length < 8) {
        showNotification('Пароль должен быть не менее 8 символов', 'error');
        return;
    }
    
    try {
        const response = await fetch('/dashboard/user/change-password', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                current_password: currentPassword,
                new_password: newPassword 
            })
        });

        const result = await response.json();
        
        if (!response.ok) {
            if (result.detail && Array.isArray(result.detail)) {
                const errorMsg = result.detail[0].msg;
                const cleanMsg = errorMsg.replace(/^Value error,\s*/i, '');
                showNotification(cleanMsg, 'error');
            } else if (result.detail) {
                showNotification(result.detail, 'error');
            } else {
                showNotification(result.message || 'Ошибка изменение пароля', 'error');
            }
            return;
        }
        
        showNotification('Пароль успешно изменен');
        hideModal('settingsModal');
    } catch (error) {
        showNotification(error.message, 'error');
    }
}

async function handleAccountDeletion(e) {
    e.preventDefault();
    const form = e.target;
    if (!confirm('Вы уверены, что хотите отправить заявку на удаление аккаунта? Это действие нельзя отменить.')) {
        return;
    }
    
    try {
        const response = await fetch('/dashboard/user/request-account-deletion', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        const result = await response.json();
        
        if (!response.ok) {
            if (result.detail && Array.isArray(result.detail)) {
                const errorMsg = result.detail[0].msg;
                const cleanMsg = errorMsg.replace(/^Value error,\s*/i, '');
                showNotification(cleanMsg, 'error');
            } else if (result.detail) {
                showNotification(result.detail, 'error');
            } else {
                showNotification(result.message || 'Ошибка отправки заявки', 'error');
            }
            return;
        }
        hideModal('settingsModal');
        showNotification('Заявка на удаление аккаунта отправлена');
    } catch (error) {
        showNotification(error.message, 'error');
    }
}

// Вспомогательные функции
function getAppealTypeName(type) {
    switch (type) {
        case 'help': return 'Помощь по форуму';
        case 'complaint': return 'Жалоба на модератора';
        case 'amnesty': return 'Амнистия наказания';
        default: return type;
    }
}

function getTypeName(type) {
    const types = {
        'help': 'Помощь',
        'complaint': 'Жалоба',
        'amnesty': 'Амнистия'
    };
    return types[type] || type;
}

function getAppealStatusName(status) {
    switch (status) {
        case 'pending': return 'Ожидает';
        case 'in_progress': return 'Обрабатывается'
        case 'resolved': return 'Завершено';
        case 'rejected': return 'Отклонено';
        default: return status;
    }
}

function getStatusClass(status) {
    switch (status) {
        case 'in_progress': return 'status-progress';
        case 'resolved': return 'status-completed'
        case 'rejected': return 'status-rejected';
        default: return 'status-pending';
    }
}

function formatDateTime(dateString) {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
}

function getActionName(actionType) {
    const actionNames = {
        'create_appeal': 'Создание обращения',
        'appeal_progress': 'Обращение в работе',
        'appeal_closed': 'Обращение закрыто',
        'update_role_user': 'Изменение роли',
        'account_deletion_requested': 'Запрос удаления',
        'update_stats_user': 'Обновление статистики',
        'reassigning_appeal': 'Переназначение',
        'banned_user': 'Блокировка',
        'unbanned_user': 'Разблокировка',
        'approved_request': 'Заявка одобрена',
        'rejected_request': 'Заявка отклонена',
        'password_changed': 'Смена пароля',
        'username_change_request': 'Запрос смены ника'
    };
    return actionNames[actionType] || actionType;
}

function getActionIcon(actionType) {
    const actionIcons = {
        'create_appeal': '<i class="fas fa-plus-circle"></i>',
        'appeal_progress': '<i class="fas fa-spinner"></i>',
        'appeal_closed': '<i class="fas fa-check-circle"></i>',
        'update_role_user': '<i class="fas fa-user-cog"></i>',
        'account_deletion_requested': '<i class="fas fa-trash-alt"></i>',
        'update_stats_user': '<i class="fas fa-chart-line"></i>',
        'reassigning_appeal': '<i class="fas fa-exchange-alt"></i>',
        'banned_user': '<i class="fas fa-ban"></i>',
        'unbanned_user': '<i class="fas fa-unlock"></i>',
        'approved_request': '<i class="fas fa-check"></i>',
        'rejected_request': '<i class="fas fa-times"></i>',
        'password_changed': '<i class="fas fa-key"></i>',
        'username_change_request': '<i class="fas fa-signature"></i>'
    };
    return actionIcons[actionType] || '<i class="fas fa-info-circle"></i>';
}
