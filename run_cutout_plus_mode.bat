@echo off
chcp 65001 > nul
setlocal

cd /d "%~dp0"
set "CUTOUT_MODE=%~1"

if "%CUTOUT_MODE%"=="" (
    echo [Error] Missing cutout_plus mode.
    echo Usage: run_cutout_plus_mode.bat chroma_magenta
    echo Modes: chroma_magenta, chroma_green, black_bg_safe
    echo.
    pause
    exit /b 1
)

if not exist "cutout_plus.py" (
    echo [Error] cutout_plus.py not found.
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

%PYTHON_CMD% -c "import PIL, tqdm" > nul 2> nul
if errorlevel 1 (
    echo Installing dependencies: pillow tqdm ...
    %PYTHON_CMD% -m pip install pillow tqdm
    if errorlevel 1 (
        echo.
        echo [Error] Dependency installation failed.
        pause
        exit /b 1
    )
)

echo Mode: %CUTOUT_MODE%
echo Input: input_images
echo Output: output_cutouts
echo.

%PYTHON_CMD% "cutout_plus.py" "%CUTOUT_MODE%"
set "RUN_ERROR=%ERRORLEVEL%"

echo.
echo Done.
pause
exit /b %RUN_ERROR%
