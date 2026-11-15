$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    $gamePath = python -c "import backend; print(backend.find_game() or '')"
    if (-not $gamePath) { throw 'Cult of the Lamb не найдена в библиотеках Steam.' }
    $managedPath = Join-Path $gamePath 'Cult Of The Lamb_Data\Managed'
    $compilerPath = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
    $references = @('mscorlib.dll','System.dll','System.Core.dll','netstandard.dll','Assembly-CSharp.dll','UnityEngine.dll','UnityEngine.CoreModule.dll','UnityEngine.IMGUIModule.dll','UnityEngine.InputLegacyModule.dll','UnityEngine.TextRenderingModule.dll') | ForEach-Object { '/r:' + (Join-Path $managedPath $_) }
    & $compilerPath /nologo /noconfig /nostdlib /target:library /out:plugin\CultTrainer.dll /r:tools\bepinex\BepInEx\core\BepInEx.dll /r:tools\bepinex\BepInEx\core\0Harmony.dll @references plugin\CultTrainer.cs
    if ($LASTEXITCODE -ne 0) { throw 'Ошибка сборки игрового модуля.' }
    python -m PyInstaller --noconfirm CultTrainerRU.spec
    if ($LASTEXITCODE -ne 0) { throw 'Ошибка сборки интерфейса.' }
} finally { Pop-Location }
