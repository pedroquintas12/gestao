@echo off
chcp 65001 >nul
pushd "%~dp0"

REM 1) Atualiza código (se for um repositório git)
if exist ".git" (
  echo [git] puxando atualizacoes...
  git pull
) else (
  echo [git] pasta nao eh repo; pulando git pull.
)

REM 2) Atualiza dependencias
if exist "requirements.txt" (
  echo [pip] instalando/atualizando requirements...
  pip install -r requirements.txt
) else (
  echo [pip] requirements.txt nao encontrado; pulando.
)

REM 3) Sobe a aplicacao
echo [python] iniciando main.py...
python main.py

echo.
echo [fim] Aplicacao finalizada. Pressione uma tecla para sair.
pause >nul
popd
