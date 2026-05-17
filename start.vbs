Set shell = CreateObject("WScript.Shell")
shell.CurrentDirectory = "D:\Claude code\claude-file\codex-bat\desktop"
shell.Run "npx electron .", 0, False
