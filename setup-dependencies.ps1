$ErrorActionPreference = 'Stop'
$dependencyPath = Join-Path $PSScriptRoot 'tools\bepinex'
$archivePath = Join-Path ([IO.Path]::GetTempPath()) ('cult-bepinex-' + [Guid]::NewGuid().ToString('N') + '.zip')
$downloadUrl = 'https://github.com/BepInEx/BepInEx/releases/download/v5.4.23.6/BepInEx_win_x64_5.4.23.6.zip'
Invoke-WebRequest -Uri $downloadUrl -OutFile $archivePath
$archiveHash = (Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash
if ($archiveHash -ne '6C57A714A892EFB4E9E1FEF63D608A3391F30EC984031C465404E4EE381A0755') {
    throw 'Контрольная сумма архива BepInEx не совпала.'
}
Expand-Archive -LiteralPath $archivePath -DestinationPath $dependencyPath -Force
$configPath = Join-Path $dependencyPath 'BepInEx\config\BepInEx.cfg'
New-Item -ItemType Directory -Path (Split-Path $configPath) -Force | Out-Null
if (-not (Test-Path -LiteralPath $configPath)) {
    Set-Content -LiteralPath $configPath -Value "[Chainloader]`nHideManagerGameObject = true`n" -Encoding UTF8
}
Remove-Item -LiteralPath $archivePath
Write-Output 'BepInEx 5.4.23.6 загружен и проверен.'
