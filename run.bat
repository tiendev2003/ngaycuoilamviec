
 @echo off
set "EXE_NAME=app.exe"
set "EXE_PATH=%~dp0%EXE_NAME%"
set "SHORTCUT_NAME=MyFlaskApp.lnk"
set "STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "SHORTCUT_PATH=%STARTUP_FOLDER%\%SHORTCUT_NAME%"

echo.
echo 📌 Tạo shortcut cho %EXE_NAME% vào thư mục Startup...
echo Target: %EXE_PATH%
echo Shortcut: %SHORTCUT_PATH%
echo.

REM Tạo shortcut bằng PowerShell
powershell -command ^
"$s = (New-Object -COM WScript.Shell).CreateShortcut('%SHORTCUT_PATH%'); ^
$s.TargetPath='%EXE_PATH%'; ^
$s.WorkingDirectory='%~dp0'; ^
$s.Save()"
echo ✅ Đã thêm vào Startup. App sẽ tự chạy khi bật máy.
pause
