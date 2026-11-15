"""UI routing test; never completes or changes a real game quest."""
import os
os.environ['QT_QPA_PLATFORM']='offscreen'
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
import trainer, backend, copy

app=QApplication([])
backend.send=lambda *args:None
backend.status=lambda:{'ready':True,'pid':1,'scene':'Test fixture','flags':'0000000000','hooks':25,'error':'','version':'1.1'}
snapshot={'session':'session-a','items':[
    {'key':'goal-a','title':'Первое задание','text':'Собрать дерево'},
    {'key':'goal-b','title':'Второе задание','text':'Построить храм'}]}
backend.quests=lambda:copy.deepcopy(snapshot)
calls=[]
def complete(session,key):
    calls.append((session,key))
    return 'request-1'
backend.complete_quest=complete
backend.quest_result=lambda request:None
w=trainer.Trainer();w.timer.stop();w.hotkey_timer.stop();w.show();w.navigate(1);app.processEvents()
assert len(w.quest_buttons)==2
QTest.mouseClick(w.quest_buttons[1],Qt.LeftButton)
assert calls==[('session-a','goal-b')]
assert w.pending_quest and all(not b.isEnabled() for b in w.quest_buttons)
w.finish_quest('session-a','goal-a')
assert len(calls)==1,'A pending request must not be repeated'
backend.quest_result=lambda request:('ok','Задание выполнено.')
snapshot['items']=snapshot['items'][:1]
# Use a new immutable snapshot as the file reader would.
backend.quests=lambda:{'session':'session-a','items':list(snapshot['items'])}
w.update_quests()
assert w.pending_quest is None and len(w.quest_buttons)==1
assert w.quest_message.text()=='Задание выполнено.'
w.close()
print('PASS: per-quest selection, session/key routing, duplicate prevention, acknowledgement, list refresh')
