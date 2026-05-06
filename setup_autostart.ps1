# Creates a Windows startup shortcut so Jarvis launches automatically at login.
# Run once from the project root:
#   powershell -ExecutionPolicy Bypass -File setup_autostart.ps1

$ErrorActionPreference = 'Stop'

$ProjectRoot  = $PSScriptRoot
$BatchFile    = Join-Path $ProjectRoot 'jarvis.bat'
$StartupDir   = [System.Environment]::GetFolderPath('Startup')
$ShortcutPath = Join-Path $StartupDir 'Jarvis.lnk'

if (-not (Test-Path $BatchFile)) {
    Write-Error "jarvis.bat not found at: $BatchFile"
    exit 1
}

$Shell    = New-Object -ComObject WScript.Shell
$Shortcut = $Shell.CreateShortcut($ShortcutPath)

$Shortcut.TargetPath       = $BatchFile
$Shortcut.WorkingDirectory = $ProjectRoot
$Shortcut.WindowStyle      = 7        # 7 = minimized
$Shortcut.Description      = 'Jarvis Voice Assistant'
$Shortcut.Save()

Write-Host ""
Write-Host "Autostart enabled." -ForegroundColor Green
Write-Host "Shortcut: $ShortcutPath"
Write-Host ""
Write-Host "Jarvis will launch automatically on the next Windows login."
Write-Host "To disable autostart, delete the shortcut:"
Write-Host "  Remove-Item '$ShortcutPath'"
