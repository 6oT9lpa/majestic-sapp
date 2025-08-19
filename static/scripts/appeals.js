document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('#appeal-btn').forEach(btn => {
        btn.addEventListener('click', async () => {
            showModal('supportModal');
            if (currentUser) {
                document.querySelectorAll('[id$="-email"], [id$="-nickname"]').forEach(el => {
                    if (el.id.includes('email')) {
                        el.value = currentUser.email;
                        el.readOnly = true;
                    } else if (el.id.includes('nickname')) {
                        el.value = currentUser.username;
                        el.readOnly = true;
                    }
                });
            }
        });
    });

    document.querySelectorAll('.password-toggle').forEach(toggle => {
        toggle.addEventListener('click', function() {
            const input = this.parentElement.querySelector('input');
            const icon = this.querySelector('i');
            if (input.type === 'password') {
                input.type = 'text';
                icon.classList.remove('fa-eye');
                icon.classList.add('fa-eye-slash');
            } else {
                input.type = 'password';
                icon.classList.remove('fa-eye-slash');
                icon.classList.add('fa-eye');
            }
        });
    });
})

document.addEventListener('DOMContentLoaded', function() {
    // Обработка формы помощи
    document.querySelector('#help-tab form').addEventListener('submit', async function(e) {
        e.preventDefault();
        await handleAppealSubmit(AppealType.HELP, this);
    });

    // Обработка формы жалобы
    document.querySelector('#complaint-tab form').addEventListener('submit', async function(e) {
        e.preventDefault();
        await handleAppealSubmit(AppealType.COMPLAINT, this);
    });

    // Обработка формы амнистии
    document.querySelector('#amnesty-tab form').addEventListener('submit', async function(e) {
        e.preventDefault();
        await handleAppealSubmit(AppealType.AMNESTY, this);
    });
});

function getFormData(type, form) {
    const data = { type };
    
    if (type === AppealType.HELP) {
        data.nickname = form.querySelector('#help-nickname').value;
        data.email = form.querySelector('#help-email').value;
        data.description = form.querySelector('#help-description').value;
        data.attachment = form.querySelector('#help-attachment').value || null;
    } else if (type === AppealType.COMPLAINT) {
        data.violator_nickname = form.querySelector('#complaint-nickname').value;
        data.description = form.querySelector('#complaint-description').value;
        data.attachment = form.querySelector('#complaint-attachment').value || null;
    } else if (type === AppealType.AMNESTY) {
        data.admin_nickname = form.querySelector('#amnesty-admin').value;
    }
    
    return data;
}

function validateUrl(url) {
    if (!url) return true; 
    
    const allowedDomains = [
        'youtube.com',
        'rutube.ru',
        'imgur.com',
        'yapix.ru'
    ];
    
    try {
        const urlObj = new URL(url.toLowerCase());
        return allowedDomains.some(domain => urlObj.hostname.includes(domain));
    } catch {
        return false;
    }
}


function validateAppealForm(type, form) {
    let isValid = true;
    
    if (type === AppealType.HELP) {
        const nickname = form.querySelector('#help-nickname');
        const email = form.querySelector('#help-email');
        const description = form.querySelector('#help-description');
        
        // Валидация никнейма
        if (!nickname.value || !/^[a-zA-Z0-9]{3,20}$/.test(nickname.value)) {
            showFieldError(nickname, 'Никнейм должен содержать 3-20 символов (буквы, цифры)');
            isValid = false;
        }
        
        // Валидация email
        if (!email.value || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value)) {
            showFieldError(email, 'Введите корректный email');
            isValid = false;
        }
        
        // Валидация описания
        if (!description.value || description.value.length < 10 || description.value.length > 1500) {
            showFieldError(description, 'Описание должно содержать от 10 до 1500 символов');
            isValid = false;
        }

        const attachment = form.querySelector('#help-attachment');
        if (attachment.value && !validateUrl(attachment.value)) {
            showFieldError(attachment, 'Разрешены только ссылки с YouTube, Rutube, Imgur или Yapix');
            isValid = false;
        }
        
    } else if (type === AppealType.COMPLAINT) {
        const violatorNickname = form.querySelector('#complaint-nickname');
        const description = form.querySelector('#complaint-description');
        
        // Валидация никнейма нарушителя
        if (!violatorNickname.value || !/^[a-zA-Z0-9]{3,50}$/.test(violatorNickname.value)) {
            showFieldError(violatorNickname, 'Никнейм должен содержать 3-50 символов (буквы, цифры)');
            isValid = false;
        }
        
        // Валидация описания
        if (!description.value || description.value.length < 10 || description.value.length > 1500) {
            showFieldError(description, 'Описание должно содержать от 10 до 1500 символов');
            isValid = false;
        }

        const attachment = form.querySelector('#complaint-attachment');
        if (attachment.value && !validateUrl(attachment.value)) {
            showFieldError(attachment, 'Разрешены только ссылки с YouTube, Rutube, Imgur или Yapx');
            isValid = false;
        }
        
    } else if (type === AppealType.AMNESTY) {
        const adminNickname = form.querySelector('#amnesty-admin');
        const description = form.querySelector('#amnesty-description');

        // Валидация никнейма администратора
        if (adminNickname.value && !/^[a-zA-Z0-9]{3,50}$/.test(adminNickname.value)) {
            showFieldError(adminNickname, 'Никнейм должен содержать 3-50 символов (буквы, цифры)');
            isValid = false;
        }

        if (!description.value || description.value.length < 10 || description.value.length > 1500) {
            showFieldError(description, 'Описание должно содержать от 10 до 1500 символов');
            isValid = false;
        }
    }
    
    return isValid;
}

function showFieldError(inputElement, message) {
    let errorElement = inputElement.nextElementSibling;
    if (!errorElement || !errorElement.classList.contains('error-message')) {
        errorElement = document.createElement('div');
        errorElement.className = 'error-message';
        inputElement.parentNode.insertBefore(errorElement, inputElement.nextSibling);
    }
    
    errorElement.textContent = message;
    inputElement.classList.add('error');
    
    const hideError = () => {
        errorElement.textContent = '';
        inputElement.classList.remove('error');
        inputElement.removeEventListener('input', hideError);
    };
    
    inputElement.addEventListener('input', hideError, { once: true });
}

function clearFieldErrors(form) {
    form.querySelectorAll('.error-message').forEach(el => {
        el.textContent = '';
    });
    form.querySelectorAll('.error').forEach(el => {
        el.classList.remove('error');
    });
}

async function checkUserExists(formData) {
    try {
        const response = await fetch('/auth/check-user', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                email: formData.email,
                username: formData.nickname || formData.violator_nickname || formData.admin_nickname
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
                showNotification(result.message || 'Ошибка проверки пользователя', 'error');
            }
            return false;
        }

        return result.exists;
    } catch (error) {
        showNotification('Ошибка при проверке пользователя', 'error');
        return false;
    }
}

async function handleAppealSubmit(type, form) {
    clearFieldErrors(form);
    
    if (!validateAppealForm(type, form)) {
        return;
    }
    
    const formData = getFormData(type, form);
    
    if (!currentUser) {
        try {
            const userExists = await checkUserExists(formData);
            
            if (userExists) {
                showNotification('Пользователь с такими данными уже существует. Пожалуйста, войдите в систему.', 'error');
                showLoginModal(formData, type);
                return;
            } else {
                showRegistrationModal(formData, type);
                return;
            }
        } catch (error) {
            return;
        }
    }
    
    try {
        const response = await fetch(`/appeal/${type}`, {
            method: 'POST',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
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
                showNotification(result.message || 'Ошибка отправки обращения', 'error');
            }
            return;
        }

        showNotification('Обращение успешно отправлено');
        if (document.querySelector('.appeals-container')) {
            loadUserAppeals();
        }

        hideModal('supportModal');
        form.reset();

    } catch (error) {
        showNotification(error.message, 'error');
    }
}

function showLoginModal(formData, appealType) {
    localStorage.setItem('pending_appeal', JSON.stringify({
        data: formData,
        type: appealType
    }));
    
    showModal('loginModal');
    document.querySelector('[data-tab="login"]').click();
    
    if (formData.email || formData.nickname) {
        document.getElementById('loginUsername').value = formData.email || formData.nickname;
    }
}

function showRegistrationModal(formData, appealType) {
    localStorage.setItem('pending_appeal', JSON.stringify({
        data: formData,
        type: appealType
    }));
    
    showModal('loginModal');
    document.querySelector('[data-tab="register"]').click();
    
    if (formData.email) {
        document.getElementById('regEmail').value = formData.email;
    }
    if (formData.nickname) {
        document.getElementById('regUsername').value = formData.nickname;
    }
    
    // Добавляем обработчик для отправки обращения после успешной регистрации
    document.addEventListener('userRegistered', () => {
        const pendingAppeal = JSON.parse(localStorage.getItem('pending_appeal'));
        if (pendingAppeal) {
            const formSelector = `#${pendingAppeal.type}-tab form`;
            const originalForm = document.querySelector(formSelector);
            
            if (originalForm) {
                Object.entries(pendingAppeal.data).forEach(([key, value]) => {
                    const input = originalForm.querySelector(`[name="${key}"]`);
                    if (input) {
                        input.value = value;
                    }
                });
                handleAppealSubmit(pendingAppeal.type, originalForm);
                localStorage.removeItem('pending_appeal');
                hideModal('loginModal');
            }
        }
    });
}

const AppealType = {
    HELP: 'help',
    COMPLAINT: 'complaint',
    AMNESTY: 'amnesty'
};