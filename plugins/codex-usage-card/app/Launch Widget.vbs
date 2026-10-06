Option Explicit
Dim shell, files, folder, python, cmd, probe
Set shell = CreateObject("WScript.Shell")
Set files = CreateObject("Scripting.FileSystemObject")
folder = files.GetParentFolderName(WScript.ScriptFullName)
python = ""
On Error Resume Next
Set probe = shell.Exec("where.exe pythonw.exe")
Do While probe.Status = 0
  WScript.Sleep 30
Loop
If probe.ExitCode = 0 Then python = Trim(Split(probe.StdOut.ReadAll, vbCrLf)(0))
On Error GoTo 0
If python = "" Or Not files.FileExists(python) Then
  MsgBox "Install Python 3.11 or later with Tcl/Tk and add Python to PATH, then try again.", 48, "Codex Usage Widget"
  WScript.Quit 1
End If
cmd = Chr(34) & python & Chr(34) & " " & Chr(34) & files.BuildPath(folder, "widget.py") & Chr(34)
shell.Run cmd, 1, False
