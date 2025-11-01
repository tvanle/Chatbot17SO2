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
    let isSending = false; // Guard to prevent duplicate sends
    async function sendMessage() {
        const text = DOM.messageInput.value.trim();
        if (text === '' || isSending) {
            console.log('[MAIN.JS] sendMessage blocked:', { text, isSending });
            return;
        }

        console.log('[MAIN.JS] sendMessage called:', text);
        isSending = true;

        try {
            await chatManager.sendMessage(text);

            // Clear input
            DOM.messageInput.value = '';
            DOM.messageInput.style.height = 'auto';
        } finally {
            isSending = false;
        }
    }

    // Event listeners - Use named functions to prevent duplicate binding
    const handleSendClick = (e) => {
        e.preventDefault(); // Prevent any default button behavior
        console.log('[MAIN.JS] Send button clicked');
        sendMessage();
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            console.log('[MAIN.JS] Enter key pressed');
            sendMessage();
        }
    };

    // Remove any existing listeners before adding new ones
    DOM.sendBtn.removeEventListener('click', handleSendClick);
    DOM.messageInput.removeEventListener('keydown', handleKeyDown);

    // Add event listeners
    DOM.sendBtn.addEventListener('click', handleSendClick);
    DOM.messageInput.addEventListener('keydown', handleKeyDown);

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
