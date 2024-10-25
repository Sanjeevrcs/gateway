import requests
from requests_sse import EventSource, InvalidStatusCodeError, InvalidContentTypeError
import requests
import threading
import time
from sseclient import SSEClient



AUTH_URL_TEMPLATE = ' http://{tenant}.localhost:8000/api/v1/gateway/authenticate/'
SSE_URL_TEMPLATE = 'http://{tenant}.localhost:8000/api/v1/gateway/events/{gateway_id}/'
# API endpoint for heartbeat
HEARTBEAT_URL_TEMPLATE = 'http://{tenant}.localhost:8000/api/v1/gateway/{gateway_id}/heartbeat'


def authenticate(tenant):
    """Prompt for username and password, and send authentication request."""
    username = input("Enter username: ")
    password = input("Enter password: ")
    auth_url = AUTH_URL_TEMPLATE.format(tenant=tenant)
    print("Authenticating...",auth_url)
    # Send the authentication request
    payload = {
        'name': username,
        'password': password
    }
    try:
        response = requests.post(auth_url, data=payload)
        if response.status_code == 200:
            token = response.json().get('token')
            gateway_id = response.json().get('id')  # Assuming your API returns this
            print("Authenticated successfully!")
            print(f"Token: {token}", f"Gateway ID: {gateway_id}")
            return token, gateway_id
        else:
            print(f"Failed to authenticate: {response.status_code}")
            return None, None
    except Exception as e:
        print(f"Error during authentication: {e}")
        return None, None



def send_heartbeat(gateway_id, tenant, token):
    """Send heartbeat data to the backend at regular intervals."""
    headers = {
        'Authorization': f'Bearer {token}'
    }
    heartbeat_url = HEARTBEAT_URL_TEMPLATE.format(tenant=tenant, gateway_id=gateway_id)
    
    while True:
        try:
            payload = {
                'gateway_id': gateway_id,
                'status': 'alive',  # or dynamic status
                'timestamp': time.time()
            }
            response = requests.post(heartbeat_url, data=payload, headers=headers)
            if response.status_code == 200:
                print("Heartbeat sent successfully.")
            else:
                print(f"Failed to send heartbeat: {response.status_code}")
        except Exception as e:
            print(f"Error sending heartbeat: {e}")
        
        time.sleep(2)



def listen_to_sse(tenant, gateway_id, token):
    sse_url = SSE_URL_TEMPLATE.format(tenant=tenant, gateway_id=gateway_id)
    
    headers = {
        'Accept': 'text/event-stream', 
        'Authorization': f'Bearer {token}',  # Include your token
        'keep-alive': 'true'
    }

    with EventSource(sse_url, timeout=30, headers=headers) as event_source:
        try:
            for event in event_source:
                print("Data received from server:", event.data)
                # connect_wsus(event.data)
        except InvalidStatusCodeError:
            print("Invalid status code error occurred.")
        except InvalidContentTypeError:
            print("Invalid content type error occurred.")
        except requests.RequestException as e:
            print(f"Request exception: {e}")


def connect_wsus(wsus_parameters):
    import pyodbc

    db_connection_string = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER=20.184.39.130;DATABASE=SUSDB;UID=wsusdbuser;PWD=SQT98563456##'

    try:
        # Connect to the WSUS database
        conn = pyodbc.connect(db_connection_string)
        cursor = conn.cursor()  
        cursor.execute('SELECT * FROM tbUpdate')
        rows = cursor.fetchall()

        # Print the results
        for row in rows:
            print(row)

    except pyodbc.Error as e:
        print(f"Error connecting to WSUS database: {e}")
        return

def main():
    tenant = input("Enter tenant ID: ")  # Prompt for tenant ID
    # Authenticate the gateway if not authenticated yet
    token, gateway_id = authenticate(tenant)
    
    if token and gateway_id:
        # Start the heartbeat mechanism in a separate thread
        heartbeat_thread = threading.Thread(target=send_heartbeat, args=(gateway_id, tenant, token))
        heartbeat_thread.daemon = True  # Daemon thread will stop when the main thread stops
        heartbeat_thread.start()
        
        # Start listening to SSE events with the gateway_id
        listen_to_sse(tenant, gateway_id, token)
    else:
        print("Authentication failed. Exiting...")


if __name__ == '__main__':
    main()