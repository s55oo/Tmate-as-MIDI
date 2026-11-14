<#
.SYNOPSIS
    TMate 1.0 - Windows 10/11 setup and verification.

.DESCRIPTION
    Checks and prepares everything the TMate MIDI controller needs:

      1. Windows 10/11, 64-bit
      2. Python 3.11+ 64-bit with the py launcher
      3. Python packages from requirements-midi.txt
      4. TMate (USB 1721:0607) bound to the Microsoft WinUSB driver
      5. One safe test read from the TMate (endpoint-0 control request only)
      6. loopMIDI installed and running, with a port named "TMate 1.0"
      7. Optional: autostart at logon (hidden console)

    The script never installs a driver itself. Binding WinUSB is done once
    with Zadig as administrator; the script tells you when that is needed.

    Run it from the package folder:

        powershell -ExecutionPolicy Bypass -File .\setup-windows.ps1

    or double-click setup-windows.cmd.

.PARAMETER CheckOnly
    Only report; do not install Python packages or change anything.

.PARAMETER Yes
    Answer "yes" to every question (non-interactive).

.PARAMETER Autostart
    Create a Startup-folder shortcut that runs the controller hidden at logon.

.PARAMETER RemoveAutostart
    Remove the Startup-folder shortcut and exit.

.PARAMETER PortName
    loopMIDI port name to look for. Default: "TMate 1.0".
#>
[CmdletBinding()]
param(
    [switch]$CheckOnly,
    [switch]$Yes,
    [switch]$Autostart,
    [switch]$RemoveAutostart,
    [string]$PortName = "TMate 1.0"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version 2

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Vid = "1721"
$Pid_ = "0607"
$ShortcutPath = Join-Path ([Environment]::GetFolderPath("Startup")) "TMate 1.0 MIDI.lnk"
$ZadigUrl = "https://zadig.akeo.ie/"
$LoopMidiUrl = "https://www.tobias-erichsen.de/software/loopmidi.html"
$PythonUrl = "https://www.python.org/downloads/windows/"

$Results = New-Object System.Collections.Generic.List[object]

function Write-Step([string]$Text) {
    Write-Host ""
    Write-Host "== $Text" -ForegroundColor Cyan
}

function Add-Result([string]$Name, [string]$State, [string]$Detail) {
    $Results.Add([pscustomobject]@{ Check = $Name; State = $State; Detail = $Detail })
    $color = switch ($State) { "OK" { "Green" } "WARN" { "Yellow" } "SKIP" { "DarkGray" } default { "Red" } }
    Write-Host ("   [{0}] {1}" -f $State, $Detail) -ForegroundColor $color
}

function Confirm-Action([string]$Question) {
    if ($CheckOnly) { return $false }
    if ($Yes) { return $true }
    $answer = Read-Host "   $Question [Y/n]"
    return ($answer -eq "" -or $answer -match '^(y|yes)$')
}

function Open-Url([string]$Url) {
    try { Start-Process $Url | Out-Null } catch { Write-Host "   Open $Url in your browser." }
}

# Run Python from the package folder so "-m tmate1_midi" finds the source.
function Invoke-Py([string[]]$PyArgs) {
    # Python code passed with -c must not contain double quotes: Windows
    # PowerShell 5.1 does not escape them for native commands.
    Push-Location $Root
    $oldPref = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        $output = & py -3 @PyArgs 2>&1 | ForEach-Object { "$_" }
        $code = $LASTEXITCODE
        return [pscustomobject]@{ Code = $code; Output = @($output) }
    } finally {
        $ErrorActionPreference = $oldPref
        Pop-Location
    }
}

# ---------------------------------------------------------------- autostart
if ($RemoveAutostart) {
    if (Test-Path $ShortcutPath) {
        Remove-Item $ShortcutPath -Force
        Write-Host "Removed $ShortcutPath"
    } else {
        Write-Host "No autostart shortcut found at $ShortcutPath"
    }
    exit 0
}

$SoftwareVersion = "unknown"
try {
    $m = Select-String -Path (Join-Path $Root "tmate1_midi\__init__.py") -Pattern '__version__ = "([^"]+)"'
    if ($m) { $SoftwareVersion = $m.Matches[0].Groups[1].Value }
} catch { }
Write-Host "TMate 1.0 - Windows setup (software v$SoftwareVersion)" -ForegroundColor White
Write-Host "Package folder: $Root"
if ($CheckOnly) { Write-Host "Check-only mode: nothing will be installed or changed." }

if (-not (Test-Path (Join-Path $Root "tmate1_midi\__main__.py"))) {
    Write-Host "This script must stay in the extracted package folder (tmate1_midi\ not found)." -ForegroundColor Red
    exit 1
}
if ($Root -match '\\AppData\\Local\\Temp\\' -or $Root -match '\.zip\\') {
    Write-Host "It looks like you are running from inside the ZIP. Extract the whole ZIP first." -ForegroundColor Red
    exit 1
}

# ---------------------------------------------------------------- 1. Windows
Write-Step "1/7 Windows"
$os = [Environment]::OSVersion.Version
if (-not [Environment]::Is64BitOperatingSystem) {
    Add-Result "Windows" "FAIL" "32-bit Windows is not supported; use Windows 10/11 64-bit."
} elseif ($os.Major -lt 10) {
    Add-Result "Windows" "WARN" "Windows $($os.Major).$($os.Minor) is not tested; Windows 10/11 is recommended."
} else {
    $build = $os.Build
    $name = if ($build -ge 22000) { "Windows 11" } else { "Windows 10" }
    Add-Result "Windows" "OK" "$name 64-bit (build $build)"
}

# ---------------------------------------------------------------- 2. Python
Write-Step "2/7 Python 3.11+ (64-bit)"
$pythonOk = $false
if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    Add-Result "Python" "FAIL" "The 'py' launcher was not found."
    if (-not $CheckOnly -and (Get-Command winget -ErrorAction SilentlyContinue)) {
        if (Confirm-Action "Install Python 3.12 with winget now?") {
            & winget install --exact --id Python.Python.3.12 --scope user --accept-package-agreements --accept-source-agreements
            Write-Host "   Python installed. Close this window, open a new PowerShell and run the setup again." -ForegroundColor Yellow
            exit 0
        }
    }
    Write-Host "   Install 64-bit Python 3.12 from $PythonUrl and tick 'Add python.exe to PATH'."
    if (Confirm-Action "Open the Python download page?") { Open-Url $PythonUrl }
} else {
    $r = Invoke-Py @('-c', "import sys,struct;print('%d.%d.%d %d' % (sys.version_info[:3] + (struct.calcsize('P')*8,)))")
    if ($r.Code -ne 0) {
        Add-Result "Python" "FAIL" "py -3 failed: $($r.Output -join ' ')"
    } else {
        $parts = ("" + ($r.Output | Select-Object -Last 1)).Trim().Split(" ")
        $ver = [version]$parts[0]
        $bits = [int]$parts[1]
        if ($ver -lt [version]"3.11.0") {
            Add-Result "Python" "FAIL" "Python $ver found; 3.11 or newer is required. Install 3.12 from $PythonUrl"
        } elseif ($bits -ne 64) {
            Add-Result "Python" "FAIL" "Python $ver is $bits-bit; install the 64-bit build (libusb and rtmidi wheels are 64-bit)."
        } else {
            Add-Result "Python" "OK" "Python $ver, $bits-bit"
            $pythonOk = $true
        }
    }
}

# ---------------------------------------------------------------- 3. packages
Write-Step "3/7 Python packages (requirements-midi.txt)"
$depsOk = $false
$importCheck = "import usb.core, libusb_package, mido, rtmidi; print('core OK')"
$trayCheck = "import pystray, PIL; print('tray OK')"
if (-not $pythonOk) {
    Add-Result "Packages" "SKIP" "Needs a working Python first."
} else {
    $r = Invoke-Py @('-c', $importCheck)
    if ($r.Code -ne 0 -and -not $CheckOnly) {
        Write-Host "   Installing packages (this needs internet access)..."
        $null = Invoke-Py @('-m', 'pip', 'install', '--upgrade', 'pip')
        $r = Invoke-Py @('-m', 'pip', 'install', '-r', 'requirements-midi.txt')
        if ($r.Code -ne 0) {
            Write-Host "   Normal install failed; retrying with prebuilt wheels only..." -ForegroundColor Yellow
            $r = Invoke-Py @('-m', 'pip', 'install', '--only-binary=:all:', '-r', 'requirements-midi.txt')
        }
        if ($r.Code -ne 0) {
            $r.Output | Select-Object -Last 15 | ForEach-Object { Write-Host "     $_" }
        }
        $r = Invoke-Py @('-c', $importCheck)
    }
    if ($r.Code -eq 0) {
        Add-Result "Packages" "OK" "pyusb, libusb-package, mido, python-rtmidi import correctly"
        $depsOk = $true
    } else {
        $last = ($r.Output | Select-Object -Last 1)
        Add-Result "Packages" "FAIL" "Core packages missing: $last. Run: py -m pip install -r requirements-midi.txt"
    }
    $t = Invoke-Py @('-c', $trayCheck)
    if ($t.Code -eq 0) {
        Add-Result "Tray" "OK" "pystray and Pillow available (tray icon enabled)"
    } else {
        Add-Result "Tray" "WARN" "Tray packages missing; the app still works with --no-tray."
    }
}

# ---------------------------------------------------------------- 4. driver
Write-Step "4/7 TMate driver (WinUSB)"
$driverOk = $false
$devices = @()
try {
    $devices = @(Get-PnpDevice -PresentOnly -ErrorAction SilentlyContinue |
        Where-Object { $_.InstanceId -like "USB\VID_$Vid&PID_$Pid_*" })
} catch {
    $devices = @()
}
if ($devices.Count -eq 0) {
    Add-Result "Device" "FAIL" "No TMate (USB $Vid`:$Pid_) is plugged in. Plug it into a rear USB port and run the setup again."
} else {
    $dev = $devices[0]
    $service = ""
    try {
        $service = (Get-PnpDeviceProperty -InstanceId $dev.InstanceId -KeyName "DEVPKEY_Device_Service" -ErrorAction Stop).Data
    } catch {
        $service = ""
    }
    if ("$service" -ieq "WINUSB") {
        if ($dev.Status -eq "OK") {
            Add-Result "Driver" "OK" "'$($dev.FriendlyName)' uses WinUSB"
            $driverOk = $true
        } else {
            Add-Result "Driver" "WARN" "WinUSB is bound but Device Manager reports '$($dev.Status)'. Unplug and replug the TMate."
        }
    } else {
        $what = if ($service) { "driver '$service'" } else { "no driver" }
        Add-Result "Driver" "FAIL" "TMate found with $what; it must use WinUSB."
        Write-Host ""
        Write-Host "   Bind it once with Zadig:" -ForegroundColor Yellow
        Write-Host "     1. Right-click zadig.exe -> Run as administrator"
        Write-Host "     2. Options -> List All Devices"
        Write-Host "     3. Select 'Tmate 1.0 USB' (USB ID 1721 0607)"
        Write-Host "     4. Target driver: WinUSB -> Replace Driver"
        Write-Host "   Do NOT install windows\Tmate_WINUSBdriver.zip (unsigned 2008 driver)."
        if ($service -and "$service" -notmatch '^(WINUSB)$') {
            Write-Host "   If an old Tmate/libusb driver is installed, first uninstall it in Device Manager"
            Write-Host "   (tick 'Attempt to remove the driver'), then replug the TMate."
        }
        if (Confirm-Action "Open the Zadig download page?") { Open-Url $ZadigUrl }
    }
}

# ---------------------------------------------------------------- 5. test read
Write-Step "5/7 TMate test read"
if (-not ($depsOk -and $driverOk)) {
    Add-Result "USB read" "SKIP" "Needs the packages and the WinUSB driver first."
} else {
    # One ReadValue control request on endpoint 0. No set_configuration(),
    # no endpoint 0x81 access - the same safe path the app uses.
    $probe = @"
import sys
from tmate1.device import Tmate1, TmateNotFound
try:
    with Tmate1() as dev:
        steps, keys, frame = dev.read()
        print('frame ' + frame.hex())
except TmateNotFound as exc:
    print('notfound ' + str(exc)); sys.exit(2)
except Exception as exc:
    print('error ' + type(exc).__name__ + ': ' + str(exc)); sys.exit(3)
"@
    $r = Invoke-Py @('-c', $probe)
    $line = ($r.Output | Select-Object -Last 1)
    switch ($r.Code) {
        0 { Add-Result "USB read" "OK" "TMate answered ($line)" }
        2 { Add-Result "USB read" "FAIL" "libusb cannot see the TMate: $line" }
        default {
            if ("$line" -match 'Access|busy|denied|Errno 13|Resource') {
                Add-Result "USB read" "FAIL" "Device busy: close Tmate.exe, tmate1_midi and the monitor, then retry. ($line)"
            } else {
                Add-Result "USB read" "FAIL" "$line"
            }
        }
    }
}

# ---------------------------------------------------------------- 6. loopMIDI
Write-Step "6/7 loopMIDI port '$PortName'"
$loopExe = @(
    (Join-Path ${env:ProgramFiles(x86)} "Tobias Erichsen\loopMIDI\loopMIDI.exe"),
    (Join-Path $env:ProgramFiles "Tobias Erichsen\loopMIDI\loopMIDI.exe")
) | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
$loopRunning = [bool](Get-Process -Name loopMIDI -ErrorAction SilentlyContinue)

if (-not $loopExe -and -not $loopRunning) {
    Add-Result "loopMIDI" "FAIL" "loopMIDI is not installed."
    if (Confirm-Action "Open the loopMIDI download page?") { Open-Url $LoopMidiUrl }
} else {
    if (-not $loopRunning -and $loopExe -and (Confirm-Action "loopMIDI is not running. Start it now?")) {
        Start-Process $loopExe | Out-Null
        Start-Sleep -Seconds 3
        $loopRunning = [bool](Get-Process -Name loopMIDI -ErrorAction SilentlyContinue)
    }
    if ($loopRunning) {
        Add-Result "loopMIDI" "OK" "loopMIDI is running"
    } else {
        Add-Result "loopMIDI" "WARN" "loopMIDI is installed but not running."
    }
}

if ($depsOk) {
    $r = Invoke-Py @('-m', 'tmate1_midi', '--list-ports')
    $ports = @($r.Output | Where-Object { $_ -and $_ -notmatch '^\d\d:\d\d:\d\d ' })
    # RtMidi on Windows lists "TMate 1.0" as "TMate 1.0 1".
    $pattern = '^' + [regex]::Escape($PortName) + '( \d+)?$'
    $match = $ports | Where-Object { $_ -match $pattern } | Select-Object -First 1
    if ($r.Code -ne 0) {
        Add-Result "MIDI port" "FAIL" "Cannot list MIDI ports: $($r.Output -join ' ')"
    } elseif ($match) {
        Add-Result "MIDI port" "OK" "Found '$match'"
    } else {
        Add-Result "MIDI port" "FAIL" "No port named '$PortName'. In loopMIDI type '$PortName' in 'New port-name' and click +."
        if ($ports.Count) { Write-Host "   Ports Windows reports: $($ports -join ', ')" }
    }
} else {
    Add-Result "MIDI port" "SKIP" "Needs the Python packages first."
}

# ---------------------------------------------------------------- 7. autostart
Write-Step "7/7 Autostart"
$vbs = Join-Path $Root "bin\tmate1-midi-hidden.vbs"
if ($Autostart) {
    if ($CheckOnly) {
        Add-Result "Autostart" "SKIP" "Check-only mode."
    } else {
        $shell = New-Object -ComObject WScript.Shell
        $lnk = $shell.CreateShortcut($ShortcutPath)
        $lnk.TargetPath = Join-Path $env:WINDIR "System32\wscript.exe"
        $lnk.Arguments = '"' + $vbs + '"'
        $lnk.WorkingDirectory = $Root
        $lnk.Description = "TMate 1.0 MIDI controller"
        $lnk.Save()
        Add-Result "Autostart" "OK" "Created $ShortcutPath"
        Write-Host "   Also enable 'Start with Windows' in loopMIDI (tray icon -> right-click)."
    }
} elseif (Test-Path $ShortcutPath) {
    Add-Result "Autostart" "OK" "Enabled ($ShortcutPath). Remove with -RemoveAutostart."
} else {
    Add-Result "Autostart" "SKIP" "Not enabled. Run again with -Autostart to start at logon."
}

# ---------------------------------------------------------------- summary
Write-Host ""
Write-Host "== Summary" -ForegroundColor Cyan
$Results | Format-Table -AutoSize | Out-String -Width 200 | Write-Host

$failed = @($Results | Where-Object { $_.State -eq "FAIL" })
if ($failed.Count -eq 0) {
    Write-Host "Ready. Start the controller with:" -ForegroundColor Green
    Write-Host "    bin\tmate1-midi.cmd --open"
    Write-Host "then turn the wheel and watch http://127.0.0.1:8067/"
    exit 0
} else {
    Write-Host "$($failed.Count) check(s) failed. Fix them (see the details above) and run the setup again." -ForegroundColor Red
    Write-Host "Full manual: TMate-1.0-Windows-Manual.pdf"
    exit 1
}
