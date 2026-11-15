"""Check DLC routing and cleanup without changing the running game."""
import os, tempfile
os.environ['QT_QPA_PLATFORM']='offscreen'
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from PySide6.QtCore import Qt
import backend, trainer

with tempfile.TemporaryDirectory() as folder:
    original_root=backend.ROOT;backend.ROOT=Path(folder)
    backend.send([False]*10,dlc_unlock=True)
    assert (backend.ROOT/'dlc-unlock.txt').read_text()=='1'
    backend.disable()
    assert not (backend.ROOT/'dlc-unlock.txt').exists()
    backend.ROOT=original_root

calls=[]
backend.send=lambda *args:calls.append(args)
backend.status=lambda:{'ready':True,'pid':1,'scene':'Test fixture','flags':'1000000000','hooks':33,'error':'','version':'1.3','dlc':False}
app=QApplication([]);w=trainer.Trainer();w.timer.stop();w.hotkey_timer.stop();w.show()
assert w.flags[0], 'An active feature should survive the trainer update'
w.navigate(2);app.processEvents();QTest.mouseClick(w.dlc_toggle,Qt.LeftButton)
assert calls[-1][3] is True
assert w.pages.currentIndex()==2
w.alloff();assert not w.dlc_toggle.isChecked() and not any(w.flags)
assert calls[-1][3] is False
w.close()
print('PASS: DLC command, disable cleanup, UI toggle, all-off, active cheat restoration')
