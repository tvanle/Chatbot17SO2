// API Configuration
export const API_BASE = "http://127.0.0.1:8000";

// DOM Elements
export const DOM = {
    sidebar: document.getElementById('sidebar'),
    menuBtn: document.getElementById('menuBtn'),
    mobileMenuBtn: document.getElementById('mobileMenuBtn'),
    messageInput: document.getElementById('messageInput'),
    sendBtn: document.getElementById('sendBtn'),
    messages: document.getElementById('messages'),
    themeToggle: document.getElementById('themeToggle'),
    userBtn: document.getElementById('userBtn'),
    newChatBtn: document.getElementById('newChatBtn'),
    attachBtn: document.getElementById('attachBtn'),
    moreBtn: document.getElementById('moreBtn'),
    modelSelector: document.getElementById('modelSelector'),
    currentModelSpan: document.getElementById('currentModel')
};

// Mock Chat Histories Data
export const mockChatHistories = [
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
