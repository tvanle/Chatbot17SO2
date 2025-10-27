import mysql.connector
db_host = 'localhost'
db_user = 'root'
db_password = '123456'
db_database = 'client_server'

def connect_to_mysql():
    try:
        connection = mysql.connector.connect(
            host=db_host,
            user=db_user,
            password=db_password,
            database=db_database
        )
        return connection
    except Exception as e:
        print(f"Error: {e}")
        return None

def close_connection(connection):
    connection.close()