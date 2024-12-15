from authentication import authenticate
from heartbeat import start_heartbeat
from sse_listener import listen_to_sse

def main():
    # tenant = input("Enter tenant ID: ")  # Prompt for tenant ID
    tenant = 'petronas'
    # Authenticate the gateway if not authenticated yet
    token, gateway_id = authenticate(tenant)
    
    if token and gateway_id:
        # Start the heartbeat mechanism
        # start_heartbeat(gateway_id, tenant, token)
        
        # Start listening to SSE events
        print("Listening to SSE events...", tenant, gateway_id, token)
        listen_to_sse(tenant, gateway_id, token)
    else:
        print("Authentication failed. Exiting...")

if __name__ == '__main__':
    main()
