from controller.DAO import connect_to_mysql, close_connection
from models.FileData import FileData
from models.User import User
from datetime import date

class FileDataDAO:
    def add_filedata(self, name, content, uploadDate, user: User, status):
        conn = connect_to_mysql()
        cursor = conn.cursor()
        query = "INSERT INTO filedata (name, content, uploadDate, user_id, status) VALUES (%s, %s, %s, %s, %s)"
        cursor.execute(query, (name, content, uploadDate, user.id, status))
        conn.commit()
        close_connection(conn)

    def check_login(self, username, password):
        conn = connect_to_mysql()
        cursor = conn.cursor()
        query = "SELECT id, username, password, email, role FROM users WHERE username = %s AND password = %s"
        cursor.execute(query, (username, password))
        result = cursor.fetchone()
        close_connection(conn)
        if result:
            return User(*result)
        return None

    def get_all_filedata(self):
        conn = connect_to_mysql()
        cursor = conn.cursor()
        query = "SELECT id, name, status, uploadDate, user_id FROM filedata"
        cursor.execute(query)
        rows = cursor.fetchall()
        result = []
        for r in rows:
            user = User(id=r[4], username='', password='', email='', role='')
            result.append(FileData(id=r[0], name=r[1], status=r[2], uploadDate=r[3], u=user, content=None))
        close_connection(conn)
        return result

    def get_filedata_by_id(self, file_id):
        conn = connect_to_mysql()
        cursor = conn.cursor()
        query = "SELECT id, name, content, status, uploadDate, user_id FROM filedata WHERE id = %s"
        cursor.execute(query, (file_id,))
        r = cursor.fetchone()
        close_connection(conn)
        if r:
            user = User(id=r[5], username='', password='', email='', role='')
            return FileData(id=r[0], name=r[1], content=r[2], status=r[3], uploadDate=r[4], u=user)
        return None
