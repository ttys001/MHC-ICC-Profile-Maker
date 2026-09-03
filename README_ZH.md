# MHC ICC Profile Maker

[English](README.md) | 简体中文

用于创建和编辑带 Microsoft Hardware Calibration（`MHC2`）元数据的 ICC v4 显示器配置文件的 Windows 图形工具。它为 ICC 文件头、标签表、本地化文本、XYZ 三刺激值、TRC、亮度及 MHC2 矩阵/1D LUT 数据提供结构化编辑界面，同时保留原始十六进制视图。

## 功能

- 创建、载入、编辑、验证并以原子方式保存 ICC v4 显示器配置文件。
- 通过专用工作区或原始十六进制数据编辑常见标签。
- 从 CSV 导入 3×3/3×4 矩阵和 RGB 1D LUT。
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
python -m PyInstaller --noconfirm --clean --onefile --windowed --optimize 2 --name "MHC-ICC-Profile-Maker_v0.93" mhc_icc_gui.py
```

## 快速工作流程

1. 选择 **File → New Profile** 或 **File → Load ICC…**。
2. 选择标签，在 Human 或 Hex 模式下编辑，然后选择 **Apply Changes**。
3. 保存配置文件。应用会更新创建时间、文件大小和 ICC Profile ID。
4. 正式使用前，请在目标 Windows 系统和显示器上验证结果。

## CSV 输入

- 矩阵：三行数值，每行三列或四列。Windows 以 3×4 格式保存矩阵，但忽略第四列。
- RGB 1D LUT：1–4096 行，每行包含 R、G、B 三列。
- LUT 可使用归一化的 `0–1`，或整数范围 `0–255`、`0–1023`、`0–4095`、`0–65535`；应用会将其归一化到 `0–1`。
- 支持逗号、分号和制表符分隔；以 `#` 开头的行为注释。
- 矩阵计算器接受 xyY 或 XYZ 格式的 W/R/G/B 四行数据。

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

MSCA 中的应用版本已于 2026-07-30 对照 Microsoft Store 实时目录核验，与 Windows HDR Calibration `1.0.152.0` 一致。MSCA 是 Microsoft 私有标签；只修改版本字符串并不能复现另一个应用版本的行为。

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

仓库中的参考配置文件带有相同的 Windows HDR Calibration `1.0.152.0` MSCA 字符串。MSCA 是私有标签，因此不能据此断定未来版本仍会使用相同数据。

## 示例

- [HDR：MSI MPG 272URX QD-OLED](samples/MSI%20MPG%20272URX%20Calibration%20Report.md)
- [SDR：BOE NE160QDM-NX2](samples/NE160QDM-NX2%20Calibration%20Report.md)
- [SDR：BOE NE160QDM-NM7](samples/NE160QDM-NM7%20Calibration%20Report.md)

## 故障排除

### 睡眠唤醒后未恢复校准

如果经典颜色管理控制面板中的显示器专用关联正确，但“设置”选择了其他显示器的配置文件，可以使用仓库附带的 [MHC Profile Guard](MHC-Profile-Guard)。它会读取每台活动显示器的硬件标识和现有高级系统默认值，再通过当前用户的 Windows 颜色配置文件 API 恢复对应的 SDR 与 HDR 配置文件。

在 PowerShell 中安装计划任务：

```powershell
.\MHC-Profile-Guard\MhcProfileGuard.ps1 -Install
```

该任务会在登录、显示配置变化、显示器连接或移除，以及睡眠唤醒后静默运行。每次运行会在 25 秒后退出，任务计划程序还会强制执行 30 秒上限；后台不会持续轮询。不带参数运行脚本，可以执行一次修复并显示当前关联。使用以下命令移除计划任务：

```powershell
.\MHC-Profile-Guard\MhcProfileGuard.ps1 -Uninstall
```

对于 Windows 自带的校准加载器，请打开任务计划程序，检查 **Microsoft → Windows → WindowsColorSystem → Calibration Loader**。启用 **Run with highest privileges**，并添加 **On an event** 触发器：System 日志、来源 `Power-Troubleshooter`、事件 ID `1`。

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
