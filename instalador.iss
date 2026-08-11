; instalador.iss
; Script de Inno Setup para empaquetar "Mi Coach de Ciclismo" como un instalador
; de verdad: ícono en el menú de inicio, acceso directo opcional en el escritorio,
; y entrada en "Agregar o quitar programas" para desinstalar prolijamente.
;
; Requiere Inno Setup instalado (gratis): https://jrsoftware.org/isdl.php
; Y haber corrido construir_exe.bat antes (para tener dist\MiCoachDeCiclismo\).
;
; Para compilarlo: construir_instalador.bat (o abrir este archivo con el
; programa de Inno Setup y tocar "Compile").

[Setup]
AppName=Mi Coach de Ciclismo
AppVersion=1.0
AppPublisher=Mi Coach de Ciclismo
DefaultDirName={localappdata}\MiCoachDeCiclismo
DefaultGroupName=Mi Coach de Ciclismo
UninstallDisplayIcon={app}\MiCoachDeCiclismo.exe
Compression=lzma2
SolidCompression=yes
OutputDir=instalador_salida
OutputBaseFilename=Instalador_MiCoachDeCiclismo
; No pide permisos de administrador - se instala en la carpeta del usuario actual,
; para que funcione en PCs de trabajo sin permisos elevados.
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear un ícono en el Escritorio"; GroupDescription: "Accesos directos:"

[Files]
Source: "dist\MiCoachDeCiclismo\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Mi Coach de Ciclismo"; Filename: "{app}\MiCoachDeCiclismo.exe"
Name: "{group}\Desinstalar Mi Coach de Ciclismo"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Mi Coach de Ciclismo"; Filename: "{app}\MiCoachDeCiclismo.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\MiCoachDeCiclismo.exe"; Description: "Abrir Mi Coach de Ciclismo ahora"; Flags: nowait postinstall skipifsilent
