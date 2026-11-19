param([string]$Python = "python", [string]$Iscc = "ISCC.exe")
$ErrorActionPreference = "Stop"
Push-Location (Join-Path $PSScriptRoot "..")
try {
    $work = Join-Path $PWD "outputs/release-work"
    New-Item -ItemType Directory -Force $work | Out-Null
    & $Python packaging/icon.py
    if ($LASTEXITCODE) { throw "Icon generation failed" }
    & $Python -m PyInstaller --noconfirm --windowed --onedir --name KnowledgeMotion --distpath "$work/dist" --workpath "$work/build" --specpath "$work" --paths . --add-data "${PWD}/web;web" --add-data "$work/library.ico;." --icon "$work/library.ico" --collect-data opencc --exclude-module matplotlib --exclude-module scipy --exclude-module IPython --exclude-module pytest desktop.py
    if ($LASTEXITCODE) { throw "PyInstaller failed" }
    & $Python packaging/copy_licenses.py
    if ($LASTEXITCODE) { throw "Copying third-party notices failed" }
    & $Iscc packaging/installer.iss
    if ($LASTEXITCODE) { throw "Installer compilation failed" }
} finally { Pop-Location }

