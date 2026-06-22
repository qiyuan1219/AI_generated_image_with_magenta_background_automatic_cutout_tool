@echo off
chcp 65001 > nul
setlocal

cd /d "%~dp0"

echo ========================================
echo 洋红背景自动抠图 - 保留原画布快速启动
echo ========================================
echo.

if not exist "magenta_preserve_canvas.py" (
    echo [错误] 当前文件夹找不到 magenta_preserve_canvas.py
    echo 请把本 bat 和 magenta_preserve_canvas.py 放在同一个文件夹。
    echo.
    pause
    exit /b 1
)

if not exist "input_images" (
    mkdir "input_images"
)

if not exist "output_cutouts" (
    mkdir "output_cutouts"
)

where python > nul 2> nul
if %errorlevel%==0 (
    set "PYTHON_CMD=python"
) else (
    where py > nul 2> nul
    if %errorlevel%==0 (
        set "PYTHON_CMD=py -3"
    ) else (
        echo [错误] 没有找到 Python。
        echo 请先安装 Python，并勾选 Add Python to PATH。
        echo.
        pause
        exit /b 1
    )
)

echo 使用 Python 命令：%PYTHON_CMD%
echo.

%PYTHON_CMD% -c "import PIL, tqdm" > nul 2> nul
if errorlevel 1 (
    echo 首次运行：正在安装依赖 pillow tqdm ...
    %PYTHON_CMD% -m pip install pillow tqdm
    if errorlevel 1 (
        echo.
        echo [错误] 依赖安装失败，请检查网络或 Python/pip 环境。
        pause
        exit /b 1
    )
    echo.
)

echo 请把需要处理的图片放入 input_images 文件夹。
echo 输出结果会保存到 output_cutouts 文件夹。
echo.

%PYTHON_CMD% "magenta_preserve_canvas.py"

echo.
echo ========================================
echo 处理结束。
echo ========================================
pause
