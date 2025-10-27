from controller.DAO import connect_to_mysql, close_connection

class StatisticDAO:
    def get_total_file(self):
        conn = connect_to_mysql()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM filedata')
        result = cursor.fetchone()[0]
        close_connection(conn)
        return result

    def get_total_url(self):
        conn = connect_to_mysql()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM crawleddata')
        result = cursor.fetchone()[0]
        close_connection(conn)
        return result
