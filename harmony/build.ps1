$ErrorActionPreference = 'Stop'

$uninstallRoots = @(
    'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*',
    'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*',
    'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*'
)

$installation = Get-ItemProperty $uninstallRoots -ErrorAction SilentlyContinue |
    Where-Object { $_.DisplayName -eq 'DevEco Studio' -and $_.InstallLocation } |
    Select-Object -First 1

if ($null -eq $installation) {
    throw 'DevEco Studio was not found. Install DevEco Studio 6.1 or later.'
}

$studioHome = $installation.InstallLocation.TrimEnd([char]92)
$hvigor = Join-Path $studioHome 'tools\hvigor\bin\hvigorw.bat'
if (-not (Test-Path -LiteralPath $hvigor)) {
    throw "Hvigor was not found: $hvigor"
}

$env:DEVECO_SDK_HOME = Join-Path $studioHome 'sdk'
$env:NODE_HOME = Join-Path $studioHome 'tools\node'

& $hvigor @args
exit $LASTEXITCODE
