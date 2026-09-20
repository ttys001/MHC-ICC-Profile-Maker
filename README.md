# MHC ICC Profile Maker

English | [简体中文](README_ZH.md)

Windows GUI for building and editing ICC v4 display profiles with Microsoft Hardware Calibration (`MHC2`) metadata. It provides structured editors for the ICC header, tag table, localized text, XYZ colorants, TRCs, luminance, and MHC2 matrix/1D LUT data, while retaining a raw hexadecimal view.

## Features

- Create, load, edit, validate, and atomically save ICC v4 display profiles.
- Edit common tags through dedicated workspaces or raw hexadecimal data.
- Import 3×3/3×4 matrices from CSV and RGB 1D LUTs from CSV, 1D Cube, or ColourSpace/Quantel TXT.
- Optionally resample RGB 1D LUTs using pure-Python shape-preserving PCHIP.
- Calculate a four-color least-squares correction matrix from W/R/G/B measurements.
- Run without third-party Python packages; NumPy is not required.
- Use the included SDR and HDR profiles and reports as practical examples.

## Download

Download the Windows x64 ZIP from [GitHub Releases](https://github.com/ttys001/MHC-ICC-Profile-Maker/releases). Extract the entire folder and run the EXE inside it. Keep the `_internal` folder beside the EXE; Python does not need to be installed.

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

Build the directory-based Windows package in an isolated environment (64-bit Python):

```powershell
python -m venv build/release-venv
build/release-venv/Scripts/python.exe -m pip install --index-url https://pypi.org/simple PyInstaller==6.22.3
./build-release.ps1 -Python ./build/release-venv/Scripts/python.exe
```

The build script produces a versioned ZIP and SHA-256 file in `dist`. It uses `--onedir --noupx`, includes the license, and refuses to overwrite an existing release. Version 0.94.1 updates packaging and increases the default window height so the MHC2 workspace, including Resample, fits without scrolling at the tested display scaling. LUT and ICC behavior is unchanged; scrolling remains available for smaller windows or larger display scaling.

### Defender detection on v0.94

A user reported `Trojan:Win32/Sabsik.TE.A!ml` for the unsigned v0.94 single-file EXE. The replacement uses a directory package without runtime self-extraction. This is a packaging mitigation, not confirmation of a false positive or a guarantee of acceptance on another computer. Do not disable Defender or add an exclusion. If blocked, use the Python source with the command above, and report the file hash and detection to [Microsoft Security Intelligence](https://www.microsoft.com/en-us/wdsi/filesubmission). SmartScreen publisher reputation and Defender malware detections are separate checks; this package is still unsigned.

## Quick workflow

1. Choose **File → New Profile** or **File → Load ICC…**.
2. Select a tag, edit it in Human or Hex mode, and choose **Apply Changes**.
3. Save the profile. The app updates the creation time, profile size, and ICC profile ID.
4. Validate the result on the target Windows system and display before relying on it.

## Matrix and RGB 1D LUT input

The expanded Cube-domain and Quantel-header support below is in the current source; the published v0.94.1 package is unchanged.

- Matrix: three numeric rows with either three or four columns. Windows stores a 3×4 matrix but ignores the fourth column.
- **Load RGB 3x1DLUT…** accepts CSV, 1D `.cube`, and ColourSpace/Light Illusion Quantel-style `.txt` with three RGB columns. 3D LUTs are rejected.
- MHC2 accepts any LUT size from **1 to 4096 entries**. Imported LUTs preserve their original entry count; power-of-two sizes are not required. A 101-row source writes exactly 101 entries, with no padding, truncation, or automatic resampling. `Entries:` is read-only.
- CSV values may be normalized `0–1`, or integer-domain `0–255`, `0–1023`, `0–4095`, or `0–65535`; the app detects the range and normalizes to `0–1`. Commas, semicolons, tabs, UTF-8 BOM, blank lines, and `#` comments are accepted.
- Cube requires `LUT_1D_SIZE` matching the data-row count and finite output values in `0–1`. `TITLE` and comments are optional. IRIDAS/Adobe `DOMAIN_MIN/MAX` and DaVinci Resolve `LUT_1D_INPUT_RANGE` accept zero-based full input ranges such as `0–1`, `0–1023`, `0–65535`, or any finite positive maximum. Input units never scale output values or change sample counts. Omitted bounds default to `0–1`; RGB channel bounds must agree, and mixed declarations must match (tolerance `1e-9`). Partial/non-zero-based domains are rejected because mapping them requires an explicit out-of-domain policy. General scene-linear/shaper Cube outputs outside `0–1` and mixed 1D+3D files are not supported by this MHC2 importer.
- Quantel TXT accepts textual headers before the table, including ColourSpace `table type 2`, `gMax` (output maximum), `gSize` (exact RGB row count), and `R G B`. Explicit `gMax`, `max value`, `bit depth`, or zero-based `range` metadata (including `#`-prefixed forms) sets normalization; otherwise CSV range detection applies. Conflicting metadata, mismatched `gSize`, unsupported table types, invalid values, and 3D declarations such as `cube size`, `cube data`, `vertices`, or `LUT3D` are rejected. A 12-bit Unity export with `gMax 4095` / `gSize 4096` imports unchanged in length; a 16-bit Unity export with `gSize 65536` exceeds the MHC2 limit and must be exported at 4096 points or fewer. Import never silently downsamples it.
- The matrix calculator accepts four W/R/G/B rows in either xyY or XYZ form.

### Optional resampling

Default: **import → preserve source samples → write that exact count into MHC2**. Choose **Resample 1DLUT…** explicitly to convert the current LUT to any target from 1–4096 entries. 4096 is an optional maximum, not a requirement; importing never resamples.

The stdlib-only PCHIP implementation preserves local shape and monotonic sections without spline ringing or repairing non-monotonic source curves. Source black and white endpoints are preserved exactly for targets of at least two entries, including calibrated white values below 1. A one-point source expands as a constant; two source points interpolate linearly. A one-entry target keeps the first source sample (it cannot retain both endpoints); an unchanged count makes no numerical changes.

Parsing and resampling retain Python float precision in the workspace. Only ICC serialization quantizes to s15Fixed16; reopening a saved profile reads those quantized values. This supports comparing the native LUT with an explicitly PCHIP-resampled LUT through the Windows/hardware pipeline; software checks do not establish the measured display result.

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

## Samples

- [HDR: MSI MPG 272URX QD-OLED](samples/MSI%20MPG%20272URX%20Calibration%20Report.md)
- [SDR: BOE NE160QDM-NX2](samples/NE160QDM-NX2%20Calibration%20Report.md)
- [SDR: BOE NE160QDM-NM7](samples/NE160QDM-NM7%20Calibration%20Report.md)

## Troubleshooting

### Calibration is not restored after sleep

After sleep or a display-topology change, Windows can select another monitor's profile even when the classic Color Management control panel shows the correct system defaults. An automatic guard is not included because display associations can follow GPU source slots between monitors; keep **Use my settings for this device** disabled and reconnect the displays or select the correct system default again if this occurs.

### Full-screen and independent flip

MHC calibration is loaded by the Windows display calibration pipeline; it is not a DWM shader. Do not infer the actual presentation path from “windowed,” “borderless,” or “full-screen” labels: a windowed flip-model application can be promoted to independent flip. HDR metadata and monitor tone mapping are separate, device-specific concerns.

The tone-mapping notes for the MSI MPG 272URX apply only to the tested monitor firmware and settings; see its [calibration report](samples/MSI%20MPG%20272URX%20Calibration%20Report.md).

## References

- [Quantel/SAM Utilities User Guide, sections 3.2.5–3.2.7 (1D LUT headers)](https://wwwapps.grassvalley.com/docs/Manuals/sam/Post%20and%20Editing/Utilities%20User%20Guide.pdf)
- [Blackmagic Design forum: Cube LUT format documentation](https://forum.blackmagicdesign.com/viewtopic.php?f=21&t=40284)
- [Windows hardware display color calibration pipeline](https://learn.microsoft.com/en-us/windows/win32/wcs/display-calibration-mhc)
- [ICC profile behavior with Advanced Color](https://learn.microsoft.com/en-us/windows/win32/wcs/advanced-color-icc-profiles)
- [Windows HDR Calibration](https://apps.microsoft.com/detail/9N7F2SM5D1LR)
- [DXGI flip-model guidance](https://learn.microsoft.com/en-us/windows/win32/direct3ddxgi/for-best-performance--use-dxgi-flip-model)
- [ICC profile specification](references/ICC.1-2022-05.pdf)

## License

GPL-3.0-or-later. Redistribution, including executable builds, must include the corresponding source and license.
