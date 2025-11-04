; installer/gestao_with_python.iss
#define MyAppName "Gestao"
#ifndef MyAppVersion
  #define MyAppVersion "0.0.0"  ; default se alguém rodar local sem passar /D
#endif
#define MyAppPublisher "Sua Empresa"
#define MyAppId "{{B1A4A2F7-6C3E-4B28-990C-C6A1E6B19A01}"
...

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={pf}\{#MyAppName}
DefaultGroupName={#MyAppName}
UninstallDisplayIcon={app}\launcher.exe
OutputBaseFilename={#MyAppName}-Setup-{#MyAppVersion}
Compression=lzma
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64
DisableDirPage=no
DisableProgramGroupPage=yes
PrivilegesRequired=admin

[Languages]
Name: "portuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Files]
; --- código do app (ajuste se tiver mais pastas) ---
Source: "..\main.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\requirements.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\app\*"; DestDir: "{app}\app"; Flags: recursesubdirs ignoreversion
Source: "..\controller\*"; DestDir: "{app}\controller"; Flags: recursesubdirs ignoreversion
Source: "..\model\*"; DestDir: "{app}\model"; Flags: recursesubdirs ignoreversion
Source: "..\views\*"; DestDir: "{app}\views"; Flags: recursesubdirs ignoreversion
Source: "..\public\*"; DestDir: "{app}\public"; Flags: recursesubdirs ignoreversion

; env.example vai junto (sem segredos)
Source: "..\env.example"; DestDir: "{app}"; DestName: "env.example"; Flags: ignoreversion

; launcher.exe (gerado pelo PyInstaller em .\dist\)
Source: "..\dist\launcher.exe"; DestDir: "{app}"; DestName: "launcher.exe"; Flags: ignoreversion

; instalador offline do Python 3.12 x64
Source: ".\binaries\python-3.12.6-amd64.exe"; DestDir: "{tmp}"; DestName: "python-installer.exe"; Flags: deleteafterinstall

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\launcher.exe"; WorkingDir: "{app}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\launcher.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na Área de Trabalho"; GroupDescription: "Atalhos:"; Flags: unchecked

[Run]
; 1) Instala Python silenciosamente (offline)
Filename: "{tmp}\python-installer.exe"; Parameters: "/quiet InstallAllUsers=1 Include_pip=1 PrependPath=1"; Flags: waituntilterminated

; 2) Cria venv em {app}\venv
Filename: "{cmd}"; Parameters: "/c ""py -3.12 -m venv ""{app}\venv"""""; Flags: runhidden waituntilterminated

; 3) Atualiza pip do venv
Filename: "{app}\venv\Scripts\python.exe"; Parameters: "-m pip install --upgrade pip"; Flags: runhidden waituntilterminated

; 4) Instala dependências do projeto
Filename: "{app}\venv\Scripts\pip.exe"; Parameters: "install -r ""{app}\requirements.txt"""; Flags: runhidden waituntilterminated

; 5) Abre o app (launcher) pós-instalação
Filename: "{app}\launcher.exe"; Description: "Iniciar {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\venv\Lib\site-packages\pip\_vendor\distlib\__pycache__"

[Code]
function GetLocalAppData(): string;
begin
  Result := ExpandConstant('{localappdata}');
end;

procedure EnsureDirExists(Dir: string);
begin
  if not DirExists(Dir) then
    ForceDirectories(Dir);
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  AppDataDir, EnvPath, ExampleSrc, OldEnvInApp: string;
begin
  if CurStep = ssPostInstall then
  begin
    AppDataDir := GetLocalAppData() + '\Gestao';
    EnvPath := AppDataDir + '\.env';
    ExampleSrc := ExpandConstant('{app}') + '\env.example';
    OldEnvInApp := ExpandConstant('{app}') + '\.env';

    EnsureDirExists(AppDataDir);

    { Migra .env antigo da pasta do app para AppData (uma vez) }
    if FileExists(OldEnvInApp) then
    begin
      try
        FileCopy(OldEnvInApp, EnvPath, False);  { False = não sobrescreve se já existir }
        DeleteFile(OldEnvInApp);
      except
      end;
    end;

    { Cria .env a partir do modelo se ainda não existir no AppData }
    if (not FileExists(EnvPath)) and FileExists(ExampleSrc) then
    begin
      try
        FileCopy(ExampleSrc, EnvPath, False);
      except
      end;
    end;
  end;
end;
