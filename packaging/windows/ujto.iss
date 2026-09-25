; Inno Setup script: dist\Ujto (PyInstaller one-dir) → dist\Ujto-windows-x64.exe
; Registers the ujto:// link scheme for the current user. Needs WebView2 (built into Windows 10/11).
#define AppVersion GetEnv("UJTO_VERSION")

[Setup]
AppId={{6E0A6E54-3C6B-4F0E-9D3A-0B3F2B1D7A11}
AppName=Ujtö̀
AppVersion={#AppVersion}
AppPublisher=Pacific Code Labs
AppPublisherURL=https://ujto.jcampos.dev
DefaultDirName={localappdata}\Programs\Ujto
DefaultGroupName=Ujtö̀
PrivilegesRequired=lowest
OutputDir=..\..\dist
OutputBaseFilename=Ujto-windows-x64
SetupIconFile=..\..\build\icon.ico
UninstallDisplayIcon={app}\Ujto.exe
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\..\dist\Ujto\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\Ujtö̀"; Filename: "{app}\Ujto.exe"
Name: "{userdesktop}\Ujtö̀"; Filename: "{app}\Ujto.exe"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Classes\ujto"; ValueType: string; ValueName: ""; ValueData: "URL:Ujto link"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\ujto"; ValueType: string; ValueName: "URL Protocol"; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\ujto\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\Ujto.exe,0"
Root: HKCU; Subkey: "Software\Classes\ujto\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Ujto.exe"" ""%1"""

[Run]
Filename: "{app}\Ujto.exe"; Description: "{cm:LaunchProgram,Ujtö̀}"; Flags: nowait postinstall skipifsilent
