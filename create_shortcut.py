"""Create desktop shortcut for Codex Adapter (VBS launcher)"""
import os
from win32com.client import Dispatch

desktop = r'D:\桌面'
target = r'D:\Claude code\claude-file\codex-bat\start.vbs'
working_dir = r'D:\Claude code\claude-file\codex-bat\desktop'

old = os.path.join(desktop, 'Codex适配器.lnk')
if os.path.exists(old):
    os.remove(old)

shell = Dispatch('WScript.Shell')
shortcut = shell.CreateShortcut(old)
shortcut.TargetPath = target
shortcut.WorkingDirectory = working_dir
shortcut.WindowStyle = 7
shortcut.Description = 'Codex 国内模型适配工具'
shortcut.IconLocation = r'C:\Windows\System32\shell32.dll,14'
shortcut.Save()

print('Shortcut updated:', old)
print('Target:', target)
