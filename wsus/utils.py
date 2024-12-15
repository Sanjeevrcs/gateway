from datetime import datetime
import socket
import struct

def parse_wsus_date(wsus_date):
    """
    Parse and format the WSUS .NET date string.
    Args:
        wsus_date (str): The date string from WSUS in the format "/Date(1732670829207)/".
    Returns:
        str: The formatted date string in "YYYY-MM-DD HH:MM:SS" format.
    """
    try:
        # Extract the milliseconds part from the WSUS date string
        milliseconds = int(wsus_date.strip('/Date()/'))
        
        # Convert milliseconds to a datetime object
        dt = datetime.utcfromtimestamp(milliseconds / 1000)
        
        # Format the datetime object into a human-readable string
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except Exception as e:
        print(f"Error parsing WSUS date: {wsus_date} - {str(e)}")
        return None
    


def int_to_ip_address(address):
    """
    Convert an integer representation of an IP address to a dotted-decimal string.
    Args:
        address (int): The integer representation of the IP address.
    Returns:
        str: The dotted-decimal IP address.
    """
    try:
        # Convert the integer to a 4-byte network byte order and then to a string
        return socket.inet_ntoa(struct.pack('!I', address))
    except Exception as e:
        print(f"Error converting address {address}: {e}")
        return None
    

# WSUS Update States Mapping:
# 
# 0: "Not Installed"        -> Not Installed
# 1: "License Agreement Not Ready"  -> Needs Installation (pending)
# 2: "Installation Impossible"      -> Not Installed (unable to install)
# 3: "Not Needed"            -> Needs Installation (not yet required)
# 4: "Not Ready"             -> Needs Installation (pending files)
# 5: "Ready"                 -> Ready to Install
# 6: "Canceled"              -> Not Installed (waiting for resume)
# 7: "Failed"                -> Not Installed (failed to install)
# 8: "License Agreement Failed" -> Not Installed (waiting for agreement)



UPDATE_STATE_MAPPING = {
    0: "Not Installed",  # Update is not installed yet
    1: "License Agreement Not Ready",  # License agreement for this update is not available yet
    2: "Installation Impossible",  # The update cannot be installed due to reasons like compatibility
    3: "Not Needed",  # The update is available but not yet needed
    4: "Not Ready",  # Update is approved for installation but required files are not yet available
    5: "Ready",  # Update is ready for installation, all files are available
    6: "Canceled",  # The update or one of its parents/children was canceled by an administrator
    7: "Failed",  # Update failed to install for various reasons (e.g., missing files)
    8: "License Agreement Failed",  # License agreement failed to download
}

def get_update_state_description(state_code):
    """
    Get the description of the WSUS update state.
    Args:
        state_code (int): The state code from WSUS.
    Returns:
        str: The description of the state.
    """
    return UPDATE_STATE_MAPPING.get(state_code, "Unknown State")

