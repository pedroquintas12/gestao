@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul

REM ================== Caminhos & variáveis ==================
set "APP_NAME=Gestao"
set "APP_DIR=%~dp0"
set "LOG_DIR=%LOCALAPPDATA%\%APP_NAME%\logs"
set "APP_LOG=%LOG_DIR%\app_console.log"
set "ENV_APPDATA=%LOCALAPPDATA%\%APP_NAME%\.env"
set "ENV_LOCAL=%APP_DIR%\.env"

REM Força UTF-8 e modo debug (seu logger no Python pode usar isso)
set "PYTHONUTF8=1"
set "GESTAO_DEBUG=1"

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%" >nul 2>&1

echo ==== %date% %time% ==== >> "%APP_LOG%"
echo [start] APP_DIR="%APP_DIR%" >> "%APP_LOG%"

REM ================== Migrar .env para AppData (uma vez) ==================
if exist "%ENV_LOCAL%" (
  if not exist "%ENV_APPDATA%" (
    echo [env] migrando ".env" para "%ENV_APPDATA%" >> "%APP_LOG%"
    if not exist "%LOCALAPPDATA%\%APP_NAME%" mkdir "%LOCALAPPDATA%\%APP_NAME%" >nul 2>&1
    copy /Y "%ENV_LOCAL%" "%ENV_APPDATA%" >nul 2>&1
  )
)

REM ================== Escolher Python (venv > sistema) ==================
set "PYEXE="
if exist "%APP_DIR%.venv\Scripts\python.exe" set "PYEXE=%APP_DIR%.venv\Scripts\python.exe"
if not defined PYEXE if exist "%APP_DIR%venv\Scripts\python.exe" set "PYEXE=%APP_DIR%venv\Scripts\python.exe"
if not defined PYEXE set "PYEXE=python"

echo [python] usando "%PYEXE%" >> "%APP_LOG%"

REM ================== Atualizar código (git pull se repo) ==================
pushd "%APP_DIR%"
if exist ".git" (
  echo [git] puxando atualizacoes... >> "%APP_LOG%"
  git pull >> "%APP_LOG%" 2>&1
) else (
  echo [git] nao eh repo git; pulando git pull. >> "%APP_LOG%"
)

REM ================== Atualizar pip e requirements ==================
echo [pip] atualizando pip... >> "%APP_LOG%"
"%PYEXE%" -m pip install -U pip >> "%APP_LOG%" 2>&1

if exist "requirements.txt" (
  echo [pip] instalando requirements... >> "%APP_LOG%"
  "%PYEXE%" -m pip install -r requirements.txt >> "%APP_LOG%" 2>&1
) else (
  echo [pip] requirements.txt nao encontrado; pulando. >> "%APP_LOG%"
)

REM ================== Iniciar aplicacao ==================
echo [run] iniciando main.py (logs em %APP_LOG%) >> "%APP_LOG%"
echo [run] ==============================================

REM -u = sem buffer; redireciona stdout+stderr para o arquivo de log
"%PYEXE%" -u "%APP_DIR%main.py" >> "%APP_LOG%" 2>&1

set "ERRLVL=%ERRORLEVEL%"
echo [end] codigo_saida=%ERRLVL% >> "%APP_LOG%"
echo.
echo ===============================================
echo  FIM. Código de saída: %ERRLVL%
echo  Veja os logs em:
echo     %APP_LOG%
echo ===============================================
pause

popd
endlocal
