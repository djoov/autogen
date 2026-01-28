@echo off
setlocal enabledelayedexpansion
echo ==================================================
echo      AUTO-GEN AGENT LAUNCHER (Docker)
echo ==================================================

REM 1. Ask for IP Address
echo.
echo [?] Masukkan IP LAN Laptop Anda (lihat di ipconfig)
echo     Contoh: 192.168.1.5
echo     (Tekan ENTER untuk menggunakan default: host.docker.internal)
echo.
set /p HOST_IP="> IP Host: "

REM Default value
if "%HOST_IP%"=="" set HOST_IP=host.docker.internal

echo.
echo [!] Menggunakan Host IP: %HOST_IP%
echo.

REM 2. Ask for MEMOS TOKEN (Optional)
echo [?] Masukkan Token Memos (Untuk Fitur Memory/RAG)
echo     (Kosongkan jika tidak menggunakan Memos)
echo.
set /p MEMOS_TOKEN="> Token: "

REM 3. Prepare Folder
echo [!] Output akan disimpan di folder: %cd%\coding_output
if not exist "coding_output" mkdir "coding_output"

echo.
echo [!] Menjalankan Docker...
echo.

REM 4. Run Docker with Token
docker run -it --rm ^
  --add-host=host.docker.internal:host-gateway ^
  -v "%cd%\coding_output:/app/coding_output" ^
  -e OLLAMA_BASE_URL="http://%HOST_IP%:11434/v1" ^
  -e MEMOS_BASE_URL="http://%HOST_IP%:5230" ^
  -e MEMOS_TOKEN="%MEMOS_TOKEN%" ^
  -e OLLAMA_MODEL="llama3.1:8b" ^
  ag-agent

echo.
echo [!] Container stopped.
pause
