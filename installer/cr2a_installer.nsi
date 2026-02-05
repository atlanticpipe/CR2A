; CR2A Contract Analysis - Windows Installer Script
; NSIS (Nullsoft Scriptable Install System) Script
; 
; This script creates a Windows installer for the CR2A Contract Analysis application.
; Build with: makensis cr2a_installer.nsi

;--------------------------------
; Installer Attributes
;--------------------------------

; Product Information
!define PRODUCT_NAME "CR2A Contract Analysis"
!define PRODUCT_VERSION "1.0.0"
!define PRODUCT_PUBLISHER "CR2A"
!define PRODUCT_WEB_SITE ""
!define PRODUCT_DIR_REGKEY "Software\Microsoft\Windows\CurrentVersion\App Paths\CR2A.exe"
!define PRODUCT_UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}"
!define PRODUCT_UNINST_ROOT_KEY "HKLM"

; Executable name
!define EXE_NAME "CR2A.exe"

;--------------------------------
; General Settings
;--------------------------------

; Installer name displayed in title bar
Name "${PRODUCT_NAME} ${PRODUCT_VERSION}"

; Output installer filename
OutFile "..\dist\CR2A_Setup.exe"

; Default installation directory
InstallDir "$PROGRAMFILES\CR2A"

; Get installation folder from registry if available (for upgrades)
InstallDirRegKey HKLM "${PRODUCT_DIR_REGKEY}" ""

; Request application privileges for Windows Vista/7/8/10/11
RequestExecutionLevel admin

; Show installation details
ShowInstDetails show
ShowUnInstDetails show

;--------------------------------
; Compression Settings
;--------------------------------

; Use LZMA compression for best compression ratio
SetCompressor /SOLID lzma
SetCompressorDictSize 64

;--------------------------------
; Icon Settings
;--------------------------------

; Installer and uninstaller icons
!define MUI_ICON "..\assets\icon.ico"
!define MUI_UNICON "..\assets\icon.ico"

; Branding text at bottom of installer
BrandingText "${PRODUCT_NAME} Installer"

;--------------------------------
; Modern UI Configuration
;--------------------------------

; Include Modern UI 2
!include "MUI2.nsh"

; MUI Settings
!define MUI_ABORTWARNING
!define MUI_UNABORTWARNING

; Welcome page header image (optional - uses default if not specified)
!define MUI_WELCOMEFINISHPAGE_BITMAP_NOSTRETCH

;--------------------------------
; Installer Version Information
;--------------------------------

; Version information for the installer executable
VIProductVersion "${PRODUCT_VERSION}.0"
VIAddVersionKey "ProductName" "${PRODUCT_NAME}"
VIAddVersionKey "CompanyName" "${PRODUCT_PUBLISHER}"
VIAddVersionKey "LegalCopyright" "Copyright (c) ${PRODUCT_PUBLISHER}"
VIAddVersionKey "FileDescription" "${PRODUCT_NAME} Installer"
VIAddVersionKey "FileVersion" "${PRODUCT_VERSION}"
VIAddVersionKey "ProductVersion" "${PRODUCT_VERSION}"

;--------------------------------
; Installer Pages (Task 1.2)
;--------------------------------

; Welcome page - introduces the installer to the user
!insertmacro MUI_PAGE_WELCOME

; Directory selection page - allows user to choose installation directory
; Requirement 2.1: Display dialog allowing user to select Installation_Directory
; Requirement 2.2: Default is "$PROGRAMFILES\CR2A" (set in InstallDir above)
!define MUI_PAGE_CUSTOMFUNCTION_LEAVE DirectoryPageLeave
!insertmacro MUI_PAGE_DIRECTORY

; Components page - allows user to select optional components (shortcuts)
!insertmacro MUI_PAGE_COMPONENTS

; Installation page - shows progress during file extraction
!insertmacro MUI_PAGE_INSTFILES

;--------------------------------
; Finish Page Configuration (Task 1.8)
;--------------------------------

; Requirement 7.3: Display a completion message when installation completes successfully
!define MUI_FINISHPAGE_TITLE "Installation Complete"
!define MUI_FINISHPAGE_TEXT "The ${PRODUCT_NAME} has been successfully installed on your computer.$\r$\n$\r$\nClick Finish to close the installer."

; Requirement 7.4: Offer an option to launch the CR2A_Application immediately
!define MUI_FINISHPAGE_RUN "$INSTDIR\${EXE_NAME}"
!define MUI_FINISHPAGE_RUN_TEXT "Launch ${PRODUCT_NAME}"
!define MUI_FINISHPAGE_RUN_CHECKED

; Finish page - displays completion message with launch option
!insertmacro MUI_PAGE_FINISH

;--------------------------------
; Uninstaller Pages
;--------------------------------

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

;--------------------------------
; Language Settings
;--------------------------------

!insertmacro MUI_LANGUAGE "English"

;--------------------------------
; Directory Validation Function (Task 1.2)
;--------------------------------

; Requirement 2.3: Validate that the path is writable
; Requirement 2.4: Display error message if not writable

Function DirectoryPageLeave
    ; Validate that the selected directory is writable
    ; This function is called when the user clicks "Next" on the directory page
    
    Push $0
    Push $1
    
    ; Check if directory exists
    IfFileExists "$INSTDIR\*.*" dir_exists try_create_dir
    
try_create_dir:
    ; Directory doesn't exist, try to create it
    ClearErrors
    CreateDirectory "$INSTDIR"
    IfErrors show_error check_write
    
dir_exists:
    ; Directory exists, fall through to write check
    
check_write:
    ; Try to create a temporary test file to verify write permissions
    ClearErrors
    FileOpen $0 "$INSTDIR\.nsis_write_test" w
    IfErrors show_error write_success
    
write_success:
    ; Successfully opened file for writing
    FileClose $0
    Delete "$INSTDIR\.nsis_write_test"
    ; Clean up: remove directory if we created it and it's now empty
    RMDir "$INSTDIR"
    Pop $1
    Pop $0
    Return
    
show_error:
    ; Requirement 2.4: Display error message and prompt for different location
    Pop $1
    Pop $0
    MessageBox MB_OK|MB_ICONEXCLAMATION "The selected directory is not writable:$\r$\n$\r$\n$INSTDIR$\r$\n$\r$\nPlease select a different installation directory or run the installer as Administrator."
    Abort
FunctionEnd

;--------------------------------
; Initialization Function
;--------------------------------

Function .onInit
    ; Any initialization code can go here
FunctionEnd

;--------------------------------
; Main Installation Section (Task 1.3)
;--------------------------------

; Requirement 1.1: Bundle CR2A_Application executable and all required dependencies
; Requirement 1.3: Include all configuration files from the config directory
; Requirement 1.4: Extract all bundled files to the Installation_Directory
; Requirement 7.1: Display a progress bar showing installation progress
; Requirement 7.2: Display the name of the file currently being installed

Section "!${PRODUCT_NAME}" SEC_MAIN
    ; This section is required (cannot be deselected)
    SectionIn RO
    
    ; Set output path to the installation directory
    SetOutPath "$INSTDIR"
    
    ; Display status message
    DetailPrint "Installing ${PRODUCT_NAME}..."
    DetailPrint "Destination: $INSTDIR"
    
    ; Copy all files from dist/CR2A to installation directory
    ; The /r flag copies recursively, including subdirectories
    ; SetDetailsPrint textonly shows file names during extraction (Requirement 7.2)
    SetDetailsPrint textonly
    
    ; Copy main application files
    DetailPrint "Extracting application files..."
    File /r "..\dist\CR2A\*.*"
    
    ; Restore normal detail printing
    SetDetailsPrint both
    
    ; Display completion message for this section
    DetailPrint "Application files installed successfully."
    
SectionEnd

;--------------------------------
; Desktop Shortcut Section (Task 1.4)
;--------------------------------

; Requirement 3.1: Display a checkbox option to create a desktop Shortcut
; Requirement 3.2: Desktop Shortcut option enabled by default (Section is selected by default)
; Requirement 3.3: Create shortcut on user's desktop pointing to CR2A_Application executable
; Requirement 3.4: Desktop Shortcut uses the application icon (assets/icon.ico)
; Requirement 3.5: Desktop Shortcut named "CR2A Contract Analysis"

Section "Desktop Shortcut" SEC_DESKTOP
    ; This section is optional (not marked with SectionIn RO)
    ; It is selected by default in NSIS
    
    ; Display status message
    DetailPrint "Creating desktop shortcut..."
    
    ; Create desktop shortcut
    ; Parameters: link, target, parameters, icon, icon_index, start_options, keyboard_shortcut, description
    CreateShortCut "$DESKTOP\${PRODUCT_NAME}.lnk" "$INSTDIR\${EXE_NAME}" "" "$INSTDIR\${EXE_NAME}" 0
    
    DetailPrint "Desktop shortcut created successfully."
    
SectionEnd

;--------------------------------
; Start Menu Shortcut Section (Task 1.5)
;--------------------------------

; Requirement 4.1: Display a checkbox option to create a Start Menu Shortcut
; Requirement 4.2: Start Menu Shortcut option enabled by default (Section is selected by default)
; Requirement 4.3: Create a program group in the Start Menu named "CR2A"
; Requirement 4.4: Program group contains shortcut to CR2A_Application executable
; Requirement 4.5: Program group contains shortcut to Uninstaller
; Requirement 4.6: Start Menu Shortcut uses the application icon (assets/icon.ico)

Section "Start Menu Shortcuts" SEC_STARTMENU
    ; This section is optional (not marked with SectionIn RO)
    ; It is selected by default in NSIS
    
    ; Display status message
    DetailPrint "Creating Start Menu shortcuts..."
    
    ; Requirement 4.3: Create program group folder in Start Menu
    CreateDirectory "$SMPROGRAMS\CR2A"
    
    ; Requirement 4.4: Create shortcut to main application executable
    ; Requirement 4.6: Use application icon
    ; Parameters: link, target, parameters, icon, icon_index, start_options, keyboard_shortcut, description
    CreateShortCut "$SMPROGRAMS\CR2A\${PRODUCT_NAME}.lnk" "$INSTDIR\${EXE_NAME}" "" "$INSTDIR\${EXE_NAME}" 0
    
    ; Requirement 4.5: Create shortcut to Uninstaller
    CreateShortCut "$SMPROGRAMS\CR2A\Uninstall ${PRODUCT_NAME}.lnk" "$INSTDIR\uninstall.exe" "" "$INSTDIR\uninstall.exe" 0
    
    DetailPrint "Start Menu shortcuts created successfully."
    
SectionEnd

;--------------------------------
; Uninstaller Generation and Registry Section (Task 1.6)
;--------------------------------

; Requirement 5.1: Generate an Uninstaller executable and place it in the Installation_Directory
; Requirement 5.2: Register the application in Windows "Add/Remove Programs" (Programs and Features)

Section -Post
    ; This section runs after all other sections and handles uninstaller setup
    
    ; Requirement 5.1: Generate uninstaller executable in installation directory
    DetailPrint "Creating uninstaller..."
    WriteUninstaller "$INSTDIR\uninstall.exe"
    
    ; Requirement 5.2: Register application in Add/Remove Programs
    DetailPrint "Registering application in Add/Remove Programs..."
    
    ; Write registry entries for Add/Remove Programs (Programs and Features)
    ; Registry path: HKLM\Software\Microsoft\Windows\CurrentVersion\Uninstall\CR2A Contract Analysis
    
    WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayName" "${PRODUCT_NAME}"
    WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayVersion" "${PRODUCT_VERSION}"
    WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "Publisher" "${PRODUCT_PUBLISHER}"
    WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "UninstallString" "$INSTDIR\uninstall.exe"
    WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "InstallLocation" "$INSTDIR"
    WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayIcon" "$INSTDIR\${EXE_NAME}"
    
    ; Additional registry entries for better Add/Remove Programs integration
    WriteRegDWORD ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "NoModify" 1
    WriteRegDWORD ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "NoRepair" 1
    
    ; Write App Paths registry key for application path resolution
    WriteRegStr HKLM "${PRODUCT_DIR_REGKEY}" "" "$INSTDIR\${EXE_NAME}"
    
    DetailPrint "Application registered successfully."
    
SectionEnd

;--------------------------------
; Uninstaller Section (Task 1.7)
;--------------------------------

; Requirement 5.3: Remove all installed files from the Installation_Directory
; Requirement 5.4: Remove the desktop Shortcut if it was created
; Requirement 5.5: Remove the Start Menu program group if it was created
; Requirement 5.6: Remove the application entry from "Add/Remove Programs"

Section "Uninstall"
    
    ; Display status message
    DetailPrint "Uninstalling ${PRODUCT_NAME}..."
    
    ;--------------------------------
    ; Requirement 5.4: Remove desktop shortcut if exists
    ;--------------------------------
    DetailPrint "Removing desktop shortcut..."
    Delete "$DESKTOP\${PRODUCT_NAME}.lnk"
    
    ;--------------------------------
    ; Requirement 5.5: Remove Start Menu program group if exists
    ;--------------------------------
    DetailPrint "Removing Start Menu shortcuts..."
    ; Remove shortcuts from the program group
    Delete "$SMPROGRAMS\CR2A\${PRODUCT_NAME}.lnk"
    Delete "$SMPROGRAMS\CR2A\Uninstall ${PRODUCT_NAME}.lnk"
    ; Remove the program group directory
    RMDir "$SMPROGRAMS\CR2A"
    
    ;--------------------------------
    ; Requirement 5.6: Remove registry entries (Add/Remove Programs)
    ;--------------------------------
    DetailPrint "Removing registry entries..."
    ; Remove the uninstall registry key
    DeleteRegKey ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}"
    ; Remove the App Paths registry key
    DeleteRegKey HKLM "${PRODUCT_DIR_REGKEY}"
    
    ;--------------------------------
    ; Requirement 5.3: Remove all installed files from Installation_Directory
    ;--------------------------------
    DetailPrint "Removing installed files..."
    
    ; Remove the uninstaller itself
    Delete "$INSTDIR\uninstall.exe"
    
    ; Remove all files and subdirectories from the installation directory
    ; Using RMDir /r to recursively remove all contents
    RMDir /r "$INSTDIR"
    
    ; Display completion message
    DetailPrint "Uninstallation completed."
    
SectionEnd

;--------------------------------
; Uninstaller Initialization Function
;--------------------------------

Function un.onInit
    ; Confirm uninstallation with the user
    MessageBox MB_ICONQUESTION|MB_YESNO|MB_DEFBUTTON2 "Are you sure you want to completely remove ${PRODUCT_NAME} and all of its components?" IDYES +2
    Abort
FunctionEnd

;--------------------------------
; Section Descriptions
;--------------------------------

; Descriptions for the components page
!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
    !insertmacro MUI_DESCRIPTION_TEXT ${SEC_MAIN} "Install the ${PRODUCT_NAME} application (required)."
    !insertmacro MUI_DESCRIPTION_TEXT ${SEC_DESKTOP} "Create a shortcut on your desktop for quick access."
    !insertmacro MUI_DESCRIPTION_TEXT ${SEC_STARTMENU} "Create shortcuts in the Windows Start Menu."
!insertmacro MUI_FUNCTION_DESCRIPTION_END
