# Build SpotiTool v1.0 executables (Windows PowerShell)
# Usage:  .\build.ps1
$ErrorActionPreference = "Stop"

Write-Host "=== SpotiTool v1.0 build ===" -ForegroundColor Cyan

python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller

Write-Host "`nBuilding executables (this takes a few minutes)..." -ForegroundColor Yellow
python -m PyInstaller spotiTool.spec --noconfirm

Write-Host "`nBuild complete. Output:" -ForegroundColor Green
Get-ChildItem dist | Select-Object Name, @{Name="SizeMB";Expression={[math]::Round($_.Length/1MB,1)}} | Format-Table -AutoSize
Write-Host "Run the app:      .\dist\SpotiTool.exe"
Write-Host "Run the CLI:      .\dist\spotitool-cli.exe --help"
