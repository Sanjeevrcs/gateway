from datetime import datetime
from producer import produce_event
import json
import winrm
from datetime import datetime

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
    
import socket
import struct

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
    
UPDATE_STATE_MAPPING = {
    0: "Not Installed",
    1: "Installing",
    2: "Installed",
    3: "Failed",
    4: "Downloaded but Not Installed",
    5: "Not Applicable",
    6: "Downloaded and Ready for Installation",
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



def pull_data(data):
    # Run the report
    ip_address = data['ip_address']
    hostname = data['hostname']
    password = data['password']
    wsus_info = get_wsus_detailed_info(ip_address, hostname, password)

    # Produce the event
    if wsus_info:
        for computer in wsus_info['Computers']:

            formatted_ip_address = int_to_ip_address(computer['IPAddress'])
            # Prepare the data for this computer
            last_status_report = parse_wsus_date(computer['LastStatusReport'])
            last_sync_time = parse_wsus_date(computer['LastSyncTime'])

            computer_data = {
                "computer_name": computer['ComputerName'],
                "ip_address": formatted_ip_address,
                "last_status_report": last_status_report,
                "last_sync_time": last_sync_time,
                "os_description": computer['OSDescription'],
                "groups": computer['Groups'],
                "updates": [
                    {
                        "kb": update['KB'],
                        "title": update['Title'],
                        "description": update['Description'],
                        "severity": update['Severity'],
                        "state": get_update_state_description(update['State']),
                        "reboot_required": update['RebootRequired'],
                        "installation_date": update.get('InstallationDate'),
                    }
                    for update in computer['Updates']
                ],
            }

            # Produce the event for this computer
            print(f"Producing event for computer: {computer['ComputerName']}")
            produce_event(json.dumps({
                "task": "pull_data",
                "data": computer_data,
            }))


def run_powershell_script(server_ip, username, password, powershell_script):
    """Execute PowerShell script on remote WSUS server"""
    try:
        session = winrm.Session(
            f'http://{server_ip}:5985/wsman',
            auth=(username, password),
            transport="ntlm",
        )
        
        result = session.run_ps(powershell_script)
        
        if result.status_code != 0:
            print(f"Error executing script: {result.std_err.decode()}")
            return None
        
        return result.std_out.decode()
    
    except Exception as e:
        print(f"Connection error: {str(e)}")
        return None

def get_wsus_detailed_info(server_ip, username, password):
    """Get comprehensive WSUS information including detailed update information"""
    powershell_script = """
    [reflection.assembly]::LoadWithPartialName("Microsoft.UpdateServices.Administration") | Out-Null
    $wsus = [Microsoft.UpdateServices.Administration.AdminProxy]::GetUpdateServer("localhost", $false, 8530)

    # Function to extract KB numbers
    function Get-KBNumber {
        param([string]$title)
        $kbMatch = $title | Select-String -Pattern "KB(\d+)" -AllMatches
        if ($kbMatch) {
            return $kbMatch.Matches.Value
        }
        return $null
    }

    # Build the result organized by computers
    $computersData = @{}
    $computerGroups = $wsus.GetComputerTargetGroups()

    foreach ($group in $computerGroups) {
        $groupComputers = $group.GetComputerTargets()
        foreach ($computer in $groupComputers) {
            if (-not $computersData.ContainsKey($computer.Id)) {
                $computersData[$computer.Id] = [PSCustomObject]@{
                    ComputerName = $computer.FullDomainName
                    IPAddress = $computer.IPAddress
                    LastStatusReport = $computer.LastReportedStatusTime
                    LastSyncTime = $computer.LastSyncTime
                    OSDescription = $computer.OSDescription
                    Groups = @()
                    Updates = @()
                }
            }
            # Add group name to the computer's group list
            $computersData[$computer.Id].Groups += $group.Name

            # Get applicable updates for the computer
            $applicableUpdates = $computer.GetUpdateInstallationInfoPerUpdate() |
                Where-Object { $_.UpdateInstallationState -ne 'NotApplicable' } |
                ForEach-Object {
                    $update = $wsus.GetUpdate($_.UpdateId)
                    $kbNumber = Get-KBNumber -title $update.Title
                    if ($kbNumber) {
                        [PSCustomObject]@{
                            KB = $kbNumber
                            Title = $update.Title
                            Description = $update.Description
                            Classification = $update.UpdateClassificationTitle
                            ReleaseDate = $update.CreationDate
                            Severity = $update.MsrcSeverity
                            State = $_.UpdateInstallationState
                            RebootRequired = $update.RequiresReboot
                            InstallationDate = if ($_.UpdateInstallationState -eq 'Installed') { $_.InstallationDate } else { $null }
                        }
                    }
                } | Where-Object { $_ -ne $null }

            # Add updates to the computer's update list
            $computersData[$computer.Id].Updates += $applicableUpdates
        }
    }

    # Combine all information
    $result = @{
        Computers = $computersData.Values
        LastReportTime = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    }

    ConvertTo-Json -InputObject $result -Depth 15 -Compress

    """
    
    # Run the script and parse the results
    output = run_powershell_script(server_ip, username, password, powershell_script)
    if output:
        try:
            wsus_data = json.loads(output)            
            # Save the data to a file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            print(f"\nWSUS data retrieved successfully at {timestamp}")
            filename = f"wsus_detailed_report.json"
            with open(filename, 'w') as f:
                json.dump(wsus_data, f, indent=2)
            print(f"\nDetailed report saved to {filename}")
            return wsus_data
        
        except json.JSONDecodeError as e:
            print(f"Error parsing WSUS data: {str(e)}")
            return None
    
    return None
