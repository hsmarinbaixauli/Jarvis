# Registers Jarvis as a Windows scheduled task that runs at user logon.
# Uses jarvis_silent.vbs so no terminal window appears.
# Run once from the project root:
#   powershell -ExecutionPolicy Bypass -File setup_autostart.ps1

#Requires -RunAsAdministrator

$ErrorActionPreference = 'Stop'

$TaskName   = 'Jarvis'
$ProjectRoot = $PSScriptRoot
$VbsFile    = Join-Path $ProjectRoot 'jarvis_silent.vbs'

if (-not (Test-Path $VbsFile)) {
    Write-Error "jarvis_silent.vbs not found at: $VbsFile"
    exit 1
}

# --- Remove old Startup-folder shortcut if it exists ---
$StartupDir   = [System.Environment]::GetFolderPath('Startup')
$ShortcutPath = Join-Path $StartupDir 'Jarvis.lnk'
if (Test-Path $ShortcutPath) {
    Remove-Item $ShortcutPath -Force
    Write-Host "Removed old Startup folder shortcut: $ShortcutPath" -ForegroundColor Yellow
}

# --- Remove existing scheduled task with the same name ---
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Replaced existing '$TaskName' scheduled task." -ForegroundColor Yellow
}

# --- Build task components ---
$Action  = New-ScheduledTaskAction `
    -Execute  'wscript.exe' `
    -Argument "`"$VbsFile`"" `
    -WorkingDirectory $ProjectRoot

$Trigger = New-ScheduledTaskTrigger -AtLogOn

$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 0)   # no timeout

$Principal = New-ScheduledTaskPrincipal `
    -UserId    ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) `
    -LogonType Interactive `
    -RunLevel  Highest

# --- Register the task ---
Register-ScheduledTask `
    -TaskName  $TaskName `
    -Action    $Action `
    -Trigger   $Trigger `
    -Settings  $Settings `
    -Principal $Principal `
    -Force | Out-Null

Write-Host ''
Write-Host "Autostart enabled via Task Scheduler (silent, no terminal window)." -ForegroundColor Green
Write-Host "Task name : $TaskName"
Write-Host "Runs      : wscript.exe `"$VbsFile`""
Write-Host "Trigger   : At logon (highest privileges)"
Write-Host ''
Write-Host "To disable autostart:"
Write-Host "  Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false"
