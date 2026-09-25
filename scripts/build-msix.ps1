# Package dist\Ujto (PyInstaller one-dir) as an MSIX for the Microsoft Store.
#   pwsh scripts/build-msix.ps1 -Edition store|full
# Identity values come from Partner Center (App → Product identity), via environment variables:
#   MSSTORE_IDENTITY_NAME, MSSTORE_PUBLISHER (CN=…), MSSTORE_PUBLISHER_DISPLAY_NAME
# Without them it uses placeholders (fine for checking the package, not for submission).
# Store submissions don't need signing: the Store signs the package.
param([ValidateSet("store", "full")][string]$Edition = "store")
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

$version = (python -c "import ujto_desktop; print(ujto_desktop.__version__)").Trim()
$parts = $version.Split(".") + @("0", "0", "0")
$msixVersion = "{0}.{1}.{2}.0" -f $parts[0], $parts[1], $parts[2]   # Store requires the 4th part = 0

$identity = if ($env:MSSTORE_IDENTITY_NAME) { $env:MSSTORE_IDENTITY_NAME } else { "PacificCodeLabs.Ujto" }
$publisher = if ($env:MSSTORE_PUBLISHER) { $env:MSSTORE_PUBLISHER } else { "CN=00000000-0000-0000-0000-000000000000" }
$publisherName = if ($env:MSSTORE_PUBLISHER_DISPLAY_NAME) { $env:MSSTORE_PUBLISHER_DISPLAY_NAME } else { "Pacific Code Labs" }

$layout = "build\msix-$Edition"
if (Test-Path $layout) { Remove-Item -Recurse -Force $layout }
New-Item -ItemType Directory -Force "$layout\Assets" | Out-Null
Copy-Item -Recurse "dist\Ujto\*" $layout
Copy-Item "build\msix-assets\*" "$layout\Assets"

$manifest = Get-Content "packaging\windows\msix\AppxManifest.xml" -Raw -Encoding UTF8
$manifest = $manifest.Replace("{{IDENTITY_NAME}}", $identity).Replace("{{PUBLISHER}}", $publisher)
$manifest = $manifest.Replace("{{PUBLISHER_DISPLAY_NAME}}", $publisherName).Replace("{{VERSION}}", $msixVersion)
$manifest = $manifest.Replace("{{DISPLAY_NAME}}", "Ujtö̀")
[System.IO.File]::WriteAllText((Join-Path (Get-Location) "$layout\AppxManifest.xml"), $manifest, (New-Object System.Text.UTF8Encoding $false))

# makeappx ships with the Windows SDK (present on GitHub's windows runners).
$makeappx = Get-ChildItem "${env:ProgramFiles(x86)}\Windows Kits\10\bin\*\x64\makeappx.exe" |
  Sort-Object FullName -Descending | Select-Object -First 1
if (-not $makeappx) { throw "makeappx.exe not found (install the Windows 10/11 SDK)" }

$suffix = if ($Edition -eq "store") { "-store" } else { "" }
$out = "dist\Ujto-windows-x64$suffix.msix"
& $makeappx.FullName pack /o /d $layout /p $out
if ($LASTEXITCODE -ne 0) { throw "makeappx failed" }
Write-Host "MSIX ($Edition, $msixVersion): $out"
