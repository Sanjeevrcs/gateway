from datetime import datetime
import json
from datetime import datetime
import json
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from datetime import datetime
from .utils import get_update_state_description, int_to_ip_address, parse_wsus_date
from .winrm_connector import run_powershell_script
from producer import produce_event



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
    try:
        # Run the script and parse the results
        output = run_powershell_script(server_ip, username, password, powershell_script)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result = None
        if output:
            try:
                wsus_data = json.loads(output)
                # Save the data to a file
                print(f"\nWSUS data retrieved successfully at {timestamp}")
                result = wsus_data

            except json.JSONDecodeError as e:
                result = f"Error occured while parsing returned data from WSUS server: {str(e)}"

        else:
            result = f"No output from WSUS server. Output: {output}"

        filename = f"./dump/wsus_detailed_report_{timestamp}.json"
        with open(filename, "w") as f:
            json.dump(result, f, indent=2)
        print(f"\nDetailed report saved to {filename}")
        return result
    except Exception as e:
        return f"Error occured while retrieving data from WSUS server: {e}"


def pull_data(data, tenant_id, gateway_id):
    # Run the report
    ip_address = data['ip_address']
    hostname = data['hostname']
    password = data['password']
    wsus_info = get_wsus_detailed_info(ip_address, hostname, password)

    # Produce the event
    if wsus_info and isinstance(wsus_info, dict):
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
            data = json.dumps(
                {
                    "task": "pull_data",
                    "data": computer_data,
                    "tenant_id": tenant_id,
                    "gateway_id": gateway_id
                }
            )
            produce_event(data)

    else:
        print(f"Error occured while retrieving data from WSUS server: {wsus_info}")
        data = json.dumps(
            {
                "task": "pull_data",
                "error": wsus_info,
                "tenant_id": tenant_id,
                "gateway_id": gateway_id
            })
        produce_event(data)


# data = {
#     "ip_address": "20.184.39.130",
#     "hostname": "server2019user",
#     "password": "WindowsUser2019",
# }
# pull_data(data, 3, 1)