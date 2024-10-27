# wsus_connector.py

import pyodbc

def connect_wsus():
    db_connection_string = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=20.184.39.130;DATABASE=SUSDB;UID=wsusdbuser;PWD=SQT98563456##'

    try:
        conn = pyodbc.connect(db_connection_string)
        cursor = conn.cursor()  
        cursor.execute('SELECT * FROM tbUpdate')
        rows = cursor.fetchall()

        for row in rows:
            print(row)
    except pyodbc.Error as e:
        print(f"Error connecting to WSUS database: {e}")
