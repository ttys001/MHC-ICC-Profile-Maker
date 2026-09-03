# MHC ICC Profile Maker

English | [简体中文](README_ZH.md)

Windows GUI for building and editing ICC v4 display profiles with Microsoft Hardware Calibration (`MHC2`) metadata. It provides structured editors for the ICC header, tag table, localized text, XYZ colorants, TRCs, luminance, and MHC2 matrix/1D LUT data, while retaining a raw hexadecimal view.

## Features

- Create, load, edit, validate, and atomically save ICC v4 display profiles.
- Edit common tags through dedicated workspaces or raw hexadecimal data.
- Import 3×3/3×4 matrices and RGB 1D LUTs from CSV.
- Calculate a four-color least-squares correction matrix from W/R/G/B measurements.
- Run without third-party Python packages; NumPy is not required.
- Use the included SDR and HDR profiles and reports as practical examples.

## Download

Download the current Windows executable from [GitHub Releases](https://github.com/ttys001/MHC-ICC-Profile-Maker/releases).

## Requirements

- Windows and Python 3.11+ with Tkinter to run from source.
- Windows 10, version 2004 or later, a supported GPU, and WDDM 2.6+ to apply the MHC hardware calibration pipeline. Some GPUs require a newer driver.
- Windows 11 for the Windows HDR Calibration app. Advanced Color feature availability also depends on the Windows version and hardware.
- PyInstaller is needed only when building an executable.

## Run, test, and build

```powershell
python mhc_icc_gui.py
python -S -m unittest -v
```

Build the optimized single-file Windows executable:

```powershell
python -m PyInstaller --noconfirm --clean --onefile --windowed --optimize 2 --name "MHC-ICC-Profile-Maker_v0.93" mhc_icc_gui.py
```

## Quick workflow

1. Choose **File → New Profile** or **File → Load ICC…**.
2. Select a tag, edit it in Human or Hex mode, and choose **Apply Changes**.
3. Save the profile. The app updates the creation time, profile size, and ICC profile ID.
4. Validate the result on the target Windows system and display before relying on it.

## CSV input

- Matrix: three numeric rows with either three or four columns. Windows stores a 3×4 matrix but ignores the fourth column.
- RGB 1D LUT: 1–4096 rows with R, G, and B columns.
- LUT values may be normalized `0–1`, or integer-domain `0–255`, `0–1023`, `0–4095`, or `0–65535`; the app normalizes them to `0–1`.
- Commas, semicolons, and tabs are accepted. Lines beginning with `#` are comments.
- The matrix calculator accepts four W/R/G/B rows in either xyY or XYZ form.

## Default profile

**File → New Profile** creates:

| Area | Default |
| --- | --- |
| Header | ICC v4 display profile (`mntr`), RGB, PCS XYZ, platform `MSFT`, media-relative colorimetric intent |
| Tag set | `cprt`, `rTRC`, `gTRC`, `bTRC`, `chad`, `rXYZ`, `gXYZ`, `bXYZ`, `wtpt`, `MSCA`, `lumi`, `MHC2`, `desc` |
| Color | sRGB primaries, D65 white normalized to Y=1, identity `chad` |
| TRCs | Shared gamma 2.2 `curveType` data |
| Luminance | `lumi` = 80 nits; MHC2 minimum = 0.2 nits and peak = 80 nits |
| MHC2 transforms | Explicit 3×4 identity matrix and two-point RGB identity LUT, matching Windows HDR Calibration output |
| Text | `Copyright (C) User.` and `Default Device Profile` |
| MSCA | `{'Appversion':'1.0.152.0','D65Adapted':True}` |

The MSCA app version was checked against Microsoft’s live Store catalog on 2026-07-30 and matches Windows HDR Calibration `1.0.152.0`. MSCA is a private Microsoft tag; changing only its version string does not reproduce another app version’s behavior.

## Essential MHC2 rules

- A usable MHC profile needs valid ST.2086 metadata: RGB primaries, white point, maximum full-frame luminance, minimum luminance, and peak luminance. Treat defaults as placeholders for the target display.
- The matrix is stored as 3×4 in row-major order, but Windows uses only the left three columns. Do not include source RGB→XYZ or XYZ→target RGB conversions; the display driver supplies them.
- The MHC2 1D LUT is a calibration adjustment applied after the wire-format transfer function. Do not encode an sRGB, gamma, or PQ transfer function into it.
- A zero matrix offset, or a zero LUT entry count with all three LUT offsets set to zero, explicitly requests an identity transform.
- Hardware can support fewer entries or less precision than the profile contains; Windows interpolates to the hardware-supported LUT size.

## Workflow guidance

### Legacy SDR

Use suitable ICC TRCs and colorants for the target color space. Use the MHC2 matrix for intentional XYZ adjustments such as color-space proofing or measured correction. Use the 1D LUT for post-transfer-function calibration, and enter valid luminance metadata.

### SDR with Advanced Color / ACM

Use measured native primaries and valid luminance metadata. Windows performs source-to-display color conversion using the active display profile. On Windows 11, legacy ICC-profile-based apps are limited to sRGB behavior unless the per-app **Use legacy display ICC color management** compatibility helper is enabled.

### HDR

Use measured or reliable display primaries/white point, store maximum full-frame luminance in `lumi`, and store minimum/peak luminance in `MHC2`. Use the matrix for intentional XYZ adjustment or measured correction, and the 1D LUT for post-transfer-function calibration. Identity is valid when no adjustment is required.

The reference profiles in this repository carry the same Windows HDR Calibration `1.0.152.0` MSCA string. MSCA is private, so these examples should not be treated as a promise that future app versions will use the same data.

## Samples

- [HDR: MSI MPG 272URX QD-OLED](samples/MSI%20MPG%20272URX%20Calibration%20Report.md)
- [SDR: BOE NE160QDM-NX2](samples/NE160QDM-NX2%20Calibration%20Report.md)
- [SDR: BOE NE160QDM-NM7](samples/NE160QDM-NM7%20Calibration%20Report.md)

## Troubleshooting

### Calibration is not restored after sleep

If Windows keeps the correct monitor-specific associations in the classic Color Management control panel but Settings selects a profile intended for another monitor, use the included [MHC Profile Guard](MHC-Profile-Guard). It reads each active display's hardware identity and existing Advanced System Defaults, then restores the corresponding SDR and HDR profile through the current-user Windows color-profile APIs.

Install the scheduled task from PowerShell:

```powershell
.\MHC-Profile-Guard\MhcProfileGuard.ps1 -Install
```

The task runs silently at logon, after display-configuration changes, after monitor connection or removal, and after resume from sleep. Each invocation exits after 25 seconds, and Task Scheduler enforces a 30-second limit; there is no persistent polling process. Run the script without options to repair and display the current associations once. Remove the task with:

```powershell
.\MHC-Profile-Guard\MhcProfileGuard.ps1 -Uninstall
```

For the inbox calibration loader itself, open Task Scheduler and inspect **Microsoft → Windows → WindowsColorSystem → Calibration Loader**. Enable **Run with highest privileges** and add an **On an event** trigger for System log, source `Power-Troubleshooter`, event ID `1`.

### Full-screen and independent flip

MHC calibration is loaded by the Windows display calibration pipeline; it is not a DWM shader. Do not infer the actual presentation path from “windowed,” “borderless,” or “full-screen” labels: a windowed flip-model application can be promoted to independent flip. HDR metadata and monitor tone mapping are separate, device-specific concerns.

The tone-mapping notes for the MSI MPG 272URX apply only to the tested monitor firmware and settings; see its [calibration report](samples/MSI%20MPG%20272URX%20Calibration%20Report.md).

## References

- [Windows hardware display color calibration pipeline](https://learn.microsoft.com/en-us/windows/win32/wcs/display-calibration-mhc)
- [ICC profile behavior with Advanced Color](https://learn.microsoft.com/en-us/windows/win32/wcs/advanced-color-icc-profiles)
- [Windows HDR Calibration](https://apps.microsoft.com/detail/9N7F2SM5D1LR)
- [DXGI flip-model guidance](https://learn.microsoft.com/en-us/windows/win32/direct3ddxgi/for-best-performance--use-dxgi-flip-model)
- [ICC profile specification](references/ICC.1-2022-05.pdf)

## License

GPL-3.0-or-later. Redistribution, including executable builds, must include the corresponding source and license.
