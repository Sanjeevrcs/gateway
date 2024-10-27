# wsus_connector.py

import pyodbc


def pull_data(data):
    """
    Pull data from the WSUS database based on the task specified in the event data.
    
    Args:
        data (dict): Event data containing the task to be executed.
        
    Returns:
        dict: Data pulled from the WSUS database based on the task.
    """
    conn, cursor = connect_wsus(data)
    if conn is None or cursor is None:
        return None
    cursor.execute('SELECT * FROM tbUpdate')
    rows = cursor.fetchall()

    for row in rows:
        print(row)
    
    cursor.close()
    conn.close()


def connect_wsus(data):
    print(data, type(data))
    db_connection_string = 'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={ip_address};DATABASE=SUSDB;UID={hostname};PWD={password}'.format(
        ip_address=data.get('ip_address'),
        hostname=data.get('hostname'),
        password=data.get('password')
    )
    try:
        print(f"Connecting to WSUS database: {db_connection_string}")
        conn = pyodbc.connect(db_connection_string)
        cursor = conn.cursor()  
        return conn, cursor
    except pyodbc.Error as e:
        print(f"Error connecting to WSUS database: {e}")
        return None, None