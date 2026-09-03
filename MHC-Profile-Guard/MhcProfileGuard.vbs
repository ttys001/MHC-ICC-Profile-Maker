Set shell = CreateObject("WScript.Shell")
Set files = CreateObject("Scripting.FileSystemObject")
script = files.BuildPath(files.GetParentFolderName(WScript.ScriptFullName), "MhcProfileGuard.ps1")
command = """C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"" -NoProfile -ExecutionPolicy Bypass -File """ & script & """ -Listen"
WScript.Quit shell.Run(command, 0, True)
