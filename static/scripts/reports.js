document.addEventListener('DOMContentLoaded', async () => {
    initTabs('.tab-btn', '.tab-content', '.tab-indicator', {
        onTabChange: (tabId) => {
            if (tabId === 'delays') {
                loadDelays();
            } else if (tabId === 'complaints') {
                loadComplaints();
            } else if (tabId === 'appeals') {
                loadAppeals();
            } else if (tabId === 'user-reports') {
                loadUserStats();
                initUserReportsTabs();
            }
        },
        saveToLocalStorage: 'reportsActiveTab'
    });


    await loadComplaints();
    setupFilters();
    setupAppealFilters();
    initRewardSettingsModal();
    document.getElementById('reward-settings-btn')?.addEventListener('click', () => {
        showModal('rewardSettingsModal');
    });
});
let currentFilters = {
    status: 'all',
    date: null,
    admin: '',
    page: 1,
    perPage: 20
};

let currentAppealFilters = {
    status: 'all',
    type: 'all',
    moderator: '',
    page: 1,
    perPage: 20
};

let currentUserReportFilters = {
    admin: '',
    page: 1,
    perPage: 20
};

let searchQueries = {
    complaints: '',
    appeals: '',
    delays: '',
    userReports: ''
};

const searchInputs = {
    complaints: document.getElementById('complaints-search-input'),
    appeals: document.getElementById('appeals-search-input'),
    delays: document.getElementById('delays-search-input')
};

let activityChart = null;
let filtersVisible = false;
let filtersAppealVisible = false;
let activeTabId = null;
let currentChartMonth = new Date().getMonth() + 1;
let currentChartYear = new Date().getFullYear();

function initUserReportsTabs() {
    const tabBtns = document.querySelectorAll('.user-tab-btn');
    const tabContents = document.querySelectorAll('.user-tab-content');
    
    tabBtns.forEach(btn => {
        btn.removeEventListener('click', handleUserTabClick);
        btn.addEventListener('click', handleUserTabClick);
    });

    function handleUserTabClick() {
        const tabId = this.getAttribute('data-tab');
        const currentActiveTab = document.querySelector('.user-tab-btn.active');

        if (currentActiveTab === this) return;
        
        tabBtns.forEach(b => b.classList.remove('active'));
        this.classList.add('active');
        
        tabContents.forEach(content => {
            content.classList.remove('active');
            if(content.id === `${tabId}-tab`) {
                content.classList.add('active');
                
                if (tabId === 'user-stats') {
                    loadUserStats();
                } else if (tabId === 'user-activity') {
                    initActivityChart();
                }
            }
        });
    }
    
    if (tabBtns.length > 0 && !document.querySelector('.user-tab-btn.active')) {
        tabBtns[0].click();
    }
}

async function loadComplaints(page = currentFilters.page) {
    currentFilters.page = page;
    const reportsList = document.querySelector('.reports-list');
    
    reportsList.innerHTML = `
        <div class="loading-row">
            <i class="fas fa-spinner fa-spin"></i> Загрузка жалоб...
        </div>
    `;

    try {
        const params = new URLSearchParams();
        if (currentFilters.status !== 'all') params.append('status', currentFilters.status);
        if (currentFilters.date) params.append('date', currentFilters.date);
        if (searchQueries.complaints) params.append('admin', searchQueries.complaints);
        params.append('page', currentFilters.page);
        params.append('per_page', currentFilters.perPage);

        const response = await fetch(`/dashboard/admin/reports/complaints?${params.toString()}`, {
            credentials: 'include'
        });

        if (!response.ok) throw new Error('Ошибка загрузки жалоб');

        const data = await response.json();
        renderComplaints(data);
    } catch (error) {
        reportsList.innerHTML = `
            <div class="no-complaints">Ошибка загрузки: ${error.message}</div>
        `;
    }
}

function renderComplaints(data) {
    const reportsList = document.querySelector('.reports-list');
    
    if (!data.complaints || data.complaints.length === 0) {
        reportsList.innerHTML = '<div class="no-complaints">Жалоб не найдено</div>';
        renderPagination(
            'complaints-pagination',
            1,
            0,
            data.per_page || currentFilters.perPage,
            loadComplaints
        );
        return;
    }

    let html = '';
    
    data.complaints.forEach(complaint => {
        const startDate = new Date(complaint.startDate).toLocaleString();
        const endDate = complaint.endDate ? new Date(complaint.endDate).toLocaleString() : '—';
        const adminName = complaint.staff ? complaint.staff.replace(/⦮ ⦯ /g, '') : 'Неизвестно';
        
        html += `
            <div class="complaint-card">
                <div class="complaint-header">
                    <span class="complaint-id">ID: ${complaint.report_id}</span>
                    <span class="complaint-status ${complaint.status === 'Решено' ? 'status-completed' : 'status-rejected'}">
                        ${complaint.status}
                    </span>
                </div>
                <div class="complaint-details">
                    <strong>Дата жалобы:</strong> ${complaint.reportDate}
                </div>
                <div class="complaint-details">
                    <strong>Администратор:</strong> ${adminName}
                </div>
                <div class="complaint-details">
                    <strong>Время обработки:</strong> ${startDate} → ${endDate}
                </div>
                <div class="complaint-details">
                    <strong>Длительность:</strong> ${complaint.durationFormatted}
                </div>
                <div class="complaint-footer">
                    <a href="${complaint.link}" target="_blank" class="complaint-link">
                        Перейти к жалобе
                    </a>
                </div>
            </div>
        `;
    });
    
    reportsList.innerHTML = html;
    renderPagination(
        'complaints-pagination',
        data.page,
        data.total,
        data.per_page,
        loadComplaints
    );
}

async function loadDelays(page = 1) {
    const delaysTab = document.querySelector('#delays-tab');
    const reportsList = delaysTab.querySelector('.reports-list');
    
    reportsList.innerHTML = `
        <div class="loading-row">
            <i class="fas fa-spinner fa-spin"></i> Загрузка просроченных жалоб...
        </div>
    `;

    try {
        const params = new URLSearchParams();
        params.append('page', page);
        params.append('per_page', currentFilters.perPage);
        if (searchQueries.delays) params.append('admin', searchQueries.delays);

        const response = await fetch(`/dashboard/admin/reports/delayed-complaints?${params.toString()}`, {
            credentials: 'include'
        });

        if (!response.ok) throw new Error('Ошибка загрузки просроченных жалоб');

        const data = await response.json();
        renderDelays(data);
    } catch (error) {
        reportsList.innerHTML = `
            <div class="no-complaints">Ошибка загрузки: ${error.message}</div>
        `;
    }
}

function renderDelays(data) {
    const reportsList = document.querySelector('#delays-tab' + ' .reports-list');
    
    if (!data.complaints || data.complaints.length === 0) {
        reportsList.innerHTML = '<div class="no-complaints">Просроченных жалоб не найдено</div>';
        return;
    }

    let html = '';
    
    data.complaints.forEach(complaint => {
        const startDate = new Date(complaint.startDate).toLocaleString();
        const endDate = new Date(complaint.endDate).toLocaleString();
        const adminName = complaint.staff ? complaint.staff.replace(/⦮ ⦯ /g, '') : 'Неизвестно';
        
        html += `
            <div class="complaint-card">
                <div class="complaint-header">
                    <span class="complaint-id">ID: ${complaint.report_id}</span>
                    <span class="complaint-status status-delayed">
                        Просрочка: ${complaint.delay_hours} ч
                    </span>
                </div>
                <div class="complaint-details">
                    <strong>Дата жалобы:</strong> ${complaint.reportDate}
                </div>
                <div class="complaint-details">
                    <strong>Администратор:</strong> ${adminName}
                </div>
                <div class="complaint-details">
                    <strong>Время обработки:</strong> ${startDate} → ${endDate}
                </div>
                <div class="complaint-details">
                    <strong>Длительность:</strong> ${complaint.durationFormatted}
                </div>
                <div class="complaint-footer">
                    <a href="${complaint.link}" target="_blank" class="complaint-link">
                        Перейти к жалобе
                    </a>
                </div>
            </div>
        `;
    });
    
    reportsList.innerHTML = html;
    
    if (data.total > data.per_page) {
        renderPagination(
            'delays-pagination',
            data.page,
            data.total,
            data.per_page,
            loadDelays
        );
    }
}

async function loadAppeals(page = currentAppealFilters.page) {
    currentAppealFilters.page = page;
    const reportsList = document.querySelector('#appeals-tab .reports-list');
    
    reportsList.innerHTML = `
        <div class="loading-row">
            <i class="fas fa-spinner fa-spin"></i> Загрузка обращений...
        </div>
    `;

    try {
        const params = new URLSearchParams();
        
        if (Array.isArray(currentAppealFilters.status)) {
            currentAppealFilters.status.forEach(status => {
                params.append('status', status);
            });
        }
        
        if (currentAppealFilters.type !== 'all') {
            params.append('appeal_type', currentAppealFilters.type);
        }
        
        if (searchQueries.appeals) {
            params.append('moderator', searchQueries.appeals);
        }
        
        params.append('page', currentAppealFilters.page);
        params.append('per_page', currentAppealFilters.perPage);
        
        const response = await fetch(`/dashboard/admin/reports/appeal-stats?${params.toString()}`, {
            credentials: 'include'
        });

        if (!response.ok) throw new Error('Ошибка загрузки обращений');

        const data = await response.json();
        renderAppeals(data);
    } catch (error) {
        reportsList.innerHTML = `
            <div class="no-complaints">Ошибка загрузки: ${error.message}</div>
        `;
    }
}

function renderAppeals(data) {
    const reportsList = document.querySelector('#appeals-tab .reports-list');
    
    if (!data.appeals || data.appeals.length === 0) {
        reportsList.innerHTML = '<div class="no-complaints">Обращений не найдено</div>';
        renderPagination(
            'appeals-pagination',
            1,
            0,
            data.per_page || currentAppealFilters.perPage,
            loadAppeals
        );
        return;
    }

    let html = ''

    data.appeals.forEach(appeal => {
        const createdDate = new Date(appeal.created_at).toLocaleString();
        const assignedDate = appeal.assigned_at ? new Date(appeal.assigned_at).toLocaleString() : '—';
        const closedDate = appeal.closed_at ? new Date(appeal.closed_at).toLocaleString() : '—';

        const typeNames = {
            'help': 'Помощь',
            'complaint': 'Жалоба',
            'amnesty': 'Амнистия'
        };
        
        const statusClasses = {
            'pending': 'appeal-status pending',
            'in_progress': 'appeal-status in_progress',
            'resolved': 'appeal-status resolved',
            'rejected': 'appeal-status rejected'
        };
        
        const statusNames = {
            'pending': 'Ожидает',
            'in_progress': 'В работе',
            'resolved': 'Рассмотрено',
            'rejected': 'Отклонено'
        };
        
        html += `
            <div class="complaint-card">
                <div class="complaint-header">
                    <span class="complaint-server">${typeNames[appeal.type] || appeal.type}</span>
                    <span class="${statusClasses[appeal.status] || 'appeal-status'}">
                        ${statusNames[appeal.status] || appeal.status}
                    </span>
                </div>
                <div class="complaint-details">
                    <strong>Создал:</strong> ${appeal.creator || 'Неизвестно'}
                </div>
                <div class="complaint-details">
                    <strong>Модератор:</strong> ${appeal.moderator || 'Не назначен'}
                </div>

                ${appeal.status === 'resolved' || appeal.status === 'rejected' ? `
                    <div class="complaint-details">
                        <strong>Время обработки:</strong> ${assignedDate} → ${closedDate}
                    </div>
                ` : appeal.assigned_at ? `
                <div class="complaint-details">
                    <strong>Назначено:</strong> ${assignedDate}
                </div>
                ` : ''}
                <div class="complaint-footer">
                    <span class="complaint-date">Создано: ${createdDate}</span>
                </div>
            </div>
        `;
    });
    
    reportsList.innerHTML = html;
    renderPagination(
        'appeals-pagination',
        data.page || currentAppealFilters.page,
        data.total || 0,
        data.per_page || currentAppealFilters.perPage,
        loadAppeals
    );
}

async function loadUserStats(page = currentUserReportFilters.page) {
    currentUserReportFilters.page = page;
    const reportsList = document.querySelector('#user-stats-tab .reports-list');
    
    reportsList.innerHTML = `
        <div class="loading-row">
            <i class="fas fa-spinner fa-spin"></i> Загрузка статистики...
        </div>
    `;

    try {
        const params = new URLSearchParams();
        if (searchQueries.userReports) params.append('admin_name', searchQueries.userReports);
        params.append('page', currentUserReportFilters.page);
        params.append('per_page', currentUserReportFilters.perPage);

        const response = await fetch(`/dashboard/admin/reports/user-stats?${params.toString()}`, {
            credentials: 'include'
        });

        if (!response.ok) throw new Error('Ошибка загрузки статистики');

        const data = await response.json();
        renderUserStats(data);
    } catch (error) {
        reportsList.innerHTML = `
            <div class="no-complaints">Ошибка загрузки: ${error.message}</div>
        `;
    }
}

function renderUserStats(data) {
    const reportsList = document.querySelector('#user-stats-tab .reports-list');
    
    if (!data.users || data.users.length === 0) {
        reportsList.innerHTML = '<div class="no-complaints">Данные не найдены</div>';
        renderPagination(
            'user-stats-pagination',
            1,
            0,
            data.per_page || currentUserReportFilters.perPage,
            loadUserStats
        );
        return;
    }

    if (isTableView) {
        convertToTableView(data.users);
    } else {
        let html = '';
        
        data.users.forEach(user => {
            html += `
                <div class="complaint-card">
                    <div class="complaint-header">
                        <span class="complaint-title">${user.username}</span>
                        <div class="complaint-actions">
                            <button class="edit-btn" data-username="${user.username}">
                                <i class="fas fa-edit"></i>
                            </button>
                            <button class="expand-btn">
                                <i class="fas fa-chevron-down"></i>
                            </button>
                        </div>
                        <span class="complaint-status ${user.payment_status === 'Выплачено' ? 'status-completed' : 'status-pending'}">
                            ${user.payment_status}
                        </span>
                    </div>
                    <div class="complaint-details-collapsible">
                        <div class="complaint-details">
                            <strong>Закрытые жалобы:</strong> <span class="positive">${user.complaints_resolved}</span>
                        </div>
                        <div class="complaint-details">
                            <strong>Отказные жалобы:</strong> <span class="negative">${user.complaints_rejected}</span>
                        </div>
                        <div class="complaint-details">
                            <strong>Закрытые обращения:</strong> <span class="positive">${user.appeals_resolved}</span>
                        </div>
                        <div class="complaint-details">
                            <strong>Отказные обращения:</strong> <span class="negative">${user.appeals_rejected}</span>
                        </div>
                        <div class="complaint-details">
                            <strong>Выданные баны:</strong> <span class="neutral">${user.bans_issued || 0}</span>
                        </div>
                        <div class="complaint-details">
                            <strong>Просрочки:</strong> <span class="negative">${user.delays}</span>
                        </div>
                        <div class="complaint-details">
                            <strong>Сервер:</strong> <span>${user.server || '—'}</span>
                        </div>
                        <div class="complaint-details">
                            <strong>Штраф:</strong> <span class="negative">${user.fine}</span>
                        </div>
                        <div class="complaint-details">
                            <strong>Итого:</strong> ${user.total}
                        </div>
                        <div class="complaint-footer">
                            <span class="complaint-date">Статус: ${user.payment_status}</span>
                        </div>
                    </div>
                </div>
            `;
        });
        
        reportsList.innerHTML = html;
    }

    // Назначаем обработчики для кнопок редактирования
    document.querySelectorAll('.edit-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const username = btn.dataset.username;
            openEditModal(username);
        });
    });

    setupExpandButtons();

    renderPagination(
        'user-stats-pagination',
        data.page,
        data.total,
        data.per_page,
        loadUserStats
    );
}

async function initActivityChart() {
    const month = parseInt(document.getElementById('chart-month-select').value);
    const year = parseInt(document.getElementById('chart-year-select').value);
    
    const ctx = document.getElementById('activityChart').getContext('2d');
    const loadingElement = document.createElement('div');
    loadingElement.className = 'loading-row';
    loadingElement.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Загрузка данных активности...';
    
    const chartContainer = document.getElementById('activityChart').parentNode;
    chartContainer.innerHTML = '';
    chartContainer.appendChild(loadingElement);

    try {
        const response = await fetch(`/dashboard/admin/reports/user-activity?month=${month}&year=${year}`, {
            credentials: 'include'
        });

        if (!response.ok) throw new Error('Ошибка загрузки данных активности');

        const data = await response.json();
        
        if (activityChart) {
            activityChart.destroy();
        }
        
        chartContainer.innerHTML = '<canvas id="activityChart"></canvas>';
        const newCtx = document.getElementById('activityChart').getContext('2d');
        
        activityChart = new Chart(newCtx, {
            type: 'line',
            data: {
                labels: data.labels,
                datasets: data.datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Количество обработанных жалоб и обращений'
                        },
                        ticks: {
                            precision: 0
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Дата'
                        },
                        ticks: {
                            maxRotation: 45,
                            minRotation: 45
                        }
                    }
                },
                plugins: {
                    title: {
                        display: true,
                        text: `Активность администраторов (${getMonthName(month)} ${year})`,
                        font: {
                            size: 16
                        }
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        callbacks: {
                            label: function(context) {
                                return `${context.dataset.label}: ${context.raw}`;
                            }
                        }
                    },
                    legend: {
                        position: 'bottom',
                        labels: {
                            boxWidth: 12,
                            padding: 20,
                            font: {
                                size: 12
                            }
                        }
                    }
                },
                interaction: {
                    mode: 'index',
                    intersect: false
                }
            }
        });
    } catch (error) {
        console.error('Ошибка при загрузке данных для графика:', error);
        chartContainer.innerHTML = `
            <div class="no-complaints">Ошибка загрузки данных: ${error.message}</div>
        `;
    }
}

function renderPagination(containerId, currentPage, totalItems, perPage, callback) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
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

function setupAppealFilters() {
    document.getElementById('appeal-filter-toggle').addEventListener('click', toggleAppealFilters);
    document.getElementById('apply-appeal-filters').addEventListener('click', applyAppealFilters);
    document.getElementById('reset-appeal-filters').addEventListener('click', resetAppealFilters);
    
    const statusSelect = document.getElementById('appeal-status-filter');
    Array.from(statusSelect.options).forEach(opt => {
        opt.selected = opt.value === 'all';
    });

    statusSelect.addEventListener('change', function() {
        const selected = Array.from(this.selectedOptions);
        if (selected.some(opt => opt.value === 'all')) {
            Array.from(this.options).forEach(opt => {
                opt.selected = opt.value === 'all';
            });
        }
        else if (selected.length > 0) {
            this.querySelector('option[value="all"]').selected = false;
        }
    });
    
    document.addEventListener('click', (e) => {
        const filtersPanel = document.getElementById('appeal-filters-panel');
        const filterToggle = document.getElementById('appeal-filter-toggle');
        
        if (!filtersPanel.contains(e.target) && e.target !== filterToggle && filtersAppealVisible) {
            toggleAppealFilters();
        }
    });
}

async function openEditModal(username) {
    try {
        const response = await fetch(`/dashboard/admin/reports/user-stats?admin_name=${encodeURIComponent(username)}`, {
            credentials: 'include'
        });
        const data = await response.json();
        
        const user = data.users[0];
        if (!user) return;

        const modal = document.getElementById('editStatsModal');
        showModal('editStatsModal');

        // Заполняем форму
        document.getElementById('modalTitle').textContent = `Редактирование статистики: ${username}`;
        document.getElementById('edit-complaints-resolved').value = user.complaints_resolved;
        document.getElementById('edit-complaints-rejected').value = user.complaints_rejected;
        document.getElementById('edit-appeals-resolved').value = user.appeals_resolved;
        document.getElementById('edit-appeals-rejected').value = user.appeals_rejected;
        document.getElementById('edit-bans-issued').value = user.bans_issued || 0;
        document.getElementById('edit-delays').value = user.delays;
        document.getElementById('edit-fine').value = user.fine || 0;
        document.getElementById('edit-server').value = user.server || '';
        
        // Сохранение изменений
        modal.querySelector('.save-edit').addEventListener('click', async () => {
            const updatedData = {
                username: username,
                complaints_resolved: parseInt(document.getElementById('edit-complaints-resolved').value),
                complaints_rejected: parseInt(document.getElementById('edit-complaints-rejected').value),
                appeals_resolved: parseInt(document.getElementById('edit-appeals-resolved').value),
                appeals_rejected: parseInt(document.getElementById('edit-appeals-rejected').value),
                bans_issued: parseInt(document.getElementById('edit-bans-issued').value),
                delays: parseInt(document.getElementById('edit-delays').value),
                fine: parseInt(document.getElementById('edit-fine').value),
                server: document.getElementById('edit-server').value.trim() || null
            };

            try {
                const response = await fetch(`/dashboard/admin/reports/update-user-stats`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    credentials: 'include',
                    body: JSON.stringify(updatedData)
                });

                if (!response.ok) {
                    throw new Error('Ошибка при сохранении изменений');
                }

                loadUserStats(currentUserReportFilters.page);
                hideModal('editStatsModal');
            } catch (error) {
                showNotification('Ошибка при сохранении изменений', 'error');
            }
        });
    } catch (error) {
        console.error('Ошибка при открытии модального окна:', error);
    }
}

function setupExpandButtons() {
    document.querySelectorAll('.complaint-card .expand-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const card = btn.closest('.complaint-card');
            card.classList.toggle('expanded');
            
            const icon = btn.querySelector('i');
            if (icon) {
                icon.classList.toggle('fa-chevron-down');
                icon.classList.toggle('fa-chevron-up');
            }
        });
    });
}

// Добавим в начало файла с другими константами
let isTableView = false;

// Добавим в функцию setupFilters() обработчик для новой кнопки
document.getElementById('export-table-btn')?.addEventListener('click', toggleTableView);

function toggleTableView() {
    isTableView = !isTableView;
    const btn = document.getElementById('export-table-btn');
    const reportsList = document.querySelector('#user-stats-tab .reports-list');
    
    if (isTableView) {
        btn.innerHTML = '<i class="fas fa-list"></i> Вернуть к карточкам';
        // Получаем текущие данные пользователей из DOM
        const cards = reportsList.querySelectorAll('.complaint-card');
        if (cards.length > 0) {
            const users = Array.from(cards).map(card => {
                // Извлекаем текст из элементов и преобразуем в числа
                const getNumberFromSelector = (selector) => {
                    const element = card.querySelector(selector);
                    return element ? parseInt(element.textContent) || 0 : 0;
                };

                return {
                    username: card.querySelector('.complaint-title')?.textContent || 'Неизвестно',
                    server: card.querySelector('.complaint-details:nth-child(7) span')?.textContent || '—',
                    complaints_resolved: getNumberFromSelector('.complaint-details:nth-child(1) .positive'),
                    complaints_rejected: getNumberFromSelector('.complaint-details:nth-child(2) .negative'),
                    appeals_resolved: getNumberFromSelector('.complaint-details:nth-child(3) .positive'),
                    appeals_rejected: getNumberFromSelector('.complaint-details:nth-child(4) .negative'),
                    bans_issued: getNumberFromSelector('.complaint-details:nth-child(5) .neutral'),
                    delays: getNumberFromSelector('.complaint-details:nth-child(6) .negative'),
                    fine: getNumberFromSelector('.complaint-details:nth-child(8) .negative'),
                    total: parseInt(card.querySelector('.complaint-details:nth-child(9)')?.textContent.replace('Итого:', '').trim()) || 0,
                    payment_status: card.querySelector('.complaint-date')?.textContent.replace('Статус:', '').trim() || 'Неизвестно'
                };
            });
            convertToTableView(users);
        }
    } else {
        btn.innerHTML = '<i class="fas fa-table"></i> Экспорт в таблицу';
        if (reportsList) {
            reportsList.innerHTML = '';
            loadUserStats(currentUserReportFilters.page);
        }
    }
}

function convertToTableView(users) {
    const reportsList = document.querySelector('#user-stats-tab .reports-list');
    if (!reportsList || !users) return;

    // Создаем контейнер для таблицы
    const tableContainer = document.createElement('div');
    tableContainer.className = 'table-container';
    
    // Создаем таблицу
    const table = document.createElement('table');
    table.className = 'exported-table';
    
    // Создаем заголовок таблицы
    const thead = document.createElement('thead');
    thead.innerHTML = `
        <tr>
            <th>Пользователь</th>
            <th>Сервер</th>
            <th>Закрытые жалобы</th>
            <th>Отказные жалобы</th>
            <th>Закрытые обращения</th>
            <th>Отказные обращения</th>
            <th>Выданные баны</th>
            <th>Просрочки</th>
            <th>Штраф</th>
            <th>Итого</th>
            <th>Статус выплаты</th>
            <th>Действия</th>
        </tr>
    `;
    table.appendChild(thead);
    
    // Заполняем таблицу данными
    const tbody = document.createElement('tbody');
    
    users.forEach(user => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${user.username}</td>
            <td>${user.server || '—'}</td>
            <td class="positive">${user.complaints_resolved}</td>
            <td class="negative">${user.complaints_rejected}</td>
            <td class="positive">${user.appeals_resolved}</td>
            <td class="negative">${user.appeals_rejected}</td>
            <td class="neutral">${user.bans_issued || 0}</td>
            <td class="negative">${user.delays}</td>
            <td class="negative">${user.fine}</td>
            <td>${user.total}</td>
            <td class="${user.payment_status === 'Выплачено' ? 'positive' : 'pending'}">${user.payment_status}</td>
            <td>
                <button class="edit-btn" data-username="${user.username}">
                    <i class="fas fa-edit"></i> Редактировать
                </button>
            </td>
        `;
        tbody.appendChild(row);
    });
    
    table.appendChild(tbody);
    tableContainer.appendChild(table);
    
    // Очищаем контейнер и добавляем новое содержимое
    reportsList.innerHTML = '';
    reportsList.appendChild(tableContainer);
    
    // Назначаем обработчики для кнопок редактирования
    document.querySelectorAll('.edit-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const username = btn.dataset.username;
            openEditModal(username);
        });
    });
}

async function initRewardSettingsModal() {
    const modal = document.getElementById('rewardSettingsModal');
    const settings = await loadRewardSettings();
    
    if (settings) {
        document.getElementById('complaint-reward').value = settings.complaint_reward;
        document.getElementById('appeal-reward').value = settings.appeal_reward;
        document.getElementById('delay-penalty').value = settings.delay_penalty;
    }
    
    // Сохранение настроек
    modal.querySelector('.save-settings-btn').addEventListener('click', async () => {
        const updatedSettings = {
            complaint_reward: parseInt(document.getElementById('complaint-reward').value),
            appeal_reward: parseInt(document.getElementById('appeal-reward').value),
            delay_penalty: parseInt(document.getElementById('delay-penalty').value)
        };
        
        await saveRewardSettings(updatedSettings);
        hideModal('rewardSettingsModal');
    });
}

async function loadRewardSettings() {
    try {
        const response = await fetch('/dashboard/admin/reports/reward-settings', {
            credentials: 'include'
        });
        return await response.json();
    } catch (error) {
        console.error('Ошибка загрузки настроек:', error);
        showNotification('Ошибка загрузки настроек', 'error');
        return null;
    }
}

async function saveRewardSettings(settings) {
    try {
        const response = await fetch('/dashboard/admin/reports/update-reward-settings', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include',
            body: JSON.stringify(settings)
        });
        
        if (!response.ok) {
            throw new Error('Ошибка сохранения настроек');
        }
        
        showNotification('Настройки успешно сохранены', 'success');
        return await response.json();
    } catch (error) {
        console.error('Ошибка сохранения настроек:', error);
        showNotification('Ошибка сохранения настроек', 'error');
        return null;
    }
}

function setupFilters() {

    // Добавлю обработчики для поиска
    document.getElementById('filter-toggle').addEventListener('click', toggleFilters);
    document.getElementById('apply-filters').addEventListener('click', applyFilters);
    document.getElementById('reset-filters').addEventListener('click', resetFilters);

    // Обработчик поиска для жалоб
    const complaintsSearch = document.querySelector('#complaints-tab .search-box');
    complaintsSearch.querySelector('button').addEventListener('click', () => {
        searchQueries.complaints = complaintsSearch.querySelector('input').value.trim();
        loadComplaints();
    });
    complaintsSearch.querySelector('input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            searchQueries.complaints = complaintsSearch.querySelector('input').value.trim();
            loadComplaints();
        }
    });

    // Обработчик поиска для просрочек
    const delaysSearch = document.querySelector('#delays-tab .search-box');
    delaysSearch.querySelector('button').addEventListener('click', () => {
        searchQueries.delays = delaysSearch.querySelector('input').value.trim();
        loadDelays();
    });
    delaysSearch.querySelector('input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            searchQueries.delays = delaysSearch.querySelector('input').value.trim();
            loadDelays();
        }
    });

    // Обработчик поиска для обращений
    const appealsSearch = document.querySelector('#appeals-tab .search-box');
    appealsSearch.querySelector('button').addEventListener('click', () => {
        searchQueries.appeals = appealsSearch.querySelector('input').value.trim();
        loadAppeals();
    });
    appealsSearch.querySelector('input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            searchQueries.appeals = appealsSearch.querySelector('input').value.trim();
            loadAppeals();
        }
    });

    // Обработчик поиска для отчетов пользователей
    const userReportsSearch = document.querySelector('#user-reports-tab .search-box');
    const userSearchInput = userReportsSearch.querySelector('input');
    userReportsSearch.querySelector('button').addEventListener('click', () => {
        currentUserReportFilters.page = 1;
        searchQueries.userReports = userSearchInput.value.trim();
        loadUserStats();
    });
    userSearchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            currentUserReportFilters.page = 1;
            searchQueries.userReports = userSearchInput.value.trim();
            loadUserStats();
        }
    });

    populateYearSelect();
    
    document.getElementById('chart-month-select').value = currentChartMonth;
    document.getElementById('refresh-chart-btn').addEventListener('click', initActivityChart);
    document.getElementById('chart-month-select').addEventListener('change', initActivityChart);
    document.getElementById('chart-year-select').addEventListener('change', initActivityChart);
}

function toggleFilters() {
    const filtersPanel = document.getElementById('filters-panel');
    filtersVisible = !filtersVisible;
    
    if (filtersVisible) {
        filtersPanel.classList.add('show');
    } else {
        filtersPanel.classList.remove('show');
    }
}

function applyFilters() {
    const statusFilter = document.getElementById('status-filter');
    const dateFilter = document.getElementById('date-filter');
    
    currentFilters = {
        status: statusFilter.value,
        date: dateFilter.value || null,
        admin: '',
        page: 1,
        perPage: 20
    };
    
    loadComplaints();
    toggleFilters();
}

function resetFilters() {
    document.getElementById('status-filter').value = 'all';
    document.getElementById('date-filter').value = '';
    
    currentFilters = {
        status: 'all',
        date: null,
        admin: '',
        page: 1,
        perPage: 20
    };
    
    searchQueries.complaints = '';
    document.getElementById('complaints-search-input').value = '';
    loadComplaints();
    toggleFilters();
}

function toggleAppealFilters() {
    const filtersPanel = document.getElementById('appeal-filters-panel');
    filtersAppealVisible = !filtersAppealVisible;
    
    if (filtersAppealVisible) {
        filtersPanel.classList.add('show');
    } else {
        filtersPanel.classList.remove('show');
    }
}

function applyAppealFilters() {
    const typeFilter = document.getElementById('appeal-type-filter');
    const statusSelect = document.getElementById('appeal-status-filter');
    
    const selectedOptions = Array.from(statusSelect.selectedOptions);
    
    currentAppealFilters = {
        status: selectedOptions.length === 0 || 
                selectedOptions.some(opt => opt.value === 'all') 
                ? 'all' 
                : selectedOptions.map(opt => opt.value),
        type: typeFilter.value,
        page: 1,
        perPage: 20,
        moderator: currentAppealFilters.moderator
    };
    
    loadAppeals();
    toggleAppealFilters();
}

function resetAppealFilters() {
    document.getElementById('appeal-type-filter').value = 'all';
    const statusSelect = document.getElementById('appeal-status-filter');
    Array.from(statusSelect.options).forEach(opt => {
        opt.selected = opt.value === 'all';
    });
    
    currentAppealFilters = {
        status: 'all',
        type: 'all',
        page: 1,
        perPage: 20,
        moderator: null
    };
    
    searchQueries.appeals = '';
    document.getElementById('appeals-search-input').value = '';
    loadAppeals();
    toggleAppealFilters();
}

function populateYearSelect() {
    const yearSelect = document.getElementById('chart-year-select');
    const currentYear = new Date().getFullYear();
    
    yearSelect.innerHTML = '';
    for (let year = currentYear; year >= currentYear - 5; year--) {
        const option = document.createElement('option');
        option.value = year;
        option.textContent = year;
        if (year === currentYear) {
            option.selected = true;
        }
        yearSelect.appendChild(option);
    }
}

function getMonthName(month) {
    const months = [
        'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
        'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
    ];
    return months[month - 1];
}