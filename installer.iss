; OneTaskAtATime Inno Setup Script
; This script creates a Windows installer for OneTaskAtATime application
;
; Build Instructions:
; 1. Build the executable first: pyinstaller OneTaskAtATime.spec
; 2. Install Inno Setup 6.x from https://jrsoftware.org/isdl.php
; 3. Open this file in Inno Setup Compiler
; 4. Click Build > Compile (or press Ctrl+F9)
; 5. Installer will be created in: Output\OneTaskAtATime-1.0.0-Setup.exe

#define MyAppName "OneTaskAtATime"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "OneTaskAtATime Project"
#define MyAppURL "https://github.com/cdavis/OneTaskAtATime"
#define MyAppExeName "OneTaskAtATime.exe"
#define MyAppCopyright "Copyright 2026 Christopher Davis"

[Setup]
; Basic application information
AppId={{8F9A5B2C-4D3E-4F1A-9B7C-2E8D6F5A4C3B}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
AppCopyright={#MyAppCopyright}

; Installation directories
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes

; License file (if exists, otherwise comment out)
; LicenseFile=LICENSE.txt

; Output configuration
OutputDir=Output
OutputBaseFilename=OneTaskAtATime-{#MyAppVersion}-Setup
SetupIconFile=resources\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

; Compression
Compression=lzma2/max
SolidCompression=yes

; Architecture - supports both 32-bit and 64-bit Windows
; The app itself is architecture-independent (Python bytecode)
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

; Windows version requirements
MinVersion=10.0
PrivilegesRequired=admin

; UI Configuration
WizardStyle=modern
WizardImageFile=compiler:WizModernImage-IS.bmp
WizardSmallImageFile=compiler:WizModernSmallImage-IS.bmp

; Uninstall configuration
UninstallDisplayName={#MyAppName}
UninstallFilesDir={app}\uninst

; Misc
DisableWelcomePage=no
DisableReadyPage=no
AlwaysShowDirOnReadyPage=yes
AlwaysShowGroupOnReadyPage=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Files]
; Main executable and all files from PyInstaller dist folder
Source: "dist\OneTaskAtATime\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; Additional documentation files (if they exist in root)
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion; Check: FileExists('README.md')
Source: "USER_GUIDE.md"; DestDir: "{app}"; Flags: ignoreversion; Check: FileExists('USER_GUIDE.md')
Source: "CHANGELOG.md"; DestDir: "{app}"; Flags: ignoreversion; Check: FileExists('CHANGELOG.md')
Source: "INSTALLATION_GUIDE.md"; DestDir: "{app}"; Flags: ignoreversion; Check: FileExists('INSTALLATION_GUIDE.md')

; NOTE: Don't use "Flags: ignoreversion" on any shared system files

[Icons]
; Start Menu shortcut
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; Comment: "A focused to-do list desktop application"
Name: "{group}\User Guide"; Filename: "{app}\USER_GUIDE.md"; Check: FileExists(ExpandConstant('{app}\USER_GUIDE.md'))
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"

; Desktop shortcut (optional, user can choose)
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; IconFilename: "{app}\{#MyAppExeName}"; Comment: "A focused to-do list desktop application"

; Quick Launch shortcut (optional, for older Windows versions)
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
; Option to launch the application after installation
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Clean up any files created during runtime (optional)
Type: filesandordirs; Name: "{app}\*.log"
Type: filesandordirs; Name: "{app}\__pycache__"

[Code]
// Check if application is running before installation
function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
begin
  Result := True;

  // Check if the application is already running
  if CheckForMutexes('OneTaskAtATimeAppMutex') then
  begin
    if MsgBox('OneTaskAtATime is currently running. Setup must close it before continuing.' + #13#10 + #13#10 +
              'Click OK to close OneTaskAtATime and continue setup, or Cancel to exit setup.',
              mbConfirmation, MB_OKCANCEL) = IDOK then
    begin
      // Try to gracefully close the application
      if Exec('taskkill', '/F /IM "' + '{#MyAppExeName}' + '"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
      begin
        Sleep(1000); // Wait a second for the process to close
        Result := True;
      end
      else
      begin
        MsgBox('Failed to close OneTaskAtATime. Please close it manually and run setup again.', mbError, MB_OK);
        Result := False;
      end;
    end
    else
    begin
      Result := False;
    end;
  end;
end;

// Check if this is an upgrade
function InitializeUninstall(): Boolean;
begin
  Result := True;

  // Check if the application is running
  if CheckForMutexes('OneTaskAtATimeAppMutex') then
  begin
    MsgBox('OneTaskAtATime is currently running. Please close it before uninstalling.', mbError, MB_OK);
    Result := False;
  end;
end;

// Custom page to inform user about data location
procedure CurPageChanged(CurPageID: Integer);
var
  InfoText: String;
begin
  if CurPageID = wpFinished then
  begin
    InfoText := 'Your tasks and settings are stored in:' + #13#10 +
                ExpandConstant('{userappdata}\OneTaskAtATime\') + #13#10 + #13#10 +
                'These files are NOT removed when uninstalling, so your data is safe.' + #13#10 +
                'To completely remove all data, manually delete that folder.';

    // Could display this in a custom page or message box if desired
    // For now, user can read it in the installation guide
  end;
end;

[Messages]
; Custom messages for better user experience
WelcomeLabel2=This will install [name/ver] on your computer.%n%nOneTaskAtATime is a focused to-do list desktop application designed to help you concentrate on one task at a time.%n%nIt is recommended that you close all other applications before continuing.
FinishedHeadingLabel=Completing the [name] Setup Wizard
FinishedLabelNoIcons=Setup has finished installing [name] on your computer. Your tasks will be stored in %APPDATA%\OneTaskAtATime\.
FinishedLabel=Setup has finished installing [name] on your computer. The application may be launched by selecting the installed shortcuts.

[Registry]
; Optional: Add registry entries for file associations or other integrations
; Currently not needed for this application

[UninstallRun]
; Optional: Run cleanup tasks before uninstall
; Currently not needed

;
; Notes for developers:
; - User data (database, settings) is stored in %APPDATA%\OneTaskAtATime\
; - This installer does NOT touch user data during uninstall
; - User must manually delete %APPDATA%\OneTaskAtATime\ to completely remove all data
; - The application creates its database on first run
; - No registry entries are created (besides standard uninstall info)
;
