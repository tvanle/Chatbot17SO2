from datetime import date
from .User import User

class CrawledData:
    def __init__(self, id: str, url: str, content: str, crawlDate: date, status: str, u: User):
        self.id = id
        self.url = url
        self.content = content
        self.crawlDate = crawlDate
        self.status = status
        self.u = u
