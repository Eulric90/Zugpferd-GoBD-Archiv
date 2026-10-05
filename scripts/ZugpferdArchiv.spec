from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_data_files

datas, binaries, hiddenimports = collect_all('saxonche')
for module in ('lxml', 'pypdf', 'cryptography'):
    datas += collect_data_files(module)
datas += [(str(Path('src/zugpferd_archiv/validation')), 'zugpferd_archiv/validation')]
hiddenimports += ['win32api', 'win32con', 'win32file', 'win32pipe', 'win32security',
                  'win32service', 'win32serviceutil', 'servicemanager', 'pywintypes',
                  'PySide6.QtPdf', 'PySide6.QtPdfWidgets', 'PySide6.QtPrintSupport']
a = Analysis(['scripts/windows_entry.py'], pathex=['src'], binaries=binaries,
             datas=datas, hiddenimports=hiddenimports)
pyz = PYZ(a.pure)
gui = EXE(pyz, a.scripts, [], exclude_binaries=True, name='ZugpferdArchiv', console=False)
service = EXE(pyz, a.scripts, [], exclude_binaries=True, name='ZugpferdArchivService', console=True)
collection = COLLECT(gui, service, a.binaries, a.datas, name='ZugpferdArchiv')
