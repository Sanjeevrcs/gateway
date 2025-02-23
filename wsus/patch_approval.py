from datetime import datetime
import json
from typing import List, Optional, Dict, Any
from .winrm_connector import run_powershell_script

def approve_wsus_updates_per_computers(
    server_ip: str, 
    username: str, 
    password: str, 
    kb_numbers: List[str],
    target_computers: Optional[List[str]] = None,  # List of computers
    temporary_group: str = "TempGroup",  # Temporary group for approval
    approval_action: str = 'Install'
) -> Dict[str, Any]:
    """
    Approve WSUS updates using WinRM with temporary group handling for individual computers.
    """
    
    kb_numbers_ps = ",".join(f'"{kb}"' for kb in kb_numbers)
    target_computers_ps = ",".join(f'"{computer}"' for computer in (target_computers or []))

    powershell_command = f"""
    [Reflection.Assembly]::LoadWithPartialName("Microsoft.UpdateServices.Administration") | Out-Null
    $wsus = [Microsoft.UpdateServices.Administration.AdminProxy]::GetUpdateServer("localhost", $false, 8530)

    $approvalResults = @{{
        Success = @();
        Failed = @();
    }}

    try {{
        $kbNumbers = @({kb_numbers_ps})
        $targetComputers = @({target_computers_ps})
        $tempGroupName = "{temporary_group}"

        # Create or get Temporary Group
        $existingGroup = $wsus.GetComputerTargetGroups() | Where-Object {{ $_.Name -eq $tempGroupName }}
        if (-not $existingGroup) {{
            $tempGroup = $wsus.CreateComputerTargetGroup($tempGroupName)
        }} else {{
            $tempGroup = $existingGroup
        }}

        foreach ($computerName in $targetComputers) {{
            $computer = $wsus.GetComputerTargetByName($computerName)
            if ($computer) {{
                $tempGroup.AddComputerTarget($computer)
            }} else {{
                $approvalResults['Failed'] += @{{
                    Target = $computerName;
                    Reason = "Computer not found";
                }}
                continue
            }}
        }}

        foreach ($kb in $kbNumbers) {{
            $updates = $wsus.SearchUpdates($kb)

            if ($updates.Count -eq 0) {{
                $approvalResults['Failed'] += @{{
                    KB = $kb;
                    Reason = "Update not found";
                }}
                continue
            }}

            $update = $updates[0]
            $update.Approve([Microsoft.UpdateServices.Administration.UpdateApprovalAction]::{approval_action}, $tempGroup)

            foreach ($computerName in $targetComputers) {{
                $approvalResults['Success'] += @{{
                    KB = $kb;
                    Target = $computerName;
                }}
            }}
        }}
    }} catch {{
        $approvalResults['Failed'] += @{{
            Reason = $_.Exception.Message;
        }}
    }}

    $approvalResults | ConvertTo-Json -Depth 10 -Compress
    """

    try:
        result = run_powershell_script(server_ip, username, password, powershell_command)
        if result is None:
            return {
                "Success": [],
                "Failed": [{"Reason": "PowerShell execution failed"}]
            }

        raw_output = result.strip()
        start_index = raw_output.find("{")
        end_index = raw_output.rfind("}")

        if start_index != -1 and end_index != -1:
            json_content = raw_output[start_index:end_index + 1]
            try:
                approval_results = json.loads(json_content)
                return approval_results
            except json.JSONDecodeError as e:
                print(f"Error parsing WSUS approval data: {str(e)}")
                return {
                    "Success": [],
                    "Failed": [{"Reason": f"JSON Parsing Error: {str(e)}"}]
                }
        else:
            print(f"Failed to locate JSON in output: {raw_output}")
            return {
                "Success": [],
                "Failed": [{"Reason": "JSON Parsing Error - JSON not found"}]
            }
    except Exception as e:
        print(f"Execution Error: {str(e)}")
        return {
            "Success": [],
            "Failed": [{"Reason": str(e)}]
        }



def approve_wsus_updates_per_groups(
    server_ip: str, 
    username: str, 
    password: str, 
    kb_numbers: List[str],
    target_groups: Optional[List[str]] = None,  # Optional target groups
    approval_action: str = 'Install'  # Default approval action
) -> Dict[str, Any]:
    """
    Approve WSUS updates using WinRM with flexible targeting.
    """
    # Prepare PowerShell command components
    kb_numbers_ps = ",".join(f'"{kb}"' for kb in kb_numbers)
    target_groups_ps = ",".join(f'"{group}"' for group in (target_groups or []))

    # Construct the PowerShell command
    powershell_command = f"""
    Add-Type -AssemblyName "Microsoft.UpdateServices.Administration"

    $approvalResults = @{{
        Success = @();
        Failed = @();
    }}

    try {{
        [Reflection.Assembly]::LoadWithPartialName("Microsoft.UpdateServices.Administration") | Out-Null
        $wsus = [Microsoft.UpdateServices.Administration.AdminProxy]::GetUpdateServer("localhost", $false, 8530)

        $kbNumbers = @({kb_numbers_ps})
        $targetGroups = @({target_groups_ps})

        foreach ($kb in $kbNumbers) {{
            $updates = $wsus.SearchUpdates($kb)

            if ($updates.Count -eq 0) {{
                $approvalResults['Failed'] += @{{
                    KB = $kb;
                    Reason = "Update not found";
                }}
                continue
            }}

            $update = $updates[0]

            if ($targetGroups.Count -gt 0) {{
                foreach ($groupName in $targetGroups) {{
                    $group = $wsus.GetComputerTargetGroups() | Where-Object {{ $_.Name -eq $groupName }}
                    if ($group) {{
                        $update.ApproveForOptionalInstall($group)
                        $approvalResults['Success'] += @{{
                            KB = $kb;
                            Group = $groupName;
                        }}
                    }} else {{
                        $approvalResults['Failed'] += @{{
                            KB = $kb;
                            Group = $groupName;
                            Reason = "Group not found";
                        }}
                    }}
                }}
            }} else {{
                $update.ApproveForAllComputers([Microsoft.UpdateServices.Administration.UpdateApprovalAction]::{approval_action})
                $approvalResults['Success'] += @{{
                    KB = $kb;
                    Target = "All Computers";
                }}
            }}
        }}
    }} catch {{
        $approvalResults['Failed'] += @{{
            Reason = $_.Exception.Message;
        }}
    }}

    $approvalResults | ConvertTo-Json -Depth 10 -Compress
    """

    # Execute the PowerShell command via WinRM
    try:
        raw_output = run_powershell_script(server_ip, username, password, powershell_command)

        if raw_output is None:
            return {
                "Success": [],
                "Failed": [{"Reason": "PowerShell execution failed"}]
            }

        # Parse JSON from the raw output
        start_index = raw_output.find("{")
        end_index = raw_output.rfind("}")

        if start_index != -1 and end_index != -1:
            json_content = raw_output[start_index:end_index + 1]
            try:
                approval_results = json.loads(json_content)
                return approval_results
            except json.JSONDecodeError as e:
                print(f"Error parsing WSUS approval data: {str(e)}")
                return {
                    "Success": [],
                    "Failed": [{"Reason": f"JSON Parsing Error: {str(e)}"}]
                }
        else:
            print(f"Failed to locate JSON in output: {raw_output}")
            return {
                "Success": [],
                "Failed": [{"Reason": "JSON Parsing Error - JSON not found"}]
            }

    except Exception as e:
        print(f"Execution Error: {str(e)}")
        return {
            "Success": [],
            "Failed": [{"Reason": str(e)}]
        }


def patch_approval(
    data: Dict[str, Any],
    tenant_id: str,
    gateway_id: str,
) -> Dict[str, Any]:
    """
    Approve WSUS patches based on provided parameters.
    """

    server_ip = data.get('ip_address')
    username = data.get('hostname')
    password = data.get('password')
    kb_numbers = data.get('kbArticle')
    target_groups = data.get('groups')
    target_computers = data.get('computers')
    temporary_group = 'TempGroup'
    approval_action = 'Install'

    # Validate input parameters
    if not kb_numbers:
        result = {
            "Success": [],
            "Failed": [{"Reason": "No KB numbers provided."}]
        }

    elif not target_groups and not target_computers:
        result = {
            "Success": [],
            "Failed": [{"Reason": "Neither target groups nor target computers provided."}]
        }

    # Determine whether to target computers or groups
    elif target_computers:
        print("Approving patches for specific computers...")
        result = approve_wsus_updates_per_computers(
            server_ip=server_ip,
            username=username,
            password=password,
            kb_numbers=kb_numbers,
            target_computers=target_computers,
            temporary_group=temporary_group,
            approval_action=approval_action
        )
    elif target_groups:
        print("Approving patches for specific groups...")
        result = approve_wsus_updates_per_groups(
            server_ip=server_ip,
            username=username,
            password=password,
            kb_numbers=kb_numbers,
            target_groups=target_groups,
            approval_action=approval_action
        )

    # Optionally save the report to a file (for logging or auditing purposes)
    # Save to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"./dump/wsus_approval_report_{timestamp}.json"
    with open(filename, 'w') as f:
        json.dump(result, f, indent=2)

    print(f"\nWSUS approval report saved to {filename}")

    return result


# patch_approval(
# {'ip_address': '20.184.39.130', 'hostname': 'server2019user', 'password': 'WindowsUser2019', 'computers': ['windows10.smarteis-9856.com'], 'kbArticle': ['KB5031539']}, '1'
# )