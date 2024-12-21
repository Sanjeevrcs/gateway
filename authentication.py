# authentication.py

import requests
from config import AUTH_URL_TEMPLATE, PROTOCOL, ATTACKBOX_SERVER_DOMAIN

tenant_id = ""

def authenticate(tenant):
    """Prompt for username and password, and send authentication request."""
    username = input("Enter username: ")
    password = input("Enter password: ")

    # username = 'g1'
    # password = 'g1'

    auth_url = AUTH_URL_TEMPLATE.format(tenant=tenant, domain=ATTACKBOX_SERVER_DOMAIN, protocol=PROTOCOL)
    
    print("Authenticating...", auth_url)
    
    payload = {
        'name': username,
        'password': password
    }
    
    try:
        response = requests.post(auth_url, data=payload)
        if response.status_code == 200:
            token = response.json().get('token')
            gateway_id = response.json().get('id')
            tenant_id = response.json().get('tenant_id')
            print("Authenticated successfully!")
            print(f"Token: {token}", f"Gateway ID: {gateway_id}", f"Tenant ID: {tenant_id}")
            return token, gateway_id, tenant_id
        else:
            print(f"Failed to authenticate: {response.status_code}")
            return None, None
    except Exception as e:
        print(f"Error during authentication: {e}")
        return None, None
