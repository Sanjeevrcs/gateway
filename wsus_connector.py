from datetime import datetime
from producer import produce_event
import pyodbc
import json


def get_computers(cursor):
    query = "SELECT CAST(ComputerID AS NVARCHAR(36)) AS ComputerID, FullDomainName FROM dbo.tbComputerTarget"
    cursor.execute(query)
    computers = cursor.fetchall()
    return [(row.ComputerID, row.FullDomainName) for row in computers]

# Query to get the list of updates needed for each computer
def get_needed_updates(cursor):
    query = """
    SELECT c.FullDomainName AS ComputerName, u.LegacyName AS UpdateTitle
    FROM dbo.tbUpdateStatusPerComputer AS us
    JOIN dbo.tbComputerTarget AS c ON CAST(us.TargetID AS NVARCHAR(36)) = CAST(c.ComputerID AS NVARCHAR(36))
    JOIN dbo.tbUpdate AS u ON us.LocalUpdateID = u.LocalUpdateID
    WHERE us.SummarizationState IN ('2', '3')  -- Using string literals to match SummarizationState
    """
    cursor.execute(query)
    needed_updates = cursor.fetchall()
    return [(row.ComputerName, row.UpdateTitle) for row in needed_updates]

# Query to get the list of updates already installed on each computer
def get_installed_updates(cursor):
    query = """
    SELECT c.FullDomainName AS ComputerName, u.LegacyName AS UpdateTitle
    FROM dbo.tbUpdateStatusPerComputer AS us
    JOIN dbo.tbComputerTarget AS c ON CAST(us.TargetID AS NVARCHAR(36)) = CAST(c.ComputerID AS NVARCHAR(36))
    JOIN dbo.tbUpdate AS u ON us.LocalUpdateID = u.LocalUpdateID
    WHERE us.SummarizationState = '4'  -- Using string literal for SummarizationState
    """
    cursor.execute(query)
    installed_updates = cursor.fetchall()
    return [(row.ComputerName, row.UpdateTitle) for row in installed_updates]


def pull_data(data):
    """
    Pull data from each table in the WSUS database and publish to Kafka.
    
    Args:
        data (dict): Connection parameters to access WSUS database.
    """
    conn, cursor = connect_wsus(data)
    if conn is None or cursor is None:
        return None
    
    print("Fetching computers...")
    computers = get_computers(cursor)
    print("Number of computers fetched:", len(computers))
    for computer in computers:
        row_data = json.dumps(computer)
        produce_event(row_data)

    # Fetch and publish data from get_needed_updates
    print("Fetching needed updates...")
    needed_updates = get_needed_updates(cursor)
    print("Number of needed updates fetched:", len(needed_updates))
    for update in needed_updates:
        row_data = json.dumps(update)
        produce_event(row_data)

    # Fetch and publish data from get_installed_updates
    print("Fetching installed updates...")
    installed_updates = get_installed_updates(cursor)
    print("Number of installed updates fetched:", len(installed_updates))
    for update in installed_updates:
        row_data = json.dumps(update)
        produce_event(row_data)

    # Close the cursor and connection
    cursor.close()
    conn.close()


def connect_wsus(data):
    """
    Establish connection to the WSUS database using provided data.
    
    Args:
        data (dict): Dictionary containing connection parameters.
        
    Returns:
        tuple: Connection and cursor objects if successful, otherwise (None, None).
    """
    db_connection_string = (
        'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={ip_address};DATABASE=SUSDB;UID={hostname};PWD={password}'
        .format(
            ip_address=data.get('ip_address'),
            hostname=data.get('hostname'),
            password=data.get('password')
        )
    )
    try:
        print(f"Connecting to WSUS database: {db_connection_string}")
        conn = pyodbc.connect(db_connection_string)
        cursor = conn.cursor()
        return conn, cursor
    except pyodbc.Error as e:
        print(f"Error connecting to WSUS database: {e}")
        return None, None
