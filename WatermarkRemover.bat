@echo off
chcp 65001 >nul

:main_menu
cls
echo ====================================================================
echo             Watermark Remover Portable (PyQt6)
echo ====================================================================
echo 1. Start GUI (remove watermarks from video/images)
echo 2. Install / Re-install Watermark Remover
echo 3. Update Watermark Remover
echo ====================================================================
echo By NeiroVlad, 2026
echo ====================================================================
set /p choice=Choose action 1-3:
if "%choice%"=="1" goto start_gui
if "%choice%"=="2" goto install_wr
if "%choice%"=="3" goto update_wr
echo Wrong choice. Please, try again.
pause
goto main_menu

:start_gui
setlocal
set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
set "VENV=%ROOT%\.venv"
set "MODELS=%ROOT%\models"
set "FFMPEG_DIR=%ROOT%\ffmpeg"
set "CACHE=%ROOT%\cache"
set "ASSETS=%ROOT%\assets"

:: UV local cache + copy mode for portability
set "UV_CACHE_DIR=%CACHE%\uv"
set "UV_LINK_MODE=copy"

echo [INFO] Starting Watermark Remover GUI...
echo [INFO] Models folder: %MODELS%
echo [INFO] Assets folder: %ASSETS%
echo [INFO] UV cache: %UV_CACHE_DIR%

set "PATH=%VENV%\Scripts;%VENV%\Library\bin;%FFMPEG_DIR%\bin;%PATH%"

REM Check PyQt6
"%VENV%\python.exe" -c "import PyQt6" 2>nul || (
    echo [WARN] PyQt6 not found. Installing...
    uv pip install PyQt6 --python "%VENV%\python.exe"
)

start /wait "" "%VENV%\python.exe" "%ROOT%\src\main.py"

echo [INFO] GUI closed.
pause
endlocal
goto main_menu

:install_wr
cls
echo [STEP] Starting installation...

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
set "TOOLS=%ROOT%\tools"
set "CONDA_DIR=%TOOLS%\miniconda"
set "VENV=%ROOT%\.venv"
set "CACHE=%ROOT%\cache"
set "MODELS=%ROOT%\models"
set "FFMPEG_DIR=%ROOT%\ffmpeg"
set "ASSETS=%ROOT%\assets"

:: UV local cache + copy mode for portability
set "UV_CACHE_DIR=%CACHE%\uv"
set "UV_LINK_MODE=copy"

set "MINICONDA_EXE=%TOOLS%\miniconda.exe"
set "UV_EXE=%TOOLS%\uv.exe"

set "CONDA_URL=https://repo.anaconda.com/miniconda/Miniconda3-py310_24.9.2-0-Windows-x86_64.exe"
set "UV_URL=https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-pc-windows-msvc.zip"

echo Root: %ROOT%
echo Tools: %TOOLS%
echo Cache: %CACHE%
echo UV cache: %UV_CACHE_DIR%

if exist "%VENV%\python.exe" (
    echo Found existing installation.
    choice /C YN /M "Re-install? (will delete old env and cache)"
    if errorlevel 2 goto main_menu
    echo Deleting old installation...
    if exist "%VENV%" rmdir /s /q "%VENV%" 2>nul
    if exist "%CACHE%" rmdir /s /q "%CACHE%" 2>nul
    if exist "%TOOLS%" rmdir /s /q "%TOOLS%" 2>nul
    if exist "%FFMPEG_DIR%" rmdir /s /q "%FFMPEG_DIR%" 2>nul
    if exist "%ASSETS%" rmdir /s /q "%ASSETS%" 2>nul
    echo Old folders deleted.
)

echo [STEP] Creating folders...
if not exist "%TOOLS%" mkdir "%TOOLS%"
if not exist "%CACHE%" mkdir "%CACHE%"
if not exist "%CACHE%\uv" mkdir "%CACHE%\uv"
if not exist "%MODELS%" mkdir "%MODELS%"
if not exist "%ASSETS%" mkdir "%ASSETS%"
if not exist "%ROOT%\src" mkdir "%ROOT%\src"

echo [STEP] Checking Miniconda...
if exist "%CONDA_DIR%\Scripts\conda.exe" goto conda_present
echo Downloading Miniconda...
powershell -NoProfile -NonInteractive -Command "Invoke-WebRequest -Uri '%CONDA_URL%' -OutFile '%MINICONDA_EXE%'"
start /wait "" "%MINICONDA_EXE%" /S /D=%CONDA_DIR%
del "%MINICONDA_EXE%" >nul 2>&1
:conda_present
echo Conda ready.

echo [STEP] Checking UV...
if exist "%UV_EXE%" goto uv_present
echo Downloading UV...
powershell -NoProfile -NonInteractive -Command "Invoke-WebRequest -Uri '%UV_URL%' -OutFile '%TOOLS%\uv.zip'"
powershell -NoProfile -NonInteractive -Command "Expand-Archive -Path '%TOOLS%\uv.zip' -DestinationPath '%TOOLS%' -Force"
del "%TOOLS%\uv.zip" >nul 2>&1
:uv_present
echo UV ready.

echo [STEP] Checking or Installing FFmpeg...

if not exist "%FFMPEG_DIR%\bin\ffmpeg.exe" (
    echo FFmpeg not found locally. Checking system...

    where ffmpeg >nul 2>&1
    if errorlevel 1 (
        echo Installing FFmpeg via Windows Package Manager...
        winget install --id Gyan.FFmpeg --silent --accept-source-agreements --accept-package-agreements
    )

    if not exist "%FFMPEG_DIR%\bin" mkdir "%FFMPEG_DIR%\bin"

    powershell -NoProfile -NonInteractive -Command "$sysPath = (Get-Command ffmpeg.exe -ErrorAction SilentlyContinue).Source; if ($sysPath) { $sysDir = Split-Path $sysPath; Copy-Item -Path \"$sysDir\*\" -Destination '%FFMPEG_DIR%\bin' -Force; echo 'FFmpeg copied to AI environment.' } else { echo '[ERROR] Failed to copy FFmpeg files!' }"

) else (
    echo ffmpeg already exists.
)

set "OLD_PATH=%PATH%"
set "PATH=%CONDA_DIR%\Scripts;%CONDA_DIR%;%TOOLS%;%FFMPEG_DIR%\bin;%PATH%"

echo [STEP] Creating conda environment...
if exist "%VENV%\python.exe" goto env_present
"%CONDA_DIR%\Scripts\conda.exe" create -p "%VENV%" python=3.10 -y --quiet
:env_present

echo [STEP] Detecting GPU...
set "HAS_GPU=0"
if exist "%SystemRoot%\System32\nvidia-smi.exe" set "HAS_GPU=1"
if exist "%ProgramFiles%\NVIDIA Corporation\NVSMI\nvidia-smi.exe" set "HAS_GPU=1"

call "%CONDA_DIR%\Scripts\activate.bat" "%VENV%"

echo [STEP] Installing PyTorch 2.4.1 (compatible with NumPy 2.x)...
if "%HAS_GPU%"=="1" (
    echo [INFO] Installing torch 2.4.1+cu121 for NVIDIA GPU...
    uv pip install --force-reinstall torch==2.4.1 torchvision==0.19.1 --index-url https://download.pytorch.org/whl/cu121 --python "%VENV%\python.exe"
) else (
    echo [INFO] Installing CPU torch 2.4.1...
    uv pip install --force-reinstall torch==2.4.1 torchvision==0.19.1 --index-url https://download.pytorch.org/whl/cpu --python "%VENV%\python.exe"
)

echo [STEP] Installing dependencies...
uv pip install opencv-python pillow tqdm --python "%VENV%\python.exe"

echo [STEP] Installing PyQt6 (UI framework)...
uv pip install PyQt6 PyQt6-Qt6 --python "%VENV%\python.exe"

echo [STEP] Installing SimpleLama...
uv pip install simple-lama-inpainting --no-deps --python "%VENV%\python.exe"

echo [STEP] Downloading LaMa model...
set "LAMA_PT=%MODELS%\big-lama.pt"
if not exist "%LAMA_PT%" (
    echo [INFO] Downloading big-lama.pt...
    powershell -NoProfile -NonInteractive -Command "Invoke-WebRequest -Uri 'https://github.com/enesmsahin/simple-lama-inpainting/releases/download/v0.1.0/big-lama.pt' -OutFile '%LAMA_PT%'"
    echo [INFO] Model saved to %LAMA_PT%
) else (
    echo [INFO] Model already exists: %LAMA_PT%
)

echo [INFO] Models folder: %MODELS%
echo [INFO] Assets folder: %ASSETS%
echo [INFO] ffmpeg: %FFMPEG_DIR%\bin
echo [INFO] UV cache: %UV_CACHE_DIR%

set "PATH=%OLD_PATH%"

echo.
echo ============================================================
echo [INFO] Installation finished!
echo ============================================================
echo.
echo IMPORTANT: Create these files manually in %ROOT%\src\:
echo   - main.py
echo   - inpainter.py
echo.
pause
goto main_menu

:update_wr
cls
echo [STEP] Updating...

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
set "TOOLS=%ROOT%\tools"
set "CONDA_DIR=%TOOLS%\miniconda"
set "VENV=%ROOT%\.venv"
set "CACHE=%ROOT%\cache"
set "FFMPEG_DIR=%ROOT%\ffmpeg"
set "ASSETS=%ROOT%\assets"

:: UV local cache + copy mode for portability
set "UV_CACHE_DIR=%CACHE%\uv"
set "UV_LINK_MODE=copy"

set "PATH=%CONDA_DIR%\Scripts;%CONDA_DIR%;%TOOLS%;%FFMPEG_DIR%\bin;%PATH%"

if not exist "%VENV%\python.exe" (
    echo Installation not found. Installing now...
    goto install_wr
)

set "HAS_GPU=0"
if exist "%SystemRoot%\System32\nvidia-smi.exe" set "HAS_GPU=1"
if exist "%ProgramFiles%\NVIDIA Corporation\NVSMI\nvidia-smi.exe" set "HAS_GPU=1"

call "%CONDA_DIR%\Scripts\activate.bat" "%VENV%"

if "%HAS_GPU%"=="1" (
    echo [INFO] Re-installing PyTorch 2.4.1+cu121...
    uv pip install --force-reinstall torch==2.4.1 torchvision==0.19.1 --index-url https://download.pytorch.org/whl/cu121 --python "%VENV%\python.exe"
) else (
    echo [INFO] Re-installing PyTorch CPU 2.4.1...
    uv pip install --force-reinstall torch==2.4.1 torchvision==0.19.1 --index-url https://download.pytorch.org/whl/cpu --python "%VENV%\python.exe"
)

echo [INFO] Updating dependencies...
uv pip install --upgrade opencv-python pillow tqdm --python "%VENV%\python.exe"

echo [INFO] Updating PyQt6...
uv pip install --upgrade PyQt6 PyQt6-Qt6 --python "%VENV%\python.exe"

echo [INFO] Updating SimpleLama...
uv pip install --upgrade simple-lama-inpainting --no-deps --python "%VENV%\python.exe"

echo [STEP] Checking ffmpeg...
if not exist "%FFMPEG_DIR%\bin\ffmpeg.exe" (
    echo [INFO] FFmpeg not found locally. Checking system...

    where ffmpeg >nul 2>&1
    if errorlevel 1 (
        echo [INFO] Installing FFmpeg via Windows Package Manager...
        winget install --id Gyan.FFmpeg --silent --accept-source-agreements --accept-package-agreements
    )

    if not exist "%FFMPEG_DIR%\bin" mkdir "%FFMPEG_DIR%\bin"

    powershell -NoProfile -NonInteractive -Command "$sysPath = (Get-Command ffmpeg.exe -ErrorAction SilentlyContinue).Source; if ($sysPath) { $sysDir = Split-Path $sysPath; Copy-Item -Path \"$sysDir\*\" -Destination '%FFMPEG_DIR%\bin' -Force; echo 'ffmpeg downloaded.' } else { echo '[ERROR] Failed to copy FFmpeg files!' }"
) else (
    echo ffmpeg already exists.
)

echo [INFO] Update finished.
echo [INFO] UV cache: %UV_CACHE_DIR%
pause
goto main_menu