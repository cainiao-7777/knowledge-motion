; 使用按用户安装，程序文件与用户作品分开
[Setup]
AppId=KnowledgeMotion.CyberLibrary
AppName=赛博图书馆
AppVersion=1.0.0
DefaultDirName={localappdata}\Programs\KnowledgeMotion
DefaultGroupName=赛博图书馆
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\outputs\release
OutputBaseFilename=KnowledgeMotion-1.0.0-Windows-x64-Setup
UninstallDisplayIcon={app}\KnowledgeMotion.exe
SetupIconFile=..\outputs\release-work\library.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Files]
Source: "..\outputs\release-work\dist\KnowledgeMotion\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion

Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\THIRD_PARTY_NOTICES.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\outputs\release-work\dist\KnowledgeMotion\THIRD_PARTY_NOTICES\*"; DestDir: "{app}\THIRD_PARTY_NOTICES"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\赛博图书馆"; Filename: "{app}\KnowledgeMotion.exe"
Name: "{userdesktop}\赛博图书馆"; Filename: "{app}\KnowledgeMotion.exe"

[Run]
Filename: "{app}\KnowledgeMotion.exe"; Description: "打开赛博图书馆"; Flags: postinstall nowait skipifsilent



