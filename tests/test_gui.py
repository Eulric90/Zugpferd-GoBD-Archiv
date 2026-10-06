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
    QTimer.singleShot(30000, loop.quit)
    loop.exec()
    assert window.worker.wait(30000)
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
    QTimer.singleShot(30000, loop.quit)
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
    assert window.worker.wait(30000)
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
    QTimer.singleShot(30000, loop.quit)
    loop.exec()
    assert window.worker.wait(30000)
    app.processEvents()
    assert heartbeat == [True]
    assert window.backup_button.isEnabled()
    window.close()


def test_documentation_wizard_validates_and_previews(tmp_path):
    from zugpferd_archiv.documentation import FIELD_GROUPS
    from zugpferd_archiv.documentation_wizard import DocumentationWizard

    app = QApplication.instance() or QApplication([])
    context = {
        "software_version": "1.0.0",
        "root": str(tmp_path),
        "archive_id": "test-archive",
        "media": {
            r: {"medium_uuid": r, "volume_id": r, "path_at_creation": r}
            for r in ("A", "B")
        },
        "last_backup": None,
    }
    wizard = DocumentationWizard(context)
    first = wizard.page(wizard.pageIds()[0])
    assert not first.isComplete()
    for _, fields in FIELD_GROUPS:
        for key, label, required in fields:
            if required:
                wizard.editors[key].setPlainText("Betriebliche Angabe <script>")
    assert first.isComplete()
    assert (
        wizard.documentation_data().values["organization"]
        == "Betriebliche Angabe <script>"
    )
    wizard.preview_page.initializePage()
    assert "Betriebliche Angabe" in wizard.preview.toPlainText()
    assert (
        "<script>" not in wizard.preview.toHtml()
    )  # User input is text, never executable HTML.
    wizard.approved.setChecked(True)
    assert not wizard.preview_page.isComplete()
    wizard.approved_by.setText("Erika Muster")
    assert wizard.preview_page.isComplete()
    assert wizard.documentation_data().approved
    wizard.close()
    app.processEvents()


def test_documentation_wizard_prefills_existing_answers(tmp_path):
    from zugpferd_archiv.documentation import DocumentationData, FIELD_GROUPS
    from zugpferd_archiv.documentation_wizard import DocumentationWizard

    app = QApplication.instance() or QApplication([])
    data = DocumentationData(
        {key: label for _, fields in FIELD_GROUPS for key, label, required in fields},
        approved=True,
        approved_by="Erika Muster",
    )
    wizard = DocumentationWizard({}, initial=data, pending=True)
    assert wizard.editors["organization"].toPlainText() == data.values["organization"]
    assert wizard.approved_by.text() == "Erika Muster"
    assert wizard.approved.isChecked()
    assert wizard.editors["organization"].isReadOnly()
    wizard.close()
    app.processEvents()


def test_main_window_documentation_action_saves_and_cancellation_does_not(
    tmp_path, monkeypatch
):
    from PySide6.QtWidgets import QMessageBox, QWizard
    from zugpferd_archiv.core import ArchiveService
    from zugpferd_archiv.documentation import FIELD_GROUPS, LOCAL_BASE, load_latest
    from zugpferd_archiv.documentation_wizard import DocumentationWizard
    from zugpferd_archiv.media import register

    root, a, b = [tmp_path / name for name in ("work", "a", "b")]
    for path in (root, a, b):
        path.mkdir()
    service = ArchiveService(root)
    service.setup()
    ma = register(a, "A")
    register(b, "B", ma.archive_id)
    service.configure(a, b)
    app = QApplication.instance() or QApplication([])
    window = MainWindow(root, use_settings=False)
    loop = QEventLoop()
    window.worker.finished.connect(loop.quit)
    QTimer.singleShot(30000, loop.quit)
    loop.exec()
    assert window.worker.wait(30000)
    app.processEvents()
    window._add_medium("A", a)
    window._add_medium("B", b)
    monkeypatch.setattr(DocumentationWizard, "exec", lambda self: QWizard.Rejected)
    window.documentation()
    loop = QEventLoop()
    window.worker.finished.connect(loop.quit)
    QTimer.singleShot(30000, loop.quit)
    loop.exec()
    assert window.worker.wait(30000)
    app.processEvents()
    assert not (root / LOCAL_BASE).exists()
    messages = []
    monkeypatch.setattr(
        QMessageBox, "information", lambda *args: messages.append(args[-1])
    )
    monkeypatch.setattr(
        QMessageBox, "warning", lambda *args: messages.append("warning")
    )
    monkeypatch.setattr(
        QMessageBox, "critical", lambda *args: messages.append("critical")
    )

    def finish(wizard):
        for _, fields in FIELD_GROUPS:
            for key, label, required in fields:
                if required:
                    wizard.editors[key].setPlainText("Betrieblicher Ablauf: " + label)
        return QWizard.Accepted

    monkeypatch.setattr(DocumentationWizard, "exec", finish)
    window.documentation()
    loop = QEventLoop()

    def poll():
        if messages:
            loop.quit()
        else:
            QTimer.singleShot(10, poll)

    QTimer.singleShot(10, poll)
    QTimer.singleShot(30000, loop.quit)
    loop.exec()
    assert window.worker.wait(30000)
    app.processEvents()
    assert messages and messages[0] not in ("warning", "critical")
    assert load_latest(root)["completed"]
    assert window.documentation_button.isEnabled()
    window.close()
