import winrm
import json
from datetime import datetime

def run_powershell_script(server_ip, username, password, powershell_script):
    """Execute PowerShell script on remote WSUS server"""
    try:
        # Create a WinRM session using HTTP
        session = winrm.Session(
            f'http://{server_ip}:5985/wsman',
            auth=(username, password),
            transport="ntlm",
        )
        
        # Run the PowerShell command
        result = session.run_ps(powershell_script)
        
        # Check for errors
        if result.status_code != 0:
            print(f"Error executing script: {result.std_err.decode()}")
            return None
        
        # Return the output
        return result.std_out.decode()
    
    except Exception as e:
        print(f"Connection error: {str(e)}")
        return None

def get_wsus_info(server_ip, username, password):
    """Get comprehensive WSUS information including computers and updates"""
    powershell_script = """
    [reflection.assembly]::LoadWithPartialName("Microsoft.UpdateServices.Administration") | Out-Null
    $wsus = [Microsoft.UpdateServices.Administration.AdminProxy]::GetUpdateServer("localhost", $false, 8530)
    
    # Get all computers
    $computers = $wsus.GetComputerTargets() | Select-Object -First 100 | ForEach-Object {
        [PSCustomObject]@{
            ComputerName = $_.FullDomainName
            IPAddress = $_.IPAddress
            LastStatusReport = $_.LastReportedStatusTime
            LastSyncTime = $_.LastSyncTime
            NeededCount = $_.GetUpdateInstallationSummary().NotInstalledCount
            InstalledCount = $_.GetUpdateInstallationSummary().InstalledCount
            FailedCount = $_.GetUpdateInstallationSummary().FailedCount
        }
    }
    
    # Get updates that need to be installed (approved but not installed)
    $neededUpdates = $wsus.GetUpdates() | Where-Object { 
        $_.IsApproved -eq $true -and $_.IsInstalled -eq $false 
    } | Select-Object -First 100 | ForEach-Object {
        [PSCustomObject]@{
            UpdateID = $_.Id.UpdateId.Guid
            Title = $_.Title
            Description = $_.Description
            Classification = $_.UpdateClassificationTitle
            ReleaseDate = $_.CreationDate
            ApprovalState = $_.ApprovalAction
        }
    }
    
    # Get recently installed updates
    $installedUpdates = $wsus.GetUpdates() | Where-Object { 
        $_.IsInstalled -eq $true 
    } | Select-Object -First 100 | ForEach-Object {
        [PSCustomObject]@{
            UpdateID = $_.Id.UpdateId.Guid
            Title = $_.Title
            Classification = $_.UpdateClassificationTitle
            InstallationState = "Installed"
        }
    }
    
    # Combine all information
    $result = [PSCustomObject]@{
        Computers = $computers
        NeededUpdates = $neededUpdates
        InstalledUpdates = $installedUpdates
        LastReportTime = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    }
    
    ConvertTo-Json -InputObject $result -Depth 10
    """
    
    # Run the script and parse the results
    output = run_powershell_script(server_ip, username, password, powershell_script)
    if output:
        try:
            wsus_data = json.loads(output)
            
            # Print summary
            print("\n=== WSUS Server Report ===")
            print(f"Report Time: {wsus_data['LastReportTime']}")
            print(f"\nComputers Found: {len(wsus_data['Computers'])}")
            print(f"Updates Needed: {len(wsus_data['NeededUpdates'])}")
            print(f"Updates Installed: {len(wsus_data['InstalledUpdates'])}")
            
            # Print detailed computer information
            print("\n=== Computer Status ===")
            for computer in wsus_data['Computers']:
                print(f"\nComputer: {computer['ComputerName']}")
                print(f"IP Address: {computer['IPAddress']}")
                print(f"Updates Needed: {computer['NeededCount']}")
                print(f"Updates Installed: {computer['InstalledCount']}")
                print(f"Failed Updates: {computer['FailedCount']}")
                print(f"Last Sync: {computer['LastSyncTime']}")
            
            # Save the data to a file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"wsus_report_{timestamp}.json"
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
wsus_info = get_wsus_info(server_ip, username, password)