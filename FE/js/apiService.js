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

    // Send message
    async sendMessage(chatId, content, model = null) {
        const formData = new FormData();
        formData.append('chat_id', chatId);
        formData.append('content', content);
        if (model) {
            formData.append('model', model);
        }

        const resp = await fetch(`${API_BASE}/api/chat/send`, {
            method: 'POST',
            body: formData,
        });
        return await resp.json();
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
