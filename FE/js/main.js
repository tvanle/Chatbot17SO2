// Main Entry Point - Khởi tạo và điều phối các module
import { DOM } from './config.js';
import { getCurrentUser } from './utils.js';
import { ChatManager } from './chatManager.js';
import { UIManager } from './uiManager.js';

// Check authentication
const currentUser = getCurrentUser();

if (!currentUser) {
    window.location.href = 'login.html';
} else {
    // Update user button
    if (DOM.userBtn) {
        DOM.userBtn.querySelector('span').textContent = currentUser.name || currentUser.email?.split('@')[0] || 'User';
    }

    // Initialize managers
    const chatManager = new ChatManager(currentUser);
    const uiManager = new UIManager(currentUser);

    // Initialize chat histories
    chatManager.initialize();

    // Send message handler
    let isSending = false;
    async function sendMessage() {
        const text = DOM.messageInput.value.trim();
        if (!text || isSending) return;

        isSending = true;
        try {
            DOM.messageInput.value = '';
            await chatManager.sendMessage(text);
            DOM.messageInput.style.height = 'auto';
        } finally {
            isSending = false;
        }
    }

    // Event listeners
    DOM.sendBtn.addEventListener('click', () => sendMessage());
    DOM.messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    DOM.newChatBtn?.addEventListener('click', () => {
        chatManager.currentChatId = null;
        uiManager.handleNewChat(chatManager);
    });

    // Focus input on load
    DOM.messageInput.focus();
}
