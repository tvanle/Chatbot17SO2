## Hướng dẫn cài đặt thư viện cho dự án 

### 1. Cài đặt Python

- Đảm bảo đã cài Python >= 3.8 (khuyến nghị dùng Python 3.13)

### 2. Cài đặt các thư viện cần thiết

Mở terminal/cmd tại thư mục dự án và chạy các lệnh sau:

```bash
pip install flask flask-cors mysql-connector-python python-docx
```

### 3. Cấu hình MySQL

- Tạo database tên `client_server` (hoặc tên bạn cấu hình trong DAO.py)
- Tạo các bảng phù hợp với models: users, filedata, crawleddata

### 4. Chạy ứng dụng

```bash
python Chatbot/main.py
```

### 5. Lưu ý

- Nếu dùng Windows, chỉ cần dùng `mysql-connector-python` (không cần MySQLdb)
- Đảm bảo MySQL đang chạy và user/password đúng như cấu hình trong DAO.py
