# MHC ICC Profile Maker

Windows GUI tool for building fully customized ICC v4 profiles that include Microsoft’s Advanced Color (MHC2) metadata. It provides human-friendly editors for header fields, tag tables, localized text, XYZ colorants, TRCs, luminance, MHC2 matrices/LUTs, and more. Default profiles load with sRGB primaries, D65 white, gamma 2.2 TRCs, and identity transforms for chad/MHC2.

## Features

- Header editor
- Tag table viewer/editor with offsets/sizes
- Workspaces for editing tags, with switch between human and raw hex view
- Four-color matrix calculator for  MHC2 matrix

## Requirements

- Python 3.11+ on Windows.
- Dependencies: `pip install numpy`.
- Tkinter ships with standard Python on Windows.

## Binary release

Download the latest release EXE from the [Releases](https://github.com/ttys001/MHC-ICC-Profile-Maker/releases).

## Running from source

```bash
pip install numpy  
python mhc_icc_gui.py
```

## Default profile (File → New Profile)

- Header: ICC v4, device class mntr, RGB space, PCS XYZ, platform MSFT, rendering intent media-relative colorimetric, creation time set on save, profile size/ID auto-managed.
- Tag set: cprt, rTRC, gTRC, bTRC, chad, rXYZ, gXYZ, bXYZ, wtpt, MSCA, lumi, MHC2, desc.
- Tag content (human values):
  - cprt: “Copyright (C) User.”
  - desc: “Default Device Profile.”
  - TRCs (r/g/b): gamma 2.2 (curve count=1).
  - Colorants: sRGB primaries (red, green, blue XYZ per sRGB) and wtpt: D65 normalized to Y=1.
  - chad: identity matrix.
  - MSCA: Windows HDR Calibration v1.0.152.0 text.
  - lumi: 80 cd/m² (X=Y=Z=80).
  - MHC2: min luminance 0.2 nits, peak luminance 80 nits, identity 3×4 matrix, identity 1DLUT with two points [0,1] per channel.

## Usage tips

- Select a tag in the Tag Table to open its workspace; toggle Human/Hex as needed; click “Apply Changes” to persist edits to the in-memory profile.
- MHC2 workspace: import matrix/LUT via CSV, apply identities, or compute a matrix in the calculator. Previews show normalized LUT values.
- TRC workspace: apply gamma presets or sRGB standard curve; updates propagate to shared TRCs at the same offset.

## SDR Profile Workflow

- ### Legacy, No ACM (Auto Color Management)

  - Curve rTRC, gTRC, bTRC
    - your calibration target curve
  - Colorant primaries rXYZ, gXYZ, bXYZ, wtpt
    - your display EDID or measured data
  - Luminance lumi
  - Advanced Color tag **MHC2**
    - min and peak luminance not required to change
    - Matrix (3x4, last column is not used by Windows)
      - enter values manually, or
      - load from csv of same format, or
      - apply default identity transform (pass-through), or
      - use four color matrix calculator to update matrix (least squares method)
      - useful for **color space proofing** e.g. source P3 to target sRGB, and **color correction**
    - 1DLUT load from csv
      - up to 4096 LUT entries
      - up to 16 bit fixed point precision (0-65535)
      - calibration profile/VCGT to your target TRC
  - update desc, cprt and header part as needed.

- ### Advanced Color with ACM

  - Curve rTRC, gTRC, bTRC use preset **sRGB** curve
    - see https://github.com/dantmnf/MHC2/issues/18
  - Advanced Color tag **MHC2**
    - Matrix use default identity transform
      - Windows will perform the color space conversion to the display's color space determined by the current default color profile.
      - by default, all apps are restricted to the sRGB gamut because Windows tells them the display is sRGB.
      - enable "Use legacy display ICC color management" in compatibility tab to grant the app access to the entire gamut of the display as specified in ICC Profile.
    - 1DLUT
      - calibration profile/VCGT to sRGB TRC
  - Everything else is same as Legacy profile workflow.

## HDR Profile Workflow

- ### Advanced Color (ACM is compulsory)

  - Colorant primaries rXYZ, gXYZ, bXYZ, wtpt
    - your display EDID or measured data
  - Luminance lumi
    - max full frame luminance
  - Advanced Color tag **MHC2**
    - min and peak luminance in nits
    - Matrix (3x4, last column is not used by Windows)
      - enter values manually, or
      - load from csv of same format, or
      - apply default identity transform (pass-through), or
      - use four color matrix calculator to update matrix (least squares method)
      - useful for **color correction**
    - 1DLUT load from csv
      - up to 4096 LUT entries
      - up to 16 bit fixed point precision (0-65535)
      - calibration profile to your target curve (BT.2100 PQ)
  - update desc, cprt and header part as needed.

- ### What profile does Windows HDR Calibration App creates?

  - Colorant primaries rXYZ, gXYZ, bXYZ, wtpt
    - read from your display EDID
  - Luminance data min, peak, and max full frame
    - based on user adjustment result in the app, not measured by hardware
  - Matrix
    - at last step of the "calibration" app, if saturation level is set to 0, identity transform applies (pass-through)
    - if you adjusted saturation level, the matrix will change accordingly
  - 1DLUT
    - identity transform (pass-through)
  - MSCA
    - Windows HDR Calibration App version and settings

## Troubleshooting

- ### My ICC profile/Advanced Color Management is not working after waking from sleep

  1. Open Task Scheduler, navigate to "Calibration Loader" task under Microsoft → Windows → WindowsColorSystem
  2. Edit properties, check "Run with highest privileges"
  3. In Triggers tab, add a new trigger "On an event"
     - Log: System
     - Source: Power-Troubleshooter
     - Event ID: 1

- ### My ICC profile/Advanced Color Management is not working for apps in full screen mode

  - Some apps (e.g. games) bypass Windows color management in full screen mode, bacause they switched Present Mode into Hardware - Independent Flip. What you can do:
    1. Disable MPO (Multi Plane Overlay), to prevent large window size trigger Independent Flip
    2. Run the app in windowed/borderless windowed mode
    3. Enable "Use legacy display ICC color management" in compatibility to force Composed Flip mode by DWM
  
## License

GPL-3.0-or-later. When redistributing (including EXE builds), provide full corresponding source and this license.

## Repository

Project home: https://github.com/ttys001/MHC-ICC-Profile-Maker
