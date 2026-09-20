# MHC ICC Profile Maker

[English](README.md) | 简体中文

用于创建和编辑带 Microsoft Hardware Calibration（`MHC2`）元数据的 ICC v4 显示器配置文件的 Windows 图形工具。它为 ICC 文件头、标签表、本地化文本、XYZ 三刺激值、TRC、亮度及 MHC2 矩阵/1D LUT 数据提供结构化编辑界面，同时保留原始十六进制视图。

## 功能

- 创建、载入、编辑、验证并以原子方式保存 ICC v4 显示器配置文件。
- 通过专用工作区或原始十六进制数据编辑常见标签。
- 从 CSV 导入 3×3/3×4 矩阵；从 CSV、1D Cube 或 ColourSpace/Quantel TXT 导入 RGB 1D LUT。
- 可选用纯 Python、保持曲线形状的 PCHIP 对 RGB 1D LUT 重采样。
- 根据 W/R/G/B 四色测量数据，以最小二乘法计算校正矩阵。
- 运行时不依赖第三方 Python 包，也不需要 NumPy。
- 附带 SDR、HDR 配置文件及校准报告作为实际示例。

## 下载

从 [GitHub Releases](https://github.com/ttys001/MHC-ICC-Profile-Maker/releases) 下载当前 Windows 可执行文件。

## 系统要求

- 从源代码运行需要 Windows、Python 3.11+ 和 Tkinter。
- 应用 MHC 硬件校准管线需要 Windows 10 2004 或更高版本、受支持的 GPU 及 WDDM 2.6+；部分 GPU 需要更新的驱动。
- Windows HDR Calibration 应用需要 Windows 11；Advanced Color 功能是否可用还取决于 Windows 版本和硬件。
- 只有构建可执行文件时才需要 PyInstaller。

## 运行、测试与构建

```powershell
python mhc_icc_gui.py
python -S -m unittest -v
```

构建优化后的单文件 Windows 可执行程序：

```powershell
python -m PyInstaller --noconfirm --clean --onefile --windowed --optimize 2 --name "MHC-ICC-Profile-Maker_v0.94" mhc_icc_gui.py
```

## 快速工作流程

1. 选择 **File → New Profile** 或 **File → Load ICC…**。
2. 选择标签，在 Human 或 Hex 模式下编辑，然后选择 **Apply Changes**。
3. 保存配置文件。应用会更新创建时间、文件大小和 ICC Profile ID。
4. 正式使用前，请在目标 Windows 系统和显示器上验证结果。

## 矩阵与 RGB 1D LUT 输入

- 矩阵：三行数值，每行三列或四列。Windows 以 3×4 格式保存矩阵，但忽略第四列。
- **Load RGB 3x1DLUT…** 支持 CSV、1D `.cube` 和 ColourSpace/Light Illusion Quantel 风格的 `.txt`，数据为 RGB 三列；拒绝 3D LUT。
- MHC2 支持 **1–4096 的任意条目数**，不要求是 2 的幂。导入保留原始采样数量：101 行源数据就写入 101 个条目，不补点、不截断、不自动重采样；`Entries:` 保持只读。
- CSV 可使用归一化的 `0–1`，或整数范围 `0–255`、`0–1023`、`0–4095`、`0–65535`；应用检测范围并归一化到 `0–1`。支持逗号、分号、制表符、UTF-8 BOM、空行及 `#` 注释。
- Cube 必须包含与数据行数一致的 `LUT_1D_SIZE`，输出值须为 `0–1`；可带 `TITLE` 和注释。输入域须省略或为 `DOMAIN_MIN 0 0 0` / `DOMAIN_MAX 1 1 1`；其他输入域会被拒绝，不会用于缩放输出值。
- Quantel TXT 允许数据表前的文字头。显式的 `max value 1023`、`max value 65535`、`bit depth 10` 或 `range 0 1023` 元数据（包括带 `#` 前缀的形式）决定归一化范围；无元数据时才采用 CSV 的范围检测。拒绝冲突元数据、无效数值及 `cube size`、`cube data`、`vertices`、`LUT3D` 等 3D 声明。
- 矩阵计算器接受 xyY 或 XYZ 格式的 W/R/G/B 四行数据。

### 可选重采样

默认流程为 **导入 → 保留源采样点 → 按原始条目数写入 MHC2**。只有主动点击 **Resample 1DLUT…**，才会将当前 LUT 转换为 1–4096 范围内的目标条目数。4096 只是可选上限，并非要求；导入从不自动重采样。

PCHIP 仅使用标准库，保持局部曲线形状与单调区间，避免普通三次样条振铃，也不会自动修复源曲线中的非单调段。目标至少为两点时，精确保留源黑白端点，包括低于 1 的白平衡校准值。单点源扩展为常量，两点源采用线性插值。目标为一点时保留源首点（无法同时保留两个端点）；目标数量不变时不改变数值。

解析和重采样在工作区保留 Python float 精度，仅在 ICC 序列化时量化为 s15Fixed16；重新打开已保存的配置文件时读取的是量化值。可据此比较原始 LUT 与主动 PCHIP 重采样后的 LUT 在 Windows/硬件管线中的结果；软件测试不能代替显示器实测。

## 默认配置文件

**File → New Profile** 会创建：

| 项目 | 默认值 |
| --- | --- |
| 文件头 | ICC v4 显示器配置文件（`mntr`）、RGB、PCS XYZ、`MSFT` 平台、媒体相对色度意图 |
| 标签 | `cprt`、`rTRC`、`gTRC`、`bTRC`、`chad`、`rXYZ`、`gXYZ`、`bXYZ`、`wtpt`、`MSCA`、`lumi`、`MHC2`、`desc` |
| 色彩 | sRGB 三原色、Y=1 的 D65 白点、单位矩阵 `chad` |
| TRC | 三通道共享 gamma 2.2 `curveType` 数据 |
| 亮度 | `lumi` = 80 nits；MHC2 最低亮度 = 0.2 nits，峰值亮度 = 80 nits |
| MHC2 变换 | 显式 3×4 单位矩阵和两点 RGB 单位 1D LUT，与 Windows HDR Calibration 输出保持一致 |
| 文本 | `Copyright (C) User.` 和 `Default Device Profile` |
| MSCA | `{'Appversion':'1.0.152.0','D65Adapted':True}` |

## MHC2 关键规则

- 可用的 MHC 配置文件必须包含有效的 ST.2086 元数据：RGB 三原色、白点、最大全帧亮度、最低亮度和峰值亮度。默认值仅应作为目标显示器的占位值。
- 矩阵以 3×4 行优先格式保存，但 Windows 只使用左侧三列。不要加入源 RGB→XYZ 或 XYZ→目标 RGB 转换；这些转换由显示驱动完成。
- MHC2 1D LUT 是在线路格式传递函数之后应用的校准调整。不要把 sRGB、gamma 或 PQ 传递函数编码到其中。
- 矩阵偏移为零，或 LUT 条目数及三个 LUT 偏移均为零时，明确表示单位变换。
- 硬件支持的 LUT 条目数或精度可能低于配置文件；Windows 会插值到硬件支持的大小。

## 工作流建议

### 传统 SDR

根据目标色彩空间使用合适的 ICC TRC 和色度标签。MHC2 矩阵可用于色彩空间校样等有意的 XYZ 调整或测量校正；1D LUT 用于线路格式传递函数之后的校准。同时应填写有效亮度元数据。

### SDR 与 Advanced Color / ACM

使用测得的原生三原色和有效亮度元数据。Windows 会根据当前显示器配置文件完成源内容到显示器的色彩转换。在 Windows 11 上，传统的 ICC 色彩管理应用默认受限于 sRGB 行为；如需访问显示器完整色域，应针对该应用启用 **Use legacy display ICC color management** 兼容选项。

### HDR

使用测得或可靠的显示器三原色/白点；在 `lumi` 中保存最大全帧亮度，在 `MHC2` 中保存最低和峰值亮度。矩阵可用于有意的 XYZ 调整或测量校正；1D LUT 用于线路格式传递函数之后的校准。无需调整时可使用单位变换。

## 示例

- [HDR：MSI MPG 272URX QD-OLED](samples/MSI%20MPG%20272URX%20Calibration%20Report.md)
- [SDR：BOE NE160QDM-NX2](samples/NE160QDM-NX2%20Calibration%20Report.md)
- [SDR：BOE NE160QDM-NM7](samples/NE160QDM-NM7%20Calibration%20Report.md)

## 故障排除

### 睡眠唤醒后未恢复校准

睡眠唤醒或显示拓扑变化后，即使经典颜色管理控制面板显示正确的系统默认值，Windows 也可能选择另一台显示器的配置文件。仓库不再提供自动守护程序，因为显示关联可能跟随 GPU 源插槽转移到另一台显示器；请关闭 **Use my settings for this device**，并在问题出现时重新连接显示器或再次选择正确的系统默认值。

### 全屏与 Independent Flip

MHC 校准由 Windows 显示校准管线载入，并不是 DWM 着色器。不要仅根据“窗口”“无边框”或“全屏”判断实际呈现路径：使用 flip model 的窗口应用也可能被提升为 independent flip。HDR 元数据和显示器 tone mapping 属于另外的、与具体设备相关的问题。

MSI MPG 272URX 的 tone mapping 说明只适用于测试时的显示器固件和设置，详情请参阅其[校准报告](samples/MSI%20MPG%20272URX%20Calibration%20Report.md)。

## 参考资料

- [Windows 硬件显示色彩校准管线](https://learn.microsoft.com/en-us/windows/win32/wcs/display-calibration-mhc)
- [Advanced Color 下的 ICC 配置文件行为](https://learn.microsoft.com/en-us/windows/win32/wcs/advanced-color-icc-profiles)
- [Windows HDR Calibration](https://apps.microsoft.com/detail/9N7F2SM5D1LR)
- [DXGI flip model 指南](https://learn.microsoft.com/en-us/windows/win32/direct3ddxgi/for-best-performance--use-dxgi-flip-model)
- [ICC 配置文件规范](references/ICC.1-2022-05.pdf)

## 许可证

GPL-3.0-or-later。再发行（包括可执行文件）时，必须同时提供对应源代码和许可证。
