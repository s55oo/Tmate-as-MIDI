' TMate 1.0 MIDI controller - start without a console window.
' Used by the autostart shortcut that setup-windows.ps1 -Autostart creates.
' Works from wherever the package folder is; no path needs editing.
' If nothing happens, run bin\tmate1-midi.cmd --no-tray once to see the error.
Option Explicit
Dim fso, sh, binDir
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
binDir = fso.GetParentFolderName(WScript.ScriptFullName)
sh.CurrentDirectory = fso.GetParentFolderName(binDir)
sh.Run "cmd /c """"" & binDir & "\tmate1-midi.cmd""""", 0, False
