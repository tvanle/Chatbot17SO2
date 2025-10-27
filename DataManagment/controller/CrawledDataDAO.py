from controller.DAO import connect_to_mysql, close_connection
from Chatbot.models.CrawledData import CrawledData
from Chatbot.models.User import User
from datetime import date

class CrawledDataDAO:
    def get_all_crawled_webs(self):
        conn = connect_to_mysql()
        cursor = conn.cursor()
        query = "SELECT id, url, content, crawlDate, status, user_id FROM crawleddata"
        cursor.execute(query)
        rows = cursor.fetchall()
        result = []
        for r in rows:
            user = User(id=r[5], username='', password='', email='', role='')
            result.append(CrawledData(id=r[0], url=r[1], content=r[2], crawlDate=r[3], status=r[4], u=user))
        close_connection(conn)
        return result
