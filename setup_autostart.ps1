# Creates a Windows startup shortcut so Jarvis launches automatically at login.
# Uses jarvis_silent.vbs so no terminal window appears.
# Run once from the project root:
#   powershell -ExecutionPolicy Bypass -File setup_autostart.ps1

$ErrorActionPreference = 'Stop'

$ProjectRoot  = $PSScriptRoot
$VbsFile      = Join-Path $ProjectRoot 'jarvis_silent.vbs'
$StartupDir   = [System.Environment]::GetFolderPath('Startup')
$ShortcutPath = Join-Path $StartupDir 'Jarvis.lnk'

if (-not (Test-Path $VbsFile)) {
    Write-Error "jarvis_silent.vbs not found at: $VbsFile"
    exit 1
}

$Shell    = New-Object -ComObject WScript.Shell
$Shortcut = $Shell.CreateShortcut($ShortcutPath)

$Shortcut.TargetPath       = 'wscript.exe'
$Shortcut.Arguments        = """$VbsFile"""
$Shortcut.WorkingDirectory = $ProjectRoot
$Shortcut.WindowStyle      = 1
$Shortcut.Description      = 'Jarvis Voice Assistant'
$Shortcut.Save()

Write-Host ""
Write-Host "Autostart enabled (silent, no terminal window)." -ForegroundColor Green
Write-Host "Shortcut: $ShortcutPath"
Write-Host ""
Write-Host "Jarvis will launch silently on the next Windows login."
Write-Host "To disable autostart, delete the shortcut:"
Write-Host "  Remove-Item '$ShortcutPath'"
