// Main Entry Point - Khởi tạo và điều phối các module
import { DOM } from './config.js';
import { getCurrentUser } from './utils.js';
import { ChatManager } from './chatManager.js';
import { UIManager } from './uiManager.js';

console.log('=== [MAIN.JS] Script loaded ===', new Date().toISOString());

// Detect page unload/reload
window.addEventListener('beforeunload', (e) => {
    console.log('!!! [MAIN.JS] Page is about to unload/reload !!!');
});

// Check authentication
const currentUser = getCurrentUser();

if (!currentUser) {
    console.log('[MAIN.JS] No user found, redirecting to login');
    window.location.href = 'login.html';
} else {
    console.log('[MAIN.JS] User authenticated:', currentUser.email);
    // Update user button
    if (DOM.userBtn) {
        DOM.userBtn.querySelector('span').textContent = currentUser.name || currentUser.email?.split('@')[0] || 'User';
    }

    // Initialize managers
    const chatManager = new ChatManager(currentUser);
    const uiManager = new UIManager(currentUser);

    // Initialize chat histories
    chatManager.initialize();

    // Send message event
    async function sendMessage() {
        const text = DOM.messageInput.value.trim();
        if (text === '') return;

        await chatManager.sendMessage(text);

        // Clear input
        DOM.messageInput.value = '';
        DOM.messageInput.style.height = 'auto';
    }

    // Event listeners
    DOM.sendBtn.addEventListener('click', (e) => {
        e.preventDefault(); // Prevent any default button behavior
        sendMessage();
    });

    DOM.messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    DOM.newChatBtn?.addEventListener('click', (e) => {
        e.preventDefault(); // Prevent any default button behavior
        // Reset current chat ID so next message creates new chat
        chatManager.currentChatId = null;
        // Show welcome message
        uiManager.handleNewChat(chatManager);
    });

    // Focus input on load
    DOM.messageInput.focus();
}
