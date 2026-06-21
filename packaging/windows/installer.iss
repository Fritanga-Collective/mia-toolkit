; Inno Setup script for the Windows installer.
; Build (after PyInstaller produces dist/MIAToolkit/):
;     ISCC.exe packaging\windows\installer.iss
; Output: dist\MIA-Toolkit-Setup-<version>.exe  (per-user, no admin required).

#define AppName "MIA Toolkit"
; Version comes from the MIA_VERSION env var (set by CI from the tag); falls
; back to a default for local builds.
#define AppVer GetEnv("MIA_VERSION")
#if AppVer == ""
  #define AppVer "0.1.0"
#endif
#define ExeName "MIA Toolkit.exe"
#define Publisher "Fritanga"

[Setup]
; A stable AppId so upgrades replace in place (keep this GUID forever).
AppId={{8F3A1C2E-7B4D-4E9A-9C1F-2D5E6A7B8C90}
AppName={#AppName}
AppVersion={#AppVer}
AppPublisher={#Publisher}
; Per-user install: no administrator rights needed.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
DefaultDirName={localappdata}\Programs\{#AppName}
DisableProgramGroupPage=yes
; x64compatible (Inno Setup 6.3+) matches x64 *and* ARM64 machines that can run
; x64 via Windows' built-in emulation. With plain "x64" the installer refuses to
; run on Windows-on-ARM ("does not support the version of Windows...") before
; emulation can kick in. This ships our x64 build to ARM users (emulated); a
; native ARM64 build is a separate, later step.
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir={#SourcePath}..\..\dist
OutputBaseFilename=MIA-Toolkit-Setup-{#AppVer}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
SetupIconFile={#SourcePath}app.ico
UninstallDisplayIcon={app}\{#ExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; \
  GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#SourcePath}..\..\dist\MIAToolkit\*"; DestDir: "{app}"; \
  Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#ExeName}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#ExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#ExeName}"; Description: "{cm:LaunchProgram,{#AppName}}"; \
  Flags: nowait postinstall skipifsilent
