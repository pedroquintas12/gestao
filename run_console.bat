[Code]
procedure CreateConsoleBat;
var
  S: string;
begin
  S :=
    '@echo off' + #13#10 +
    'cd /d "%~dp0"' + #13#10 +
    'call "%~dp0venv\Scripts\activate.bat"' + #13#10 +
    'python "%~dp0main.py"' + #13#10 +
    'echo.' + #13#10 +
    'echo (Pressione qualquer tecla para fechar este terminal...)' + #13#10 +
    'pause';
  SaveStringToFile(ExpandConstant('{app}\run_console.bat'), S, False);
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  AppDataDir, EnvPath, ExampleSrc, OldEnvInApp: string;
begin
  if CurStep = ssPostInstall then
  begin
    // (seu código que já existe)
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

    // *** cria o BAT de console ***
    CreateConsoleBat;
  end;
end;
