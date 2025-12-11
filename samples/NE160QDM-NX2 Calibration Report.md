# BOE NE160QDM-NX2 Calibration Report

## Setting up

- Max panel backlight setting: 516 nits at native
- Target Color Space: sRGB, P3D65, Native (for ACM)
- Target White Point: D65
- Target TRC: sRGB

## Ouptput Profiles

- MHC ICC Profile for Legacy Color Management
  - NE160QDM-NX2 SDR sRGB.icc
  - NE160QDM-NX2 SDR P3D65.icc
- MHC ICC Profile for Advanced Color Management (ACM)
  - NE160QDM-NX2 SDR ACM.icc

## Calibration Report

### Grayscale

Post-calibration white point at 476 nits.

| Pre-calibration | Post-calibration |
|:-:|:-:|
| ![Native Grayscale](./NE160QDM-NX2/precal_grayscale.png) | ![Postcal Grayscale](./NE160QDM-NX2/postcal_grayscale.png) |

### Color Checker

| Pre-cal Native Gamut | Post-cal sRGB |
|:-:|:-:|
| ![Native Gamut](./NE160QDM-NX2/precal_gamut.png) | ![sRGB](./NE160QDM-NX2/postcal_sRGB.png) |
| **Post-cal P3D65** | **Post-cal ACM to sRGB** |
| ![sRGB](./NE160QDM-NX2/postcal_P3D65.png) | ![P3D65](./NE160QDM-NX2/postcal_ACM_sRGB.png) |
