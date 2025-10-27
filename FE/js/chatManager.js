// Chat Manager - Quản lý chat histories và messages
import { apiService } from './apiService.js';
import { showNotification, scrollToBottom, createMessageElement } from './utils.js';
import { DOM } from './config.js';

export class ChatManager {
    constructor(currentUser) {
        this.currentUser = currentUser;
        this.chatHistories = [];
        this.currentChatId = null;
    }

    // Initialize chat histories
    async initialize() {
        try {
            const data = await apiService.getChatList(this.currentUser.id);

            if (data.ok && data.chats) {
                this.chatHistories = data.chats.map(chat => ({
                    id: chat.id,
                    title: chat.title,
                    timestamp: new Date(chat.updated_at).getTime(),
                    messages: []
                }));
            } else {
                this.chatHistories = [];
            }

            this.saveChatHistories();
            this.renderChatList();

            // Load first chat by default
            if (this.chatHistories.length > 0) {
                await this.loadChat(this.chatHistories[0].id);
            }
        } catch (err) {
            console.error('Error loading chat histories:', err);
            this.chatHistories = [];
            this.renderChatList();
        }
    }

    // Save to localStorage
    saveChatHistories() {
        localStorage.setItem('chatHistories', JSON.stringify(this.chatHistories));
    }

    // Render chat list
    renderChatList() {
        const chatList = document.querySelector('.chat-list');
        if (!chatList) return;

        chatList.innerHTML = this.chatHistories.map((chat, index) => `
            <button class="chat-item ${chat.id === this.currentChatId ? 'active' : ''}" data-chat-id="${chat.id}">
                ${index === 0 ? '<i class="far fa-comment"></i>' : ''}
                <span class="chat-title">${chat.title}</span>
            </button>
        `).join('');

        // Add event listeners
        chatList.querySelectorAll('.chat-item').forEach(item => {
            item.addEventListener('click', () => {
                const chatId = item.dataset.chatId;
                if (chatId !== this.currentChatId) {
                    this.currentChatId = chatId;
                    this.loadChat(chatId);
                    this.renderChatList();
                }
            });
        });
    }

    // Load chat messages
    async loadChat(chatId) {
        this.currentChatId = chatId;

        // Update active state
        document.querySelectorAll('.chat-item').forEach(item => {
            item.classList.toggle('active', item.dataset.chatId == chatId);
        });

        try {
            const data = await apiService.getChatMessages(chatId);

            if (!data.ok) {
                showNotification(data.message || 'Lỗi khi tải tin nhắn', 'error');
                return;
            }

            // Clear and load messages
            DOM.messages.innerHTML = '';

            data.messages.forEach(msg => {
                const messageElement = createMessageElement(msg.content, msg.type);
                DOM.messages.appendChild(messageElement);
            });

            // Update local chat history
            const chat = this.chatHistories.find(c => c.id == chatId);
            if (chat) {
                chat.messages = data.messages;
                this.saveChatHistories();
            }

            scrollToBottom(DOM.messages);

            // Close sidebar on mobile
            if (window.innerWidth <= 768) {
                DOM.sidebar.classList.remove('active');
            }
        } catch (err) {
            console.error('Error loading chat:', err);
            showNotification('Lỗi kết nối tới server', 'error');
        }
    }

    // Create new chat
    async createNewChat(firstMessage = null) {
        try {
            const title = firstMessage ? firstMessage.substring(0, 30) + (firstMessage.length > 30 ? '...' : '') : 'New Chat';

            const data = await apiService.createChat(this.currentUser.id, title);

            if (!data.ok) {
                showNotification(data.message || 'Lỗi khi tạo chat', 'error');
                return null;
            }

            // Create local chat object
            const newChat = {
                id: data.chat.id,
                title: data.chat.title,
                timestamp: Date.now(),
                messages: []
            };

            this.chatHistories.unshift(newChat);
            this.saveChatHistories();
            this.renderChatList();
            this.loadChat(newChat.id);

            return newChat.id;
        } catch (err) {
            console.error('Error creating chat:', err);
            showNotification('Lỗi kết nối tới server', 'error');
            return null;
        }
    }

    // Send message
    async sendMessage(text) {
        // If no active chat, create new one
        if (!this.currentChatId) {
            const chatId = await this.createNewChat(text);
            if (!chatId) return;
            this.currentChatId = chatId;
        }

        // Create user message
        const userMessage = createMessageElement(text, 'user');
        DOM.messages.appendChild(userMessage);
        scrollToBottom(DOM.messages);

        try {
            // Get selected model from UI
            const modelElement = document.getElementById('currentModel');
            const selectedModel = modelElement ? modelElement.textContent.trim() : null;

            const data = await apiService.sendMessage(this.currentChatId, text, selectedModel);

            if (data.ok) {
                // Display bot response
                const assistantMessage = createMessageElement(data.bot_message.content, 'assistant');
                DOM.messages.appendChild(assistantMessage);
                scrollToBottom(DOM.messages);

                // Update local chat history
                const chat = this.chatHistories.find(c => c.id === this.currentChatId);
                if (chat) {
                    chat.messages.push({ type: 'user', content: text });
                    chat.messages.push({ type: 'assistant', content: data.bot_message.content, model: data.bot_message.model });
                    chat.timestamp = Date.now();
                    this.saveChatHistories();
                }
            } else {
                showNotification(data.message || 'Lỗi khi gửi tin nhắn', 'error');
            }
        } catch (err) {
            console.error('Error sending message:', err);
            showNotification('Lỗi kết nối tới server', 'error');
        }
    }
}
