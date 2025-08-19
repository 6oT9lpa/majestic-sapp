document.addEventListener('DOMContentLoaded', function() {
    const curr_year = document.getElementById('current-year');
    if (curr_year)
    {
        curr_year.textContent = new Date().getFullYear();
    }

    const savedTheme = localStorage.getItem('theme') || 'dark';
    setTheme(savedTheme);

    const themeToggle = document.querySelector('.theme-toggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', toggleTheme);
    }

    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)');
    if (!localStorage.getItem('theme') && prefersDark.matches) {
        setTheme('dark');
    }

    document.querySelectorAll('.close-modal').forEach(btn => {
        btn.addEventListener('click', function() {
            const modal = this.closest('.modal');
            if (modal) {
                hideModal(modal.id);
            }
        });
    });

    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            hideModal();
        }
    });
});

function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
}

function toggleTheme() {
    const currentTheme = localStorage.getItem('theme') || 'dark';
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    setTheme(newTheme);
}

function showModal(modalId) {
    const modal = document.getElementById(modalId);
    modal.style.display = 'flex';

    // Очищаем все поля ввода в модальном окне
    const inputs = modal.querySelectorAll('input, textarea');
    inputs.forEach(input => {
        input.value = '';
        // Убираем классы ошибок, если они есть
        if (input.nextElementSibling && input.nextElementSibling.classList.contains('error-message')) {
            input.nextElementSibling.textContent = '';
        }
        // Сбрасываем состояние видимости пароля
        if (input.type === 'text' && input.id.includes('Password')) {
            const toggle = input.parentElement.querySelector('.password-toggle i');
            if (toggle) {
                toggle.classList.remove('fa-eye-slash');
                toggle.classList.add('fa-eye');
            }
            input.type = 'password';
        }
    });

    // Сбрасываем индикатор сложности пароля, если есть
    const strengthBar = modal.querySelector('.strength-bar');
    if (strengthBar) {
        strengthBar.style.width = '0%';
        strengthBar.style.backgroundColor = '';
        const strengthText = modal.querySelector('.strength-text');
        if (strengthText) strengthText.textContent = 'Сложность: слабый';
    }

    // Сбрасываем активную вкладку на первую
    const firstTab = modal.querySelector('.tab-btn');
    if (firstTab) firstTab.click();

    setTimeout(() => {
        modal.classList.remove('hidden');
        modal.classList.add('show');
    }, 10);
}

function hideModal(modalId = null) {
    if (modalId) {
        // Закрываем конкретное модальное окно
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.remove('show');
            modal.classList.add('hidden');
            
            setTimeout(() => {
                modal.style.display = 'none';
            }, 450);
        }
    } else {
        // Закрываем все модальные окна 
        const modals = document.querySelectorAll('.modal');
        modals.forEach(modal => {
            modal.classList.remove('show');
            modal.classList.add('hidden');
            
            setTimeout(() => {
                modal.style.display = 'none';
            }, 450);
        });
    }
}

let refreshAttempted = false;

async function get_current_user() {
    try {
        const response = await fetch('/auth/get-user', {
            method: 'GET',
            credentials: 'include',
            headers: {
                'Accept': 'application/json'
            }
        });

        if (response.status === 401) {
            if (!refreshAttempted) {
                refreshAttempted = true;
                const refreshSuccess = await refreshToken();
                if (refreshSuccess) {
                    return get_current_user();
                }
            }
            
            clearTokens();
            return null;
        }

        if (!response.ok) {
            throw new Error('Failed to get user');
        }

        refreshAttempted = false; 
        return await response.json();

    } catch (e) {
        console.error('Failed to get current user:', e);
        clearTokens();
        return null;
    }
}

async function refreshToken() {
    try {
        const response = await fetch('/auth/refresh', {
            method: 'POST',
            credentials: 'include', 
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
        });

        if (!response.ok) {
            return false;
        }

        return true;

    } catch (error) {
        console.error('Refresh token error:', error);
        showNotification('Ошибка обновления сессии. Пожалуйста, войдите снова.', 'error');
        return false;
    }
}

async function clearTokens() {
    let response = await fetch('/auth/logout', {
        method: 'POST',
        credentials: 'include' 
    })

    if (!response.ok) {
        return false;
    }
    return true;
}

function logout() {
    fetch('/auth/logout', {
        method: 'POST',
        credentials: 'include' 
    }).finally(() => {
        window.location.href = '/';
    });
}

function showNotification(message, type = 'success', duration = 3000, action = null) {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    
    let actionButton = '';
    if (action) {
        actionButton = `<button class="notification-action">Открыть</button>`;
    }
    
    notification.innerHTML = `
        <div class="notification-icon">
            <i class="fas fa-${type === 'success' ? 'check-circle' : 
            type === 'error' ? 'exclamation-circle' : 
            'exclamation-triangle'}"></i>
        </div>
        <div class="notification-message">${message}</div>
        ${actionButton}
    `;
    
    document.body.appendChild(notification);
    
    if (action) {
        notification.querySelector('.notification-action').addEventListener('click', action);
    }
    
    setTimeout(() => {
        notification.classList.add('fade-out');
        setTimeout(() => notification.remove(), 3000);
    }, duration);
}

function hasAuthToken() {
    return document.cookie.split(';').some(cookie => 
        cookie.trim().startsWith('access_token=')
    );
}

document.querySelectorAll('form').forEach(form => {
    form.addEventListener('submit', function(e) {
        const btn = this.querySelector('button[type="submit"]');
        if (btn) {
            btn.classList.add('loading');
        }
    });
});

function initTabs(tabButtonsSelector, tabContentsSelector, indicatorSelector, options = {}) {
    const tabBtns = document.querySelectorAll(tabButtonsSelector);
    const tabContents = document.querySelectorAll(tabContentsSelector);
    const tabIndicator = document.querySelector(indicatorSelector);
    const dropdownBtn = options.dropdownBtn ? document.querySelector(options.dropdownBtn) : null;
    const dropdown = dropdownBtn?.closest('.dropdown');
    const dropdownItems = options.dropdownItems ? document.querySelectorAll(options.dropdownItems) : [];

    const isMobileScreen = () => window.innerWidth <= 768;

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
        const newActiveElement = element || document.querySelector(`${tabButtonsSelector}[data-tab="${tabId}"]`);

        if (currentActiveTab === newActiveElement) {
            return;
        }

        tabBtns.forEach(b => b.classList.remove('active'));
        if (dropdownItems.length > 0) {
            dropdownItems.forEach(item => item.classList.remove('active'));
        }

        if (element) {
            element.classList.add('active');

            if (dropdownItems.length > 0 && element.classList.contains('dropdown-item')) {
                if (dropdownBtn) {
                    dropdownBtn.innerHTML = element.textContent +
                        `<svg class="dropdown-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M6 9L12 15L18 9" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                        </svg>`;
                }
            }
        } else {
            const dropdownItem = document.querySelector(`.dropdown-item[data-tab="${tabId}"]`);
            if (dropdownItem) dropdownItem.classList.add('active');
        }

        tabContents.forEach(content => {
            content.classList.remove('active');
            if (content.id === `${tabId}-tab`) {
                content.classList.add('active');

                if (options.onTabChange) {
                    options.onTabChange(tabId);
                }
            }
        });

        updateTabIndicator();

        if (options.saveToLocalStorage) {
            localStorage.setItem(options.saveToLocalStorage, tabId);
        }
    }

    if (dropdownBtn) {
        dropdownBtn.addEventListener('click', function (e) {
            e.stopPropagation();
            dropdown.classList.toggle('active');
        });

        dropdownItems.forEach(item => {
            item.addEventListener('click', function () {
                const tabId = this.getAttribute('data-tab');
                activateTab(tabId, this);
                dropdown.classList.remove('active');
            });
        });
    }

    document.addEventListener('click', function () {
        if (dropdown) dropdown.classList.remove('active');
    });

    function updateTabIndicator() {
        if (isMobileScreen()) {
            tabIndicator.style.display = 'none';
            return;
        }

        const activeBtn = document.querySelector(`${tabButtonsSelector}.active`);
        if (activeBtn && activeBtn.getAttribute('data-tab') !== 'settings') {
            tabIndicator.style.display = 'block';
            tabIndicator.style.width = `${activeBtn.offsetWidth}px`;
            tabIndicator.style.left = `${activeBtn.offsetLeft}px`;
        } else {
            tabIndicator.style.display = 'none';
        }
    }

    window.addEventListener('resize', updateTabIndicator);

    // Активация таба по умолчанию
    const savedTabId = options.saveToLocalStorage ? localStorage.getItem(options.saveToLocalStorage) : null;
    const defaultTabId = savedTabId || (options.defaultTabId ? options.defaultTabId : tabBtns[0]?.getAttribute('data-tab'));

    if (defaultTabId) {
        const tabToActivate = Array.from(tabBtns).find(btn => btn.getAttribute('data-tab') === defaultTabId) ||
            (dropdownItems.length > 0 ? Array.from(dropdownItems).find(item => item.getAttribute('data-tab') === defaultTabId) : null);

        if (tabToActivate) {
            tabToActivate.click();
        } else if (tabBtns.length > 0) {
            tabBtns[0].click();
        } else if (dropdownItems.length > 0) {
            dropdownItems[0].click();
        }
    } else if (tabBtns.length > 0) {
        tabBtns[0].click();
    } else if (dropdownItems.length > 0) {
        dropdownItems[0].click();
    }

    setTimeout(updateTabIndicator, 100);
}