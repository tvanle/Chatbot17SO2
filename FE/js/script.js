// DOM Elements
const sidebar = document.getElementById('sidebar');
const menuBtn = document.getElementById('menuBtn');
const mobileMenuBtn = document.getElementById('mobileMenuBtn');
const messageInput = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');
const messages = document.getElementById('messages');
const themeToggle = document.getElementById('themeToggle');
const userBtn = document.getElementById('userBtn');
const newChatBtn = document.getElementById('newChatBtn');
const attachBtn = document.getElementById('attachBtn');
const moreBtn = document.getElementById('moreBtn');
const modelSelector = document.getElementById('modelSelector');
const currentModelSpan = document.getElementById('currentModel');
const API_BASE = "http://127.0.0.1:8000"; // cổng BE FastAPI

// Mock Chat Histories Data
const mockChatHistories = [
    {
    id: 'chat-1',
    title: 'Cổng thông tin PTIT',
    timestamp: Date.now() - 1000 * 60 * 30,
    messages: [
        { type: 'user', content: 'Cổng thông tin Học viện Công nghệ Bưu chính Viễn thông (PTIT) là gì?' },
        { type: 'assistant', content: 'Cổng thông tin chính thức của PTIT là: https://ptit.edu.vn/' }
    ]
},
{
    id: 'chat-2',
    title: 'Liên kết Phòng Giáo vụ PTIT',
    timestamp: Date.now() - 1000 * 60 * 60 * 2,
    messages: [
        { type: 'user', content: 'Link Phòng Giáo vụ của PTIT là gì?' },
        { type: 'assistant', content: 'Trang Phòng Giáo vụ PTIT: https://giaovu.ptit.edu.vn/' }
    ]
},
{
    id: 'chat-3',
    title: 'Trang QLĐT PTIT',
    timestamp: Date.now() - 1000 * 60 * 60 * 5,
    messages: [
        { type: 'user', content: 'Trang quản lý đào tạo của PTIT là gì?' },
        { type: 'assistant', content: 'Hệ thống QLĐT của PTIT: https://qldt.ptit.edu.vn' }
    ]
},
{
    id: 'chat-4',
    title: 'Hệ thống Slink PTIT',
    timestamp: Date.now() - 1000 * 60 * 60 * 24,
    messages: [
        { type: 'user', content: 'Web Slink của PTIT là gì?' },
        { type: 'assistant', content: 'Slink PTIT: https://slink.ptit.edu.vn/' }
    ]
},
{
    id: 'chat-5',
    title: 'Địa chỉ trụ sở chính PTIT',
    timestamp: Date.now() - 1000 * 60 * 60 * 24 * 2,
    messages: [
        { type: 'user', content: 'Trụ sở chính của PTIT nằm ở đâu?' },
        { type: 'assistant', content: 'Trụ sở chính: 122 Hoàng Quốc Việt, Cầu Giấy, Hà Nội. Điện thoại: 024.37562186; Fax: 024.37562036; Website: www.ptit.edu.vn; Email: vanphonghv@ptit.edu.vn' }
    ]
},
{
    id: 'chat-6',
    title: 'Các cơ sở đào tạo PTIT',
    timestamp: Date.now() - 1000 * 60 * 60 * 24 * 3,
    messages: [
        { type: 'user', content: 'PTIT có bao nhiêu cơ sở đào tạo?' },
        { type: 'assistant', content: 'PTIT có 3 cơ sở: 2 tại Hà Nội (Km10 Nguyễn Trãi, Hà Đông; Ngõ 33 Đại Mỗ, Nam Từ Liêm) và 1 tại TP.HCM (97 Man Thiện, Hiệp Phú, TP. Thủ Đức).' }
    ]
},
{
    id: 'chat-7',
    title: 'Liên hệ CTSV Hà Nội',
    timestamp: Date.now() - 1000 * 60 * 60 * 24 * 4,
    messages: [
        { type: 'user', content: 'Sinh viên học tại Hà Nội cần hỗ trợ chế độ chính sách thì liên hệ đâu?' },
        { type: 'assistant', content: 'Liên hệ Phòng Chính trị & Công tác sinh viên (CTSV) – Tầng 1 nhà A1, Km10 Nguyễn Trãi, Hà Đông. SĐT: (024) 3854 7795; Email: ctsv@ptit.edu.vn.' }
    ]
},
{
    id: 'chat-8',
    title: 'Thông tin cơ sở TP.HCM',
    timestamp: Date.now() - 1000 * 60 * 60 * 24 * 5,
    messages: [
        { type: 'user', content: 'Thông tin liên hệ cơ sở TP.HCM của PTIT?' },
        { type: 'assistant', content: 'Địa chỉ: 11 Nguyễn Đình Chiểu, Q.1 và 97 Man Thiện, Hiệp Phú, TP. Thủ Đức. Điện thoại: 028.38295258; Fax: 028.39105510; Email: hvbcvthcm@ptithcm.edu.vn; Website: https://ptithcm.edu.vn' }
    ]
},
{
    id: 'chat-9',
    title: 'Chương trình/trao đổi quốc tế',
    timestamp: Date.now() - 1000 * 60 * 60 * 24 * 6,
    messages: [
        { type: 'user', content: 'Muốn tìm hiểu chương trình liên kết/trao đổi quốc tế của PTIT thì liên hệ ai?' },
        { type: 'assistant', content: 'Liên hệ Trung tâm Đào tạo Quốc tế (CIE) – Tầng 5 nhà A1, Km10 Nguyễn Trãi, Hà Đông. SĐT: (024) 3352 5741; Email: cie@ptit.edu.vn.' }
    ]
},
{
    id: 'chat-10',
    title: 'Tra cứu lịch thi & phúc khảo',
    timestamp: Date.now() - 1000 * 60 * 60 * 24 * 7,
    messages: [
        { type: 'user', content: 'Tôi muốn tra cứu lịch thi hoặc đăng ký phúc khảo thì làm ở đâu?' },
        { type: 'assistant', content: 'Liên hệ Phòng Khảo thí & ĐBCLGD – Tầng 1 nhà A1, Km10 Nguyễn Trãi, Hà Đông. SĐT: (024) 3854 3664; Email: khaothi@ptit.edu.vn. Một số thủ tục có thể thực hiện qua QLĐT.' }
    ]
}
];

// Current active chat
let currentChatId = null;
let chatHistories = [];

// Check if user is logged in
let currentUser = null;
try {
    const userData = localStorage.getItem('user') || sessionStorage.getItem('user');
    if (userData) {
        currentUser = JSON.parse(userData);
    }
} catch (error) {
    console.error('Error parsing user data:', error);
    localStorage.removeItem('user');
    sessionStorage.removeItem('user');
}

if (!currentUser) {
    // Redirect to login if not authenticated
    window.location.href = 'login.html';
} else {
    // Update user button with user info
    if (userBtn) {
        userBtn.querySelector('span').textContent = currentUser.name || currentUser.email?.split('@')[0] || 'User';
    }
}

// Initialize chat histories
function initializeChatHistories() {
    // Always use the latest mockChatHistories (updated PTIT data)
    // Clear old localStorage data to ensure fresh start
    localStorage.removeItem('chatHistories');
    
    chatHistories = [...mockChatHistories];
    saveChatHistories();
    renderChatList();

    // Load first chat by default
    if (chatHistories.length > 0) {
        loadChat(chatHistories[0].id);
    }
}

// Save chat histories to localStorage
function saveChatHistories() {
    localStorage.setItem('chatHistories', JSON.stringify(chatHistories));
}

// Render chat list in sidebar
function renderChatList() {
    const chatList = document.querySelector('.chat-list');
    if (!chatList) return;

    chatList.innerHTML = chatHistories.map((chat, index) => `
        <button class="chat-item ${chat.id === currentChatId ? 'active' : ''}" data-chat-id="${chat.id}">
            ${index === 0 ? '<i class="far fa-comment"></i>' : ''}
            <span class="chat-title">${chat.title}</span>
        </button>
    `).join('');

    // Add event listeners
    chatList.querySelectorAll('.chat-item').forEach(item => {
        // Click on chat item to load chat
        item.addEventListener('click', function () {
            const chatId = this.dataset.chatId;
            if (chatId !== currentChatId) {
                currentChatId = chatId;
                loadChat(chatId);
                renderChatList(); // Re-render to update active state
            }
        });
    });
}



// Load chat messages
function loadChat(chatId) {
    const chat = chatHistories.find(c => c.id === chatId);
    if (!chat) return;

    currentChatId = chatId;

    // Update active state
    document.querySelectorAll('.chat-item').forEach(item => {
        item.classList.toggle('active', item.dataset.chatId === chatId);
    });

    // Clear and load messages
    messages.innerHTML = '';

    chat.messages.forEach(msg => {
        const messageElement = createMessageElement(msg.content, msg.type);
        messages.appendChild(messageElement);
    });

    scrollToBottom();

    // Close sidebar on mobile
    if (window.innerWidth <= 768) {
        sidebar.classList.remove('active');
    }
}

// Initialize on page load
initializeChatHistories();

// Theme Management
let currentTheme = localStorage.getItem('theme') || 'dark';

// Apply saved theme on load
if (currentTheme === 'light') {
    document.body.classList.add('light-theme');
    updateThemeIcon();
}

themeToggle?.addEventListener('click', function () {
    document.body.classList.toggle('light-theme');
    currentTheme = document.body.classList.contains('light-theme') ? 'light' : 'dark';
    localStorage.setItem('theme', currentTheme);
    updateThemeIcon();
});

function updateThemeIcon() {
    const icon = themeToggle.querySelector('i');
    if (document.body.classList.contains('light-theme')) {
        icon.className = 'fas fa-moon';
    } else {
        icon.className = 'fas fa-sun';
    }
}

// Toggle Sidebar
function toggleSidebar() {
    sidebar.classList.toggle('active');
}

menuBtn?.addEventListener('click', toggleSidebar);
mobileMenuBtn?.addEventListener('click', toggleSidebar);

// Model Selector
modelSelector?.addEventListener('click', function (e) {
    e.stopPropagation();
    showModelSelector();
});

async function showModelSelector() {
    const menu = document.createElement('div');
    menu.className = 'model-menu';

    let models = [];
    try {
        // correct backend route is under /api/chat
        const response = await fetch(`${API_BASE}/api/chat/models`, { method: 'GET', credentials: 'include' });
        if (!response.ok) {
            console.error('Failed to fetch models', response.status, await response.text().catch(() => ''));
            showNotification('Không thể lấy danh sách mô hình (server error)', 'error');
            return;
        }
        const data = await response.json();
        models = data.models || [];
    } catch (err) {
        console.error('Error fetching models', err);
        showNotification('Lỗi khi kết nối tới server để lấy mô hình', 'error');
        return;
    }

    menu.innerHTML = models.map(model => `
        <div class="model-item" data-model="${model.name}">
            <div class="model-info">
                <div class="model-name">${model.name}</div>
                <div class="model-desc">${model.description}</div>
            </div>
            ${currentModelSpan.textContent === model.name ? '<i class="fas fa-check"></i>' : ''}
        </div>
    `).join('');

    const rect = modelSelector.getBoundingClientRect();
    menu.style.cssText = `
        position: fixed;
        top: ${rect.bottom + 8}px;
        left: ${rect.left}px;
        background: var(--bg-tertiary);
        border: 1px solid var(--border-color);
        border-radius: 8px;
        padding: 8px;
        min-width: 280px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        z-index: 1000;
    `;

    document.body.appendChild(menu);

    // Handle model selection
    menu.querySelectorAll('.model-item').forEach(item => {
        item.addEventListener('click', function () {
            const modelName = this.dataset.model;
            currentModelSpan.textContent = modelName;
            localStorage.setItem('selectedModel', modelName);
            showNotification(`Đã chuyển sang ${modelName}`, 'success');
            menu.remove();
        });
    });

    // Close menu when clicking outside
    setTimeout(() => {
        document.addEventListener('click', function closeMenu(e) {
            if (!menu.contains(e.target) && e.target !== modelSelector) {
                menu.remove();
                document.removeEventListener('click', closeMenu);
            }
        });
    }, 100);
}

// Load saved model
const savedModel = localStorage.getItem('selectedModel');
if (savedModel && currentModelSpan) {
    currentModelSpan.textContent = savedModel;
}

// Auto-resize textarea
messageInput.addEventListener('input', function () {
    this.style.height = 'auto';
    this.style.height = Math.min(this.scrollHeight, 120) + 'px';
});

// Send Message
function sendMessage() {
    const text = messageInput.value.trim();

    if (text === '') return;

    // If no active chat, create new one
    if (!currentChatId) {
        createNewChat(text);
        return;
    }

    // Create user message
    const userMessage = createMessageElement(text, 'user');
    messages.appendChild(userMessage);

    // Add to current chat history
    const chat = chatHistories.find(c => c.id === currentChatId);
    if (chat) {
        chat.messages.push({ type: 'user', content: text });
        chat.timestamp = Date.now();
        saveChatHistories();
    }

    // Clear input
    messageInput.value = '';
    messageInput.style.height = 'auto';

    // Scroll to bottom
    scrollToBottom();

    // Simulate assistant response
    setTimeout(() => {
        const responses = [
            "That's an interesting question! Let me help you with that.",
            "I understand what you're asking. Here's my response...",
            "Great question! Here's what I think...",
            "Let me break this down for you.",
            "I'd be happy to help with that!"
        ];
        const randomResponse = responses[Math.floor(Math.random() * responses.length)];
        const assistantMessage = createMessageElement(randomResponse, 'assistant');
        messages.appendChild(assistantMessage);

        // Add to chat history
        if (chat) {
            chat.messages.push({ type: 'assistant', content: randomResponse });
            saveChatHistories();
        }

        scrollToBottom();
    }, 1000);
}

// Create new chat
function createNewChat(firstMessage = null) {
    const newChat = {
        id: 'chat-' + Date.now(),
        title: firstMessage ? firstMessage.substring(0, 30) + (firstMessage.length > 30 ? '...' : '') : 'New Chat',
        timestamp: Date.now(),
        messages: []
    };

    if (firstMessage) {
        newChat.messages.push({ type: 'user', content: firstMessage });
    }

    chatHistories.unshift(newChat);
    saveChatHistories();
    renderChatList();
    loadChat(newChat.id);

    // If there was a first message, get response
    if (firstMessage) {
        setTimeout(() => {
            const responses = [
                "That's an interesting question! Let me help you with that.",
                "I understand what you're asking. Here's my response...",
                "Great question! Here's what I think...",
                "Let me break this down for you.",
                "I'd be happy to help with that!"
            ];
            const randomResponse = responses[Math.floor(Math.random() * responses.length)];
            const assistantMessage = createMessageElement(randomResponse, 'assistant');
            messages.appendChild(assistantMessage);

            newChat.messages.push({ type: 'assistant', content: randomResponse });
            saveChatHistories();
            scrollToBottom();
        }, 1000);
    }
}

// Create Message Element
function createMessageElement(text, type) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}-message`;

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';

    const textP = document.createElement('p');
    textP.textContent = text;
    contentDiv.appendChild(textP);


    messageDiv.appendChild(contentDiv);
    return messageDiv;
}


// Scroll to Bottom
function scrollToBottom() {
    messages.scrollTop = messages.scrollHeight;
}

// Send on Enter (Shift+Enter for new line)
messageInput.addEventListener('keydown', function (e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

// Send Button Click
sendBtn.addEventListener('click', sendMessage);

// New Chat Button
newChatBtn?.addEventListener('click', function () {
    createNewChat();

    // Show welcome message
    messages.innerHTML = `
        <div class="message assistant-message">
            <div class="message-content">
                <p>Hi! How can I help you today?</p>
            </div>
        </div>
    `;

    // Close sidebar on mobile
    if (window.innerWidth <= 768) {
        sidebar.classList.remove('active');
    }
});

// Close sidebar when clicking outside on mobile
document.addEventListener('click', function (e) {
    if (window.innerWidth <= 768) {
        if (!sidebar.contains(e.target) && !mobileMenuBtn.contains(e.target) && sidebar.classList.contains('active')) {
            sidebar.classList.remove('active');
        }
    }
});

// User Button - Show menu
userBtn?.addEventListener('click', function () {
    showUserMenu();
});

function showUserMenu() {
    const menu = document.createElement('div');
    menu.className = 'user-menu';
    menu.innerHTML = `
        <div class="user-menu-item" onclick="showProfile()">
            <i class="fas fa-user"></i>
            <span>Hồ sơ</span>
        </div>
        <div class="user-menu-divider"></div>
        <div class="user-menu-item" onclick="handleLogout()">
            <i class="fas fa-sign-out-alt"></i>
            <span>Đăng xuất</span>
        </div>
    `;

    // Position menu
    const rect = userBtn.getBoundingClientRect();
    menu.style.cssText = `
        position: fixed;
        bottom: ${window.innerHeight - rect.top + 10}px;
        left: ${rect.left}px;
        background: var(--bg-tertiary);
        border: 1px solid var(--border-color);
        border-radius: 8px;
        padding: 8px;
        min-width: 200px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        z-index: 1000;
    `;

    document.body.appendChild(menu);

    // Close menu when clicking outside
    setTimeout(() => {
        document.addEventListener('click', function closeMenu(e) {
            if (!menu.contains(e.target) && e.target !== userBtn) {
                menu.remove();
                document.removeEventListener('click', closeMenu);
            }
        });
    }, 100);
}

async function showProfile() {
    // Fetch profile from backend and show modal
    try {
        // backend expects a user_id query parameter; include it
        if (!currentUser || !currentUser.id) {
            showNotification('Không tìm thấy người dùng. Vui lòng đăng nhập lại.', 'error');
            return;
        }

        const resp = await fetch(`${API_BASE}/api/auth/profile?user_id=${encodeURIComponent(currentUser.id)}`, { method: 'GET' });
        const data = await resp.json().catch(() => ({}));

        if (!data || !data.ok) {
            showNotification(data?.message || 'Không thể lấy hồ sơ người dùng', 'error');
            return;
        }

    const profile = data.profile || {};
    const name = profile.name || currentUser?.name || '';
    const email = profile.email || currentUser?.email || '';
    const joinedAt = profile.joined_at || profile.created_at || new Date().toLocaleDateString('vi-VN');

        // Create profile modal
        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h2>Hồ sơ người dùng</h2>
                    <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="modal-body">
                    <div class="profile-section">
                        <div class="profile-avatar">
                            <i class="fas fa-user-circle"></i>
                        </div>
                        <div class="profile-info">
                            <div class="form-group">
                                <label>Họ và tên</label>
                                <input type="text" value="${escapeHtml(name)}" class="profile-input" readonly>
                            </div>
                            <div class="form-group">
                                <label>Email</label>
                                <input type="email" value="${escapeHtml(email)}" class="profile-input" readonly>
                            </div>
                            <div class="form-group">
                                <label>Ngày tham gia</label>
                                <input type="text" value="${escapeHtml(joinedAt)}" class="profile-input" readonly>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="btn-cancel" onclick="this.closest('.modal-overlay').remove()">Đóng</button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);

        // Close modal when clicking overlay
        modal.addEventListener('click', function (e) {
            if (e.target === modal) {
                modal.remove();
            }
        });

    } catch (err) {
        console.error('Error fetching profile:', err);
        showNotification('Lỗi khi kết nối tới server để lấy hồ sơ', 'error');
    }
}

// small helper to avoid injecting raw HTML into inputs
function escapeHtml(str) {
    if (str === undefined || str === null) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

async function handleLogout() {
  if (!confirm('Bạn có chắc muốn đăng xuất?')) return;

  try {
    // Gọi BE để sau này có thể huỷ session/token phía server
    await fetch(`${API_BASE}/api/auth/logout`, {
      method: 'POST',
    });
  } catch (e) {
    console.warn('Logout API error:', e);
  } finally {
    localStorage.removeItem('user');
    sessionStorage.removeItem('user');
    showNotification('Đã đăng xuất thành công!', 'success');
    setTimeout(() => {
      window.location.replace('login.html');
    }, 500);
  }
}

// Notification System
function showNotification(message, type = 'info') {
    const existing = document.querySelector('.notification');
    if (existing) {
        existing.remove();
    }

    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <i class="fas ${type === 'success' ? 'fa-check-circle' : type === 'error' ? 'fa-exclamation-circle' : 'fa-info-circle'}"></i>
        <span>${message}</span>
    `;

    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${type === 'success' ? '#d1d5db' : type === 'error' ? '#ef4444' : '#d1d5db'};
        color: ${type === 'error' ? 'white' : '#1f2937'};
        padding: 12px 20px;
        border-radius: 8px;
        display: flex;
        align-items: center;
        gap: 10px;
        font-size: 14px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        z-index: 10000;
        animation: slideIn 0.3s ease;
    `;

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Add CSS for menus and animations
const style = document.createElement('style');
style.textContent = `
    .user-menu-item {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 10px 12px;
        border-radius: 6px;
        cursor: pointer;
        transition: background-color 0.2s;
        color: var(--text-primary);
        font-size: 14px;
    }
    
    .user-menu-item:hover {
        background-color: var(--hover-bg);
    }
    
    .user-menu-divider {
        height: 1px;
        background-color: var(--border-color);
        margin: 4px 0;
    }
    
    
    .modal-overlay {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.6);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10000;
        animation: fadeIn 0.2s ease;
    }
    
    .modal-content {
        background: var(--bg-secondary);
        border-radius: 12px;
        width: 90%;
        max-width: 500px;
        max-height: 80vh;
        overflow: hidden;
        display: flex;
        flex-direction: column;
        box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);
        animation: slideUp 0.3s ease;
    }
    
    @media (max-width: 640px) {
        .modal-content {
            width: 95%;
            max-width: none;
            max-height: 85vh;
            border-radius: 10px;
        }
        
        .modal-header {
            padding: 16px 18px;
        }
        
        .modal-header h2 {
            font-size: 18px;
        }
        
        .modal-body {
            padding: 18px;
        }
        
        .modal-footer {
            padding: 12px 18px;
        }
        
        .profile-avatar {
            font-size: 64px;
        }
        
        .profile-info label {
            font-size: 12px;
        }
        
        .profile-input {
            font-size: 13px;
            padding: 9px 12px;
        }
        
        
        .btn-cancel {
            font-size: 13px;
            padding: 9px 16px;
        }
    }
    
    @media (max-width: 480px) {
        .modal-content {
            width: 96%;
            max-height: 90vh;
            border-radius: 8px;
        }
        
        .modal-header {
            padding: 14px 16px;
        }
        
        .modal-header h2 {
            font-size: 17px;
        }
        
        .modal-body {
            padding: 16px;
        }
        
        .modal-footer {
            padding: 10px 16px;
            gap: 8px;
        }
        
        
        .btn-cancel {
            font-size: 12px;
            padding: 8px 14px;
        }
    }
    
    .modal-header {
        padding: 20px 24px;
        border-bottom: 1px solid var(--border-color);
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    
    .modal-header h2 {
        font-size: 20px;
        font-weight: 600;
        color: var(--text-primary);
        margin: 0;
    }
    
    .modal-close {
        background: none;
        border: none;
        color: var(--text-secondary);
        font-size: 20px;
        cursor: pointer;
        padding: 4px 8px;
        border-radius: 6px;
        transition: all 0.2s;
    }
    
    .modal-close:hover {
        background: var(--hover-bg);
        color: var(--text-primary);
    }
    
    .modal-body {
        padding: 24px;
        overflow-y: auto;
        flex: 1;
    }
    
    .modal-body::-webkit-scrollbar {
        width: 6px;
    }
    
    .modal-body::-webkit-scrollbar-thumb {
        background: var(--bg-tertiary);
        border-radius: 3px;
    }
    
    .modal-footer {
        padding: 16px 24px;
        border-top: 1px solid var(--border-color);
        display: flex;
        gap: 12px;
        justify-content: flex-end;
    }
    
    .profile-section {
        display: flex;
        flex-direction: column;
        gap: 24px;
    }
    
    .profile-avatar {
        display: flex;
        justify-content: center;
        align-items: center;
        font-size: 80px;
        color: var(--text-secondary);
    }
    
    .profile-info {
        display: flex;
        flex-direction: column;
        gap: 16px;
    }
    
    .profile-info .form-group {
        display: flex;
        flex-direction: column;
        gap: 8px;
    }
    
    .profile-info label {
        font-size: 13px;
        font-weight: 500;
        color: var(--text-secondary);
    }
    
    .profile-input {
        padding: 10px 14px;
        background: var(--bg-primary);
        border: 1px solid var(--border-color);
        border-radius: 8px;
        color: var(--text-primary);
        font-size: 14px;
        font-family: inherit;
        transition: border-color 0.2s;
    }
    
    .profile-input:focus {
        outline: none;
        border-color: var(--text-secondary);
    }
    
    .profile-input:readonly {
        opacity: 0.6;
        cursor: not-allowed;
    }
    
    .btn-cancel {
        padding: 10px 20px;
        border: none;
        border-radius: 8px;
        font-size: 14px;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s;
        background: var(--hover-bg);
        color: var(--text-primary);
    }
    
    .btn-cancel:hover {
        background: var(--bg-tertiary);
    }
    
    
    
    @keyframes slideUp {
        from {
            transform: translateY(40px);
            opacity: 0;
        }
        to {
            transform: translateY(0);
            opacity: 1;
        }
    }
    
    .model-menu {
        font-family: 'Charter', 'Georgia', serif;
    }
    
    @media (max-width: 480px) {
        .model-menu {
            min-width: 240px;
        }
        
        .model-item {
            padding: 10px;
        }
        
        .model-name {
            font-size: 13px;
        }
        
        .model-desc {
            font-size: 11px;
        }
        
        .user-menu-item {
            font-size: 13px;
            padding: 9px 10px;
        }
    }
    
    .model-item {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 12px;
        border-radius: 6px;
        cursor: pointer;
        transition: background-color 0.2s;
        color: var(--text-primary);
    }
    
    .model-item:hover {
        background-color: var(--hover-bg);
    }
    
    .model-info {
        flex: 1;
    }
    
    .model-name {
        font-size: 14px;
        font-weight: 600;
        margin-bottom: 2px;
    }
    
    .model-desc {
        font-size: 12px;
        color: var(--text-secondary);
    }
    
    .model-item i {
        color: #667eea;
        font-size: 16px;
    }
    
    @keyframes slideIn {
        from {
            transform: translateX(400px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(400px);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// Focus input on load
messageInput.focus();
