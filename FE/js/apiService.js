// API Service - Xử lý gọi API tới backend
import { API_BASE } from './config.js';

export const apiService = {
    // Get chat list
    async getChatList(userId) {
        const resp = await fetch(`${API_BASE}/api/chat/list?user_id=${userId}`, {
            method: 'GET',
        });
        return await resp.json();
    },

    // Get chat messages
    async getChatMessages(chatId) {
        const resp = await fetch(`${API_BASE}/api/chat/messages?chat_id=${chatId}`, {
            method: 'GET',
        });
        return await resp.json();
    },

    // Create new chat
    async createChat(userId, title) {
        const formData = new FormData();
        formData.append('user_id', userId);
        formData.append('title', title);

        const resp = await fetch(`${API_BASE}/api/chat/create`, {
            method: 'POST',
            body: formData,
        });
        return await resp.json();
    },

    // Send message - DIRECTLY to RAG API (bypass chat service)
    async sendMessage(chatId, content, model = null) {
        console.log('🌐 Calling RAG API directly:', `${API_BASE}/api/rag/answer`);
        console.log('📦 Question:', content);

        const resp = await fetch(`${API_BASE}/api/rag/answer`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                namespace_id: 'ptit_docs',
                question: content,
                top_k: 5,
                token_budget: 2000
            })
        });

        console.log('📥 Response status:', resp.status);
        const data = await resp.json();

        // Transform RAG response to chat format
        return {
            ok: true,
            message: 'Success',
            bot_message: {
                content: data.answer || 'Không có câu trả lời',
                type: 'assistant'
            },
            user_message: {
                content: content,
                type: 'user'
            }
        };
    },

    // Get models
    async getModels() {
        const response = await fetch(`${API_BASE}/api/chat/models`, {
            method: 'GET',
            credentials: 'include'
        });
        return await response.json();
    },

    // Get user profile
    async getUserProfile(userId) {
        const resp = await fetch(`${API_BASE}/api/auth/profile?user_id=${encodeURIComponent(userId)}`, {
            method: 'GET'
        });
        return await resp.json();
    },

    // Logout
    async logout() {
        await fetch(`${API_BASE}/api/auth/logout`, {
            method: 'POST',
        });
    }
};
