// UI Manager - Quản lý giao diện, theme, sidebar, modals
import { apiService } from './apiService.js';
import { showNotification, escapeHtml } from './utils.js';
import { DOM } from './config.js';

export class UIManager {
    constructor(currentUser) {
        this.currentUser = currentUser;
        this.currentTheme = localStorage.getItem('theme') || 'dark';
        this.setupEventListeners();
        this.applyTheme();
        this.loadSavedModel();
        this.injectStyles();
    }

    // Setup all event listeners
    setupEventListeners() {
        // Theme toggle
        DOM.themeToggle?.addEventListener('click', () => this.toggleTheme());

        // Sidebar toggles
        DOM.menuBtn?.addEventListener('click', () => this.toggleSidebar());
        DOM.mobileMenuBtn?.addEventListener('click', () => this.toggleSidebar());

        // Model selector
        DOM.modelSelector?.addEventListener('click', (e) => {
            e.stopPropagation();
            this.showModelSelector();
        });

        // User button
        DOM.userBtn?.addEventListener('click', () => this.showUserMenu());

        // New chat button
        DOM.newChatBtn?.addEventListener('click', () => this.handleNewChat());

        // Auto-resize textarea
        DOM.messageInput.addEventListener('input', function () {
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 120) + 'px';
        });

        // Close sidebar on mobile when clicking outside
        document.addEventListener('click', (e) => {
            if (window.innerWidth <= 768) {
                if (!DOM.sidebar.contains(e.target) &&
                    !DOM.mobileMenuBtn.contains(e.target) &&
                    DOM.sidebar.classList.contains('active')) {
                    DOM.sidebar.classList.remove('active');
                }
            }
        });
    }

    // Theme management
    toggleTheme() {
        document.body.classList.toggle('light-theme');
        this.currentTheme = document.body.classList.contains('light-theme') ? 'light' : 'dark';
        localStorage.setItem('theme', this.currentTheme);
        this.updateThemeIcon();
    }

    applyTheme() {
        if (this.currentTheme === 'light') {
            document.body.classList.add('light-theme');
        }
        this.updateThemeIcon();
    }

    updateThemeIcon() {
        const icon = DOM.themeToggle.querySelector('i');
        if (document.body.classList.contains('light-theme')) {
            icon.className = 'fas fa-moon';
        } else {
            icon.className = 'fas fa-sun';
        }
    }

    // Sidebar toggle
    toggleSidebar() {
        DOM.sidebar.classList.toggle('active');
    }

    // Model selector
    async showModelSelector() {
        const menu = document.createElement('div');
        menu.className = 'model-menu';

        try {
            const data = await apiService.getModels();
            const models = data.models || [];

            menu.innerHTML = models.map(model => `
                <div class="model-item" data-model="${model.name}">
                    <div class="model-info">
                        <div class="model-name">${model.name}</div>
                        <div class="model-desc">${model.description}</div>
                    </div>
                    ${DOM.currentModelSpan.textContent === model.name ? '<i class="fas fa-check"></i>' : ''}
                </div>
            `).join('');

            const rect = DOM.modelSelector.getBoundingClientRect();
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
                item.addEventListener('click', () => {
                    const modelName = item.dataset.model;
                    DOM.currentModelSpan.textContent = modelName;
                    localStorage.setItem('selectedModel', modelName);
                    showNotification(`Đã chuyển sang ${modelName}`, 'success');
                    menu.remove();
                });
            });

            // Close menu when clicking outside
            setTimeout(() => {
                document.addEventListener('click', function closeMenu(e) {
                    if (!menu.contains(e.target) && e.target !== DOM.modelSelector) {
                        menu.remove();
                        document.removeEventListener('click', closeMenu);
                    }
                });
            }, 100);
        } catch (err) {
            console.error('Error fetching models', err);
            showNotification('Lỗi khi kết nối tới server để lấy mô hình', 'error');
        }
    }

    async loadSavedModel() {
        try {
            // First, try to load saved model from localStorage
            const savedModel = localStorage.getItem('selectedModel');

            // Fetch available models from server
            const data = await apiService.getModels();
            const models = data.models || [];

            if (models.length === 0) {
                DOM.currentModelSpan.textContent = 'No models available';
                return;
            }

            // Check if saved model is still available
            let modelToUse = null;
            if (savedModel) {
                modelToUse = models.find(m => m.name === savedModel);
            }

            // If no saved model or saved model not available, use first available model
            if (!modelToUse) {
                modelToUse = models[0];
                localStorage.setItem('selectedModel', modelToUse.name);
            }

            DOM.currentModelSpan.textContent = modelToUse.name;

        } catch (err) {
            console.error('Error loading model:', err);
            DOM.currentModelSpan.textContent = 'Error loading models';
        }
    }

    // User menu
    showUserMenu() {
        const menu = document.createElement('div');
        menu.className = 'user-menu';
        menu.innerHTML = `
            <div class="user-menu-item" id="profile-menu-item">
                <i class="fas fa-user"></i>
                <span>Hồ sơ</span>
            </div>
            <div class="user-menu-divider"></div>
            <div class="user-menu-item" id="logout-menu-item">
                <i class="fas fa-sign-out-alt"></i>
                <span>Đăng xuất</span>
            </div>
        `;

        // Position menu
        const rect = DOM.userBtn.getBoundingClientRect();
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

        // Add event listeners
        menu.querySelector('#profile-menu-item').addEventListener('click', () => {
            menu.remove();
            this.showProfile();
        });

        menu.querySelector('#logout-menu-item').addEventListener('click', () => {
            menu.remove();
            this.handleLogout();
        });

        // Close menu when clicking outside
        setTimeout(() => {
            document.addEventListener('click', function closeMenu(e) {
                if (!menu.contains(e.target) && e.target !== DOM.userBtn) {
                    menu.remove();
                    document.removeEventListener('click', closeMenu);
                }
            });
        }, 100);
    }

    // Show profile modal
    async showProfile() {
        try {
            if (!this.currentUser || !this.currentUser.id) {
                showNotification('Không tìm thấy người dùng. Vui lòng đăng nhập lại.', 'error');
                return;
            }

            const data = await apiService.getUserProfile(this.currentUser.id);

            if (!data || !data.ok) {
                showNotification(data?.message || 'Không thể lấy hồ sơ người dùng', 'error');
                return;
            }

            const profile = data.profile || {};
            const name = profile.name || this.currentUser?.name || '';
            const email = profile.email || this.currentUser?.email || '';
            const joinedAt = profile.joined_at || profile.created_at || new Date().toLocaleDateString('vi-VN');

            // Create profile modal
            const modal = document.createElement('div');
            modal.className = 'modal-overlay';
            modal.innerHTML = `
                <div class="modal-content">
                    <div class="modal-header">
                        <h2>Hồ sơ người dùng</h2>
                        <button class="modal-close">
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
                        <button class="btn-cancel">Đóng</button>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);

            // Event listeners
            modal.querySelector('.modal-close').addEventListener('click', () => modal.remove());
            modal.querySelector('.btn-cancel').addEventListener('click', () => modal.remove());
            modal.addEventListener('click', (e) => {
                if (e.target === modal) modal.remove();
            });

        } catch (err) {
            console.error('Error fetching profile:', err);
            showNotification('Lỗi khi kết nối tới server để lấy hồ sơ', 'error');
        }
    }

    // Handle logout
    async handleLogout() {
        if (!confirm('Bạn có chắc muốn đăng xuất?')) return;

        try {
            await apiService.logout();
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

    // Handle new chat
    handleNewChat() {
        // This will be called from main.js with chatManager
        DOM.messages.innerHTML = `
            <div class="message assistant-message">
                <div class="message-content">
                    <p>Xin chào! Tôi là trợ lý AI của PTIT. Tôi có thể giúp bạn tìm hiểu về:</p>
                    <ul>
                        <li>📚 Quy chế đào tạo và học vụ</li>
                        <li>🎓 Thông tin tuyển sinh</li>
                        <li>📍 Địa chỉ và liên hệ các phòng ban</li>
                        <li>🌐 Các hệ thống trực tuyến của PTIT</li>
                    </ul>
                    <p>Bạn muốn hỏi gì?</p>
                </div>
            </div>
        `;

        // Close sidebar on mobile
        if (window.innerWidth <= 768) {
            DOM.sidebar.classList.remove('active');
        }
    }

    // Inject CSS styles
    injectStyles() {
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
    }
}
