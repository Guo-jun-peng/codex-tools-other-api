"""Create desktop shortcut for Codex Adapter"""
import os
from win32com.client import Dispatch

desktop = r'D:\桌面'
target = r'D:\Claude code\claude-file\codex-bat\start.bat'
working_dir = r'D:\Claude code\claude-file\codex-bat'

# Delete old shortcut if exists
old = os.path.join(desktop, 'Codex适配器.lnk')
if os.path.exists(old):
    os.remove(old)

print(f'Creating shortcut...')

shell = Dispatch('WScript.Shell')
shortcut = shell.CreateShortcut(old)
shortcut.TargetPath = target
shortcut.WorkingDirectory = working_dir
shortcut.WindowStyle = 7  # Minimized
shortcut.Description = 'Codex Adapter'
shortcut.IconLocation = r'C:\Windows\System32\shell32.dll,14'
shortcut.Save()

# Verify
shell2 = Dispatch('WScript.Shell')
sc2 = shell2.CreateShortcut(old)
print('Target:', sc2.TargetPath)
print('Exists:', os.path.exists(old))
print('Done!')
