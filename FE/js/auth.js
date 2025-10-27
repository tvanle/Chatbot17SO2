// Theme Toggle for Auth Page
const themeToggleAuth = document.getElementById('themeToggleAuth');
let currentTheme = localStorage.getItem('theme') || 'dark';

// Apply saved theme on load
if (currentTheme === 'light') {
    document.body.classList.add('light-theme');
    updateThemeIcon();
}

themeToggleAuth?.addEventListener('click', function() {
    document.body.classList.toggle('light-theme');
    currentTheme = document.body.classList.contains('light-theme') ? 'light' : 'dark';
    localStorage.setItem('theme', currentTheme);
    updateThemeIcon();
});

function updateThemeIcon() {
    const icon = themeToggleAuth.querySelector('i');
    if (document.body.classList.contains('light-theme')) {
        icon.className = 'fas fa-moon';
    } else {
        icon.className = 'fas fa-sun';
    }
}

// Form Switching
function showLoginForm(event) {
    event.preventDefault();
    document.getElementById('registerForm').classList.remove('active');
    document.getElementById('loginForm').classList.add('active');
}

function showRegisterForm(event) {
    event.preventDefault();
    document.getElementById('loginForm').classList.remove('active');
    document.getElementById('registerForm').classList.add('active');
}


const API_BASE = "http://127.0.0.1:8000"; // BE FastAPI

// Handle Login (call BE)
async function handleLogin(event) {
    event.preventDefault();

    const email = document.getElementById('loginEmail').value.trim();
    const password = document.getElementById('loginPassword').value;

    if (!email || !password) {
        showNotification('Vui lòng nhập email và mật khẩu', 'error');
        return false;
    }

    try {
        const resp = await fetch(`${API_BASE}/api/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: new URLSearchParams({ email, password })
        });

        // Luôn trả 200 -> đọc JSON để biết ok true/false
        const data = await resp.json();

        if (!data.ok) {
            showNotification(data.message || 'Đăng nhập thất bại', 'error');
            return false;
        }

        // Lưu thông tin user
        localStorage.setItem('user', JSON.stringify(data.user));
        showNotification('Đăng nhập thành công!', 'success');

        setTimeout(() => window.location.replace('index.html'), 800);
        return false;
    } catch (e) {
        console.error(e);
        showNotification('Lỗi kết nối tới server', 'error');
        return false;
    }
}

// Handle Register (call BE)
async function handleRegister(event) {
    event.preventDefault();

    const name = document.getElementById('registerName').value.trim();
    const email = document.getElementById('registerEmail').value.trim();
    const password = document.getElementById('registerPassword').value;
    const confirmPassword = document.getElementById('registerConfirmPassword').value;

    if (!name || !email || !password) {
        showNotification('Vui lòng nhập đầy đủ thông tin', 'error');
        return false;
    }
    if (password !== confirmPassword) {
        showNotification('Mật khẩu không khớp', 'error');
        return false;
    }

    try {
        const resp = await fetch(`${API_BASE}/api/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: new URLSearchParams({ name, email, password })
        });
        const data = await resp.json();

        if (!data.ok) {
            showNotification(data.message || 'Đăng ký thất bại', 'error');
            return false;
        }

        localStorage.setItem('user', JSON.stringify(data.user));
        showNotification('Đăng ký thành công!', 'success');
        setTimeout(() => window.location.replace('index.html'), 1000);
        return false;
    } catch (e) {
        console.error(e);
        showNotification('Lỗi kết nối tới server', 'error');
        return false;
    }
}

// Notification System
function showNotification(message, type = 'info') {
    // Remove existing notification
    const existing = document.querySelector('.notification');
    if (existing) {
        existing.remove();
    }
    
    // Create notification
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <i class="fas ${type === 'success' ? 'fa-check-circle' : type === 'error' ? 'fa-exclamation-circle' : 'fa-info-circle'}"></i>
        <span>${message}</span>
    `;
    
    // Add styles
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${type === 'success' ? '#10a37f' : type === 'error' ? '#ef4444' : '#667eea'};
        color: white;
        padding: 16px 24px;
        border-radius: 8px;
        display: flex;
        align-items: center;
        gap: 12px;
        font-size: 14px;
        font-weight: 500;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        z-index: 10000;
        animation: slideIn 0.3s ease;
    `;
    
    document.body.appendChild(notification);
    
    // Auto remove after 3 seconds
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Add animation styles
const style = document.createElement('style');
style.textContent = `
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
