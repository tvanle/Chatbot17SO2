# MODULE: TẠO CHAT MỚI VÀ TRÒ CHUYỆN

**Sinh viên:** Lê Văn Trọng - B22DCCN863
**Đề tài:** Hệ thống Chatbot tư vấn thông tin
**Nhóm:** 17 - Lớp học phần: 06

---

## 1. THIẾT KẾ CƠ SỞ DỮ LIỆU

### 1.1. Bảng tblChat (Đoạn chat)

| Tên cột | Kiểu dữ liệu | Ràng buộc | Mô tả |
|---------|--------------|-----------|-------|
| **id** | Integer | PRIMARY KEY, AUTO_INCREMENT | ID đoạn chat |
| **user_id** | Integer | FOREIGN KEY → tblUser.id, NOT NULL, INDEX | ID người dùng sở hữu chat |
| **title** | String(500) | NOT NULL | Tiêu đề đoạn chat |
| **created_at** | DateTime | DEFAULT NOW() | Thời gian tạo |
| **updated_at** | DateTime | DEFAULT NOW(), ON UPDATE NOW() | Thời gian cập nhật |

### 1.2. Bảng tblMessage (Tin nhắn)

| Tên cột | Kiểu dữ liệu | Ràng buộc | Mô tả |
|---------|--------------|-----------|-------|
| **id** | Integer | PRIMARY KEY, AUTO_INCREMENT | ID tin nhắn |
| **chat_id** | Integer | FOREIGN KEY → tblChat.id, NOT NULL, INDEX | ID đoạn chat chứa tin nhắn |
| **type** | Enum | NOT NULL | Loại tin nhắn: "user" hoặc "assistant" |
| **content** | Text | NOT NULL | Nội dung tin nhắn |
| **created_at** | DateTime | DEFAULT NOW() | Thời gian gửi |

### 1.3. Sơ đồ quan hệ

```
tblUser (1) ─────< (n) tblChat (1) ─────< (n) tblMessage
```

**Giải thích:**
- Một User có nhiều Chat (quan hệ 1-n)
- Một Chat có nhiều Message (quan hệ 1-n)
- Khi xóa Chat → tự động xóa các Message liên quan (CASCADE)

---

## 2. THIẾT KẾ LỚP THỰC THỂ

### 2.1. Lớp Chat (BE/models/Chat.py)

```python
from sqlalchemy import Column, Integer, String, DateTime, func, ForeignKey
from sqlalchemy.orm import relationship
from BE.db.session import Base

class Chat(Base):
    __tablename__ = "tblChat"

    # Thuộc tính
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("tblUser.id"), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Quan hệ
    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan")
```

**Mô tả thuộc tính:**
- `id`: Định danh duy nhất của đoạn chat
- `user_id`: ID của user sở hữu chat (khóa ngoại)
- `title`: Tiêu đề đoạn chat
- `created_at`: Thời điểm tạo chat
- `updated_at`: Thời điểm cập nhật gần nhất
- `messages`: Danh sách các tin nhắn trong chat (relationship)

---

### 2.2. Lớp Message (BE/models/Message.py)

```python
from sqlalchemy import Column, Integer, String, Text, DateTime, func, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from BE.db.session import Base
import enum

class MessageType(enum.Enum):
    user = "user"
    assistant = "assistant"

class Message(Base):
    __tablename__ = "tblMessage"

    # Thuộc tính
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(Integer, ForeignKey("tblChat.id"), nullable=False, index=True)
    type = Column(SQLEnum(MessageType), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    # Quan hệ
    chat = relationship("Chat", back_populates="messages")
```

**Mô tả thuộc tính:**
- `id`: Định danh duy nhất của tin nhắn
- `chat_id`: ID đoạn chat chứa tin nhắn (khóa ngoại)
- `type`: Loại tin nhắn (user hoặc assistant)
- `content`: Nội dung tin nhắn
- `created_at`: Thời điểm gửi tin nhắn
- `chat`: Tham chiếu đến đoạn chat (relationship)

---

## 3. THIẾT KẾ BIỂU ĐỒ LỚP CHI TIẾT

### 3.1. Tầng Giao diện (Frontend)

**File: FE/index.html**
- `btnNewChat: Button` - Nút tạo chat mới
- `btnChatHistory: Button` - Nút chọn chat cũ (trên sidebar)
- `txtChat: Textarea` - Ô nhập tin nhắn
- `btnSend: Button` - Nút gửi tin nhắn
- `lblMessage: Label` - Hiển thị tin nhắn trên màn hình

**File: FE/js/chatManager.js**
```javascript
class ChatManager {
    - currentUser: User
    - chatHistories: Array<Chat>
    - currentChatId: String|Number

    + initialize(): Promise<void>
    + renderChatList(): void
    + loadChat(chatId): Promise<void>
    + createNewChat(firstMessage): Promise<Number>
    + sendMessage(text): Promise<void>
    + saveChatHistories(): void
}
```

**File: FE/js/apiService.js**
```javascript
const apiService = {
    + getChatList(userId): Promise<Response>
    + getChatMessages(chatId): Promise<Response>
    + createChat(userId, title): Promise<Response>
    + sendMessage(chatId, content): Promise<Response>
    + getModels(): Promise<Response>
}
```

---

### 3.2. Tầng Controller (API)

**File: BE/controllers/chat.py**
```python
router = APIRouter(prefix="/api/chat", tags=["chat"])

+ new_chat(user_id: int, title: str, db: Session): JSONResponse
+ get_chat_list(user_id: int, db: Session): JSONResponse
+ get_chat_messages(chat_id: int, db: Session): JSONResponse
+ send_message(chat_id: int, content: str, db: Session): JSONResponse
+ get_models(): JSONResponse
```

---

### 3.3. Tầng Service (Business Logic)

**File: BE/services/chatService.py**
```python
class ChatService:
    + create_chat(db: Session, user_id: int, title: str): dict
    + get_chat_list(db: Session, user_id: int): dict
    + get_chat_messages(db: Session, chat_id: int): dict
    + send_message(db: Session, chat_id: int, content: str): dict
    + get_models(): dict
```

---

### 3.4. Tầng DAO (Data Access Object)

**File: BE/dao/ChatDAO.py**
```python
class ChatDAO:
    + create(db: Session, user_id: int, title: str): Chat
    + find_by_id(db: Session, chat_id: int): Chat | None
    + find_by_user(db: Session, user_id: int): list[Chat]
    + update_title(db: Session, chat_id: int, title: str): Chat | None
    + delete(db: Session, chat_id: int): bool
```

**File: BE/dao/MessageDAO.py**
```python
class MessageDAO:
    + create(db: Session, chat_id: int, msg_type: MessageType, content: str): Message
    + find_by_chat(db: Session, chat_id: int): list[Message]
    + find_by_id(db: Session, message_id: int): Message | None
```

---

### 3.5. Sơ đồ lớp chi tiết đầy đủ

```
┌─────────────────────┐
│   index.html        │
├─────────────────────┤
│ - btnNewChat        │
│ - btnChatHistory    │◄─────────┐
│ - txtChat           │          │
│ - btnSend           │          │
│ - lblMessage        │          │
└──────────┬──────────┘          │
           │                     │
           ▼                     │
┌─────────────────────┐          │
│   chatManager.js    │          │
├─────────────────────┤          │
│ + initialize()      │          │
│ + createNewChat()   │──────────┤
│ + sendMessage()     │          │
│ + loadChat()        │          │
└──────────┬──────────┘          │
           │                     │
           ▼                     │
┌─────────────────────┐          │
│   apiService.js     │          │
├─────────────────────┤          │
│ + createChat()      │          │
│ + sendMessage()     │          │
│ + getChatMessages() │          │
└──────────┬──────────┘          │
           │                     │
           ▼ HTTP Request        │
┌─────────────────────┐          │
│   chat.py           │          │
│   (Controller)      │          │
├─────────────────────┤          │
│ + new_chat()        │          │
│ + send_message()    │          │
│ + get_chat_messages()│         │
└──────────┬──────────┘          │
           │                     │
           ▼                     │
┌─────────────────────┐          │
│   chatService.py    │          │
│   (Service)         │          │
├─────────────────────┤          │
│ + create_chat()     │          │
│ + send_message()    │          │
│ + get_chat_messages()│         │
└─────┬────────┬──────┘          │
      │        │                 │
      ▼        ▼                 │
┌──────────┐ ┌──────────────┐   │
│ChatDAO.py│ │MessageDAO.py │   │
├──────────┤ ├──────────────┤   │
│+ create()│ │+ create()    │   │
│+ find_*()│ │+ find_*()    │   │
└────┬─────┘ └──────┬───────┘   │
     │              │            │
     ▼              ▼            │
┌─────────────────────────┐     │
│      Database           │     │
│  tblChat  tblMessage    │     │
└─────────────────────────┘     │
                                │
     Response JSON ─────────────┘
```

---

## 4. BIỂU ĐỒ HOẠT ĐỘNG

### 4.1. Tạo chat mới và gửi tin nhắn

```
[Bắt đầu]
   │
   ▼
┌────────────────────────┐
│ User click "New Chat"  │
│ hoặc gửi tin nhắn      │
│ khi chưa có chat       │
└──────────┬─────────────┘
           │
           ▼
┌────────────────────────┐
│ chatManager.js:        │
│ createNewChat()        │
└──────────┬─────────────┘
           │
           ▼
┌────────────────────────┐
│ apiService.js:         │
│ POST /api/chat/new     │
└──────────┬─────────────┘
           │
           ▼
┌────────────────────────┐
│ chat.py:               │
│ new_chat()             │
└──────────┬─────────────┘
           │
           ▼
┌────────────────────────┐
│ chatService.py:        │
│ create_chat()          │
└──────────┬─────────────┘
           │
           ▼
┌────────────────────────┐
│ ChatDAO.py:            │
│ create()               │
│ → Lưu vào DB           │
└──────────┬─────────────┘
           │
           ▼
┌────────────────────────┐
│ Trả về chat.id         │
└──────────┬─────────────┘
           │
           ▼
┌────────────────────────┐
│ Nếu có firstMessage:   │
│ → gọi sendMessage()    │
└──────────┬─────────────┘
           │
           ▼
[Kết thúc]
```

---

### 4.2. Gửi tin nhắn trong chat hiện tại

```
[Bắt đầu]
   │
   ▼
┌────────────────────────┐
│ User nhập tin nhắn     │
│ và click Send          │
└──────────┬─────────────┘
           │
           ▼
┌────────────────────────┐
│ Hiển thị tin nhắn user │
│ lên giao diện          │
└──────────┬─────────────┘
           │
           ▼
┌────────────────────────┐
│ apiService.js:         │
│ POST /api/chat/send    │
└──────────┬─────────────┘
           │
           ▼
┌────────────────────────┐
│ chat.py:               │
│ send_message()         │
└──────────┬─────────────┘
           │
           ▼
┌────────────────────────┐
│ chatService.py:        │
│ send_message()         │
└──────────┬─────────────┘
           │
           ▼
┌────────────────────────┐
│ MessageDAO.py:         │
│ create() - user msg    │
│ → Lưu tin nhắn user    │
└──────────┬─────────────┘
           │
           ▼
┌────────────────────────┐
│ TODO: Gọi AI model     │
│ (Hiện tại: mock data)  │
└──────────┬─────────────┘
           │
           ▼
┌────────────────────────┐
│ MessageDAO.py:         │
│ create() - bot msg     │
│ → Lưu phản hồi bot     │
└──────────┬─────────────┘
           │
           ▼
┌────────────────────────┐
│ Trả về bot_message     │
└──────────┬─────────────┘
           │
           ▼
┌────────────────────────┐
│ Hiển thị phản hồi bot  │
│ lên giao diện          │
└──────────┬─────────────┘
           │
           ▼
[Kết thúc]
```

---

### 4.3. Chọn chat cũ và xem lịch sử

```
[Bắt đầu]
   │
   ▼
┌────────────────────────┐
│ User click chat cũ     │
│ trên sidebar           │
└──────────┬─────────────┘
           │
           ▼
┌────────────────────────┐
│ chatManager.js:        │
│ loadChat(chatId)       │
└──────────┬─────────────┘
           │
           ▼
┌────────────────────────┐
│ apiService.js:         │
│ GET /api/chat/messages │
└──────────┬─────────────┘
           │
           ▼
┌────────────────────────┐
│ chat.py:               │
│ get_chat_messages()    │
└──────────┬─────────────┘
           │
           ▼
┌────────────────────────┐
│ chatService.py:        │
│ get_chat_messages()    │
└──────────┬─────────────┘
           │
           ▼
┌────────────────────────┐
│ MessageDAO.py:         │
│ find_by_chat()         │
│ → Lấy messages từ DB   │
└──────────┬─────────────┘
           │
           ▼
┌────────────────────────┐
│ Trả về danh sách       │
│ messages               │
└──────────┬─────────────┘
           │
           ▼
┌────────────────────────┐
│ Hiển thị lịch sử chat  │
│ lên giao diện          │
└──────────┬─────────────┘
           │
           ▼
[Kết thúc]
```

---

## 5. BIỂU ĐỒ TUẦN TỰ

### 5.1. Tạo chat mới và gửi tin nhắn đầu tiên

```
User        index.html    chatManager.js    apiService.js    chat.py    chatService.py    ChatDAO    MessageDAO    Database
 │               │                │                │            │              │              │           │             │
 │─ click New ──>│                │                │            │              │              │           │             │
 │               │─ createNew() ─>│                │            │              │              │           │             │
 │               │                │─ createChat() ─>│           │              │              │           │             │
 │               │                │                │─ POST /new>│              │              │           │             │
 │               │                │                │            │─ create_chat>│              │           │             │
 │               │                │                │            │              │─ create() ──>│           │             │
 │               │                │                │            │              │              │─ INSERT ─>│             │
 │               │                │                │            │              │              │<─ chat ───│             │
 │               │                │                │            │              │<─ chat ──────│           │             │
 │               │                │                │            │<─ {ok,chat} ─│              │           │             │
 │               │                │                │<─ data ────│              │              │           │             │
 │               │                │<─ newChat.id ──│            │              │              │           │             │
 │               │                │                │            │              │              │           │             │
 │               │                │─ sendMessage()─────────────────────────────────────────────────────────────────────>│
 │               │                │                │─ POST send>│              │              │           │             │
 │               │                │                │            │─send_message>│              │           │             │
 │               │                │                │            │              │──────────────────────> create(user) ──>│
 │               │                │                │            │              │              │           │─ INSERT ───>│
 │               │                │                │            │              │<TODO: AI>    │           │             │
 │               │                │                │            │              │──────────────────────> create(bot) ───>│
 │               │                │                │            │              │              │           │─ INSERT ───>│
 │               │                │                │            │<─ {ok,msgs} ─│              │           │             │
 │               │                │                │<─ data ────│              │              │           │             │
 │               │<─ display ─────│                │            │              │              │           │             │
 │<─ show bot ───│                │                │            │              │              │           │             │
```

---

### 5.2. Chọn chat cũ và xem tin nhắn

```
User        index.html    chatManager.js    apiService.js    chat.py    chatService.py    MessageDAO    Database
 │               │                │                │            │              │              │             │
 │─ click chat ─>│                │                │            │              │              │             │
 │               │─ loadChat() ──>│                │            │              │              │             │
 │               │                │─ getChatMsgs()>│            │              │              │             │
 │               │                │                │─GET /msgs ─>│              │              │             │
 │               │                │                │            │─get_chat_msgs>│              │             │
 │               │                │                │            │              │─find_by_chat>│             │
 │               │                │                │            │              │              │─ SELECT ──>│
 │               │                │                │            │              │              │<─ msgs ────│
 │               │                │                │            │              │<─ msgs ──────│             │
 │               │                │                │            │<─ {ok,msgs} ─│              │             │
 │               │                │                │<─ data ────│              │              │             │
 │               │                │<─ messages ────│            │              │              │             │
 │               │<─ display ─────│                │            │              │              │             │
 │<─ show msgs ──│                │                │            │              │              │             │
```

---

### 5.3. Gửi tin nhắn trong chat hiện có

```
User        index.html    chatManager.js    apiService.js    chat.py    chatService.py    MessageDAO    Database
 │               │                │                │            │              │              │             │
 │─ type & send>│                │                │            │              │              │             │
 │               │─ show user ───>│                │            │              │              │             │
 │               │                │─ sendMessage()>│            │              │              │             │
 │               │                │                │─POST /send>│              │              │             │
 │               │                │                │            │─send_message>│              │             │
 │               │                │                │            │              │─create(user)>│             │
 │               │                │                │            │              │              │─ INSERT ──>│
 │               │                │                │            │              │<TODO: AI>    │             │
 │               │                │                │            │              │─create(bot)─>│             │
 │               │                │                │            │              │              │─ INSERT ──>│
 │               │                │                │            │<─{ok,bot_msg}│              │             │
 │               │                │                │<─ data ────│              │              │             │
 │               │                │<─ bot_msg ─────│            │              │              │             │
 │               │<─ display bot ─│                │            │              │              │             │
 │<─ show bot ───│                │                │            │              │              │             │
```

---

## KẾT LUẬN

Module "Tạo chat mới và trò chuyện" đã được thiết kế và triển khai hoàn chỉnh với:

✅ **Đã hoàn thành:**
1. Thiết kế CSDL với 2 bảng: tblChat, tblMessage
2. Xây dựng lớp thực thể: Chat, Message với đầy đủ relationships
3. Tầng DAO: ChatDAO, MessageDAO xử lý truy xuất dữ liệu
4. Tầng Service: ChatService xử lý logic nghiệp vụ
5. Tầng Controller: chat.py cung cấp 5 API endpoints
6. Frontend: chatManager.js, apiService.js tích hợp hoàn chỉnh
7. Lưu trữ lịch sử chat vào database

⚠️ **Cần hoàn thiện:**
- Tích hợp AI model thật (hiện dùng mock response: "Xin chào! Tôi là chatbot...")
- Chưa có file llmClient.py để gọi API AI

**Cấu trúc files thực tế:**
```
BE/
├── models/Chat.py           ✅
├── models/Message.py        ✅
├── dao/ChatDAO.py           ✅
├── dao/MessageDAO.py        ✅
├── services/chatService.py  ✅
└── controllers/chat.py      ✅

FE/
├── js/chatManager.js        ✅
├── js/apiService.js         ✅
└── index.html               ✅
```

---

*Báo cáo được viết dựa trên code thực tế đã triển khai*
