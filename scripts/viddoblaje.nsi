; VidDoblaje NSIS Installer
!define MyAppName "VidDoblaje"
!define MyAppVersion "1.0.0"
!define MyAppPublisher "VidDoblaje"
!define MyAppExeName "VidDoblaje.exe"
!define MyAppAssocExt ".viddoblaje"
!define MyAppAssocKey "VidDoblaje.Project"

!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "FileFunc.nsh"

Name "${MyAppName}"
OutFile "..\dist\Output\VidDoblajeSetup.exe"
InstallDir "$LOCALAPPDATA\${MyAppName}"
InstallDirRegKey HKCU "Software\${MyAppName}" "InstallDir"
RequestExecutionLevel user
Unicode true
ShowInstDetails show
ShowUnInstDetails show

VIAddVersionKey "ProductName" "${MyAppName}"
VIAddVersionKey "CompanyName" "${MyAppPublisher}"
VIAddVersionKey "FileDescription" "VidDoblaje Setup"
VIAddVersionKey "FileVersion" "${MyAppVersion}"
VIProductVersion "1.0.0.0"
VIFileVersion "1.0.0.0"

SetCompressor /SOLID zlib

!define MUI_ABORTWARNING
!define MUI_ICON "..\assets\icon.ico"
!define MUI_UNICON "..\assets\icon.ico"
!define MUI_WELCOMEPAGE_TITLE "Bienvenido al instalador de ${MyAppName}"
!define MUI_WELCOMEPAGE_TEXT "VidDoblaje traduce y dobla automáticamente tus vídeos al español, de forma 100% local.$\r$\n$\r$\nHaz clic en Siguiente para continuar."

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "..\LICENSE.txt"
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH
!insertmacro MUI_LANGUAGE "Spanish"
!insertmacro MUI_RESERVEFILE_LANGDLL

Section "Icono en escritorio" SecDesktop
    SectionIn 1
SectionEnd

Section "Asociar archivos .viddoblaje" SecAssoc
    SectionIn 1
SectionEnd

Section "VidDoblaje (requerido)" SecCore
    SectionIn RO
    SetOutPath "$INSTDIR"

    ; FFmpeg bundled
    SetOutPath "$INSTDIR\bin"
    File /nonfatal "..\build\ffmpeg\ffmpeg.exe"
    File /nonfatal "..\build\ffmpeg\ffprobe.exe"
    File /nonfatal "..\build\ffmpeg\avcodec-63.dll"
    File /nonfatal "..\build\ffmpeg\avdevice-63.dll"
    File /nonfatal "..\build\ffmpeg\avfilter-12.dll"
    File /nonfatal "..\build\ffmpeg\avformat-63.dll"
    File /nonfatal "..\build\ffmpeg\avutil-61.dll"
    File /nonfatal "..\build\ffmpeg\swresample-7.dll"
    File /nonfatal "..\build\ffmpeg\swscale-10.dll"
    SetOutPath "$INSTDIR"

    ; PyInstaller dist (if exists)
    File /nonfatal /r "..\dist\VidDoblaje\*"

    ; Source code
    SetOutPath "$INSTDIR\src"
    File /nonfatal /r "..\src\*"
    SetOutPath "$INSTDIR"

    ; Docs
    SetOutPath "$INSTDIR\docs"
    File /nonfatal "..\LICENSE.txt"
    File /nonfatal "..\README.md"
    File /nonfatal "..\requirements.txt"
    SetOutPath "$INSTDIR"

    WriteRegStr HKCU "Software\${MyAppName}" "InstallDir" "$INSTDIR"
    WriteUninstaller "$INSTDIR\uninstall.exe"

    CreateDirectory "$SMPROGRAMS\${MyAppName}"
    ${If} ${FileExists} "$INSTDIR\${MyAppExeName}"
        CreateShortcut "$SMPROGRAMS\${MyAppName}\${MyAppName}.lnk" "$INSTDIR\${MyAppExeName}"
    ${EndIf}
    CreateShortcut "$SMPROGRAMS\${MyAppName}\Desinstalar ${MyAppName}.lnk" "$INSTDIR\uninstall.exe"

    SectionGetFlags ${SecDesktop} $0
    IntOp $0 $0 & ${SF_SELECTED}
    ${If} $0 <> 0
        ${If} ${FileExists} "$INSTDIR\${MyAppExeName}"
            CreateShortcut "$DESKTOP\${MyAppName}.lnk" "$INSTDIR\${MyAppExeName}"
        ${EndIf}
    ${EndIf}

    SectionGetFlags ${SecAssoc} $0
    IntOp $0 $0 & ${SF_SELECTED}
    ${If} $0 <> 0
        WriteRegStr HKCU "Software\Classes\${MyAppAssocExt}" "" "${MyAppAssocKey}"
        WriteRegStr HKCU "Software\Classes\${MyAppAssocKey}" "" "VidDoblaje Project"
        WriteRegStr HKCU "Software\Classes\${MyAppAssocKey}\DefaultIcon" "" "$INSTDIR\${MyAppExeName},0"
        WriteRegStr HKCU "Software\Classes\${MyAppAssocKey}\shell\open\command" "" '"$INSTDIR\${MyAppExeName}" "%1"'
    ${EndIf}

    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${MyAppName}" "DisplayName" "${MyAppName}"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${MyAppName}" "DisplayVersion" "${MyAppVersion}"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${MyAppName}" "Publisher" "${MyAppPublisher}"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${MyAppName}" "UninstallString" '"$INSTDIR\uninstall.exe"'
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${MyAppName}" "QuietUninstallString" '"$INSTDIR\uninstall.exe" /S'
    WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${MyAppName}" "NoModify" 1
    WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${MyAppName}" "NoRepair" 1

SectionEnd

!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
    !insertmacro MUI_DESCRIPTION_TEXT ${SecDesktop} "Crea un acceso directo en el escritorio"
    !insertmacro MUI_DESCRIPTION_TEXT ${SecAssoc} "Abre archivos .viddoblaje con VidDoblaje"
    !insertmacro MUI_DESCRIPTION_TEXT ${SecCore} "Componentes principales (incluye FFmpeg LGPL)"
!insertmacro MUI_FUNCTION_DESCRIPTION_END

Function .onInit
    SectionGetFlags ${SecDesktop} $0
    IntOp $0 $0 | ${SF_SELECTED}
    SectionSetFlags ${SecDesktop} $0
    SectionGetFlags ${SecAssoc} $0
    IntOp $0 $0 | ${SF_SELECTED}
    SectionSetFlags ${SecAssoc} $0
FunctionEnd

Section "Uninstall"
    RMDir /r "$INSTDIR"
    RMDir /r "$SMPROGRAMS\${MyAppName}"
    Delete "$DESKTOP\${MyAppName}.lnk"
    DeleteRegKey HKCU "Software\Classes\${MyAppAssocKey}"
    DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${MyAppName}"
    DeleteRegKey HKCU "Software\${MyAppName}"
    MessageBox MB_YESNO|MB_ICONQUESTION "¿Eliminar también tus proyectos de VidDoblaje?$\r$\n$\r$\nEsta acción NO se puede deshacer." /SD IDNO IDNO skip
        RMDir /r "$PROFILE\Documents\VidDoblajeProjects"
    skip:
SectionEnd
