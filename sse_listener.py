# sse_listener.py
from requests_sse import EventSource, InvalidStatusCodeError, InvalidContentTypeError
import requests
from config import SSE_URL_TEMPLATE
import json

from wsus_connector import pull_data

def validate_sse_data(event_data):
    """
    Validates if the incoming SSE event data matches the required format.

    Expected format:
    {
        "task": "string",
        "data": { "key": "value", ... } or [{"key": "value", ...}]
    }

    Returns:
        bool: True if data is valid, False otherwise.
    """
    # Check if event_data is already a dictionary
    if isinstance(event_data, str):
        try:
            # Parse the event data from JSON if it's in string format
            data = json.loads(event_data)
        except json.JSONDecodeError:
            print("Validation Error: Invalid JSON format received.")
            return False, None
    elif isinstance(event_data, dict):
        data = event_data
    else:
        print("Validation Error: Unsupported data format.")
        return False, None

    # Now validate the structure of the data dictionary
    if "task" in data and "data" in data:
        if isinstance(data["task"], str) and isinstance(data["data"], (dict, list)):
            return True, data
        else:
            print("Validation Error: 'task' should be a string and 'data' should be a dict or list.")
    else:
        print("Validation Error: Missing 'task' or 'data' keys or incorrect format.")
    
    return False, None



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
                # Validate the event data format
                valid, event_data = validate_sse_data(event.data)
                if valid:
                    print("Validated data:", event_data)
                    
                    switcher = {
                        "pull_data": pull_data,
                    }
                    function = switcher.get(event_data["task"], lambda x: print("Invalid task"))

                    # Call the function with event_data["data"] if it's valid
                    if function:
                        print("Calling function...", event_data["data"])
                        for data in event_data['data']:
                            function(data)
                    # Process the event here if data is valid
                else:
                    print("Invalid data format received.")
                    
        except InvalidStatusCodeError:
            print("Invalid status code error occurred.")
        except InvalidContentTypeError:
            print("Invalid content type error occurred.")
        except requests.RequestException as e:
            print(f"Request exception: {e}")
