# MHC ICC Profile Maker

Windows GUI tool for building fully customized ICC v4 profiles that include Microsoft’s Advanced Color (MHC2) metadata. It provides human-friendly editors for header fields, tag tables, localized text, XYZ colorants, TRCs, luminance, MHC2 matrices/LUTs, and more. Default profiles load with sRGB primaries, D65 white, gamma 2.2 TRCs, and identity transforms for chad/MHC2.

## Features
- Header editor with human/hex toggle, ICC v4 field validation, automatic profile size/ID updates.
- Tag table viewer/editor with offsets/sizes, search/add/remove/reorder, duplicate prevention.
- Workspaces: mluc (cprt/desc), XYZ (r/g/b/wtpt), luminance, chad identity, MSCA text, MHC2 matrix+1DLUT (with CSV import, identity, previews, calculator), TRC presets (gamma/sRGB curves), raw hex view.
- Four-color matrix calculator with XYZ/xyY switch, quick fills from standard RGB color spaces, CSV import, and least-squares solve to MHC2 matrix.
- File menu for new profiles, loading/saving ICC/ICM files, and “About” dialog.

## Requirements
- Python 3.11+ on Windows.
- Dependencies: `pip install colour-science numpy`
- Tkinter ships with standard Python on Windows.

## Running from source
```bash
pip install -r requirements.txt  # or install colour-science, numpy manually
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
  - Tag table: offsets/sizes recomputed on build; duplicate data shared across RGB TRCs where applicable.

## Usage tips
- Select a tag in the Tag Table to open its workspace; toggle Human/Hex as needed; click “Apply Changes” to persist edits to the in-memory profile.
- MHC2 workspace: import/export matrix/LUT via CSV, apply identities, or compute a matrix in the calculator. Previews show normalized LUT samples.
- TRC workspace: apply gamma presets or sRGB standard curve; updates propagate to shared TRCs at the same offset.

## License
GPL-3.0-or-later. When redistributing (including EXE builds), provide full corresponding source and this license.

## Repository
Project home: https://github.com/ttys001/MHC-ICC-Profile-Maker
