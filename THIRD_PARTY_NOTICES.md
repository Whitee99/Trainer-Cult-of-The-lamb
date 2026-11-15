# Зависимости

Проект использует следующие сторонние компоненты. Их исходники, условия лицензий и сведения об авторах доступны в официальных репозиториях:

- BepInEx 5.4.23.6: https://github.com/BepInEx/BepInEx/tree/v5.4.23.6
- HarmonyX и компоненты MonoMod/Mono.Cecil из официального дистрибутива BepInEx: https://github.com/BepInEx/HarmonyX, https://github.com/MonoMod/MonoMod, https://github.com/jbevain/cecil
- PySide6 / Qt for Python: https://code.qt.io/pyside/pyside-setup.git/, https://www.qt.io/licensing/
- PyInstaller: https://github.com/pyinstaller/pyinstaller, https://pyinstaller.org/en/stable/license.html

Исходные игровые DLL и ресурсы Cult of the Lamb в репозиторий не включаются. Для пересборки игрового модуля необходима локально установленная игра. Дистрибутив BepInEx загружается отдельным скриптом с проверкой SHA-256.
