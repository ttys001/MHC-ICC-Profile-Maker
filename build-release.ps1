param(
    [Parameter(Mandatory = $true)]
    [string]$Python
)

$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$version = & $Python -S -c 'from mhc_icc_gui import APP_VERSION; print(APP_VERSION)'
if ($LASTEXITCODE -ne 0) { throw 'Could not read application version.' }
if ($version -notmatch '^\d+\.\d+(\.\d+)?$') { throw 'Invalid application version.' }
$name = "MHC-ICC-Profile-Maker_v$version"
$bundle = Join-Path $PSScriptRoot "dist\$name"
$archive = "$bundle-windows-x64.zip"
if ((Test-Path -LiteralPath $bundle) -or (Test-Path -LiteralPath $archive)) {
    throw 'Release output already exists. Preserve it or choose a new version before building.'
}

# Directory distribution avoids onefile's runtime extraction. No UPX packing.
& $Python -m PyInstaller --onedir --noupx --windowed --optimize 2 --name $name `
    --specpath build --workpath "build\$name" --distpath dist mhc_icc_gui.py
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller build failed.' }
Copy-Item -LiteralPath LICENSE, README.md, README_ZH.md -Destination $bundle
Compress-Archive -LiteralPath $bundle -DestinationPath $archive
$digest = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant()
Set-Content -LiteralPath "$archive.sha256" -Value "$digest  $([IO.Path]::GetFileName($archive))" -Encoding ascii
Write-Output $archive
