from datetime import datetime
from producer import produce_event
import json
import winrm
from typing import List, Optional, Dict, Any'[=]
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



def approve_updates(computer):
    pass

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


def generate_wsus_approval_script(
    kb_numbers: List[str], 
    target_groups: Optional[List[str]] = None, 
    target_computers: Optional[List[str]] = None,
    approval_action: str = 'Install'
) -> str:
    """
    Generate a PowerShell script for WSUS update approvals
    
    :param kb_numbers: List of KB numbers to approve
    :param target_groups: Optional list of computer groups
    :param target_computers: Optional list of computer names
    :param approval_action: Approval action type
    :return: Formatted PowerShell script
    """
    powershell_script = f"""
    [reflection.assembly]::LoadWithPartialName("Microsoft.UpdateServices.Administration") | Out-Null
    $wsus = [Microsoft.UpdateServices.Administration.AdminProxy]::GetUpdateServer("localhost", $false, 8530)

    # Prepare KB numbers
    $kbNumbers = {json.dumps(kb_numbers)}

    # Prepare target groups if provided
    $targetGroups = {json.dumps(target_groups or [])}

    # Prepare target computers if provided
    $targetComputers = {json.dumps(target_computers or [])}

    # Results tracking
    $approvalResults = @{{
        Successful = @()
        Failed = @()
        Skipped = @()
    }}

    # Get updates matching KB numbers
    foreach ($kb in $kbNumbers) {{
        $updates = $wsus.GetUpdates() | Where-Object {{ 
            $_.Title -match "KB$kb" 
        }}

        if ($updates.Count -eq 0) {{
            $approvalResults['Skipped'] += @{{
                KB = $kb
                Reason = "No matching update found"
            }}
            continue
        }}

        foreach ($update in $updates) {{
            try {{
                # If target groups are specified
                if ($targetGroups.Count -gt 0) {{
                    foreach ($groupName in $targetGroups) {{
                        $group = $wsus.GetComputerTargetGroups() | Where-Object {{ $_.Name -eq $groupName }}
                        if ($group) {{
                            $update.ApproveForGroup($group, [Microsoft.UpdateServices.Administration.UpdateApprovalAction]::{approval_action})
                            $approvalResults['Successful'] += @{{
                                KB = $kb
                                Group = $groupName
                                Action = "{approval_action}"
                            }}
                        }} else {{
                            $approvalResults['Failed'] += @{{
                                KB = $kb
                                Group = $groupName
                                Reason = "Group not found"
                            }}
                        }}
                    }}
                }}

                # If target computers are specified
                if ($targetComputers.Count -gt 0) {{
                    foreach ($computerName in $targetComputers) {{
                        $computer = $wsus.GetComputerTargets() | Where-Object {{ $_.FullDomainName -eq $computerName }}
                        if ($computer) {{
                            $update.ApproveForComputer($computer, [Microsoft.UpdateServices.Administration.UpdateApprovalAction]::{approval_action})
                            $approvalResults['Successful'] += @{{
                                KB = $kb
                                Computer = $computerName
                                Action = "{approval_action}"
                            }}
                        }} else {{
                            $approvalResults['Failed'] += @{{
                                KB = $kb
                                Computer = $computerName
                                Reason = "Computer not found"
                            }}
                        }}
                    }}
                }}

                # If no specific targets, approve for all computers
                if ($targetGroups.Count -eq 0 -and $targetComputers.Count -eq 0) {{
                    $update.ApproveForAllComputers([Microsoft.UpdateServices.Administration.UpdateApprovalAction]::{approval_action})
                    $approvalResults['Successful'] += @{{
                        KB = $kb
                        Target = "All Computers"
                        Action = "{approval_action}"
                    }}
                }}
            }}
            catch {{
                $approvalResults['Failed'] += @{{
                    KB = $kb
                    Reason = $_.Exception.Message
                }}
            }}
        }}
    }}

    ConvertTo-Json -InputObject $approvalResults -Depth 10 -Compress
    """
    return powershell_script

def approve_wsus_updates(
    server_ip: str, 
    username: str, 
    password: str, 
    kb_numbers: List[str],\
    target_groups: Optional[List[str]] = None, 
    target_computers: Optional[List[str]] = None,
    approval_action: str = 'Install'
) -> Dict[str, Any]:
    """
    Approve WSUS updates with flexible targeting
    
    :param server_ip: IP address of the WSUS server
    :param username: Username for authentication
    :param password: Password for authentication
    :param kb_numbers: List of KB numbers to approve
    :param target_groups: Optional list of computer groups
    :param target_computers: Optional list of computer names
    :param approval_action: Approval action type
    :return: Dictionary with approval results
    """
    # Generate the PowerShell script
    powershell_script = generate_wsus_approval_script(
        kb_numbers, 
        target_groups, 
        target_computers, 
        approval_action
    )
    
    # Run the script and parse results
    output = run_powershell_script(server_ip, username, password, powershell_script)
    
    if output:
        try:
            return json.loads(output)
        except json.JSONDecodeError as e:
            print(f"Error parsing approval results: {str(e)}")
            return {}
    
    return {}