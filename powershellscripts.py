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

def get_wsus_detailed_info(server_ip, username, password):
    """Get comprehensive WSUS information including detailed update information"""
    powershell_script = """
    [reflection.assembly]::LoadWithPartialName("Microsoft.UpdateServices.Administration") | Out-Null
    $wsus = [Microsoft.UpdateServices.Administration.AdminProxy]::GetUpdateServer("localhost", $false, 8530)
    
    # Function to extract KB numbers from title
    function Get-KBNumber {
        param([string]$title)
        if ($title -match "KB\d+") {
            return $matches[0]
        }
        return "N/A"
    }
    
    # Get all computers
    $computers = $wsus.GetComputerTargets() | ForEach-Object {
        $computer = $_
        
        # Get needed updates for this computer
        $neededUpdates = $computer.GetUpdateInstallationInfoPerUpdate() | 
            Where-Object { $_.UpdateInstallationState -eq 'NotInstalled' } |
            ForEach-Object {
                $update = $wsus.GetUpdate($_.UpdateId)
                [PSCustomObject]@{
                    KB = (Get-KBNumber $update.Title)
                    Title = $update.Title
                    Description = $update.Description
                    Classification = $update.UpdateClassificationTitle
                    ReleaseDate = $update.CreationDate
                    Severity = $update.MsrcSeverity
                    RebootRequired = $update.RequiresReboot
                }
            }
        
        # Get installed updates for this computer
        $installedUpdates = $computer.GetUpdateInstallationInfoPerUpdate() | 
            Where-Object { $_.UpdateInstallationState -eq 'Installed' } |
            ForEach-Object {
                $update = $wsus.GetUpdate($_.UpdateId)
                [PSCustomObject]@{
                    KB = (Get-KBNumber $update.Title)
                    Title = $update.Title
                    Classification = $update.UpdateClassificationTitle
                    InstallationDate = $_.InstallationDate
                    Severity = $update.MsrcSeverity
                }
            }
        
        [PSCustomObject]@{
            ComputerName = $computer.FullDomainName
            IPAddress = $computer.IPAddress
            LastStatusReport = $computer.LastReportedStatusTime
            LastSyncTime = $computer.LastSyncTime
            OSDescription = $computer.OSDescription
            NeededCount = $computer.GetUpdateInstallationSummary().NotInstalledCount
            InstalledCount = $computer.GetUpdateInstallationSummary().InstalledCount
            FailedCount = $computer.GetUpdateInstallationSummary().FailedCount
            NeededUpdates = @($neededUpdates)
            InstalledUpdates = @($installedUpdates)
        }
    }
    
    # Combine all information
    $result = [PSCustomObject]@{
        Computers = $computers
        LastReportTime = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    }
    
    ConvertTo-Json -InputObject $result -Depth 10 -Compress
    """
    
    # Run the script and parse the results
    output = run_powershell_script(server_ip, username, password, powershell_script)
    if output:
        try:
            wsus_data = json.loads(output)
            
            # Print summary
            print("\n=== WSUS Server Detailed Report ===")
            print(f"Report Time: {wsus_data['LastReportTime']}")
            print(f"\nComputers Found: {len(wsus_data['Computers'])}")
            
            # Print detailed computer information
            for computer in wsus_data['Computers']:
                print(f"\n{'='*50}")
                print(f"Computer: {computer['ComputerName']}")
                print(f"OS: {computer['OSDescription']}")
                print(f"IP Address: {computer['IPAddress']}")
                print(f"Updates Needed: {computer['NeededCount']}")
                print(f"Updates Installed: {computer['InstalledCount']}")
                print(f"Failed Updates: {computer['FailedCount']}")
                print(f"Last Sync: {computer['LastSyncTime']}")
                
                if computer['NeededUpdates']:
                    print("\nNeeded Updates:")
                    for update in computer['NeededUpdates']:
                        print(f"\n- KB: {update['KB']}")
                        print(f"  Title: {update['Title']}")
                        print(f"  Classification: {update['Classification']}")
                        print(f"  Severity: {update['Severity']}")
                        print(f"  Reboot Required: {update['RebootRequired']}")
                
                if computer['InstalledUpdates']:
                    print("\nRecently Installed Updates:")
                    for update in computer['InstalledUpdates'][-5:]:  # Show last 5 installed updates
                        print(f"\n- KB: {update['KB']}")
                        print(f"  Title: {update['Title']}")
                        print(f"  Classification: {update['Classification']}")
                        print(f"  Installation Date: {update['InstallationDate']}")
            
            # Save the data to a file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"wsus_detailed_report_{timestamp}.json"
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