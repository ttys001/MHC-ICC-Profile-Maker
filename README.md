# MHC ICC Profile Maker

Windows GUI tool for building fully customized ICC v4 profiles that include Microsoft’s Advanced Color (MHC2) metadata. It provides human-friendly editors for header fields, tag tables, localized text, XYZ colorants, TRCs, luminance, MHC2 matrices/LUTs, and more. Default profiles load with sRGB primaries, D65 white, gamma 2.2 TRCs, and identity transforms for chad/MHC2.

## Features
- Header editor with human/hex toggle, ICC v4 field validation, automatic profile size/ID updates.
- Tag table viewer/editor with offsets/sizes, search/add/remove/reorder, duplicate prevention.
- Workspaces: mluc (cprt/desc), XYZ (r/g/b/wtpt), luminance, chad identity, MSCA text, MHC2 matrix+1DLUT (with CSV import, identity, previews, calculator), TRC presets (gamma/sRGB curves), raw hex view.
- Four-color matrix calculator with XYZ/xyY switch, quick fills from standard RGB color spaces, CSV import, and least-squares solve to MHC2 matrix.
- File menu for new profiles, loading/saving ICC/ICM files.

## Requirements
- Python 3.11+ on Windows.
- Dependencies: `pip install numpy`.
- Tkinter ships with standard Python on Windows.

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
      - use four color matrix calculator to update matrix
      - useful for **color space proofing** e.g. source P3 to target sRGB, calculator uses least squares method
    - 1DLUT load from csv
      - up to 4096 LUT entries
      - up to 16 bit fixed point precision (0-65535)
      - calibration profile/VCGT to your target TRC
  - update desc, cprt and header part as needed.
- ### Advanced Color with ACM
  - Curve rTRC, gTRC, bTRC use preset **sRGB** curve
    - see https://github.com/dantmnf/MHC2/issues/18
  - MHC2
    - Matrix use default identity transform
      - Windows will perform the color space conversion to the display's color space determined by the current default color profile.
      - by default, all apps are restricted to the sRGB gamut because Windows tells them the display is sRGB.
      - enable "Use legacy display ICC color management" in compatibility tab to grant the app access to entire gamut the display as specified in ICC Profile.
    - 1DLUT
      - calibration profile/VCGT to sRGB TRC
  - Everything else is same as Legacy profile workflow.

## HDR Profile Workflow
- ### Advanced Color (ACM is compulsory)
  - Colorant primaries rXYZ, gXYZ, bXYZ, wtpt
    - your display EDID or measured data
  - Luminance lumi
    - max full frame luminance
  - Advanced Color tag MHC2
    - min and peak luminance in nits
    - Matrix (3x4, last column is not used by Windows)
      - enter values manually, or
      - load from csv of same format, or
      - apply default identity transform (pass-through), or
      - use four color matrix calculator to update matrix
      - useful for **color correction**, uses least squares method
    - 1DLUT load from csv
      - up to 4096 LUT entries
      - up to 16 bit fixed point precision (0-65535)
      - calibration profile to your target curve (BT.2100 PQ)
  - update desc, cprt and header part as needed.
- ### What profile does Windows HDR Calibration tool creates?
  - Colorant primaries rXYZ, gXYZ, bXYZ, wtpt
    - read from your display EDID
  - Luminance data min, peak max full frame
    - based on user adjustment result in the app, not measured by hardware
  - Matrix
    - at last step of the tool "calibration", if saturation level is set to 0, then identity transform (pass-through)
    - if you adjusted saturation level, the matrix will change accordingly
  - 1DLUT
    - identity transform (pass-through)

## License
GPL-3.0-or-later. When redistributing (including EXE builds), provide full corresponding source and this license.

## Repository
Project home: https://github.com/ttys001/MHC-ICC-Profile-Maker
