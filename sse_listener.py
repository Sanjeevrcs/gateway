# sse_listener.py

from requests_sse import EventSource, InvalidStatusCodeError, InvalidContentTypeError
import requests
from config import SSE_URL_TEMPLATE

def listen_to_sse(tenant, gateway_id, token):
    sse_url = SSE_URL_TEMPLATE.format(tenant=tenant, gateway_id=gateway_id)
    headers = {
        'Accept': 'text/event-stream', 
        'Authorization': f'Bearer {token}',
        'keep-alive': 'true'
    }

    with EventSource(sse_url, timeout=30, headers=headers) as event_source:
        try:
            for event in event_source:
                print("Data received from server:", event.data)
        except InvalidStatusCodeError:
            print("Invalid status code error occurred.")
        except InvalidContentTypeError:
            print("Invalid content type error occurred.")
        except requests.RequestException as e:
            print(f"Request exception: {e}")
