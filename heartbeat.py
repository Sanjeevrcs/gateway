# heartbeat.py

import time
import requests
import threading
from config import HEARTBEAT_URL_TEMPLATE

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

def start_heartbeat(gateway_id, tenant, token):
    heartbeat_thread = threading.Thread(target=send_heartbeat, args=(gateway_id, tenant, token))
    heartbeat_thread.daemon = True
    heartbeat_thread.start()
