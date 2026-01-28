;NSIS Self-Contained Installer for Contract Analysis Desktop App
;Single EXE that automatically starts installation when opened

!include "MUI2.nsh"
!include "FileFunc.nsh"
!include "LogicLib.nsh"
!include "WinVer.nsh"

;General Configuration
Name "Contract Analysis Tool"
OutFile "ContractAnalysisSetup.exe"
Unicode True
InstallDir "$PROGRAMFILES64\Contract Analysis Tool"
InstallDirRegKey HKCU "Software\ContractAnalysisTool" ""
RequestExecutionLevel user
ShowInstDetails show

;Modern UI Configuration
!define MUI_ABORTWARNING
!define MUI_ICON "app.ico"
!define MUI_UNICON "app.ico"
!define MUI_HEADERIMAGE
!define MUI_HEADERIMAGE_BITMAP "header.bmp"
!define MUI_WELCOMEFINISHPAGE_BITMAP "wizard.bmp"

;Welcome Page
!define MUI_WELCOMEPAGE_TITLE "Welcome to Contract Analysis Tool Setup"
!define MUI_WELCOMEPAGE_TEXT "This wizard will guide you through the installation of Contract Analysis Tool, an AI-powered contract analysis application for Windows 11.$\n$\nKey Features:$\n• Drag & drop PDF/DOCX contract analysis$\n• AI-powered risk assessment$\n• Professional PDF report generation$\n• Enterprise-grade validation$\n$\nClick Next to continue."

;Pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "LICENSE.txt"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!define MUI_FINISHPAGE_RUN "$INSTDIR\ContractAnalysisApp.exe"
!define MUI_FINISHPAGE_RUN_TEXT "Launch Contract Analysis Tool"
!define MUI_FINISHPAGE_SHOWREADME "$INSTDIR\README.txt"
!define MUI_FINISHPAGE_SHOWREADME_TEXT "View Installation Guide"
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

;Languages
!insertmacro MUI_LANGUAGE "English"

;Version Information
VIProductVersion "1.0.0.0"
VIAddVersionKey "ProductName" "Contract Analysis Tool"
VIAddVersionKey "CompanyName" "Atlantic Pipe Services"
VIAddVersionKey "FileVersion" "1.0.0.0"
VIAddVersionKey "ProductVersion" "1.0.0.0"
VIAddVersionKey "FileDescription" "AI-powered contract analysis desktop application for Windows 11"
VIAddVersionKey "LegalCopyright" "© 2025 Atlantic Pipe Services"

;Check Windows Version
Function .onInit
    ${IfNot} ${AtLeastWin11}
        MessageBox mb_iconstop "Contract Analysis Tool requires Windows 11 or later.$\nPlease upgrade your operating system and try again."
        Quit
    ${EndIf}

    ;Check if already installed
    ReadRegStr $R0 HKCU "Software\ContractAnalysisTool" ""
    ${If} $R0 != ""
        MessageBox mb_iconquestion "Contract Analysis Tool is already installed. Would you like to reinstall it?" /SD IDYES IDNO end
        Quit
        end:
    ${EndIf}
FunctionEnd

;Installer Sections
Section "Install" SecInstall

    SetOutPath "$INSTDIR"
    SetOverwrite on

    ;Kill any running instances
    DetailPrint "Checking for running instances..."
    nsExec::Exec 'taskkill /f /im "ContractAnalysisApp.exe" /im "ContractAnalyzer.exe"'

    ;Create installation directory
    CreateDirectory "$INSTDIR"
    CreateDirectory "$INSTDIR\schemas"
    CreateDirectory "$INSTDIR\policy"

    ;Copy main executable (this will be the PyInstaller EXE)
    File "dist\ContractAnalysisApp.exe"

    ;Copy configuration files
    File "output_schemas_v1.json"
    File "validation_rules_v1.json"

    ;Copy to subdirectories as expected by application
    CreateDirectory "$INSTDIR\schemas"
    CopyFiles "$INSTDIR\output_schemas_v1.json" "$INSTDIR\schemas\"

    CreateDirectory "$INSTDIR\policy"
    CopyFiles "$INSTDIR\validation_rules_v1.json" "$INSTDIR\policy\"

    ;Create README for installation directory
    FileOpen $0 "$INSTDIR\README.txt" w
    FileWrite $0 "Contract Analysis Tool$\n"
    FileWrite $0 "====================$\n$\n"
    FileWrite $0 "Installation Directory: $INSTDIR$\n$\n"
    FileWrite $0 "To launch the application:$\n"
    FileWrite $0 "- Double-click the Desktop shortcut$\n"
    FileWrite $0 "- Use Start Menu: Contract Analysis Tool$\n"
    FileWrite $0 "- Double-click any PDF or DOCX file$\n$\n"
    FileWrite $0 "OpenAI API Key:$\n"
    FileWrite $0 "Make sure OPENAI_API_KEY environment variable is set$\n"
    FileWrite $0 "before using the application.$\n$\n"
    FileWrite $0 "For support, check error.log in this directory.$\n"
    FileClose $0

    ;Create uninstaller
    WriteUninstaller "$INSTDIR\Uninstall.exe"

    ;Registry entries for uninstaller
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\ContractAnalysisTool" "DisplayName" "Contract Analysis Tool"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\ContractAnalysisTool" "UninstallString" "$INSTDIR\Uninstall.exe"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\ContractAnalysisTool" "DisplayVersion" "1.0.0"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\ContractAnalysisTool" "Publisher" "Atlantic Pipe Services"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\ContractAnalysisTool" "InstallLocation" "$INSTDIR"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\ContractAnalysisTool" "HelpLink" "https://github.com/atlanticpipe/APS"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\ContractAnalysisTool" "URLInfoAbout" "https://github.com/atlanticpipe/APS"
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\ContractAnalysisTool" "NoModify" 1
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\ContractAnalysisTool" "NoRepair" 1
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\ContractAnalysisTool" "EstimatedSize" 25000

    ;File associations
    WriteRegStr HKCR ".pdf" "" "ContractAnalysisTool.Document"
    WriteRegStr HKCR "ContractAnalysisTool.Document" "" "Contract Analysis Document"
    WriteRegStr HKCR "ContractAnalysisTool.Document\DefaultIcon" "" "$INSTDIR\ContractAnalysisApp.exe,0"
    WriteRegStr HKCR "ContractAnalysisTool.Document\shell\open\command" "" '"$INSTDIR\ContractAnalysisApp.exe" "%1"'

    WriteRegStr HKCR ".docx" "" "ContractAnalysisTool.Document"
    WriteRegStr HKCR "ContractAnalysisTool.Document\DefaultIcon" "" "$INSTDIR\ContractAnalysisApp.exe,0"
    WriteRegStr HKCR "ContractAnalysisTool.Document\shell\open\command" "" '"$INSTDIR\ContractAnalysisApp.exe" "%1"'

    ;Refresh shell icons
    System::Call 'shell32.dll::SHChangeNotify(i, i, i, i) v (0x08000000, 0, 0, 0)'

    ;Create Start Menu shortcuts
    CreateDirectory "$SMPROGRAMS\Contract Analysis Tool"
    CreateShortCut "$SMPROGRAMS\Contract Analysis Tool\Contract Analysis Tool.lnk" "$INSTDIR\ContractAnalysisApp.exe" "" "$INSTDIR\ContractAnalysisApp.exe" 0 "" "" "AI-powered contract analysis desktop application"
    CreateShortCut "$SMPROGRAMS\Contract Analysis Tool\Uninstall Contract Analysis Tool.lnk" "$INSTDIR\Uninstall.exe" "" "$INSTDIR\Uninstall.exe" 0 "" "" "Uninstall Contract Analysis Tool"

    ;Create Desktop shortcut
    CreateShortCut "$DESKTOP\Contract Analysis Tool.lnk" "$INSTDIR\ContractAnalysisApp.exe" "" "$INSTDIR\ContractAnalysisApp.exe" 0 "" "" "AI-powered contract analysis desktop application"

    ;Store installation folder
    WriteRegStr HKCU "Software\ContractAnalysisTool" "" $INSTDIR
    WriteRegStr HKCU "Software\ContractAnalysisTool" "InstallDate" "2025-10-09"

    ;Create log directory
    CreateDirectory "$APPDATA\ContractAnalysisTool"
    WriteRegStr HKCU "Software\ContractAnalysisTool" "LogDir" "$APPDATA\ContractAnalysisTool"

    DetailPrint "Installation completed successfully!"

SectionEnd

;Uninstaller Section
Section "Uninstall"

    ;Kill any running instances
    DetailPrint "Stopping running instances..."
    nsExec::Exec 'taskkill /f /im "ContractAnalysisApp.exe" /im "ContractAnalyzer.exe"'

    ;Remove files and directories
    Delete "$INSTDIR\ContractAnalysisApp.exe"
    Delete "$INSTDIR\output_schemas_v1.json"
    Delete "$INSTDIR\validation_rules_v1.json"
    Delete "$INSTDIR\README.txt"
    Delete "$INSTDIR\Uninstall.exe"

    RMDir "$INSTDIR\schemas"
    RMDir "$INSTDIR\policy"
    RMDir "$INSTDIR"

    ;Remove Start Menu shortcuts
    Delete "$SMPROGRAMS\Contract Analysis Tool\Contract Analysis Tool.lnk"
    Delete "$SMPROGRAMS\Contract Analysis Tool\Uninstall Contract Analysis Tool.lnk"
    RMDir "$SMPROGRAMS\Contract Analysis Tool"

    ;Remove Desktop shortcut
    Delete "$DESKTOP\Contract Analysis Tool.lnk"

    ;Remove registry entries
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\ContractAnalysisTool"
    DeleteRegKey HKCR "ContractAnalysisTool.Document"
    DeleteRegValue HKCR ".pdf" "ContractAnalysisTool.Document"
    DeleteRegValue HKCR ".docx" "ContractAnalysisTool.Document"

    ;Remove user settings
    DeleteRegKey HKCU "Software\ContractAnalysisTool"

    ;Remove log directory
    RMDir /r "$APPDATA\ContractAnalysisTool"

    ;Refresh shell icons
    System::Call 'shell32.dll::SHChangeNotify(i, i, i, i) v (0x08000000, 0, 0, 0)'

    DetailPrint "Uninstallation completed successfully!"

SectionEnd

;Installation Success Function
Function .onInstSuccess
    MessageBox mb_information "Contract Analysis Tool has been successfully installed!$\n$\nThe application is ready to use. You can:$\n• Launch it from the Desktop shortcut$\n• Find it in the Start Menu$\n• Double-click PDF or DOCX files to analyze them$\n$\nMake sure to set your OPENAI_API_KEY environment variable before first use."
FunctionEnd

;Descriptions
!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
!insertmacro MUI_DESCRIPTION_TEXT ${SecInstall} "Installs the Contract Analysis Tool application with all necessary files, shortcuts, and file associations."
!insertmacro MUI_FUNCTION_DESCRIPTION_END

;Elevation Request (if needed for file associations)
Function RequestElevation
    !ifmacrodef UAC_RunElevated
        UAC_RunElevated
    !else
        MessageBox mb_iconinformation "Some features may require administrator privileges for full functionality."
    !endif
FunctionEnd