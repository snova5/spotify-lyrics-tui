param([switch]$Uninstall)

$Name = "spotifylyr"
$Dir = Join-Path $env:LOCALAPPDATA $Name
$UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($null -eq $UserPath) { $UserPath = "" }
$Parts = @($UserPath.Split(";") | Where-Object { $_ -ne "" })

if ($Uninstall) {
    if (Test-Path $Dir) { Remove-Item $Dir -Recurse -Force }
    $Kept = @($Parts | Where-Object { $_ -ne $Dir })
    [Environment]::SetEnvironmentVariable("Path", ($Kept -join ";"), "User")
    Write-Host "$Name was removed."
    exit 0
}

$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Script = Join-Path $Here "spotify_lyrics.py"
$Req = Join-Path $Here "requirements-windows.txt"
if (-not (Test-Path $Script)) {
    Write-Host "spotify_lyrics.py not found next to install.ps1"
    exit 1
}

function Find-Python {
    $candidates = @()
    if (Get-Command py -ErrorAction SilentlyContinue) { $candidates += ,@("py", "-3") }
    if (Get-Command python -ErrorAction SilentlyContinue) { $candidates += ,@("python") }
    foreach ($c in $candidates) {
        $extra = @()
        if ($c.Count -gt 1) { $extra = $c[1..($c.Count - 1)] }
        try {
            $out = & $c[0] @extra -c "import sys; print(sys.executable)" 2>$null
            if ($LASTEXITCODE -eq 0 -and $out) { return ($out | Select-Object -Last 1).Trim() }
        } catch {}
    }
    return $null
}

$Python = Find-Python
if (-not $Python) {
    Write-Host "Python 3 was not found."
    Write-Host "Install it from https://www.python.org/downloads/ and check 'Add python.exe to PATH', then run install.cmd again."
    exit 1
}
Write-Host "Using Python: $Python"

Write-Host "Installing the Python packages..."
& $Python -m pip install --user --upgrade -r $Req
if ($LASTEXITCODE -ne 0) {
    Write-Host "pip could not install the packages. Check your internet connection and try again."
    exit 1
}

New-Item -ItemType Directory -Force -Path $Dir | Out-Null
Copy-Item $Script (Join-Path $Dir "spotify_lyrics.py") -Force
$Launcher = "@echo off`r`n`"$Python`" `"%LOCALAPPDATA%\$Name\spotify_lyrics.py`" %*`r`n"
Set-Content -Path (Join-Path $Dir "$Name.cmd") -Value $Launcher -Encoding Default -NoNewline

if ($Parts -notcontains $Dir) {
    [Environment]::SetEnvironmentVariable("Path", ((@($Parts) + $Dir) -join ";"), "User")
}

Write-Host ""
Write-Host "Installed: $Dir\$Name.cmd"
Write-Host "Open a new terminal window and run: $Name"
