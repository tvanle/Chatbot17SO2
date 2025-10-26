# Chatbot17SO2 - Kiến trúc MVC 3 tầng

## Cấu trúc dự án

```
Chatbot17SO2/
├── BE/                    # Backend
│   ├── controllers/       # Tầng Controller - Giao tiếp với FE
│   │   └── auth.py       # Xử lý các HTTP requests/responses
│   ├── services/         # Tầng Service - Logic nghiệp vụ
│   │   └── authService.py
│   ├── dao/              # Tầng DAO - Data Access Object
│   │   └── UserDAO.py    # Truy vấn database
│   ├── models/           # Database models
│   │   └── User.py
│   ├── db/               # Database configuration
│   │   └── session.py
│   ├── core/             # Core configuration
│   │   └── config.py
│   └── main.py           # Entry point
└── FE/                   # Frontend
    ├── index.html
    ├── login.html
    └── js/
        ├── auth.js
        └── script.js
```

## Kiến trúc 3 tầng MVC

### 1. Controller (Tầng giao tiếp FE)
- **Vị trí**: `BE/controllers/`
- **Chức năng**: Nhận HTTP requests từ FE, gọi Service layer, trả về responses
- **Ví dụ**: `auth.py` - xử lý login, register, logout, profile

### 2. Service (Tầng logic nghiệp vụ)
- **Vị trí**: `BE/services/`
- **Chức năng**: Xử lý business logic, validate dữ liệu, gọi DAO layer
- **Ví dụ**: `authService.py` - kiểm tra login, đăng ký user

### 3. DAO (Tầng truy vấn database)
- **Vị trí**: `BE/dao/`
- **Chức năng**: Thực hiện các câu query SQL, tương tác trực tiếp với database
- **Ví dụ**: `UserDAO.py` - find_by_email, create, checkUser

## Cài đặt & Chạy

### 1. Cài đặt dependencies
```bash
pip install -r requirements.txt
```

### 2. Chạy server
```bash
python -m uvicorn BE.main:app --reload --port 8000
```

Server sẽ chạy tại: **http://127.0.0.1:8000**

### 3. Truy cập API Documentation
- **Swagger UI**: http://127.0.0.1:8000/docs
- **ReDoc**: http://127.0.0.1:8000/redoc
- **Health Check**: http://127.0.0.1:8000/health

### 4. Mở Frontend
Mở file `FE/login.html` hoặc `FE/index.html` trong trình duyệt (hoặc dùng Live Server).

## API Endpoints

### Authentication
- `POST /api/auth/login` - Đăng nhập
- `POST /api/auth/register` - Đăng ký
- `POST /api/auth/logout` - Đăng xuất
- `GET /api/auth/profile?user_id={id}` - Lấy thông tin profile

### Health Check
- `GET /health` - Kiểm tra trạng thái server và database

## Database

### SQLite (Mặc định - Đang sử dụng)
```bash
# Không cần cài đặt gì thêm, database tự động tạo file chatbot.db
```

### MySQL (Tùy chọn)
Để chuyển sang MySQL, set biến môi trường:
```bash
export USE_SQLITE=false
export DB_USER=root
export DB_PASS=yourpassword
export DB_HOST=127.0.0.1
export DB_PORT=3306
export DB_NAME=chatbot
```

## Ghi chú
- ✅ Mặc định sử dụng **SQLite** - không cần cài MySQL
- ⚠️ Password được lưu plain text (chưa hash) - cần cải thiện security
- ✅ CORS đã được config cho phép gọi từ FE (localhost, file://)
- ✅ Database tự động tạo bảng khi server khởi động
- ✅ Hỗ trợ cả SQLite và MySQL
