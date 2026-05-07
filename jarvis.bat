@echo off
cd /d "%~dp0"
for /d /r src\ %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
python -m src.main
exit /b 0
