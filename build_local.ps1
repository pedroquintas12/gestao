# build_local.ps1 — compila o gui.exe e gera o instalador
# Uso:
#   .\build_local.ps1                    # versão "0.0.0-local"
#   .\build_local.ps1 -Version "0.5.0"   # versão custom
[CmdletBinding()]
param(
  [string]$Version = "0.0.0-local"
)

$ErrorActionPreference = "Stop"

# ===== Pré-checagens =====
Write-Host "== Verificando pré-requisitos ==" -ForegroundColor Cyan

# Python 3.12
$py = Get-Command py -ErrorAction SilentlyContinue
if (-not $py) { throw "Python 'py' launcher não encontrado. Instale Python 3.12 do python.org." }

# Python offline pro instalador
$pyOffline = "installer\binaries\python-3.12.6-amd64.exe"
if (!(Test-Path $pyOffline)) {
  Write-Host ">> Faltando: $pyOffline" -ForegroundColor Yellow
  Write-Host "   Baixe Python 3.12.6 x64 em https://www.python.org/downloads/release/python-3126/" -ForegroundColor Yellow
  Write-Host "   e salve em 'installer\binaries\python-3.12.6-amd64.exe'." -ForegroundColor Yellow
  throw "Instalador offline do Python não encontrado."
}

# Inno Setup
$iscc = Get-Command iscc.exe -ErrorAction SilentlyContinue
if (-not $iscc) {
  $isccDefault = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
  if (Test-Path $isccDefault) {
    $iscc = $isccDefault
    Write-Host ">> ISCC.exe não está no PATH, usando: $iscc" -ForegroundColor Yellow
  } else {
    throw "Inno Setup 6 não encontrado. Instale de https://jrsoftware.org/isinfo.php"
  }
} else {
  $iscc = $iscc.Source
}

# ===== venv + dependências =====
Write-Host "== Preparando venv ==" -ForegroundColor Cyan
if (!(Test-Path ".venv")) { py -3.12 -m venv .venv }
. .\.venv\Scripts\Activate.ps1

python -m pip install -U pip | Out-Null
Write-Host "   Instalando requirements.txt e pyinstaller..." -ForegroundColor DarkGray
pip install -q -r requirements.txt
pip install -q pyinstaller pillow

# ===== Versão =====
Write-Host "== Gerando config\version.py com $Version ==" -ForegroundColor Cyan
"`$__version__ = `"$Version`"" | Out-Null  # placeholder pra evitar BOM
@"
__version__ = "$Version"
"@ | Out-File -FilePath .\config\version.py -Encoding UTF8

# ===== Limpa build anterior =====
Write-Host "== Limpando build/ dist/ *.spec ==" -ForegroundColor Cyan
Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue
Remove-Item -Force *.spec -ErrorAction SilentlyContinue

# ===== Build gui.exe =====
Write-Host "== Construindo gui.exe ==" -ForegroundColor Cyan
pyinstaller --onefile --noconsole --icon public\favicon.ico --name gui GUI.py
if (!(Test-Path "dist\gui.exe")) { throw "PyInstaller terminou mas dist\gui.exe não existe." }

# ===== Compila o instalador =====
Write-Host "== Compilando instalador (Inno Setup) ==" -ForegroundColor Cyan
& $iscc "/DMyAppVersion=$Version" "installer\gestao_with_python.iss"
if ($LASTEXITCODE -ne 0) { throw "ISCC retornou código $LASTEXITCODE" }

$out = Get-ChildItem -Path "installer\Output" -Filter "*.exe" -ErrorAction SilentlyContinue |
       Sort-Object LastWriteTime -Descending | Select-Object -First 1

if ($out) {
  Write-Host ""
  Write-Host "== OK ==" -ForegroundColor Green
  Write-Host "   Instalador: $($out.FullName)" -ForegroundColor Green
} else {
  Write-Host "Instalador compilado mas não encontrei .exe em installer\Output." -ForegroundColor Yellow
}
