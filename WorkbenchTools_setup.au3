#RequireAdmin
#include <ButtonConstants.au3>
#include <EditConstants.au3>
#include <GUIConstantsEx.au3>
#include <StaticConstants.au3>
#include <WindowsConstants.au3>
#include <Array.au3>
#include <File.au3>
#include <FileConstants.au3>
#include <MsgBoxConstants.au3>
#include <WinAPIFiles.au3>
#include <constants.au3>
#include <GuiStatusBar.au3>
#include <progressconstants.au3>


#Region ### START Koda GUI section ### Form=
$Form1 = GUICreate("Workbench Tool Installer", 485, 270, -1, -1)
$Group1 = GUICtrlCreateGroup("Blender path", 16, 8, 457, 65)
$Input_FolderBlender = GUICtrlCreateInput("Input1", 40, 32, 313, 21)
$Button_SelectBlender = GUICtrlCreateButton("Pick file", 360, 32, 99, 25)
GUICtrlCreateGroup("", -99, -99, 1, 1)
$Group4 = GUICtrlCreateGroup("Enfusion tools path", 16, 82, 457, 65)
$Input_FolderTools = GUICtrlCreateInput("Input1", 40, 106, 313, 21)
$Button_SelectTools = GUICtrlCreateButton("Pick file", 360, 106, 99, 25)
GUICtrlCreateGroup("", -99, -99, 1, 1)
$Button_Install = GUICtrlCreateButton("Install", 16, 160, 459, 89)
GUISetState(@SW_SHOW)
#EndRegion ### END Koda GUI section ###

; ###########################
; # Global variables & init #
; ###########################

Global $blenderPath = ""
Global $toolsPath = ""
Global $blenderVersion = ""
Global $blenderVersionArray[8]
FindPaths()
ValidatePaths()
VerifyBlender()

; #############
; # Main Loop #
; #############

While 1
   $nMsg = GUIGetMsg()

   If $nMsg > 0 Then
	  $blenderPath = GUICtrlRead($Input_FolderBlender)
	  ValidatePaths()
   EndIf

   Switch $nMsg
	  Case $GUI_EVENT_CLOSE
		 Exit

	  Case $Button_SelectBlender
		 Local $initDir = ""
		 _PathSplit($blenderPath, "", $initDir, "", "")
		 Local $sFileSelectFolder = FileOpenDialog ("Select Blender exe", $initDir,"Blender (blender.exe)",$FD_FILEMUSTEXIST,"blender.exe")
		 If Not @error Then
			$blenderPath = $sFileSelectFolder
			VerifyBlender()
			GUICtrlSetData($Input_FolderBlender,$sFileSelectFolder, "")
			ValidatePaths()
		 EndIf

	  Case $Button_SelectTools
		 Local $initDir = ""
		 _PathSplit($toolsPath, "", $initDir, "", "")
		 Local $sFileSelectFolder = FileOpenDialog ("Select Enfusion Tools dir", $initDir,"Enfusion Tools (Enfusion Tools)",$FD_FILEMUSTEXIST,"EnfusionBlenderFBX")
		 If Not @error Then
			GUICtrlSetData($Input_FolderExport,$sFileSelectFolder, "")
			ValidatePaths()
		EndIf

	  Case $Button_Install
		 InstallPlugin()
   EndSwitch

WEnd

; #############
; # Functions #
; #############

Func FindPaths()
   ; Look for Blender exe
   $blenderPath = RegRead("HKEY_CLASSES_ROOT\Applications\blender.exe\shell\open\command", "")
   If Not $blenderPath = "" Then
	  $blenderPath = StringRegExp($blenderPath, '["''].*?["'']|[^ ]+', $STR_REGEXPARRAYGLOBALMATCH)
	  $blenderPath = $blenderPath[0]
	  $blenderPath = StringReplace($blenderPath, '"', '')
	  GUICtrlSetData($Input_FolderBlender,$blenderPath, "")
   EndIf

   ; Look for EnfusionTools
   $toolsPath = @WorkingDir & "\EnfusionBlenderFBX"
   If FileExists($toolsPath) Then
	  GUICtrlSetData($Input_FolderTools,$toolsPath, "")
   EndIf
EndFunc

Func ValidatePaths()
   ; Install button is disabled if one of the paths is invalid
   GUICtrlSetState ($Button_Install,$GUI_ENABLE)
   If  Not FileExists($blenderPath) Then
	  GUICtrlSetData($Input_FolderBlender,"Please select path to Blender exe!" , "")
	  GUICtrlSetState ($Button_Install,$GUI_DISABLE)
   EndIf
   If Not FileExists($toolsPath) Then
	  GUICtrlSetData($Input_FolderExport,'Please select path to "EnfusionBlenderFBX"!' , "")
	  GUICtrlSetState ($Button_Install,$GUI_DISABLE)
  EndIf

EndFunc

Func VerifyBlender()
   If FileExists($blenderPath) Then
	  $blenderVersion = FileGetVersion($blenderPath)
	  $blenderVersionArray = StringSplit($blenderVersion, ".")
	  If ($blenderVersionArray[1]*10) + $blenderVersionArray[2] < 28 Then
		 MsgBox($MB_SYSTEMMODAL, "Warning", "Plugin works only with version 2.8 and higher! Selected version: " & $blenderVersion)
	  EndIf
   EndIf
EndFunc

Func InstallPlugin()
   ; Instal plugin in user app data folder. It is later activated

   If $blenderVersionArray[2] == 0 and $blenderVersionArray[3] == 0 Then
	  $blenderVersion =  $blenderVersionArray[1] & "." & $blenderVersionArray[2]
   Else
	  $blenderVersion =  $blenderVersionArray[1] & "." & $blenderVersionArray[2]
   EndIf

   If $blenderVersionArray[2] == 0 and $blenderVersionArray[3] > 0 Then
	  $blenderVersion =  $blenderVersionArray[1] & "." & $blenderVersionArray[2]
   EndIf
   MsgBox($MB_SYSTEMMODAL, "Wersja", $blenderVersionArray[2] & " " & $blenderVersionArray[3] & " " & $blenderVersion )

   ; Instal Enfusion Tools
   $pathToPlugin = _PathFull("Blender Foundation\Blender\" & $blenderVersion & "\scripts\addons\",@AppDataDir)
   Local $importFileName = "enf_import_fbx.py"
   Local $copyStatus1 = FileCopy($toolsPath,$pathToPlugin & "EnfusionBlenderFBX\",$FC_OVERWRITE + $FC_CREATEPATH)

   ; Handle file association. Since Windows 8 its no longer possible to use ASSOC and register entries are protected by hash
   ; In order to bypass that restriction a 3rd party exe is used https://github.com/DanysysTeam/SFTA
   ; Add new file type to register
   Local $associationPath = '"' & $blenderPath & '"' & ' --python "' & $pathToPlugin & "EnfusionBlenderFBX\" & $importFileName & '" -- "%1"'
   RunWait(@ComSpec & " /c FTYPE FBX.File=" & $associationPath,"",@SW_SHOW)
   ; Change file association
   RunWait("SFTA.exe" & " FBX.File .FBX",@WorkingDir,@SW_SHOW)
   ;$g = GUICreate("test",200,50,-1,-1,$WS_POPUP)
   ;$l = GUICtrlCreateLabel("Instalation in progress", 20, 35, 120, 21)
   ;GUISetBkColor(0xffff00)
   ;GUISetState()
   ;GUICtrlSetState ($Button_Install,$GUI_DISABLE)
   ;$progress = GUICtrlCreateProgress(0, 0, 200, 30, $PBS_MARQUEE)
   ;_SendMessage(GUICtrlGetHandle($progress), $PBM_SETMARQUEE, 1, 200)

   ;RunWait(@ComSpec & ' /c  powershell.exe -ExecutionPolicy Bypass -command "& { . ' &  @ScriptDir & '\SFTA.ps1; Set-FTA "FBX.File" ".FBX" }"',"",@SW_HIDE)

   ;GUICtrlDelete($progress)
   ;GUIDelete($g)
   ;GUICtrlDelete($l)
   ;GUICtrlSetState ($Button_Install,$GUI_ENABLE)

   ; Report if instalation went correctly
   Local $statusString_title, $statusString_msg, $statusString_flag
   If $copyStatus1 = 0 Then
	  $statusString_flag = $MB_SYSTEMMODAL & $MB_ICONERROR
	  $statusString_title = "Error!"
	  $statusString_msg = "Plugin was not installed correctly" & @LF
   EndIf
   If $statusString_title = "" Then
	  $statusString_flag = $MB_SYSTEMMODAL
	  $statusString_title = "Success!"
	  $statusString_msg = "Plugin was installed successfully!"
   EndIf

   MsgBox($statusString_flag, $statusString_title, $statusString_msg)

EndFunc