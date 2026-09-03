[CmdletBinding()]
param(
    [switch]$Install,
    [switch]$Uninstall,
    [switch]$Listen,
    [string]$TaskName = 'MHC Profile Guard'
)

$ErrorActionPreference = 'Stop'

function Install-GuardTask {
    $launcher = Join-Path $PSScriptRoot 'MhcProfileGuard.vbs'
    if (-not (Test-Path $launcher)) { throw "Missing launcher: $launcher" }

    $sid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
    $escapedLauncher = [Security.SecurityElement]::Escape($launcher)
    $xml = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo><Description>Listens for display topology changes and repairs monitor-specific SDR/HDR ICC defaults.</Description><Author>$sid</Author></RegistrationInfo>
  <Triggers>
    <LogonTrigger><Enabled>true</Enabled><UserId>$sid</UserId></LogonTrigger>
  </Triggers>
  <Principals><Principal id="Author"><UserId>$sid</UserId><LogonType>InteractiveToken</LogonType><RunLevel>LeastPrivilege</RunLevel></Principal></Principals>
  <Settings><MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy><DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries><StopIfGoingOnBatteries>false</StopIfGoingOnBatteries><AllowHardTerminate>true</AllowHardTerminate><StartWhenAvailable>true</StartWhenAvailable><RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable><IdleSettings><StopOnIdleEnd>false</StopOnIdleEnd><RestartOnIdle>false</RestartOnIdle></IdleSettings><AllowStartOnDemand>true</AllowStartOnDemand><Enabled>true</Enabled><Hidden>true</Hidden><RunOnlyIfIdle>false</RunOnlyIfIdle><DisallowStartOnRemoteAppSession>false</DisallowStartOnRemoteAppSession><UseUnifiedSchedulingEngine>true</UseUnifiedSchedulingEngine><WakeToRun>false</WakeToRun><ExecutionTimeLimit>PT0S</ExecutionTimeLimit><Priority>7</Priority></Settings>
  <Actions Context="Author"><Exec><Command>C:\Windows\System32\wscript.exe</Command><Arguments>&quot;$escapedLauncher&quot;</Arguments></Exec></Actions>
</Task>
"@

    $existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($existing) {
        Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    }
    Register-ScheduledTask -TaskName $TaskName -Xml $xml | Out-Null
    Start-ScheduledTask -TaskName $TaskName
    Get-ScheduledTask -TaskName $TaskName
}

if (($Install -and ($Uninstall -or $Listen)) -or ($Uninstall -and $Listen)) {
    throw 'Choose only one of -Install, -Uninstall, or -Listen.'
}
if ($Uninstall) {
    Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    return
}
if ($Install) {
    Install-GuardTask
    return
}

if (-not ('MhcProfileGuard.Native' -as [type])) {
    Add-Type -TypeDefinition @'
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;

namespace MhcProfileGuard {
    [StructLayout(LayoutKind.Sequential)]
    public struct Luid { public uint LowPart; public int HighPart; }

    [StructLayout(LayoutKind.Sequential)]
    struct Rational { public uint Numerator, Denominator; }

    [StructLayout(LayoutKind.Sequential)]
    struct SourceInfo { public Luid adapterId; public uint id, modeInfoIdx, statusFlags; }

    [StructLayout(LayoutKind.Sequential)]
    struct TargetInfo {
        public Luid adapterId;
        public uint id, modeInfoIdx;
        public int outputTechnology, rotation, scaling;
        public Rational refreshRate;
        public int scanLineOrdering;
        [MarshalAs(UnmanagedType.Bool)] public bool targetAvailable;
        public uint statusFlags;
    }

    [StructLayout(LayoutKind.Sequential)]
    struct PathInfo { public SourceInfo sourceInfo; public TargetInfo targetInfo; public uint flags; }

    [StructLayout(LayoutKind.Sequential)]
    struct ModeInfo {
        public uint infoType, id;
        public Luid adapterId;
        [MarshalAs(UnmanagedType.ByValArray, SizeConst = 48)] public byte[] data;
    }

    [StructLayout(LayoutKind.Sequential)]
    struct Header { public uint type, size; public Luid adapterId; public uint id; }

    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    struct SourceName {
        public Header header;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 32)] public string viewGdiDeviceName;
    }

    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    struct TargetName {
        public Header header;
        public uint flags;
        public int outputTechnology;
        public ushort edidManufacturerId, edidProductCodeId;
        public uint connectorInstance;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 64)] public string monitorFriendlyDeviceName;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 128)] public string monitorDevicePath;
    }

    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    struct DisplayDevice {
        public int cb;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 32)] public string DeviceName;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 128)] public string DeviceString;
        public uint StateFlags;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 128)] public string DeviceID;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 128)] public string DeviceKey;
    }

    public sealed class ActiveDisplay {
        public Luid AdapterId;
        public uint SourceId;
        public string FriendlyName;
        public string HardwareId;
        public string InstanceId;
        public string SourceName;
        public string ResolverDeviceId;
    }

    public static class Native {
        [DllImport("user32.dll")]
        static extern int GetDisplayConfigBufferSizes(uint flags, out uint paths, out uint modes);

        [DllImport("user32.dll")]
        static extern int QueryDisplayConfig(uint flags, ref uint paths, [Out] PathInfo[] pathInfo,
            ref uint modes, [Out] ModeInfo[] modeInfo, IntPtr topology);

        [DllImport("user32.dll", CharSet = CharSet.Unicode)]
        static extern int DisplayConfigGetDeviceInfo(ref SourceName request);

        [DllImport("user32.dll", CharSet = CharSet.Unicode)]
        static extern int DisplayConfigGetDeviceInfo(ref TargetName request);

        [DllImport("user32.dll", CharSet = CharSet.Unicode)]
        static extern bool EnumDisplayDevices(string device, uint index, ref DisplayDevice result, uint flags);

        [DllImport("mscms.dll", CharSet = CharSet.Unicode)]
        static extern int ColorProfileGetDisplayDefault(int scope, Luid adapterId, uint sourceId,
            int profileType, int profileSubtype, out IntPtr profileName);

        [DllImport("mscms.dll", CharSet = CharSet.Unicode)]
        static extern int ColorProfileAddDisplayAssociation(int scope, string profileName, Luid adapterId,
            uint sourceId, bool setAsDefault, bool advancedColor);

        [DllImport("kernel32.dll")]
        static extern IntPtr LocalFree(IntPtr memory);

        static void Check(int result, string operation) {
            if (result != 0) throw new InvalidOperationException(operation + " failed: " + result);
        }

        public static ActiveDisplay[] GetActiveDisplays() {
            uint pathCount, modeCount;
            Check(GetDisplayConfigBufferSizes(2, out pathCount, out modeCount), "GetDisplayConfigBufferSizes");
            var paths = new PathInfo[pathCount];
            var modes = new ModeInfo[modeCount];
            Check(QueryDisplayConfig(2, ref pathCount, paths, ref modeCount, modes, IntPtr.Zero), "QueryDisplayConfig");

            var result = new List<ActiveDisplay>();
            for (int i = 0; i < pathCount; i++) {
                var path = paths[i];
                var source = new SourceName();
                source.header.type = 1;
                source.header.size = (uint)Marshal.SizeOf(typeof(SourceName));
                source.header.adapterId = path.sourceInfo.adapterId;
                source.header.id = path.sourceInfo.id;
                Check(DisplayConfigGetDeviceInfo(ref source), "Get source name");

                var target = new TargetName();
                target.header.type = 2;
                target.header.size = (uint)Marshal.SizeOf(typeof(TargetName));
                target.header.adapterId = path.targetInfo.adapterId;
                target.header.id = path.targetInfo.id;
                Check(DisplayConfigGetDeviceInfo(ref target), "Get target name");

                var resolver = new DisplayDevice();
                resolver.cb = Marshal.SizeOf(typeof(DisplayDevice));
                if (!EnumDisplayDevices(source.viewGdiDeviceName, 0, ref resolver, 0))
                    throw new InvalidOperationException("EnumDisplayDevices failed for " + source.viewGdiDeviceName);

                string[] parts = target.monitorDevicePath.Split('#');
                if (parts.Length < 3) throw new InvalidOperationException("Unexpected monitor path: " + target.monitorDevicePath);
                result.Add(new ActiveDisplay {
                    AdapterId = path.targetInfo.adapterId,
                    SourceId = path.sourceInfo.id,
                    FriendlyName = target.monitorFriendlyDeviceName,
                    HardwareId = parts[1],
                    InstanceId = parts[2],
                    SourceName = source.viewGdiDeviceName,
                    ResolverDeviceId = resolver.DeviceID
                });
            }
            return result.ToArray();
        }

        public static string GetDefault(ActiveDisplay display, bool advancedColor) {
            IntPtr value;
            int hr = ColorProfileGetDisplayDefault(1, display.AdapterId, display.SourceId, 0,
                advancedColor ? 8 : 7, out value);
            if (hr < 0) return null;
            try { return value == IntPtr.Zero ? null : Marshal.PtrToStringUni(value); }
            finally { if (value != IntPtr.Zero) LocalFree(value); }
        }

        public static void SetDefault(ActiveDisplay display, string profile, bool advancedColor) {
            int hr = ColorProfileAddDisplayAssociation(1, profile, display.AdapterId, display.SourceId,
                true, advancedColor);
            if (hr < 0) throw new InvalidOperationException("ColorProfileAddDisplayAssociation failed: 0x" + ((uint)hr).ToString("X8"));
        }
    }
}
'@
}

function Get-SystemDefaults([string]$HardwareId, [string]$InstanceId) {
    $device = "HKLM:\SYSTEM\CurrentControlSet\Enum\DISPLAY\$HardwareId\$InstanceId"
    if (-not (Test-Path $device)) { throw "No monitor device instance found for $HardwareId\$InstanceId" }

    $driver = (Get-ItemProperty $device).Driver
    $profiles = Get-ItemProperty "HKLM:\SYSTEM\CurrentControlSet\Control\Class\$driver"
    [pscustomobject]@{
        Standard = @($profiles.ICMProfile | Where-Object { $_ })[-1]
        Extended = @($profiles.ICMProfileAC | Where-Object { $_ })[-1]
    }
}

function Repair-MhcProfiles {
    $plans = foreach ($display in [MhcProfileGuard.Native]::GetActiveDisplays()) {
        $defaults = Get-SystemDefaults $display.HardwareId $display.InstanceId
        if ($display.ResolverDeviceId -notmatch '(\{[0-9A-Fa-f-]+\}\\\d{4})$') {
            throw "Cannot map WCS resolver $($display.ResolverDeviceId)"
        }
        [pscustomobject]@{ Display = $display; Defaults = $defaults; ResolverDriver = $Matches[1] }
    }

    $collision = $plans | Group-Object ResolverDriver | Where-Object {
        ($_.Group.Defaults.Standard | Sort-Object -Unique).Count -gt 1 -or
        ($_.Group.Defaults.Extended | Sort-Object -Unique).Count -gt 1
    }
    if ($collision) { throw 'Windows mapped multiple active monitors to the same WCS association; no safe automatic repair is possible.' }

    foreach ($plan in $plans) {
        $display = $plan.Display
        $userKey = "HKCU:\Software\Microsoft\Windows NT\CurrentVersion\ICM\ProfileAssociations\Display\$($plan.ResolverDriver)"
        New-Item $userKey -Force | Out-Null
        Set-ItemProperty $userKey UsePerUserProfiles 1 -Type DWord

        if ($plan.Defaults.Standard -and [MhcProfileGuard.Native]::GetDefault($display, $false) -ne $plan.Defaults.Standard) {
            [MhcProfileGuard.Native]::SetDefault($display, $plan.Defaults.Standard, $false)
        }
        if ($plan.Defaults.Extended -and [MhcProfileGuard.Native]::GetDefault($display, $true) -ne $plan.Defaults.Extended) {
            [MhcProfileGuard.Native]::SetDefault($display, $plan.Defaults.Extended, $true)
        }

        $actualStandard = [MhcProfileGuard.Native]::GetDefault($display, $false)
        $actualExtended = [MhcProfileGuard.Native]::GetDefault($display, $true)
        if ($actualStandard -ne $plan.Defaults.Standard -or $actualExtended -ne $plan.Defaults.Extended) {
            throw "Profile verification failed for $($display.FriendlyName)"
        }
        [pscustomobject]@{
            Display  = $display.FriendlyName
            Source   = $display.SourceName
            Standard = $actualStandard
            Extended = $actualExtended
        }
    }
}

if (-not $Listen) {
    Repair-MhcProfiles
    return
}

$eventName = 'MhcProfileGuard.DisplaySettingsChanged'
Register-ObjectEvent -InputObject ([Microsoft.Win32.SystemEvents]) `
    -EventName DisplaySettingsChanged -SourceIdentifier $eventName | Out-Null
try {
    try { Repair-MhcProfiles }
    catch { Write-Error $_ -ErrorAction Continue }
    while ($true) {
        $event = Wait-Event -SourceIdentifier $eventName
        Remove-Event -EventIdentifier $event.EventIdentifier
        Start-Sleep -Milliseconds 750
        Get-Event -SourceIdentifier $eventName -ErrorAction Ignore | Remove-Event
        try { Repair-MhcProfiles }
        catch { Write-Error $_ -ErrorAction Continue }
    }
}
finally {
    Unregister-Event -SourceIdentifier $eventName -ErrorAction Ignore
}
