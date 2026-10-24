#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif

[Setup]
AppId={{3E292AA3-8D01-4AB5-9464-CC5430C73930}
AppName=AwayGuard
AppVersion={#AppVersion}
AppPublisher=AwayGuard contributors
AppPublisherURL=https://github.com/Weiqiang-Jin/AwayGuard
DefaultDirName={localappdata}\Programs\AwayGuard
DefaultGroupName=AwayGuard
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\AwayGuard.exe
AppMutex=Local\AwayGuard.UI.v1
OutputDir=..\dist
OutputBaseFilename=AwayGuard-Setup-x64
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
SetupLogging=yes

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"

[Files]
Source: "..\dist\AwayGuard\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{userdesktop}\AwayGuard"; Filename: "{app}\AwayGuard.exe"; WorkingDir: "{app}"; Tasks: desktopicon
Name: "{group}\AwayGuard"; Filename: "{app}\AwayGuard.exe"; WorkingDir: "{app}"
Name: "{group}\Uninstall AwayGuard"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\AwayGuard.exe"; Description: "Launch AwayGuard"; Flags: nowait postinstall skipifsilent

; User logs and preferences live outside {app}. Uninstall deliberately retains them.
