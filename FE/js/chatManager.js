// Chat Manager - Quản lý chat histories và messages
import { apiService } from './apiService.js';
import { showNotification, scrollToBottom, createMessageElement, createTypingIndicator } from './utils.js';
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

            this.renderChatList();

            // Load first chat by default if exists
            if (this.chatHistories.length > 0) {
                await this.loadChat(this.chatHistories[0].id);
            } else {
                // Show welcome message if no chat history
                this.showWelcomeMessage();
            }
        } catch (err) {
            console.error('Error loading chat histories:', err);
            this.chatHistories = [];
            this.renderChatList();
            // Show welcome message on error
            this.showWelcomeMessage();
        }
    }

    // Show welcome message
    showWelcomeMessage() {
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
    }

    // Render chat list
    renderChatList() {
        // Save to localStorage when rendering
        localStorage.setItem('chatHistories', JSON.stringify(this.chatHistories));
        const chatList = document.querySelector('.chat-list');
        if (!chatList) return;

        chatList.innerHTML = this.chatHistories.map((chat, index) => `
            <button type="button" class="chat-item ${chat.id === this.currentChatId ? 'active' : ''}" data-chat-id="${chat.id}">
                ${index === 0 ? '<i class="far fa-comment"></i>' : ''}
                <span class="chat-title">${chat.title}</span>
            </button>
        `).join('');

        // Add event listeners
        chatList.querySelectorAll('.chat-item').forEach(item => {
            item.addEventListener('click', () => {
                const chatId = item.dataset.chatId;
                if (chatId !== this.currentChatId) {
                    this.loadChat(chatId);
                }
            });
        });
    }

    // Load chat messages
    async loadChat(chatId) {
        this.currentChatId = chatId;
        this.renderChatList(); // Update active state

        try {
            const data = await apiService.getChatMessages(chatId);

            if (!data.ok) {
                showNotification(data.message || 'Lỗi khi tải tin nhắn', 'error');
                return;
            }

            // Clear and render messages
            DOM.messages.innerHTML = '';
            data.messages.forEach(msg => {
                DOM.messages.appendChild(createMessageElement(msg.content, msg.type));
            });

            // Update local chat history
            const chat = this.chatHistories.find(c => c.id == chatId);
            if (chat) {
                chat.messages = data.messages;
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
    async createNewChat(firstMessage = null, clearMessages = false) {
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
            this.currentChatId = newChat.id;
            this.renderChatList();

            // Only clear messages if explicitly requested (when user clicks "New Chat" button)
            // NEVER clear when called from sendMessage (firstMessage exists)
            if (clearMessages) {
                DOM.messages.innerHTML = '';
            }

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

        // Show typing indicator
        const typingIndicator = createTypingIndicator();
        DOM.messages.appendChild(typingIndicator);
        scrollToBottom(DOM.messages);

        try {
            // Get selected model from UI
            const modelElement = document.getElementById('currentModel');
            const selectedModel = modelElement ? modelElement.textContent.trim() : null;

            console.log('🚀 Sending message:', text);
            console.log('📝 Chat ID:', this.currentChatId);
            console.log('🤖 Selected model:', selectedModel);

            // Add try-catch để bắt lỗi navigation/reload
            let data;
            try {
                data = await apiService.sendMessage(this.currentChatId, text, selectedModel);
                console.log('✅ Response received successfully');
            } catch (apiError) {
                console.error('❌ API Error:', apiError);
                throw apiError;
            }

            console.log('✅ Response data:', data);
            console.log('📄 Bot message content:', data?.bot_message?.content);
            console.log('📊 Content length:', data?.bot_message?.content?.length);

            // Remove typing indicator
            typingIndicator.remove();

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
                    localStorage.setItem('chatHistories', JSON.stringify(this.chatHistories));
                }
            } else {
                showNotification(data.message || 'Lỗi khi gửi tin nhắn', 'error');
            }
        } catch (err) {
            console.error('Error sending message:', err);
            // Remove typing indicator on error
            const typingIndicator = DOM.messages.querySelector('.typing-indicator');
            if (typingIndicator) {
                typingIndicator.remove();
            }
            showNotification('Lỗi kết nối tới server', 'error');
        }
    }
}
