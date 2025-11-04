# build_local.ps1 — compila o launcher e gera o instalador
$ErrorActionPreference = "Stop"
Write-Host "== Preparando ambiente ==" -ForegroundColor Cyan

if (!(Test-Path ".venv")) { py -3.12 -m venv .venv }
.\.venv\Scripts\Activate.ps1

python -m pip install -U pip
pip install pyinstaller

Write-Host "== Construindo launcher ==" -ForegroundColor Cyan
pyinstaller -y --onefile --noconsole --icon public\favicon.ico --name launcher update\launcher.py

$pyOffline = "installer\binaries\python-3.12.6-amd64.exe"
if (!(Test-Path $pyOffline)) {
  Write-Host ">> Faltando $pyOffline" -ForegroundColor Yellow
  Write-Host "Baixe o Python 3.12.6 x64 do site oficial e salve com esse nome/pasta." -ForegroundColor Yellow
  throw "Python offline installer não encontrado"
}

Write-Host "== Gerando instalador (Inno Setup) ==" -ForegroundColor Cyan
try {
  iscc.exe installer\gestao_with_python.iss
  Write-Host "Instalador gerado com sucesso (pasta Output/ ou na mesma pasta do .iss)." -ForegroundColor Green
} catch {
  Write-Host "ISCC não encontrado no PATH. Abrindo o Inno Setup GUI..." -ForegroundColor Yellow
  & "C:\Program Files (x86)\Inno Setup 6\Compil32.exe" "installer\gestao_with_python.iss"
  Write-Host "No Inno Setup, pressione F9 para compilar." -ForegroundColor Yellow
}
