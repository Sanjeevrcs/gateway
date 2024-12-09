import winrm
import json
from datetime import datetime

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

import json
from datetime import datetime

def get_wsus_detailed_info(server_ip, username, password):
    """Get comprehensive WSUS information organized by computers"""
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
            
            # Save the report to a file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"wsus_detailed_report.json"
            with open(filename, 'w') as f:
                json.dump(wsus_data, f, indent=2)
            print(f"\nDetailed report saved to {filename}")
            
            return wsus_data
        
        except json.JSONDecodeError as e:
            print(f"Error parsing WSUS data: {str(e)}")
            return None
    
    return None

# Server details
server_ip = "20.184.39.130"
username = "server2019user"
password = "SQT28102024##"

# Run the report
wsus_info = get_wsus_detailed_info(server_ip, username, password)
