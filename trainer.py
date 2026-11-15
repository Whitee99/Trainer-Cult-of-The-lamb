import sys, os, ctypes, subprocess, time
from pathlib import Path
from PySide6.QtCore import Qt, QTimer, QSize, QLockFile, QPropertyAnimation, Property, QEasingCurve
from PySide6.QtGui import QColor, QPainter, QPen, QFont, QIcon, QPixmap, QDesktopServices, QFontDatabase
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel, QPushButton, QVBoxLayout,
    QHBoxLayout, QGridLayout, QFrame, QStackedWidget, QSpinBox, QFileDialog, QMessageBox, QCheckBox, QScrollArea)
import backend

FEATURES = [
 ('Бессмертие', 'Урон больше не остановит Агнца.', '♡', 'F1'),
 ('Больше ресурсов', 'Умножение предметов при подборе.', '◇', 'F2'),
 ('Мгновенная молитва', 'Быстрое накопление преданности.', '✧', 'F3'),
 ('Без голода', 'Сытость последователей на максимуме.', '♧', 'F4'),
 ('Бесконечная энергия', 'Последователи не устают.', '☾', 'F5'),
 ('Несокрушимая вера', 'Вера культа всегда на максимуме.', '✦', 'F6'),
 ('Бесплатное строительство', 'Постройки не требуют ресурсов.', '⌂', 'F7'),
 ('Бесконечные заклинания', 'Проклятия не расходуют рвение.', 'ϟ', 'F8'),
 ('Без инакомыслия', 'Предотвращение новых бунтов.', '♜', 'F9'),
 ('Без болезней', 'Защита последователей от заражения.', '✚', 'F10'),
]

class Sigil(QWidget):
    def __init__(self, parent=None, hero=False):
        super().__init__(parent); self.hero=hero; self.setFixedSize(160 if hero else 52, 150 if hero else 52)
    def paintEvent(self,e):
        p=QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        p.translate(self.width()/2,self.height()/2); p.scale(self.width()/110,self.width()/110)
        p.setPen(QPen(QColor('#642f39' if self.hero else '#da5266'),1))
        p.drawEllipse(-43,-43,86,86); p.drawEllipse(-49,-49,98,98)
        p.setPen(QPen(QColor('#be4058'),2)); p.drawLine(-38,31,0,-39);p.drawLine(0,-39,38,31);p.drawLine(38,31,-38,31)
        p.setBrush(QColor('#e7dcca'));p.setPen(Qt.NoPen)
        p.drawEllipse(-23,-8,46,37);p.drawEllipse(-33,-10,17,15);p.drawEllipse(16,-10,17,15)
        p.setBrush(QColor('#17171e'));p.drawRoundedRect(-17,-5,34,28,12,12)
        p.setBrush(QColor('#ef536c'));p.drawEllipse(-10,3,5,7);p.drawEllipse(5,3,5,7)
        p.setBrush(QColor('#d74760'))
        from PySide6.QtGui import QPolygonF
        from PySide6.QtCore import QPointF
        p.drawPolygon(QPolygonF([QPointF(-15,-12),QPointF(-18,-30),QPointF(-6,-23),QPointF(0,-36),QPointF(6,-23),QPointF(18,-30),QPointF(15,-12)]))
        p.setBrush(QColor('#17171e'));p.drawEllipse(-3,-24,6,7)

class Toggle(QPushButton):
    def __init__(self):
        super().__init__();self.setCheckable(True);self.setFixedSize(44,26);self.setCursor(Qt.PointingHandCursor)
        self._pos=0.;self.animation=QPropertyAnimation(self,b'position');self.animation.setDuration(150);self.animation.setEasingCurve(QEasingCurve.OutCubic)
        self.toggled.connect(self.animate)
        self.setAccessibleName('Включить функцию')
    def animate(self,on):
        self.animation.stop();self.animation.setStartValue(self._pos);self.animation.setEndValue(1. if on else 0.);self.animation.start()
    def getpos(self):return self._pos
    def setpos(self,v):self._pos=v;self.update()
    position=Property(float,getpos,setpos)
    def paintEvent(self,e):
        p=QPainter(self);p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor('#e9536f' if self.isChecked() else '#45434f'),1));p.setBrush(QColor('#ac344c' if self.isChecked() else '#2b2b36'))
        p.drawRoundedRect(1,2,42,22,11,11);p.setPen(Qt.NoPen);p.setBrush(QColor('#fff1e9' if self.isChecked() else '#8c899b'));p.drawEllipse(int(5+18*self._pos),6,14,14)

def label(text,name=None):
    w=QLabel(text)
    if name:w.setObjectName(name)
    return w

class Trainer(QMainWindow):
    def __init__(self, preview=False):
        super().__init__();self.preview=preview;self.game=backend.find_game();self.flags=[False]*10;self.keys={};self.state=None
        resume=backend.status() if not preview else None
        self.setWindowTitle('Cult of the Lamb · Трейнер');self.resize(1120,850);self.setMinimumSize(1030,800)
        self.setWindowIcon(QIcon(str(backend.ASSETS/'assets/icon.ico')))
        root=QWidget();root.setObjectName('root');self.setCentralWidget(root);outer=QHBoxLayout(root);outer.setContentsMargins(0,0,0,0);outer.setSpacing(0)
        side=QFrame();side.setObjectName('sidebar');side.setFixedWidth(222);sl=QVBoxLayout(side);sl.setContentsMargins(24,30,24,24);sl.setSpacing(16)
        sl.addWidget(Sigil());sl.addWidget(label('CULT OF\nTHE LAMB','brand'));sl.addWidget(label('ЛИЧНЫЙ ТРЕЙНЕР','eyebrow'));sl.addSpacing(26)
        self.nav=[];self.pages=QStackedWidget()
        for i,t in enumerate(['Управление','Квесты','Дополнения','Как пользоваться','О программе']):
            b=QPushButton(t);b.setObjectName('nav');b.setCheckable(True);b.setChecked(i==0);b.setCursor(Qt.PointingHandCursor);b.clicked.connect(lambda _,n=i:self.navigate(n));sl.addWidget(b);self.nav.append(b)
        sl.addStretch();sl.addWidget(label('ТВОЙ КУЛЬТ.\nТВОИ ПРАВИЛА.','slogan'))
        self.top=QCheckBox('Поверх окон');self.top.toggled.connect(self.pin);sl.addWidget(self.top)
        sl.addWidget(label('RU   /   ВЕРСИЯ 1.4','eyebrow'));outer.addWidget(side)
        area=QWidget();al=QVBoxLayout(area);al.setContentsMargins(30,24,30,18);al.setSpacing(18)
        header=QHBoxLayout();header.addWidget(label('ЦЕНТР УПРАВЛЕНИЯ','eyebrow'));header.addStretch();self.connection=label('●  Ожидание игры','connection');header.addWidget(self.connection);al.addLayout(header)
        al.addWidget(self.pages,1);outer.addWidget(area,1)
        self.build_controls();self.build_quests();self.build_dlc();self.build_help();self.build_about()
        self.last_show_request=(backend.ROOT/'show.txt').stat().st_mtime_ns if (backend.ROOT/'show.txt').exists() else 0
        self.timer=QTimer(self);self.timer.timeout.connect(self.tick)
        if not preview:self.timer.start(500)
        self.hotkey_timer=QTimer(self);self.hotkey_timer.timeout.connect(self.hotkeys)
        if not preview:self.hotkey_timer.start(35)
        self.setStyleSheet(STYLE)
        if self.game:self.path_label.setText('Steam · игра найдена')
        if resume and resume.get('ready'):
            for i,value in enumerate(resume['flags'][:10]):self.toggles[i].setChecked(value=='1')
            self.dlc_toggle.setChecked(resume.get('dlc',False))
        self.tick()
    def navigate(self,n):
        self.pages.setCurrentIndex(n)
        for i,b in enumerate(self.nav):b.setChecked(i==n)
        self.tick()
    def build_controls(self):
        page=QWidget();layout=QVBoxLayout(page);layout.setContentsMargins(0,0,0,0);layout.setSpacing(16)
        hero=QFrame();hero.setObjectName('hero');hl=QHBoxLayout(hero);hl.setContentsMargins(24,12,15,12)
        text=QVBoxLayout();text.addWidget(label('ВЛАСТЬ НАД НЕИЗВЕДАННЫМ','accent'));text.addWidget(label('Во имя Агнца','title'));text.addWidget(label('Настрой своё путешествие. Возглавь идеальный культ.','muted'));hl.addLayout(text,1);hl.addWidget(Sigil(hero=True));layout.addWidget(hero)
        bar=QHBoxLayout();bar.addWidget(label('Возможности','section'));self.counter=label('0 / 10 ВКЛЮЧЕНО','eyebrow');bar.addStretch();bar.addWidget(self.counter);layout.addLayout(bar)
        grid=QGridLayout();grid.setSpacing(10);self.toggles=[];self.cards=[];self.ack=[]
        for i,(title,desc,glyph,key) in enumerate(FEATURES):
            card=QFrame();card.setObjectName('card');cl=QVBoxLayout(card);cl.setContentsMargins(15,10,15,10);cl.setSpacing(5)
            row=QHBoxLayout();ico=label(glyph,'glyph');ico.setFixedWidth(24);row.addWidget(ico);row.addWidget(label(title,'cardtitle'));row.addStretch();toggle=Toggle();toggle.setAccessibleName(title);toggle.toggled.connect(lambda on,n=i:self.setflag(n,on));row.addWidget(toggle);cl.addLayout(row)
            description=label(desc,'description');description.setWordWrap(True);cl.addWidget(description)
            bottom=QHBoxLayout();bottom.addWidget(label(key,'key'));bottom.addStretch();ack=label('Выключено','small');bottom.addWidget(ack);cl.addLayout(bottom)
            grid.addWidget(card,i//2,i%2);self.toggles.append(toggle);self.cards.append(card);self.ack.append(ack)
        layout.addLayout(grid,1)
        options=QHBoxLayout();options.addWidget(label('Множитель ресурсов','muted'));self.multiplier=QSpinBox();self.multiplier.setRange(2,100);self.multiplier.setValue(10);self.multiplier.setPrefix('× ');self.multiplier.valueChanged.connect(lambda _:self.tick());options.addWidget(self.multiplier);options.addStretch();off=QPushButton('Отключить всё');off.setObjectName('secondary');off.clicked.connect(self.alloff);options.addWidget(off);layout.addLayout(options)
        footer=QFrame();footer.setObjectName('footer');fl=QHBoxLayout(footer);fl.setContentsMargins(16,12,16,12);status=QVBoxLayout();self.path_label=label('Укажи папку игры','cardtitle');status.addWidget(self.path_label);self.detail=label('Модуль подключится после запуска игры.','small');status.addWidget(self.detail);fl.addLayout(status,1);self.launch=QPushButton('Запустить игру');self.launch.setObjectName('primary');self.launch.clicked.connect(self.launch_game);fl.addWidget(self.launch);layout.addWidget(footer)
        layout.addWidget(label('Insert  ·  открыть трейнер из игры     /     F1–F10  ·  функции     /     Ctrl + F12  ·  отключить всё','small'))
        self.pages.addWidget(page)
    def build_help(self):
        p=QWidget();l=QVBoxLayout(p);l.setContentsMargins(0,10,0,0);l.setSpacing(20);l.addWidget(label('Как пользоваться','title'))
        for title,text in [
            ('01   Запусти игру','Нажми «Запустить игру». Трейнер установит модуль и создаст резервную копию существующих сохранений. Если игра уже открыта без модуля, её нужно перезапустить.'),
            ('02   Дождись подключения','Зелёный индикатор подтверждает связь с игровым модулем. В главном меню можно выбрать функции заранее; их игровой эффект применяется после загрузки сохранения.'),
            ('03   Включи нужные функции','Используй переключатели или F1–F10. Подпись «Активно» появляется после подтверждения от игры. Ctrl + F12 отключает всё.'),
            ('04   Заверши сеанс','При закрытии трейнера функции отключаются. При аварийном завершении связь истекает через 5 секунд. Уже полученные предметы и изменения показателей остаются в сохранении.'),
            ('Особенности функций','Мгновенная молитва ускоряет получение преданности у святилища. Множитель применяется к подбираемым ресурсам. «Без инакомыслия» предотвращает новые бунты; существующий бунт может требовать перевоспитания. Функции потребностей действуют при обновлении показателей последователей.')]:
            l.addWidget(label(title,'section'));w=label(text,'muted');w.setWordWrap(True);l.addWidget(w)
        l.addStretch();b=QPushButton('Открыть резервные копии');b.setObjectName('secondary');b.clicked.connect(lambda:QDesktopServices.openUrl(QUrl.fromLocalFile(str(backend.ROOT/'backups'))));l.addWidget(b);self.pages.addWidget(p)
    def build_dlc(self):
        p=QWidget();l=QVBoxLayout(p);l.setContentsMargins(0,10,0,0);l.setSpacing(18)
        l.addWidget(label('Дополнения','title'))
        w=label('Открой доступ к контенту DLC, который уже содержится в установленных файлах игры.','muted');w.setWordWrap(True);l.addWidget(w)
        card=QFrame();card.setObjectName('card');cl=QVBoxLayout(card);cl.setContentsMargins(22,20,22,20);row=QHBoxLayout();row.addWidget(label('Открыть все DLC','section'));row.addStretch();self.dlc_toggle=Toggle();self.dlc_toggle.setAccessibleName('Открыть все DLC');self.dlc_toggle.toggled.connect(lambda _:self.tick());row.addWidget(self.dlc_toggle);cl.addLayout(row)
        self.dlc_status=label('Выключено','accent');cl.addWidget(self.dlc_status);l.addWidget(card)
        for name,desc in [('Cultist Pack','Формы последователей и украшения'),('Heretic Pack','Формы, украшения и одеяние'),('Sinful Pack','Дополнительные облики, наряды и украшения'),('Pilgrim Pack','Контент набора Pilgrim'),('Woolhaven','Доступ к содержимому основного сюжетного дополнения'),('Бонусные наборы','Бонусы предзаказа, Plush и PAX')]:
            row=QHBoxLayout();row.addWidget(label(name,'cardtitle'));row.addStretch();row.addWidget(label(desc,'small'));l.addLayout(row)
        l.addStretch();w=label('Включи переключатель в главном меню и загрузи сохранение. При включении в культе игра повторно проверит дополнения. Сюжетные условия открытия локаций сохраняются.\n\nТрейнер нужно оставить открытым. Функция действует в локальной игре и не изменяет покупки в Steam.','muted');w.setWordWrap(True);l.addWidget(w);self.pages.addWidget(p)
    def build_quests(self):
        p=QWidget();l=QVBoxLayout(p);l.setContentsMargins(0,10,0,0);l.setSpacing(18)
        l.addWidget(label('Квесты одним кликом','title'))
        w=label('Здесь появятся задания из списка справа в игре. Нажми «Выполнить» рядом с нужной целью.','muted');w.setWordWrap(True);l.addWidget(w)
        self.quest_message=label('Загрузи сохранение и дождись подключения.','accent');self.quest_message.setWordWrap(True);l.addWidget(self.quest_message)
        scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setFrameShape(QFrame.NoFrame);scroll.setStyleSheet('QScrollArea {background:transparent;}')
        content=QWidget();content.setStyleSheet('background:transparent;');self.quest_layout=QVBoxLayout(content);self.quest_layout.setContentsMargins(0,0,6,0);self.quest_layout.setSpacing(12);self.quest_layout.addStretch();scroll.setWidget(content);l.addWidget(scroll,1)
        w=label('Выполнение сохраняет прогресс квеста. Если игра требует разговора для награды, поговори с персонажем. Перед действием создаётся резервная копия сохранений.','small');w.setWordWrap(True);l.addWidget(w)
        self.quest_snapshot=None;self.pending_quest=None;self.quest_buttons=[];self.pages.addWidget(p)
    def update_quests(self):
        if not hasattr(self,'quest_message') or self.preview:return
        if self.pages.currentIndex()!=1 and not self.pending_quest:return
        data=backend.quests() if self.state and self.state['ready'] else None
        if self.pending_quest:
            request,stamp=self.pending_quest;result=backend.quest_result(request)
            if result:
                self.quest_message.setText(result[1]);self.pending_quest=None
            elif time.monotonic()-stamp>12:
                self.quest_message.setText('Нет подтверждения от игры. Проверь соединение и список заданий.');self.pending_quest=None
        if data==self.quest_snapshot:
            for b in self.quest_buttons:b.setEnabled(not self.pending_quest)
            return
        self.quest_snapshot=data
        while self.quest_layout.count()>1:
            item=self.quest_layout.takeAt(0)
            if item.widget():item.widget().deleteLater()
        self.quest_buttons=[]
        if not data:
            self.quest_message.setText('Нет связи с модулем квестов. Запусти или перезапусти игру.')
            return
        if not data['items']:
            self.quest_message.setText('Сейчас нет незавершённых отслеживаемых целей. Загрузи сохранение или выбери квест в игре.')
        elif not self.pending_quest and not self.quest_message.text().startswith('Задание выполнено'):
            self.quest_message.setText(f"Целей на экране: {len(data['items'])}")
        for item in data['items']:
            card=QFrame();card.setObjectName('card');cl=QHBoxLayout(card);cl.setContentsMargins(20,18,20,18);texts=QVBoxLayout();title=label(item['title'],'section');title.setWordWrap(True);texts.addWidget(title);text=label(item['text'],'muted');text.setWordWrap(True);texts.addWidget(text);cl.addLayout(texts,1)
            b=QPushButton('Выполнить');b.setObjectName('primary');b.setEnabled(not self.pending_quest);b.clicked.connect(lambda _,s=data['session'],k=item['key']:self.finish_quest(s,k));cl.addWidget(b);self.quest_buttons.append(b);self.quest_layout.insertWidget(self.quest_layout.count()-1,card)
    def finish_quest(self,session,key):
        if self.pending_quest:return
        try:
            request=backend.complete_quest(session,key);self.pending_quest=(request,time.monotonic());self.quest_message.setText('Завершаю выбранную цель…')
            for b in self.quest_buttons:b.setEnabled(False)
        except Exception as e:self.quest_message.setText('Не удалось выполнить задание: '+str(e))
    def build_about(self):
        p=QWidget();l=QVBoxLayout(p);l.setContentsMargins(0,10,0,0);l.setSpacing(20);l.addWidget(label('Cult Trainer RU','title'));l.addWidget(label('Создан для твоего путешествия.','section'))
        w=label('Русскоязычный трейнер для Windows и Steam-версии Cult of the Lamb на Unity Mono. 10 функций, горячие клавиши и подтверждение подключения.\n\nПодготовлен для установленной сборки Steam 25223484. Обновления игры могут потребовать обновления модуля.\n\nМодуль: BepInEx 5.4.23.6 и HarmonyX. Оригинальные игровые сборки не заменяются.\n\nНеофициальный проект. Не связан с Massive Monster, Devolver Digital или WeMod.','muted');w.setWordWrap(True);l.addWidget(w)
        b=QPushButton('Выбрать папку игры');b.setObjectName('secondary');b.clicked.connect(self.choose_game);l.addWidget(b)
        b=QPushButton('Открыть журнал модуля');b.setObjectName('secondary');b.clicked.connect(self.open_log);l.addWidget(b)
        b=QPushButton('Удалить установленный модуль');b.setObjectName('secondary');b.clicked.connect(self.remove_mod);l.addWidget(b);l.addStretch();self.pages.addWidget(p)
    def pin(self,on):
        self.setWindowFlag(Qt.WindowStaysOnTopHint,on);self.show()
    def setflag(self,n,on):
        self.flags[n]=on;self.cards[n].setProperty('active',on);self.cards[n].style().unpolish(self.cards[n]);self.cards[n].style().polish(self.cards[n]);self.tick()
    def alloff(self):
        self.dlc_toggle.setChecked(False)
        for t in self.toggles:t.setChecked(False)
        self.tick()
    def tick(self):
        if not hasattr(self,'multiplier'):return
        if not self.preview:
            self.check_show_request()
            try:backend.send(self.flags,self.multiplier.value(),(self.pages.currentIndex()==1 and not self.isMinimized()) or self.pending_quest is not None,self.dlc_toggle.isChecked());self.state=backend.status()
            except OSError as e:self.detail.setText('Ошибка связи: '+str(e))
        self.counter.setText(f'{sum(self.flags)} / 10 ВКЛЮЧЕНО')
        connected=bool(self.state and self.state['ready'])
        self.connection.setText('●  Игра подключена' if connected else ('●  Ошибка модуля' if self.state else '●  Ожидание игры'))
        self.connection.setStyleSheet('color: #81c9ac;' if connected else 'color: #c7ab80;')
        for i,ack in enumerate(self.ack):
            confirmed=connected and self.state['flags'][i:i+1]=='1'
            ack.setText(('Активно' if confirmed else 'Ожидает подключения' if not connected else 'Применяется…') if self.flags[i] else ('Отключается…' if confirmed else 'Выключено'))
            ack.setStyleSheet('color:#dc687f;' if self.flags[i] else '')
        if self.dlc_toggle.isChecked():
            self.dlc_status.setText('Доступ открыт' if connected and self.state.get('dlc') else 'Перезапусти игру для модуля 1.4' if connected and self.state.get('version') not in ('1.3','1.4') else 'Ожидает подтверждения от игры')
        else:self.dlc_status.setText('Выключено')
        if connected:self.detail.setText('Для кнопки в игре перезапусти игру: установлен модуль 1.4.' if self.state.get('version')!='1.4' else f"Модуль 1.4 готов · {self.state['hooks']} подключений · {self.state['scene']}")
        elif self.state:self.detail.setText(self.state['error'][:110])
        else:self.detail.setText('Запусти игру и дождись подключения модуля.')
        self.update_quests()
    def check_show_request(self):
        try:stamp=(backend.ROOT/'show.txt').stat().st_mtime_ns
        except OSError:return
        if stamp<=self.last_show_request:return
        self.last_show_request=stamp
        self.showNormal();self.raise_();self.activateWindow()
        if sys.platform=='win32':
            hwnd=int(self.winId());ctypes.windll.user32.ShowWindow(hwnd,9);ctypes.windll.user32.SetForegroundWindow(hwnd)
    def hotkeys(self):
        # Poll global key transitions so the keys work while the game has focus.
        if sys.platform!='win32':return
        for i,key in enumerate(range(0x70,0x7a)):
            pressed=bool(ctypes.windll.user32.GetAsyncKeyState(key)&0x8000)
            if pressed and not self.keys.get(key,False):self.toggles[i].toggle()
            self.keys[key]=pressed
        combo=bool(ctypes.windll.user32.GetAsyncKeyState(0x7b)&0x8000) and bool(ctypes.windll.user32.GetAsyncKeyState(0x11)&0x8000)
        if combo and not self.keys.get('off',False):self.alloff()
        self.keys['off']=combo
    def choose_game(self):
        folder=QFileDialog.getExistingDirectory(self,'Папка Cult of the Lamb',str(self.game or Path.home()))
        if folder:
            p=Path(folder)
            if not (p/backend.GAME_EXE).exists():QMessageBox.warning(self,'Папка игры','Здесь нет Cult Of The Lamb.exe.');return
            self.game=p;(backend.ROOT/'game.txt').write_text(str(p),encoding='utf-8');self.path_label.setText('Папка игры выбрана')
    def launch_game(self):
        if not self.game:self.choose_game()
        if not self.game:return
        if self.state: self.activateWindow();return
        self.launch.setEnabled(False);self.detail.setText('Подготовка модуля и резервной копии…');QApplication.processEvents()
        try:
            backend.install(self.game)
            os.startfile('steam://rungameid/1313140')
            self.detail.setText('Игра запускается. Если она уже открыта — перезапусти её.')
        except Exception as e:QMessageBox.warning(self,'Не удалось запустить',str(e))
        finally:self.launch.setEnabled(True)
    def open_log(self):
        p=self.game/'BepInEx/LogOutput.log' if self.game else backend.ROOT
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(p)))
    def remove_mod(self):
        if backend.status():QMessageBox.information(self,'Закрой игру','Сначала закрой игру, затем нажми эту кнопку ещё раз.');return
        self.alloff()
        try:backend.uninstall();QMessageBox.information(self,'Готово','Установленные трейнером файлы удалены. Резервные копии сохранены.')
        except Exception as e:QMessageBox.warning(self,'Ошибка удаления',str(e))
    def closeEvent(self,e):
        if not self.preview:backend.disable()
        e.accept()

STYLE='''
QWidget {font-family: 'Segoe UI';font-size:13px;color:#e9e3de;}
QWidget#root {background:#14141b;} QFrame#sidebar {background:#101016;border-right:1px solid #2b2732;}
QLabel {background:transparent;} QLabel#brand {font-size:25px;font-weight:800;letter-spacing:1px;}
QLabel#eyebrow {font-size:10px;font-weight:600;color:#85808e;letter-spacing:1.5px;}
QLabel#accent {font-size:10px;font-weight:700;color:#dc687f;letter-spacing:1.4px;}
QLabel#title {font-family:'Georgia';font-size:36px;color:#f4e9de;font-weight:700;}
QLabel#section {font-size:18px;font-weight:600;} QLabel#slogan {font-family:'Georgia';font-size:19px;color:#a397a1;line-height:1.4;}
QLabel#muted {color:#aaa2af;font-size:13px;} QLabel#small {color:#847e8e;font-size:10px;}
QLabel#description {color:#a29aaa;font-size:11px;}
QLabel#cardtitle {font-size:13px;font-weight:600;}
QLabel#glyph {color:#df657c;font-family:'Segoe UI Symbol';font-size:22px;}
QLabel#key {color:#88818f;font-size:10px;background:#27242e;border:1px solid #39313f;border-radius:4px;padding:1px 6px;}
QLabel#connection {font-size:11px;background:#211e24;border:1px solid #3d333b;border-radius:14px;padding:7px 12px;}
QFrame#hero {background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #30202a,stop:1 #1c1923);border:1px solid #57303d;border-radius:14px;}
QFrame#card {background:#1c1b24;border:1px solid #302c39;border-radius:10px;}
QFrame#card[active=true] {background:#2a1d29;border:1px solid #934052;}
QFrame#footer {background:#1c1b24;border:1px solid #302c39;border-radius:10px;}
QPushButton {border:0;border-radius:7px;padding:10px 14px;font-weight:600;}
QPushButton#nav {text-align:left;background:transparent;color:#9b93a5;padding:12px 10px;}
QPushButton#nav:checked {background:#30212c;color:#f1bbc8;border:1px solid #56303f;}
QPushButton#nav:hover {background:#25202c;}
QPushButton#primary {background:#bf3e58;color:#fff0eb;padding:12px 20px;}
QPushButton#primary:hover {background:#d94e69;} QPushButton#primary:disabled {background:#4a2c38;color:#9a7b85;}
QPushButton#secondary {background:#27232e;border:1px solid #443647;color:#d3bfcc;}
QPushButton#secondary:hover {background:#362939;}
QSpinBox {background:#27232e;border:1px solid #443647;border-radius:6px;padding:5px 10px;min-width:66px;}
QCheckBox {color:#9d93a6;font-size:12px;spacing:9px;}
QCheckBox::indicator {width:14px;height:14px;border:1px solid #514454;border-radius:4px;background:#24202b;}
QCheckBox::indicator:checked {background:#bf3e58;border-color:#dc687f;}
QMessageBox {background:#1c1b24;} QToolTip {background:#27232e;color:#eee0e5;border:1px solid #553b4d;}
'''

def main():
    app=QApplication(sys.argv);app.setApplicationName('Cult Trainer RU')
    for name in ['segoeui.ttf','segoeuib.ttf','seguisym.ttf','georgia.ttf','georgiab.ttf']:
        QFontDatabase.addApplicationFont(str(Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts'/name))
    app.setFont(QFont('Segoe UI',10))
    preview='--preview' in sys.argv
    lock=QLockFile(str(backend.ROOT/'trainer.lock'));lock.setStaleLockTime(0)
    if not preview and not lock.tryLock(100):
        backend.request_show();return
    if not preview:backend.register_launcher()
    window=Trainer(preview);window.show()
    if preview:
        QTimer.singleShot(500,lambda:(window.grab().save(str(Path(__file__).parent/'preview.png')),app.quit()))
    sys.exit(app.exec())

if __name__=='__main__':main()
