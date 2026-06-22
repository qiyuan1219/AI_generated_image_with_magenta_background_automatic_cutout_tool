@echo off
chcp 65001 > nul
setlocal

cd /d "%~dp0"
set "AUTO_MODE=%~1"

if "%AUTO_MODE%"=="" (
    echo [Error] Missing auto_cutout mode.
    echo Usage: run_auto_cutout_mode.bat item
    echo Modes: character, item, monster, aggressive, safe
    echo.
    pause
    exit /b 1
)

if not exist "auto_cutout.py" (
    echo [Error] auto_cutout.py not found.
    echo Please put this bat in the project root.
    echo.
    pause
    exit /b 1
)

if not exist "input_images" mkdir "input_images"
if not exist "output_cutouts" mkdir "output_cutouts"

where python > nul 2> nul
if %errorlevel%==0 (
    set "PYTHON_CMD=python"
) else (
    where py > nul 2> nul
    if %errorlevel%==0 (
        set "PYTHON_CMD=py -3"
    ) else (
        echo [Error] Python was not found.
        echo Install Python and enable Add Python to PATH.
        echo.
        pause
        exit /b 1
    )
)

%PYTHON_CMD% -c "import PIL, tqdm, rembg" > nul 2> nul
if errorlevel 1 (
    echo Installing dependencies: pillow tqdm rembg ...
    %PYTHON_CMD% -m pip install pillow tqdm rembg
    if errorlevel 1 (
        echo.
        echo [Error] Dependency installation failed.
        pause
        exit /b 1
    )
)

echo Mode: %AUTO_MODE%
echo Input: input_images
echo Output: output_cutouts
echo.

%PYTHON_CMD% "auto_cutout.py" "%AUTO_MODE%"
set "RUN_ERROR=%ERRORLEVEL%"

echo.
echo Done.
pause
exit /b %RUN_ERROR%
