@echo off
REM Build SpotiTool v1.0 executables (Windows)
setlocal
echo === SpotiTool v1.0 build ===
python -m pip install --upgrade pip || goto :error
python -m pip install -r requirements.txt pyinstaller || goto :error
echo.
echo Building executables (this takes a few minutes)...
python -m PyInstaller spotiTool.spec --noconfirm || goto :error
echo.
echo Build complete. Output is in the dist\ folder:
dir /b dist
echo.
echo Run the app:  dist\SpotiTool.exe
echo Run the CLI:  dist\spotitool-cli.exe --help
goto :eof

:error
echo.
echo BUILD FAILED - see the messages above.
exit /b 1
