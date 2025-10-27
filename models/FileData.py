from datetime import date
from .User import User

class FileData:
    def __init__(self, id: str, name: str, content: str, uploadDate: date, u: User, status: str):
        self.id = id
        self.name = name
        self.content = content
        self.uploadDate = uploadDate
        self.u = u
        self.status = status
