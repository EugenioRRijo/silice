; Sílice: instalador de Windows (spec S5 §7.3; RF-97). No se compila a mano: lo hace
; construir.py con ISCC.exe /DVersion=<SemVer> [/DCompleto] /DOrg=<build\app>
;   /DRaiz=<repositorio> /DSalida=<build\salida> silice.iss
#ifndef Version
  #error Falta /DVersion=<versión SemVer del pyproject>
#endif
#ifndef Org
  #error Falta /DOrg=<carpeta build\app>
#endif
#ifndef Raiz
  #error Falta /DRaiz=<carpeta del repositorio>
#endif
#ifndef Salida
  #define Salida Raiz + "\build\salida"
#endif
#ifdef Completo
  #define Sufijo "-completo"
#else
  #define Sufijo ""
#endif
; Atajos: las secciones de Inno no admiten líneas partidas y deben caber en 100 columnas.
#define Op "-E -s -B -X utf8 -m operacion"
#define OpA "-E -s -B -X utf8 -m operacion arrancar"
#define OpP "-E -s -B -X utf8 -m operacion parar"
#define OpR "-E -s -B -X utf8 -m operacion red-local activar"
#define OpD "-E -s -B -X utf8 -m operacion demostracion"
#define Ej "Filename: {app}\python\python.exe; WorkingDir: {app}\codigo;"
#define Rec "recursesubdirs createallsubdirs ignoreversion"
#define Mod "{app}\modulos\similitud"
#define Sp "{app}\python\Lib\site-packages"

[Setup]
; El AppId no cambia jamás: la actualización reconoce así la instalación anterior.
AppId={{D3E5A9C1-6B24-4F0A-8E7D-2C41B96A5F30}
AppName=Sílice
AppVersion={#Version}
AppPublisher=Eugenio Rijo
DefaultDirName={autopf}\Silice
DefaultGroupName=Sílice
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
MinVersion=10.0.19045
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
LicenseFile={#Raiz}\LICENSE
OutputDir={#Salida}
OutputBaseFilename=Silice-{#Version}{#Sufijo}
UninstallDisplayIcon={app}\python\python.exe
SetupLogging=yes
UsePreviousAppDir=yes

[Languages]
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"

[Types]
Name: "est"; Description: "Instalación estándar"
Name: "per"; Description: "Instalación personalizada"; Flags: iscustom

[Components]
Name: "programa"; Description: "Sílice"; Types: est per; Flags: fixed
Name: "demostracion"; Description: "Caso de demostración (datos ficticios)"; Types: est per
#ifdef Completo
Name: "similitud"; Description: "Similitud de partidas (módulo opcional, ~1 GB)"; Types: est per
#endif

[Tasks]
Name: "escritorio"; Description: "Acceso directo en el escritorio"; Flags: unchecked

[Files]
Source: "{#Org}\python\*"; DestDir: "{app}\python"; Components: programa; Flags: {#Rec}
Source: "{#Org}\codigo\*"; DestDir: "{app}\codigo"; Components: programa; Flags: {#Rec}
Source: "{#Org}\LICENCIAS\*"; DestDir: "{app}\LICENCIAS"; Components: programa; Flags: {#Rec}
Source: "{#Org}\manifiesto.json"; DestDir: "{app}"; Components: programa; Flags: ignoreversion
#ifdef Completo
Source: "{#Org}\modulos\similitud\*"; DestDir: "{#Mod}"; Components: similitud; Flags: {#Rec}
Source: "{#Org}\silice_similitud.pth"; DestDir: "{#Sp}"; Components: similitud; Flags: ignoreversion
#endif

[InstallDelete]
; Al actualizar no deben quedar paquetes de la versión anterior. Los datos viven fuera de {app}.
Type: filesandordirs; Name: "{app}\python"
Type: filesandordirs; Name: "{app}\modulos"
Type: filesandordirs; Name: "{app}\codigo"
Type: filesandordirs; Name: "{app}\LICENCIAS"

[Icons]
Name: "{autoprograms}\Sílice"; {#Ej} Parameters: "{#OpA}"; Flags: runminimized
Name: "{autoprograms}\Detener Sílice"; {#Ej} Parameters: "{#OpP}"; Flags: runminimized
Name: "{autoprograms}\Sílice: red local (administrador)"; {#Ej} Parameters: "{#OpR}"
Name: "{autodesktop}\Sílice"; {#Ej} Parameters: "{#OpA}"; Flags: runminimized; Tasks: escritorio

[Run]
{#Ej} Parameters: "{#OpD}"; Components: demostracion; Flags: runhidden
{#Ej} Parameters: "{#OpA}"; Description: "Abrir Sílice"; Flags: postinstall nowait skipifsilent

[UninstallRun]
{#Ej} Parameters: "{#OpP}"; Flags: runhidden; RunOnceId: "DetenerSilice"

[UninstallDelete]
; Solo el programa; nunca la carpeta de datos.
Type: filesandordirs; Name: "{app}\codigo"
Type: filesandordirs; Name: "{app}\python"
Type: filesandordirs; Name: "{app}\modulos"

[Code]
const
  ClaveDesinstalador =
    'Software\Microsoft\Windows\CurrentVersion\Uninstall\' +
    '{D3E5A9C1-6B24-4F0A-8E7D-2C41B96A5F30}_is1';

function TomarNumero(var S: String): Integer;
var
  I: Integer;
  N: String;
begin
  I := 1;
  while (I <= Length(S)) and (S[I] >= '0') and (S[I] <= '9') do
    I := I + 1;
  N := Copy(S, 1, I - 1);
  S := Copy(S, I, Length(S));
  if (Length(S) > 0) and (S[1] = '.') then
    S := Copy(S, 2, Length(S));
  Result := StrToIntDef(N, 0);
end;

{ X.Y.Z[-rc.N] como un número comparable; la versión final vale más que cualquier candidata. }
function ClaveDeVersion(Texto: String): Int64;
var
  X, Y, Z, N, I: Integer;
begin
  X := TomarNumero(Texto);
  Y := TomarNumero(Texto);
  Z := TomarNumero(Texto);
  N := 999;
  if (Length(Texto) > 0) and (Texto[1] = '-') then
  begin
    I := Pos('.', Texto);
    if I > 0 then
      N := StrToIntDef(Copy(Texto, I + 1, Length(Texto)), 0)
    else
      N := 0;
  end;
  Result := (((Int64(X) * 1000 + Y) * 1000 + Z) * 1000) + N;
end;

function VersionInstalada(): String;
var
  V: String;
begin
  Result := '';
  if RegQueryStringValue(HKCU, ClaveDesinstalador, 'DisplayVersion', V) then
    Result := V
  else if RegQueryStringValue(HKLM, ClaveDesinstalador, 'DisplayVersion', V) then
    Result := V;
end;

function InitializeSetup(): Boolean;
var
  Previa: String;
begin
  Result := True;
  Previa := VersionInstalada();
  if (Previa <> '') and (ClaveDeVersion(Previa) > ClaveDeVersion('{#Version}')) then
    Result := SuppressibleMsgBox(
      'Ya hay instalada una versión más nueva de Sílice (' + Previa + '). Instalar la ' +
      '{#Version} es bajar de versión y puede dejar sus datos sin abrir. ¿Continuar?',
      mbConfirmation, MB_YESNO or MB_DEFBUTTON2, IDNO) = IDYES;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  Codigo: Integer;
  Python: String;
begin
  Result := '';
  Python := ExpandConstant('{app}\python\python.exe');
  if FileExists(Python) then
    Exec(Python, '{#Op} parar', ExpandConstant('{app}\codigo'),
      SW_HIDE, ewWaitUntilTerminated, Codigo);
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  Codigo: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    if (not Exec(ExpandConstant('{app}\python\python.exe'), '{#Op} migrar',
        ExpandConstant('{app}\codigo'), SW_HIDE, ewWaitUntilTerminated, Codigo)) then
      Codigo := -1;
    Log('operacion migrar: codigo ' + IntToStr(Codigo));
    if Codigo <> 0 then
      SuppressibleMsgBox(
        'Sílice se instaló, pero no pudo actualizar sus bases de datos. Sus datos no se ' +
        'tocaron y hay un respaldo previo. Abra Sílice: le dirá qué hacer (manual de ' +
        'instalación, «base no adoptable» o «versión más nueva»).',
        mbError, MB_OK, IDOK);
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usDone then
    SuppressibleMsgBox(
      'Sus datos quedan en ' + ExpandConstant('{localappdata}') + '\Silice. ' +
      'Bórrelos a mano si ya no los necesita.', mbInformation, MB_OK, IDOK);
end;
