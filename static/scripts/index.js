document.addEventListener('DOMContentLoaded', function() {
    initTabs('#loginModal .tab-btn', '#loginModal .tab-content', '#loginModal .tab-indicator');
    initTabs('#supportModal .tab-btn', '#supportModal .tab-content', '#supportModal .tab-indicator');
});

document.addEventListener('DOMContentLoaded', function() {
    document.querySelector('.profile-btn').addEventListener('click', async () => {
        if (currentUser) {
            window.location.href = "/dashboard/";
        }
        else {
            showModal('loginModal');
        }
    });
});

document.addEventListener('DOMContentLoaded', () => {
    const registerForm = document.getElementById('registerForm');

    // Валидация формы регистрации
    const regEmail = document.getElementById('regEmail');
    const regUsername = document.getElementById('regUsername');
    const regPassword = document.getElementById('regPassword');
    const regConfirmPassword = document.getElementById('regConfirmPassword');
    const emailError = document.getElementById('emailError');
    const usernameError = document.getElementById('usernameError');
    const passwordError = document.getElementById('passwordError');

    const strengthBar = document.querySelector('.strength-bar');
    const strengthText = document.querySelector('.strength-text');

    regPassword.addEventListener('input', function() {
        const password = this.value;
        let strength = 0;
        
        const hasUpper = /[A-Z]/.test(password);
        const hasLower = /[a-z]/.test(password);
        const hasNumber = /[0-9]/.test(password);
        const hasSpecial = /[!@#$%^&*(),.?":{}|<>]/.test(password);
        const hasLength = password.length >= 8;

        if (hasUpper) strength++;
        if (hasLower) strength++;
        if (hasNumber) strength++;
        if (hasSpecial) strength++;
        if (hasLength) strength++;
        
        const width = (strength / 5) * 100;
        strengthBar.style.width = `${width}%`;
        
        if (strength <= 1) {
            strengthBar.style.backgroundColor = '#ff4757';
            strengthText.textContent = 'Сложность: слабый';
        } else if (strength <= 3) {
            strengthBar.style.backgroundColor = '#ffa502';
            strengthText.textContent = 'Сложность: средний';
        } else {
            strengthBar.style.backgroundColor = '#2ed573';
            strengthText.textContent = 'Сложность: сильный';
        }
    });
    
    // Валидация email
    regEmail.addEventListener('blur', function() {
        const email = this.value.trim();
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        
        if (!email) {
            emailError.textContent = 'Поле обязательно для заполнения';
        } else if (!emailRegex.test(email)) {
            emailError.textContent = 'Введите корректный email';
        } else {
            emailError.textContent = '';
        }
    });
    
    // Валидация никнейма
    regUsername.addEventListener('blur', function() {
        const username = this.value.trim();
        const usernameRegex = /^[a-zA-Z0-9_ .]{3,50}$/;
        
        if (!username) {
            usernameError.textContent = 'Поле обязательно для заполнения';
        } else if (!usernameRegex.test(username)) {
            usernameError.textContent = 'Никнейм должен содержать 3-50 символов (буквы, цифры, пробелы и точки)';
        } else {
            usernameError.textContent = '';
        }
    });
    
    // Валидация подтверждения пароля
    regConfirmPassword.addEventListener('blur', function() {
        if (this.value !== regPassword.value) {
            passwordError.textContent = 'Пароли не совпадают';
        } else {
            passwordError.textContent = '';
        }
    });

    // Отправка формы регистрации
    registerForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        regEmail.dispatchEvent(new Event('blur'));
        regUsername.dispatchEvent(new Event('blur'));
        regPassword.dispatchEvent(new Event('input'));
        regConfirmPassword.dispatchEvent(new Event('blur'));
        
        const errors = document.querySelectorAll('.error-message');
        let hasErrors = false;
        
        errors.forEach(error => {
            if (error.textContent !== '') {
                hasErrors = true;
            }
        });

        if (!hasErrors) {
            const formData = {
                email: regEmail.value,
                username: regUsername.value,
                password: regPassword.value,
                password_confirm: regConfirmPassword.value
            };

            try {
                const response = await fetch('/auth/register', {
                    method: 'POST',
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
                        showNotification(result.message || 'Ошибка регистрации пользователя', 'error');
                    }
                    return;
                }
                this.reset();
                hideModal("loginModal");
                showNotification('На вашу почту отправлено письмо с подтверждением');

            } catch (error) {
                showNotification('Ошибка регистрации пользователя', 'error');

            }
        }
    });
});

document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('loginForm');
    const loginInput = document.getElementById('loginUsername');
    const passwordInput = document.getElementById('loginPassword');
    const loginError = document.createElement('div');
    loginError.className = 'error-message';
    loginInput.parentNode.appendChild(loginError);

    const passwordError = document.createElement('div');
    passwordError.className = 'error-message';
    passwordInput.parentNode.appendChild(passwordError);

    // Валидация логина (email или никнейм)
    loginInput.addEventListener('blur', function() {
        const value = this.value.trim();
        
        if (!value) {
            loginError.textContent = 'Поле обязательно для заполнения';
            return;
        }
        
        if (value.includes('@')) {
            // Проверка email
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(value)) {
                loginError.textContent = 'Введите корректный email';
            } else {
                loginError.textContent = '';
            }
        } else {
            // Проверка никнейма
            const usernameRegex = /^[a-zA-Z0-9_ .]{3,50}$/;
            if (!usernameRegex.test(value)) {
                loginError.textContent = 'Никнейм должен содержать 3-50 символов (буквы, цифры, пробелы и точки)';
            } else {
                loginError.textContent = '';
            }
        }
    });

    // Валидация пароля
    passwordInput.addEventListener('blur', function() {
        const password = this.value;
        
        if (!password) {
            passwordError.textContent = 'Поле обязательно для заполнения';
        } else if (password.length < 8) {
            passwordError.textContent = 'Пароль должен содержать минимум 8 символов';
        } else {
            passwordError.textContent = '';
        }
    });

    loginForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        // Триггерим проверки перед отправкой
        loginInput.dispatchEvent(new Event('blur'));
        passwordInput.dispatchEvent(new Event('blur'));
        
        // Проверяем наличие ошибок
        const errors = document.querySelectorAll('#loginForm .error-message');
        let hasErrors = false;
        
        errors.forEach(error => {
            if (error.textContent !== '') {
                hasErrors = true;
            }
        });
        
        if (hasErrors) {
            return;
        }
        
        const formData = new FormData(e.target);
        const loginValue = formData.get('loginUsername');
        const password = formData.get('loginPassword');
        
        try {
            const response = await fetch('/auth/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    login: loginValue,
                    password: password
                }),
            });

            const result = await response.json();
            console.log(response);
            
            if (!response.ok) {
                if (result.detail && Array.isArray(result.detail)) {
                    const errorMsg = result.detail[0].msg;
                    const cleanMsg = errorMsg.replace(/^Value error,\s*/i, '');
                    showNotification(cleanMsg, 'error');
                } else if (result.detail) {
                    showNotification(result.detail, 'error');
                } else {
                    showNotification(result.message || 'Ошибка авторизации пользователя', 'error');
                }
                return;
            }

            this.reset();
            hideModal("loginModal");

            showNotification("Успешный вход. Переадресация...");
            window.location.href = "/dashboard/";
        } catch (error) {
            showNotification("Ошибка авторизации пользователя", 'error');

        }
    });
});

document.addEventListener('DOMContentLoaded', function() {
    const faqItems = document.querySelectorAll('.faq-item');
    
    faqItems.forEach(item => {
        const header = item.querySelector('.faq-header');
        
        header.addEventListener('click', () => {
            faqItems.forEach(otherItem => {
                if (otherItem !== item && otherItem.classList.contains('active')) {
                    otherItem.classList.remove('active');
                }
            });
            
            item.classList.toggle('active');
        });
    });
});

