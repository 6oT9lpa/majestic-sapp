let socket = null;
let isConnecting = false;
let messageQueue = [];

let currentAppealId = null;
let currentAppeal = null;
let reassignTimer = null;
let closeTimer = null;

let attachments = [];
let currentUploads = [];

document.getElementById('attachment-btn').addEventListener('click', () => {
    document.getElementById('file-input').click();
});

const fileInput = document.createElement('input');
fileInput.type = 'file';
fileInput.id = 'file-input';
fileInput.multiple = true;
fileInput.accept = 'image/png, image/jpeg, image/gif';
fileInput.style.display = 'none';
fileInput.addEventListener('change', handleFileSelect);
document.body.appendChild(fileInput);

document.addEventListener("DOMContentLoaded", async () => {
    toggleModalClass();
    setupDragAndDrop();
});
window.addEventListener('resize', toggleModalClass);

function toggleModalClass() {
    const container = document.querySelector('.appeal-chat-container');
    if (!container) return;

    if (window.innerWidth <= 1200) {
        container.classList.add('modal');
    } else {
        container.classList.remove('modal');
    }
}

async function connectWebSocket(appealId) {
    if (!appealId) {
        console.error('Invalid appealId');
        return;
    }

    if (socket && socket.readyState === WebSocket.OPEN && currentAppealId === appealId) {
        return;
    }

    if (socket) {
        socket.close(1000, "Reconnecting");
        socket = null;
    }

    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/messanger/appeals/${appealId}/ws`;
    
    return new Promise((resolve, reject) => {
        try {
            socket = new WebSocket(wsUrl);
            
            socket.onopen = () => {
                currentAppealId = appealId;
                isConnecting = false;
                
                setupMessageHandler();
                
                while (messageQueue.length > 0) {
                    const message = messageQueue.shift();
                    socket.send(JSON.stringify(message));
                }
                resolve();
            };
            
            socket.onmessage = (event) => {
                const message = JSON.parse(event.data);
                
                if (message.error) {
                    return;
                }
                
                addMessageToChat(message);
            };
            
            socket.onclose = (event) => {
                isConnecting = false;
                console.log("WebSocket closed:", event);

                if (event.code !== 1000) {
                    canNotWriteToTheChat();
                }
            };
            
            socket.onerror = (error) => {
                isConnecting = false;
                reject(error);
            };
            
        } catch (error) {
            isConnecting = false;
            reject(error);
        }
    });
}

function addMessageToChat(message) {
    const messagesContainer = document.getElementById('appeal-messages');
    if (!messagesContainer) return;
    
    const messageElement = document.createElement('div');
    messageElement.className = message.is_system ? 'message system-message' : 
                            message.user_id === currentAppeal.user_id ? 'message user-message' : 'message admin-message';
    
    let displayName = message.is_system ? 'Система' : 
                    message.username || 
                    (message.user_id === currentAppeal.user_id ? currentAppeal.user_name : 
                    (message.user_id === currentAppeal.assigned_moder_id ? currentAppeal.assigned_moder_name : 
                    'Пользователь #' + message.user_id.substring(0, 8)));

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
            <strong>${displayName}</strong>
            <span class="message-date">${new Date(message.created_at).toLocaleString()}</span>
        </div>
        ${message.message ? `<div class="message-content">${message.message}</div>` : ''}
        ${attachmentsHtml}
    `;
    
    messagesContainer.appendChild(messageElement);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function setupDragAndDrop() {
    const chatContainer = document.getElementById('appeal-chat-container');
    
    chatContainer.addEventListener('dragover', (e) => {
        e.preventDefault();
        chatContainer.classList.add('drag-over');
    });
    
    chatContainer.addEventListener('dragleave', () => {
        chatContainer.classList.remove('drag-over');
    });
    
    chatContainer.addEventListener('drop', (e) => {
        e.preventDefault();
        chatContainer.classList.remove('drag-over');
        
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            fileInput.files = e.dataTransfer.files;
            handleFileSelect({ target: fileInput });
        }
    });
}

function handleFileSelect(event) {
    const files = event.target.files;
    if (!files || files.length === 0) return;
    
    if (files.length > 10) {
        showNotification('Можно загрузить не более 10 файлов за раз', 'error');
        return;
    }
    
    for (let i = 0; i < files.length; i++) {
        const file = files[i];
        
        if (file.size > 10 * 1024 * 1024) {
            showNotification(`Файл ${file.name} слишком большой (макс. 10MB)`, 'error');
            return;
        }
        
        const ext = file.name.split('.').pop().toLowerCase();
        if (!['png', 'jpg', 'jpeg', 'gif'].includes(ext)) {
            showNotification(`Недопустимый формат файла ${file.name}`, 'error');
            return;
        }
    }
    
    currentUploads = Array.from(files);
    renderAttachmentsList();
}

function renderAttachmentsList() {
    const attachmentsContainer = document.getElementById('attachments-list');
    if (!attachmentsContainer) return;
    
    attachmentsContainer.innerHTML = '';
    
    currentUploads.forEach((file, index) => {
        const attachmentItem = document.createElement('div');
        attachmentItem.className = 'attachment-item';
        attachmentItem.innerHTML = `
            <span class="attachment-name">${file.name}</span>
            <span class="attachment-size">${formatFileSize(file.size)}</span>
            <button class="remove-attachment" data-index="${index}">×</button>
        `;
        attachmentsContainer.appendChild(attachmentItem);
    });
    
    document.querySelectorAll('.remove-attachment').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const index = parseInt(e.target.getAttribute('data-index'));
            currentUploads.splice(index, 1);
            renderAttachmentsList();
        });
    });
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1) + ' ' + sizes[i]);

}

function setupMessageHandler() {
    socket.onmessage = (event) => {
        try {
            const message = JSON.parse(event.data);
            
            console.log(message);
            if (message.error && message.error !== "Слишком частые сообщения. Пожалуйста, подождите.") {
                showNotification(message.error, 'error');
                console.log("WebSocket closed:", event);
                canNotWriteToTheChat();
                return;
            }

            if (message.error) {
                showNotification(message.error, 'error');
                return;
            }

            canWriteToTheChat();
            
            if (message.attachments) {
                addMessageToChat({
                    ...message,
                    attachments: message.attachments
                });
            } 
            else if (message.is_system) {
                addMessageToChat(message);
                
                if (message.message.includes('взято в работу') && currentAppeal) {
                    currentAppeal.assigned_moder_id = message.user_id;
                    currentAppeal.assigned_moder_name = message.user_name;
                    currentAppeal.status = 'in_progress';
                    updateAppealStatusUI();
                }
                
                if (message.message.includes('закрыто') || message.message.includes('переназначено')) {
                    loadAppealChat(currentAppealId);
                }
            } 
            else {
                addMessageToChat(message);
            }
            
            document.getElementById('message-input').value = '';
            document.getElementById('char-count').textContent = '0';
            
        } catch (error) {
            console.error('Ошибка обработки сообщения:', error);
        }
    };
}

async function sendMessage() {
    const messageInput = document.getElementById('message-input');
    const message = messageInput.value.trim();
    
    if (!message && currentUploads.length === 0) return;
    
    try {
        let attachmentIds = [];
        
        // Если есть файлы для загрузки
        if (currentUploads.length > 0) {
            const formData = new FormData();
            currentUploads.forEach(file => {
                formData.append('files', file);
            });
            
            const uploadResponse = await fetch(`/messanger/appeals/${currentAppealId}/upload`, {
                method: 'POST',
                credentials: 'include',
                body: formData
            });
            
            if (!uploadResponse.ok) {
                const error = await uploadResponse.json();
                throw new Error(error.detail || 'Ошибка загрузки файлов');
            }
            
            const uploadResult = await uploadResponse.json();
            attachmentIds = uploadResult.attachments.map(att => att.saved_name);  
        }
        
        // Отправка сообщения
        const messageToSend = {
            message: message,
            attachment_ids: attachmentIds  
        };
        
        if (socket && socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify(messageToSend));
        } else {
            messageQueue.push(messageToSend);
            await connectWebSocket(currentAppealId);
        }
        
        // Очищаем после отправки
        messageInput.value = '';
        currentUploads = [];
        renderAttachmentsList();
        document.getElementById('char-count').textContent = '0';
        if (document.getElementById('appeals-active-tab')) {
            loadAppeals('appeals-active');
        }
    } catch (error) {
        showNotification(error.message, 'error');
    }
}

function showAppealChat(appealId) {
    const dashboardContent = document.querySelector('.dashboard-content');
    const chatContainer = document.getElementById('appeal-chat-container');
    
    dashboardContent.classList.add('chat-open');
    chatContainer.style.display = 'flex';
}

function hideAppealChat() {
    const dashboardContent = document.querySelector('.dashboard-content');
    const chatContainer = document.getElementById('appeal-chat-container');
    
    dashboardContent.classList.remove('chat-open');
    chatContainer.style.display = 'none';
    
    if (socket) {
        socket.close(1000);
        socket = null;
    }
    
    currentAppealId = null;
    currentAppeal = null;
}

async function loadAppealChat(appealId) {
    try {
        const response = await fetch(`/messanger/appeals/${appealId}/chat`, {
            credentials: 'include'
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Ошибка загрузки');
        }
        
        const data = await response.json();
        currentAppeal = data.appeal;
        renderAppealChat(data);
        await connectWebSocket(appealId);
        
    } catch (error) {
        showNotification(error.message, 'error');
        hideAppealChat();
    }
}

function renderAppealChat(data) {
    const { appeal, messages, can_send_messages, attachments } = data;

    document.getElementById('appeal-id').textContent = `ID: ${appeal.id}`;
    document.getElementById('appeal-type').textContent = `${getTypeName(appeal.type)}`;

    const messagesContainer = document.getElementById('appeal-messages');
    messagesContainer.innerHTML = '';

    let fullDescription = appeal.description;

    if (appeal.additional_info) {
        if (appeal.type === 'help' && appeal.additional_info.attachment) {
            fullDescription += `<br><br><strong>Доказательство:</strong> ${appeal.additional_info.attachment}`;
        }
        else if (appeal.type === 'complaint') {
            if (appeal.additional_info.violator_nickname) {
                fullDescription += `<br><br><strong>Нарушитель:</strong> ${appeal.additional_info.violator_nickname}`;
            }
            if (appeal.additional_info.attachment) {
                fullDescription += `<br><strong>Прикрепленный файл:</strong> ${appeal.additional_info.attachment}`;
            }
        }
        else if (appeal.type === 'amnesty' && appeal.additional_info.admin_nickname) {
            fullDescription += `<br><br><strong>Администратор:</strong> ${appeal.additional_info.admin_nickname}`;
        }
    }

    const appealMessage = document.createElement('div');
    appealMessage.className = 'message user-message';
    appealMessage.innerHTML = `
        <div class="message-header">
            <strong>${appeal.user_name || 'Аноним'}</strong>
            <span class="message-date">${new Date(appeal.created_at).toLocaleString()}</span>
        </div>
        <div class="message-content">${fullDescription}</div>
    `;
    messagesContainer.appendChild(appealMessage);

    if (can_send_messages && appeal.assigned_moder_id === currentUser.id) {
        addControlButtons(appeal);
    }

    messages.forEach(msg => {
        // Добавляем сообщение с вложениями, если они есть
        addMessageToChat({
            ...msg,
            attachments: msg.attachments || []
        });
    });

    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    if (can_send_messages) {
        canWriteToTheChat();
    } else {
        canNotWriteToTheChat(appeal);
    }

    initChatForm();
}

async function showReassignOptions(appealId) {
    try {
        const response = await fetch(`/dashboard/admin/appeals/${appealId}/support-moderator`, {
            credentials: 'include'
        });
        
        let hasSupportModerator = false;
        let moderatorInfo = null;
        
        if (response.ok) {
            moderatorInfo = await response.json();
            hasSupportModerator = !!moderatorInfo?.moderator;
        }

        const modal = document.createElement('div');
        modal.className = 'reassign-modal';
        modal.innerHTML = `
            <div class="modal-content">
                <h3>Переназначить обращение</h3>
                <div class="options">
                    <button class="option-btn" data-type="unassign">
                        <i class="fas fa-user-slash"></i> Снять модератора
                    </button>
                    ${hasSupportModerator ? `
                    <button class="option-btn" data-type="to_support_moderator">
                        <i class="fas fa-user-tag"></i> Переназначить на ${moderatorInfo.moderator.name}
                        ${moderatorInfo.support_team.length > 1 ? 
                        ` (+${moderatorInfo.support_team.length - 1} других саппортов)` : ''}
                    </button>
                    ` : ''}
                </div>
                <button class="cancel-btn">Отмена</button>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        modal.querySelectorAll('.option-btn').forEach(btn => {
            btn.addEventListener('click', async () => {
                const type = btn.getAttribute('data-type');
                
                try {
                    await fetch(`/messanger/appeals/${appealId}/reassign`, {
                        method: 'POST',
                        credentials: 'include',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            reassign_type: type
                        })
                    });
                    
                    modal.remove();
                    showNotification('Обращение переназначено', 'success');
                    loadAppealChat(appealId);
                } catch (error) {
                    console.error(error);
                    showNotification('Ошибка переназначения', 'error');
                }
            });
        });
        
        modal.querySelector('.cancel-btn').addEventListener('click', () => {
            modal.remove();
        });

        if (document.getElementById('appeals-active-tab')) {
            loadAppeals('appeals-active');
        }
    } catch (error) {
        console.error(error);
    }
}

async function showCloseOptions(appealId, appealType) {
    const existingModal = document.querySelector('.close-appeal');
    if (existingModal) existingModal.remove();

    const modal = document.createElement('div');
    modal.className = 'close-appeal';
    modal.innerHTML = `
        <div class="modal-content">
            <h3>Закрыть обращение</h3>
            <div class="options">
                ${appealType === 'help' ? `
                <button class="option-btn" data-status="resolved">
                    Закрыть обращение
                </button>
                ` : `
                <button class="option-btn" data-status="resolved">
                    <i class="fas fa-check"></i> Одобрить
                </button>
                <button class="option-btn" data-status="rejected">
                    <i class="fas fa-times"></i> Отклонить
                </button> `}
            </div>
            <button class="cancel-btn">Отмена</button>
        </div>
    `;
    
    modal.querySelectorAll('.option-btn').forEach(btn => {
        btn.addEventListener('click', async () => {
            const status = btn.getAttribute('data-status');
            
            try {
                await closeAppeal(appealId, status);
                modal.remove();

            } catch (error) {
                console.error(error);
                showNotification('Ошибка закрытия обращения', 'error');
            }
        });
    });
    
    modal.querySelector('.cancel-btn').addEventListener('click', () => {
        modal.remove();
    });

    if (document.getElementById('appeals-active-tab')) {
        loadAppeals('appeals-active');
    }
    
    document.body.appendChild(modal);
}

async function closeAppeal(appealId, status) {
    try {
        const response = await fetch(`/messanger/appeals/${appealId}/close`, {
            method: 'POST',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                status: status
            })
        });
        
        if (!response.ok) throw new Error('Ошибка закрытия');
        
        const result = await response.json();
        showNotification(result.detail, 'success');
        await loadAppealChat(appealId);
        hideAppealChat();
        
    } catch (error) {
        console.error(error);
        showNotification(error.message, 'error');
        throw error;
    }
}

function addControlButtons(appeal) {
    const controlsContainer = document.createElement('div');
    controlsContainer.className = 'appeal-controls';
    
    controlsContainer.innerHTML = `
        <button class="control-btn reassign-btn">
            <i class="fas fa-user-edit"></i> Переназначить
        </button>
        <button class="control-btn close-appeal-btn">
            <i class="fas fa-lock"></i> Закрыть
        </button>
    `;

    controlsContainer.querySelector('.reassign-btn').addEventListener('click', () => {
        showReassignOptions(appeal.id);
    });
    
    controlsContainer.querySelector('.close-appeal-btn').addEventListener('click', () => {
        showCloseOptions(appeal.id, appeal.type);
    });
    
    document.getElementById('appeal-messages').appendChild(controlsContainer);
}

function initChatForm() {
    const textarea = document.getElementById('message-input');
    const charCount = document.getElementById('char-count');
    
    textarea.addEventListener('input', () => {
        charCount.textContent = textarea.value.length;
    });

    document.getElementById('send-message-btn').addEventListener('click', sendMessage);
    
    textarea.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
}

function initAppealActions() {
    document.querySelectorAll('.take-btn').forEach(btn => {
        btn.addEventListener('click', async () => {
            const appealId = btn.getAttribute('data-id');
            
            if (currentAppealId === appealId) {
                hideAppealChat();
                return;
            }
            
            showAppealChat(appealId);
            await loadAppealChat(appealId);
        });
    });
    
    document.querySelector('.close-chat-btn')?.addEventListener('click', hideAppealChat);
}

// Вспомогательные функции
function getPermissionWarningText(type, status) {
    if (status === 'resolved' || status === 'rejected') {
        return "Это обращение уже закрыто, отправка сообщений невозможна";
    }
    
    const warnings = {
        'help': "Вы не можете отвечать в данное обращение.",
        'complaint': "Вы не можете отвечать в данное обращение.",
        'amnesty': "Вы не можете отвечать в данное обращение."
    };
    
    return warnings[type] || "У вас нет прав на отправку сообщений в это обращение";
}

function updateAppealStatusUI() {
    if (!currentAppeal) return;
    
    const statusElement = document.getElementById('appeal-status');
    if (statusElement) {
        statusElement.textContent = getStatusName(currentAppeal.status);
    }

    loadAppealChat(currentAppealId);
}

function canNotWriteToTheChat(appeal) {
    const messageForm = document.getElementById('appeal-messages');
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-message-btn');
    const attachmentBtn = document.getElementById('attachment-btn');

    messageInput.placeholder = "Вы не можете отправлять сообщения в это обращение";
    messageInput.disabled = true;
    sendButton.disabled = true;
    attachmentBtn.disabled = true;
    
    if (appeal) {
        const existingWarning = messageForm.querySelector('.permission-warning');
        if (existingWarning) {
            existingWarning.remove();
        }
        
        const warning = document.createElement('div');
        warning.className = 'permission-warning';
        if (appeal.status === 'resolved' || appeal.status === 'rejected') {
            warning.textContent = "Это обращение уже закрыто, отправка сообщений невозможна";
        } else {
            warning.textContent = getPermissionWarningText(appeal.type, appeal.status);
        }
        messageForm.insertBefore(warning, messageForm.firstChild);
    }
}

function canWriteToTheChat() {
    const messageForm = document.getElementById('appeal-messages');
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-message-btn');
    const attachmentBtn = document.getElementById('attachment-btn');

    const existingWarning = messageForm.querySelector('.permission-warning');
    if (existingWarning) {
        existingWarning.remove();
    }

    messageInput.placeholder = "Введите сообщение...";
    messageInput.disabled = false;
    sendButton.disabled = false;
    attachmentBtn.disabled = false;
}