"""Installation and file IPC for the local Unity Mono plugin."""
import os, sys, re, json, shutil, hashlib, time, uuid, base64
from pathlib import Path

ROOT = Path(os.environ['LOCALAPPDATA']) / 'CultTrainerRU'
ROOT.mkdir(parents=True, exist_ok=True)
ASSETS = Path(getattr(sys, '_MEIPASS', Path(__file__).parent))
GAME_EXE = 'Cult Of The Lamb.exe'

def find_game():
    import winreg
    paths = [Path(r'C:\Program Files (x86)\Steam')]
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Valve\Steam') as k:
            paths.insert(0, Path(winreg.QueryValueEx(k, 'SteamPath')[0]))
    except OSError:
        pass
    for steam in list(paths):
        vdf = steam / 'steamapps/libraryfolders.vdf'
        if vdf.exists():
            paths.extend(Path(p.replace('\\\\', '\\')) for p in re.findall(r'"path"\s+"([^"]+)"', vdf.read_text(encoding='utf-8')))
    for steam in paths:
        game = steam / 'steamapps/common/Cult of the Lamb'
        if (game / GAME_EXE).exists():
            return game
    config = ROOT / 'game.txt'
    if config.exists():
        game = Path(config.read_text(encoding='utf-8'))
        if (game / GAME_EXE).exists(): return game
    return None

def backup_saves():
    saves = Path(os.environ['USERPROFILE']) / 'AppData/LocalLow/Massive Monster/Cult Of The Lamb'
    if saves.exists():
        target = ROOT / 'backups' / time.strftime('%Y%m%d-%H%M%S')
        shutil.copytree(saves, target, ignore=shutil.ignore_patterns('Player.log', 'Player-prev.log', '*.tmp'))
        return str(target)
    return ''

def install(game):
    game = Path(game)
    if not (game / GAME_EXE).exists(): raise RuntimeError('В выбранной папке нет Cult Of The Lamb.exe')
    mono = game / 'Cult Of The Lamb_Data/Managed/Assembly-CSharp.dll'
    if not mono.exists(): raise RuntimeError('Нужна версия игры Unity Mono.')
    backup = backup_saves()
    own = game / 'BepInEx/plugins/CultTrainerRU/CultTrainer.dll'
    manifest_path = ROOT / 'installed.json'
    record = json.loads(manifest_path.read_text(encoding='utf-8')) if manifest_path.exists() else {'files': {}}
    if record.get('game') and record['game'] != str(game): record = {'files': {}}
    record['game'] = str(game)
    record['backup'] = backup or record.get('backup', '')
    loader = ASSETS / 'tools/bepinex'
    if not (game / 'winhttp.dll').exists():
        for source in loader.rglob('*'):
            if not source.is_file(): continue
            rel = str(source.relative_to(loader))
            dest = game / rel
            if dest.exists(): continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, dest)
            record['files'][rel] = hashlib.sha256(dest.read_bytes()).hexdigest()
    elif not (game / 'BepInEx/core/BepInEx.dll').exists():
        raise RuntimeError('В папке игры уже есть другой winhttp.dll. Он сохранён; автоматическая установка остановлена.')
    if own.exists() and own.read_bytes() != (ASSETS / 'plugin/CultTrainer.dll').read_bytes():
        backup_file = ROOT / 'backups' / ('CultTrainer-' + time.strftime('%Y%m%d-%H%M%S') + '.dll')
        backup_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(own, backup_file)
    own.parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copy2(ASSETS / 'plugin/CultTrainer.dll', own)
    except OSError as error:
        if getattr(error,'winerror',None) != 1224: raise
        # Windows allows renaming this mapped Mono image, but blocks overwriting
        # it. Keep the loaded image intact while placing the next version beside it.
        previous=own.with_name('CultTrainer.loaded-'+uuid.uuid4().hex+'.bak')
        if previous.resolve().parent != own.resolve().parent: raise RuntimeError('Некорректный путь резервной копии модуля')
        os.replace(own,previous)
        record['files'][str(previous.relative_to(game))]=hashlib.sha256(previous.read_bytes()).hexdigest()
        try: shutil.copy2(ASSETS / 'plugin/CultTrainer.dll', own)
        except OSError:
            os.replace(previous,own)
            raise
    record['files'][str(own.relative_to(game))] = hashlib.sha256(own.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    (ROOT / 'game.txt').write_text(str(game), encoding='utf-8')
    return backup

_last_payload=None
_last_heartbeat=0
_last_view=0
_read_cache={}

def read_cached(path):
    stamp=path.stat().st_mtime_ns
    cached=_read_cache.get(str(path))
    if cached and cached[0]==stamp:return cached[1]
    value=path.read_text(encoding='utf-8-sig')
    _read_cache[str(path)]=(stamp,value)
    return value

def send(flags, multiplier=10, quest_view=False, dlc_unlock=False):
    global _last_payload,_last_heartbeat,_last_view
    payload='|'.join(['1' if f else '0' for f in flags] + [str(multiplier)])
    now=time.monotonic()
    target=ROOT/'command.txt'
    if payload!=_last_payload or not target.exists():
        temporary=ROOT/'command.new'
        temporary.write_text(payload,encoding='ascii')
        os.replace(temporary,target)
        _last_payload=payload;_last_heartbeat=now
    elif now-_last_heartbeat>=1:
        os.utime(target,None);_last_heartbeat=now
    view=ROOT/'quest-view.txt'
    if quest_view:
        if now-_last_view>=0.75 or not view.exists():
            view.touch();_last_view=now
    elif view.exists():view.unlink()
    dlc=ROOT/'dlc-unlock.txt'
    if dlc_unlock:
        if not dlc.exists():dlc.write_text('1',encoding='ascii')
    elif dlc.exists():dlc.unlink()

def status():
    try:
        p = ROOT / 'status.txt'
        if time.time() - p.stat().st_mtime > 3: return None
        lines = read_cached(p).splitlines()
        return {'ready': lines[0] == 'ready', 'pid': int(lines[1]), 'scene': lines[2], 'flags': lines[3], 'hooks': int(lines[4]), 'error': lines[5] if len(lines)>5 else '', 'version':next((x[8:] for x in lines if x.startswith('version=')),'1.0'), 'session':next((x[8:] for x in lines if x.startswith('session=')),None), 'dlc':'dlc=1' in lines}
    except (OSError, ValueError, IndexError): return None

def disable():
    send([False] * 10)

def register_launcher():
    executable=Path(sys.executable) if getattr(sys,'frozen',False) else ASSETS/'dist/CultTrainerRU.exe'
    if executable.is_file(): (ROOT/'launcher.txt').write_text(str(executable.resolve()),encoding='utf-8')

def request_show():
    temporary=ROOT/'show.new'
    temporary.write_text(uuid.uuid4().hex,encoding='ascii')
    os.replace(temporary,ROOT/'show.txt')

def quests():
    try:
        path = ROOT / 'quests.txt'
        current=status()
        if not current:return None
        lines = read_cached(path).splitlines()
        if current.get('session') and lines[0]!=current['session']:return None
        rows=[]
        for line in lines[1:]:
            key,title,text=line.split('\t')
            decode=lambda s: re.sub('<[^>]+>', '', base64.b64decode(s).decode('utf-8')).strip()
            rows.append({'key':key,'title':decode(title) or 'Текущее задание','text':decode(text) or 'Выполнить цель'})
        return {'session':lines[0],'items':rows}
    except (OSError, ValueError, IndexError): return None

def complete_quest(session,key):
    backup_saves()
    request=uuid.uuid4().hex
    p=ROOT/'quest-command.new'
    p.write_text('|'.join([request,session,key]),encoding='ascii')
    os.replace(p,ROOT/'quest-command.txt')
    return request

def quest_result(request):
    try:
        rid,result,message=(ROOT/'quest-result.txt').read_text(encoding='utf-8-sig').strip().split('|')
        if rid==request:return result,base64.b64decode(message).decode('utf-8')
    except (OSError, ValueError): pass
    return None

def uninstall():
    disable()
    path = ROOT / 'installed.json'
    if not path.exists(): return
    data = json.loads(path.read_text(encoding='utf-8'))
    game = Path(data['game']).resolve()
    for rel, digest in data['files'].items():
        dest = (game / rel).resolve()
        if game not in dest.parents: raise RuntimeError('Некорректный путь в журнале установки')
        if dest.is_file() and hashlib.sha256(dest.read_bytes()).hexdigest() == digest: dest.unlink()
    path.unlink()
