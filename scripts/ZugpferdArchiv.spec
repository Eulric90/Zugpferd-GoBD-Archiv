from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, get_module_file_attribute

project = Path(SPECPATH).parent
datas, binaries, hiddenimports = [], [], ['saxonche']
saxon_directory = Path(get_module_file_attribute('saxonche')).parent / 'saxonche.libs'
if saxon_directory.exists():
    binaries += [(str(path), 'saxonche.libs') for path in saxon_directory.rglob('*') if path.is_file()]
for dependency in Path(get_module_file_attribute('saxonche')).parent.glob('*saxonc*.dll'):
    binaries.append((str(dependency), '.'))
for module in ('lxml', 'pypdf', 'cryptography'):
    datas += collect_data_files(module)
datas += [(str(project / 'src/zugpferd_archiv/validation'), 'zugpferd_archiv/validation')]
hiddenimports += ['win32api', 'win32con', 'win32file', 'win32pipe', 'win32security',
                  'win32service', 'win32serviceutil', 'servicemanager', 'pywintypes',
                  'PySide6.QtPdf', 'PySide6.QtPdfWidgets', 'PySide6.QtPrintSupport']
a = Analysis([str(project / 'scripts/windows_entry.py')], pathex=[str(project / 'src')], binaries=binaries,
             datas=datas, hiddenimports=hiddenimports)
pyz = PYZ(a.pure)
gui = EXE(pyz, a.scripts, [], exclude_binaries=True, name='ZugpferdArchiv', console=False)
service = EXE(pyz, a.scripts, [], exclude_binaries=True, name='ZugpferdArchivService', console=True)
collection = COLLECT(gui, service, a.binaries, a.datas, name='ZugpferdArchiv')
