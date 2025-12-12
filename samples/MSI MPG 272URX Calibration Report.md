# MSI MPG 272URX QD-OLED Calibration Report

## Setting up

- Monitor HDR Mode: True Black 400
- Windows HDR Mode: On
- Windows SDR Content Brightness: 90 (target luminance ~ 90*4+80=440 nits)
- Target Color Space: BT.2020 HDR
- Target White Point: D65
- Target TRC: ST 2084 PQ
- Window Size: 10%

## Ouptput Profile

- MHC ICC Profile for Advanced Color Management (ACM)
  - MPG272URX HDR Profile.icc
    - Matrix: Identity transform
    - 1DLUT: 4096 entries, 0-65535 range (calibrated with 33 grayscale points)

## Calibration Report

### Grayscale

Pre-calibration peak white: 477 nits, Post-calibration peak white: 465 nits.

| Pre-calibration <br> Avg $\Delta$ E=2.5, Max $\Delta$ E =4 | Post-calibration <br> Avg $\Delta$ E=0.5, Max $\Delta$ E=1.5 |
|:-:|:-:|
| ![Native Grayscale1](./MSI%20MPG%20272URX%20QD-OLED/precal_grayscale1.png) | ![Postcal Grayscale1](./MSI%20MPG%20272URX%20QD-OLED/postcal_grayscale1.png) |
| ![Native Grayscale2](./MSI%20MPG%20272URX%20QD-OLED/precal_grayscale2.png) | ![Postcal Grayscale2](./MSI%20MPG%20272URX%20QD-OLED/postcal_grayscale2.png) |

### ColorMatch HDR

| Pre-calibration <br> Avg $\Delta$ E=1.3, Max $\Delta$ E=3.87 | Post-calibration <br> Avg $\Delta$ E=0.88, Max $\Delta$ E=2.97 |
|:-:|:-:|
| ![Native Grayscale1](./MSI%20MPG%20272URX%20QD-OLED/precal_colormatch.png) | ![Postcal Grayscale1](./MSI%20MPG%20272URX%20QD-OLED/postcal_colormatch.png) |

### ColorChecker HDR

| Pre-calibration <br> Avg $\Delta$ E=1.35, Max $\Delta$ E=3.94 | Post-calibration <br> Avg $\Delta$ E=0.61, Max $\Delta$ E=1.47 |
|:-:|:-:|
| ![Native Grayscale1](./MSI%20MPG%20272URX%20QD-OLED/precal_colorchecker.png) | ![Postcal Grayscale1](./MSI%20MPG%20272URX%20QD-OLED/postcal_colorchecker.png) |

### ColorChecker SDR

Validated with sRGB target in HDR Mode to test ACM color space conversion and gamut mapping accuracy.

- Note that after calibration, the SDR white 440 nits is matching our SDR content slider (90/100) target.
- As reference, RTINGS review native sRGB SDR mode Avg $\Delta$ E=1.27, Max $\Delta$ E=2.14, and HDTVTest review the same mode Avg $\Delta$ E=1.06, Max $\Delta$ E=2.25.

| Pre-calibration <br> Avg $\Delta$ E=1.7, Max $\Delta$ E=4.2 | Post-calibration <br> Avg $\Delta$ E=0.4, Max $\Delta$ E=2 |
|:-:|:-:|
| ![Native Grayscale1](./MSI%20MPG%20272URX%20QD-OLED/precal_colorchecker_sdr.png) | ![Postcal Grayscale1](./MSI%20MPG%20272URX%20QD-OLED/postcal_colorchecker_sdr.png) |
