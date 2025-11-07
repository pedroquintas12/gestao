; installer/gestao_with_python.iss
#define MyAppName "Gestao"
#ifndef MyAppVersion
  #define MyAppVersion "0.0.0"
#endif
#define MyAppPublisher "Workflow"

[Setup]
AppId={{B1A4A2F7-6C3E-4B28-990C-C6A1E6B19A01}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={pf}\{#MyAppName}
DefaultGroupName={#MyAppName}
UninstallDisplayIcon={app}\gui.exe
OutputBaseFilename={#MyAppName}-Setup-{#MyAppVersion}
Compression=lzma
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64
DisableDirPage=no
DisableProgramGroupPage=yes
PrivilegesRequired=admin

; garantir fechamento de processos
RestartApplications=no
CloseApplications=force
CloseApplicationsFilter=gui.exe;launcher.exe;python.exe;pythonw.exe;Gestao.exe

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
Source: "..\config\*"; DestDir: "{app}\config"; Flags: recursesubdirs ignoreversion
Source: "..\enums\*"; DestDir: "{app}\enums"; Flags: recursesubdirs ignoreversion
Source: "..\helpers\*"; DestDir: "{app}\helpers"; Flags: recursesubdirs ignoreversion
Source: "..\routes\*"; DestDir: "{app}\routes"; Flags: recursesubdirs ignoreversion
Source: "..\service\*"; DestDir: "{app}\service"; Flags: recursesubdirs ignoreversion
Source: "..\utils\*"; DestDir: "{app}\utils"; Flags: recursesubdirs ignoreversion

; binários (com restartreplace e kill prévio)
Source: "..\dist\gui.exe";      DestDir: "{app}"; DestName: "gui.exe";      Flags: ignoreversion restartreplace; BeforeInstall: KillRunningApps

; env.example vai junto (sem segredos)
Source: "..\env.example"; DestDir: "{app}"; DestName: "env.example"; Flags: ignoreversion

; instalador offline do Python 3.12 x64
Source: ".\binaries\python-3.12.6-amd64.exe"; DestDir: "{tmp}"; DestName: "python-installer.exe"; Flags: deleteafterinstall

[Icons]
Name: "{group}\{#MyAppName}";         Filename: "{app}\gui.exe"; WorkingDir: "{app}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\gui.exe"; WorkingDir: "{app}"; Tasks: desktopicon

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

; 5a) INTERATIVO: só mostra o checkbox quando NÃO estiver em /SILENT
Filename: "{app}\gui.exe"; Description: "Iniciar Gestao (GUI)"; Flags: nowait postinstall runasoriginaluser; Check: not WizardSilent

; 5b) SILENCIOSO: em /SILENT ou /VERYSILENT, abre a GUI no final com pequeno atraso
Filename: "{cmd}"; Parameters: "/c ping -n 2 127.0.0.1 > nul & start """" ""{app}\gui.exe"""; Flags: nowait runasoriginaluser; Check: WizardSilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\venv\Lib\site-packages\pip\_vendor\distlib\__pycache__ "

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

procedure KillRunningApps;
var
  RC: Integer;
begin
  { fecha possíveis travas – não mata o próprio instalador }
  Exec(ExpandConstant('{cmd}'), '/c taskkill /IM gui.exe /F',       '', SW_HIDE, ewWaitUntilTerminated, RC);
  Exec(ExpandConstant('{cmd}'), '/c taskkill /IM launcher.exe /F',  '', SW_HIDE, ewWaitUntilTerminated, RC);
  Exec(ExpandConstant('{cmd}'), '/c taskkill /IM python.exe /F',    '', SW_HIDE, ewWaitUntilTerminated, RC);
  Exec(ExpandConstant('{cmd}'), '/c taskkill /IM pythonw.exe /F',   '', SW_HIDE, ewWaitUntilTerminated, RC);
  Exec(ExpandConstant('{cmd}'), '/c taskkill /IM Gestao.exe /F',    '', SW_HIDE, ewWaitUntilTerminated, RC);
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  AppDataDir, EnvPath, ExampleSrc, OldEnvInApp: string;
begin
  { kill redundante logo ao entrar na fase de instalação }
  if CurStep = ssInstall then
    KillRunningApps;

  { pós-instalação: migra/cria .env no AppData }
  if CurStep = ssPostInstall then
  begin
    AppDataDir := GetLocalAppData() + '\Gestao';
    EnvPath := AppDataDir + '\.env';
    ExampleSrc := ExpandConstant('{app}') + '\env.example';
    OldEnvInApp := ExpandConstant('{app}') + '\.env';

    EnsureDirExists(AppDataDir);

    if FileExists(OldEnvInApp) then
    begin
      try
        FileCopy(OldEnvInApp, EnvPath, False);
        DeleteFile(OldEnvInApp);
      except
      end;
    end;

    if (not FileExists(EnvPath)) and FileExists(ExampleSrc) then
    begin
      try
        FileCopy(ExampleSrc, EnvPath, False);
      except
      end;
    end;
  end;
end;
