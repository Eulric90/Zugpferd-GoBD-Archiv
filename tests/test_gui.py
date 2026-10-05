import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

from zugpferd_archiv.gui import MainWindow, Worker


def test_window_has_required_actions_and_stays_responsive(tmp_path):
    app = QApplication.instance() or QApplication([])
    window = MainWindow(tmp_path, use_settings=False)
    loop = QEventLoop()
    window.worker.finished.connect(loop.quit)
    QTimer.singleShot(5000, loop.quit)
    loop.exec()
    assert window.worker.wait(5000)
    app.processEvents()
    assert window.backup_button.text() == 'Sichern auf A und B'
    assert window.check_button.isEnabled()
    assert window.compare_button.isEnabled()
    assert window.export_button.isEnabled()
    assert window.root_edit.text() == str(tmp_path)
    window.show()
    app.processEvents()
    window.close()


def test_worker_returns_result_on_gui_event_loop():
    app = QApplication.instance() or QApplication([])
    result = []
    loop = QEventLoop()
    worker = Worker(lambda progress: 42)
    worker.result.connect(result.append)
    worker.finished.connect(loop.quit)
    worker.start()
    QTimer.singleShot(5000, loop.quit)
    loop.exec()
    assert worker.wait(5000)
    app.processEvents()
    assert result == [42]
