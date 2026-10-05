import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

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
    assert window.backup_button.text() == "Sichern auf A und B"
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


def test_gui_timer_runs_while_worker_is_busy(tmp_path):
    from threading import Event

    app = QApplication.instance() or QApplication([])
    window = MainWindow(tmp_path, use_settings=False)
    initial = QEventLoop()
    window.worker.finished.connect(initial.quit)
    QTimer.singleShot(5000, initial.quit)
    initial.exec()
    assert window.worker.wait(5000)
    app.processEvents()
    release = Event()
    heartbeat = []
    window.launch(lambda progress: release.wait(5))
    assert not window.backup_button.isEnabled()
    loop = QEventLoop()

    def tick():
        heartbeat.append(True)
        release.set()

    QTimer.singleShot(20, tick)
    window.worker.finished.connect(loop.quit)
    QTimer.singleShot(5000, loop.quit)
    loop.exec()
    assert window.worker.wait(5000)
    app.processEvents()
    assert heartbeat == [True]
    assert window.backup_button.isEnabled()
    window.close()
