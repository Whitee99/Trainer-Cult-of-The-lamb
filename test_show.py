"""Test restoring the window without touching game state."""
import os,tempfile,time
os.environ['QT_QPA_PLATFORM']='offscreen'
from pathlib import Path
from PySide6.QtWidgets import QApplication
import backend,trainer

app=QApplication([])
with tempfile.TemporaryDirectory() as folder:
    backend.ROOT=Path(folder)
    backend.status=lambda:None
    backend.send=lambda *args:None
    w=trainer.Trainer();w.timer.stop();w.hotkey_timer.stop()
    w.showMinimized();app.processEvents();assert w.isMinimized()
    backend.request_show();w.check_show_request();app.processEvents()
    assert w.isVisible() and not w.isMinimized()
    stamp=w.last_show_request
    w.check_show_request();assert w.last_show_request==stamp
    w.close()
print('PASS: show request restores minimized window and is consumed once')
