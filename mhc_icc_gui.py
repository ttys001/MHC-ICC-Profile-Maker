import hashlib
import re
import struct
import tkinter as tk
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Dict, List, Tuple

import numpy as np


DEVICE_CLASSES: Dict[str, str] = {
    "scnr": "Input device (scanner)",
    "mntr": "Display device",
    "prtr": "Output device (printer)",
    "link": "DeviceLink",
    "spac": "ColorSpace",
    "abst": "Abstract",
    "nmcl": "NamedColor",
}

COLOR_SPACES: Dict[str, str] = {
    "XYZ ": "nCIEXYZ",
    "Lab ": "CIELAB",
    "Luv ": "CIELUV",
    "YCbr": "YCbCr",
    "Yxy ": "Yxy",
    "RGB ": "RGB",
    "GRAY": "Gray",
    "HSV ": "HSV",
    "HLS ": "HLS",
    "CMYK": "CMYK",
    "CMY ": "CMY",
    "2CLR": "2 color",
    "3CLR": "3 color (other than those listed above)",
    "4CLR": "4 color (other than CMYK)",
    "5CLR": "5 color",
    "6CLR": "6 color",
    "7CLR": "7 color",
    "8CLR": "8 color",
    "9CLR": "9 color",
    "ACLR": "10 color",
    "BCLR": "11 color",
    "CCLR": "12 color",
    "DCLR": "13 color",
    "ECLR": "14 color",
    "FCLR": "15 color",
}

ILLUMINANTS: Dict[str, Tuple[float, float]] = {
    "D50": (0.34570000584, 0.35849999729),
    "D55": (0.33243000092, 0.34743999954),
    "D60": (0.32161670651, 0.33761992471),
    "D65": (0.31269998882, 0.3289999976),
    "D75": (0.29903001216, 0.31488000081),
}

RGB_SPACE_DATA: Dict[str, Dict[str, object]] = {
    "sRGB": {
        "white": "D65",
        "matrix": [
            [0.4124, 0.3576, 0.1805],
            [0.2126, 0.7152, 0.0722],
            [0.0193, 0.1192, 0.9505],
        ],
    },
    "ITU-R BT.709": {
        "white": "D65",
        "matrix": [
            [0.4123908, 0.3575843, 0.1804808],
            [0.2126390, 0.7151687, 0.0721923],
            [0.0193308, 0.1191948, 0.9505321],
        ],
    },
    "Adobe RGB (1998)": {
        "white": "D65",
        "matrix": [
            [0.57667, 0.18556, 0.18823],
            [0.29734, 0.62736, 0.07529],
            [0.02703, 0.07069, 0.99134],
        ],
    },
    "P3-D65": {
        "white": "D65",
        "matrix": [
            [0.4865709486482162, 0.26566769316909306, 0.1982172852343625],
            [0.2289745640697488, 0.6917385218365064, 0.079286914093745],
            [0.0000000000000000, 0.04511338185890264, 1.043944368900976],
        ],
    },
    "DCI-P3": {
        "white": "DCI",
        "white_xy": (0.314, 0.351),
        "matrix": [
            [0.445169815, 0.2771344092, 0.1722826698],
            [0.2094916779, 0.7215952542, 0.0689130679],
            [0.0000000000, 0.0470605601, 0.9073553944],
        ],
    },
    "ITU-R BT.2020": {
        "white": "D65",
        "matrix": [
            [0.6369580483012914, 0.14461690358620832, 0.1688809751641721],
            [0.2627002120112671, 0.6779980715188708, 0.05930171646986196],
            [0.0000000000000000, 0.028072693049087428, 1.060985057710791],
        ],
    },
}

def xy_to_XYZ_custom(xy: Tuple[float, float], Y: float = 1.0) -> Tuple[float, float, float]:
    x, y = xy
    if y == 0:
        return (0.0, 0.0, 0.0)
    X = (x * Y) / y
    Z = ((1 - x - y) * Y) / y
    return (X, Y, Z)


def xyY_to_XYZ_custom(xyy: Tuple[float, float, float]) -> Tuple[float, float, float]:
    x, y, Y = xyy
    if y == 0:
        return (0.0, 0.0, 0.0)
    X = (x * Y) / y
    Z = ((1 - x - y) * Y) / y
    return (X, Y, Z)


def XYZ_to_xyY_custom(XYZ: Tuple[float, float, float]) -> Tuple[float, float, float]:
    X, Y, Z = XYZ
    total = X + Y + Z
    if total == 0:
        return (0.0, 0.0, 0.0)
    x = X / total
    y = Y / total
    return (x, y, Y)


def rgb_primary_from_matrix(space: str, primary: str) -> Tuple[float, float, float]:
    data = RGB_SPACE_DATA[space]
    mat = np.asarray(data["matrix"], dtype=float)
    if primary == "r":
        vec = mat[:, 0]
    elif primary == "g":
        vec = mat[:, 1]
    else:
        vec = mat[:, 2]
    return tuple(float(v) for v in vec)


def rgb_whitepoint_xyz(space: str) -> Tuple[float, float, float]:
    data = RGB_SPACE_DATA[space]
    if "white_xy" in data:
        xy = data["white_xy"]
    else:
        xy = ILLUMINANTS.get(data["white"], (0.31270, 0.32900))
    return xy_to_XYZ_custom(xy)


PCS_CHOICES: Dict[str, str] = {
    "XYZ ": "PCSXYZ",
    "Lab ": "PCSLAB",
}

PLATFORM_CHOICES: Dict[str, str] = {
    "0000": "Empty (zero)",
    "APPL": "Apple",
    "MSFT": "Microsoft",
    "SGI ": "Silicon Graphics",
    "SUNW": "Sun Microsystems",
}

RENDERING_INTENTS: Dict[int, str] = {
    0: "Perceptual",
    1: "Media-relative colorimetric",
    2: "Saturation",
    3: "ICC-absolute colorimetric",
}

# Header defaults pulled from the sample BASE profile
HEADER_FIELDS: List[Dict[str, object]] = [
    {"key": "size", "label": "Profile size (bytes)", "length": 4, "type": "size", "default_hex": "0000032C"},
    {"key": "cmm_type", "label": "CMM type", "length": 4, "type": "sig", "default_hex": "53494343"},
    {"key": "version", "label": "ICC version", "length": 4, "type": "version", "default_hex": "04400000"},
    {"key": "device_class", "label": "Device class", "length": 4, "type": "choice", "choices": DEVICE_CLASSES, "default_hex": "6D6E7472"},
    {"key": "color_space", "label": "Color space", "length": 4, "type": "choice", "choices": COLOR_SPACES, "default_hex": "52474220"},
    {"key": "pcs", "label": "PCS", "length": 4, "type": "choice", "choices": PCS_CHOICES, "default_hex": "58595A20"},
    {"key": "date_time", "label": "Creation date", "length": 12, "type": "datetime-fixed", "default_hex": "07E9000C00040010002F0010"},
    {"key": "acsp", "label": "acsp signature", "length": 4, "type": "sig-fixed", "default_hex": "61637370"},
    {"key": "platform", "label": "Platform", "length": 4, "type": "choice", "choices": PLATFORM_CHOICES, "default_hex": "4D534654"},
    {"key": "flags", "label": "Flags", "length": 4, "type": "flags", "default_hex": "00000000"},
    {"key": "manufacturer", "label": "Manufacturer", "length": 4, "type": "sig-limited", "default_hex": "00000000"},
    {"key": "model", "label": "Model", "length": 4, "type": "sig-limited", "default_hex": "00000000"},
    {"key": "attributes", "label": "Device attributes", "length": 8, "type": "attributes", "default_hex": "0000000000000001"},
    {"key": "rendering_intent", "label": "Rendering intent", "length": 4, "type": "intent", "default_hex": "00000001"},
    {"key": "illuminant", "label": "Illuminant (XYZ)", "length": 12, "type": "illuminant", "default_hex": "0000F6D6000100000000D32D"},
    {"key": "creator", "label": "Profile creator", "length": 4, "type": "sig-limited", "default_hex": "4D534654"},
    {"key": "profile_id", "label": "Profile ID", "length": 16, "type": "profile_id", "default_hex": "00" * 16},
    {"key": "reserved", "label": "Reserved", "length": 28, "type": "hex", "default_hex": "00" * 28, "hidden": True},
]


def clean_hex(value: str) -> str:
    return re.sub(r"[^0-9A-Fa-f]", "", value or "")


def int_to_hex(value: int, length_bytes: int) -> str:
    max_val = 256 ** length_bytes - 1
    if value < 0 or value > max_val:
        raise ValueError(f"Value {value} does not fit in {length_bytes} bytes.")
    return f"{value:0{length_bytes * 2}X}"


def hex_to_sig(hex_str: str) -> str:
    bytes_val = bytes.fromhex(hex_str[:8])
    try:
        return bytes_val.decode("ascii")
    except Exception:
        return bytes_val.hex().upper()


def sig_to_hex(sig: str) -> str:
    if len(sig) != 4:
        raise ValueError("Signature must be exactly 4 characters.")
    try:
        encoded = sig.encode("ascii")
    except Exception:
        raise ValueError("Signature must be ASCII.")
    return encoded.hex().upper()


def hex_to_version(hex_str: str) -> str:
    value = int(hex_str, 16)
    major = (value >> 24) & 0xFF
    minor = (value >> 20) & 0x0F
    bugfix = (value >> 16) & 0x0F
    return f"{major}.{minor}{bugfix if bugfix else ''}"


def version_to_hex(text: str) -> str:
    m = re.match(r"^(\d+)(?:\.(\d)(\d)?)?$", text.strip())
    if not m:
        raise ValueError("Version must be like 4.4 or 4.31")
    major = int(m.group(1))
    minor = int(m.group(2) or 0)
    bugfix = int(m.group(3) or 0)
    value = (major << 24) | (minor << 20) | (bugfix << 16)
    return int_to_hex(value, 4)


def hex_to_datetime_text(hex_str: str) -> str:
    parts = [int(hex_str[i : i + 4], 16) for i in range(0, 24, 4)]
    try:
        dt = datetime(*parts)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return f"{parts[0]:04d}-{parts[1]:02d}-{parts[2]:02d} {parts[3]:02d}:{parts[4]:02d}:{parts[5]:02d}"


def datetime_text_to_hex(text: str) -> str:
    try:
        dt = datetime.strptime(text.strip(), "%Y-%m-%d %H:%M:%S")
    except Exception:
        raise ValueError("Date must be YYYY-MM-DD HH:MM:SS")
    parts = [dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second]
    return "".join(int_to_hex(p, 2) for p in parts)


def to_s15fixed16(value: float) -> int:
    return int(round(value * 65536))


def from_s15fixed16(raw: int) -> float:
    if raw & 0x80000000:
        raw = -((~raw + 1) & 0xFFFFFFFF)
    return raw / 65536.0


def hex_to_xyz_text(hex_str: str) -> str:
    if len(hex_str) < 24:
        raise ValueError("XYZ needs 12 bytes")
    x_raw, y_raw, z_raw = struct.unpack(">iii", bytes.fromhex(hex_str[:24]))
    vals = [from_s15fixed16(v) for v in (x_raw, y_raw, z_raw)]
    return ",".join(f"{v:.5f}" for v in vals)


def xyz_text_to_hex(text: str) -> str:
    parts = re.split(r"[ ,]+", text.strip())
    if len(parts) != 3:
        raise ValueError("XYZ needs three values like 0.9642,1.0000,0.8249")
    vals = [float(p) for p in parts]
    fixed = [to_s15fixed16(v) for v in vals]
    return struct.pack(">iii", *fixed).hex().upper()


def human_to_hex(field: Dict[str, object], text: str) -> str:
    t = field["type"]
    length = field["length"]
    if t == "u32":
        return int_to_hex(int(text), length)
    if t == "u64":
        return int_to_hex(int(text), length)
    if t == "hex":
        cleaned = clean_hex(text).upper()
        return cleaned.zfill(length * 2)[: length * 2]
    if t in {"sig", "sig-fixed"}:
        return sig_to_hex(text.strip().ljust(4)[:4])
    if t == "sig-limited":
        cleaned = text.rstrip()
        if len(cleaned) > 4:
            raise ValueError("Field must be 4 characters or fewer.")
        if not cleaned:
            return "00000000"
        padded = cleaned.ljust(4)
        return sig_to_hex(padded)
    if t == "choice":
        if text.startswith("0000"):
            return "00000000"
        sig = text[:4]
        return sig_to_hex(sig)
    if t == "version":
        return version_to_hex(text)
    if t == "datetime":
        return datetime_text_to_hex(text)
    if t == "xyz":
        return xyz_text_to_hex(text)
    if t == "intent":
        m = re.match(r"\s*(\d+)", text)
        intent_val = int(m.group(1)) if m else next((k for k, v in RENDERING_INTENTS.items() if v.lower() == text.lower()), None)
        if intent_val is None or intent_val not in RENDERING_INTENTS:
            raise ValueError("Rendering intent must be 0-3")
        return int_to_hex(intent_val, length)
    raise ValueError(f"Unsupported field type {t}")


def hex_to_human(field: Dict[str, object], hex_str: str) -> str:
    t = field["type"]
    if t in {"u32", "u64"}:
        return str(int(hex_str, 16))
    if t == "hex":
        return hex_str.upper()
    if t in {"sig", "sig-fixed", "choice", "sig-limited"}:
        return hex_to_sig(hex_str)
    if t == "version":
        return hex_to_version(hex_str)
    if t == "datetime":
        return hex_to_datetime_text(hex_str)
    if t == "xyz":
        return hex_to_xyz_text(hex_str)
    if t == "intent":
        val = int(hex_str, 16)
        return RENDERING_INTENTS.get(val, "Unknown")
    return hex_str


def normalize_hex_length(field: Dict[str, object], hex_str: str) -> str:
    cleaned = clean_hex(hex_str).upper()
    required = field["length"] * 2
    if len(cleaned) < required:
        cleaned = cleaned.ljust(required, "0")
    return cleaned[:required]


def decode_flags(hex_str: str) -> Tuple[str, str]:
    val = int(hex_str, 16)
    embedded = "Embedded" if val & 0x1 else "Not embedded"
    independent = "Independent" if not (val & 0x2) else "Not independent"
    return embedded, independent


def encode_flags(embedded: str, independent: str) -> str:
    val = 0
    emb_txt = embedded.strip().lower()
    indep_txt = independent.strip().lower()
    if emb_txt.startswith("embed"):
        val |= 0x1  # bit0 = 1 => embedded
    if indep_txt.startswith("not"):
        val |= 0x2  # bit1 = 1 => not independent
    return int_to_hex(val, 4)


def decode_attributes(hex_str: str) -> Tuple[str, str, str, str]:
    val = int(hex_str, 16)
    reflective = "Reflective" if not (val & 0x1) else "Transparency"
    gloss = "Glossy" if not (val & 0x2) else "Matte"
    polarity = "Positive" if not (val & 0x4) else "Negative"
    color = "Color" if not (val & 0x8) else "Black & White"
    return reflective, gloss, polarity, color


def encode_attributes(reflective: str, gloss: str, polarity: str, color: str) -> str:
    val = 0
    if reflective.strip().lower().startswith("trans"):
        val |= 0x1  # bit0
    if gloss.strip().lower().startswith("matte"):
        val |= 0x2  # bit1
    if polarity.strip().lower().startswith("neg"):
        val |= 0x4  # bit2
    if color.strip().lower().startswith("black"):
        val |= 0x8  # bit3
    return int_to_hex(val, 8)


def hex_to_xyz_components(hex_str: str) -> Tuple[float, float, float]:
    if len(hex_str) < 24:
        raise ValueError("XYZ needs 12 bytes")
    x_raw, y_raw, z_raw = struct.unpack(">iii", bytes.fromhex(hex_str[:24]))
    return tuple(from_s15fixed16(v) for v in (x_raw, y_raw, z_raw))


def xyz_components_to_hex(x: float, y: float, z: float) -> str:
    fixed = [to_s15fixed16(v) for v in (x, y, z)]
    return struct.pack(">iii", *fixed).hex().upper()


def chad_identity_bytes() -> bytes:
    values = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]
    fixed = [to_s15fixed16(v) for v in values]
    return struct.pack(">4s4x" + "i" * 9, b"sf32", *fixed)


def identity_matrix12() -> List[float]:
    return [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0]


def default_header_values_hex() -> Dict[str, str]:
    now = datetime.now()
    now_hex = datetime_text_to_hex(now.strftime("%Y-%m-%d %H:%M:%S"))
    values = {}
    for f in HEADER_FIELDS:
        if f["key"] == "date_time":
            values[f["key"]] = now_hex
        else:
            values[f["key"]] = f["default_hex"]
    return values


@dataclass
class TagEntry:
    signature: str
    description: str
    data_hex: str
    offset: int = 0

    def data_bytes(self) -> bytes:
        cleaned = clean_hex(self.data_hex)
        if len(cleaned) % 2:
            raise ValueError(f"Tag {self.signature}: hex data must have an even number of characters.")
        return bytes.fromhex(cleaned)

    def size(self) -> int:
        return len(self.data_bytes())


# Expanded tag library from ICC v4 plus Windows-specific tags
KNOWN_TAG_LIBRARY: Dict[str, str] = {
    "A2B0": "AToB0 (PCS -> Device)",
    "A2B1": "AToB1",
    "A2B2": "AToB2",
    "A2B3": "AToB3",
    "B2A0": "BToA0 (Device -> PCS)",
    "B2A1": "BToA1",
    "B2A2": "BToA2",
    "B2A3": "BToA3",
    "bXYZ": "Blue colorant",
    "bTRC": "Blue tone reproduction curve",
    "bkpt": "Media black point",
    "calt": "Calibration date/time",
    "chad": "Chromatic adaptation",
    "chrm": "Chromaticity",
    "clro": "Colorant order",
    "clrt": "Colorant table",
    "cprt": "Copyright",
    "crdi": "CrdInfo",
    "dmdd": "Device model description",
    "dmnd": "Device manufacturer description",
    "desc": "Profile description",
    "gamt": "Gamut",
    "gXYZ": "Green colorant",
    "gTRC": "Green tone reproduction curve",
    "kTRC": "Black tone reproduction curve",
    "lumi": "Luminance",
    "meas": "Measurement",
    "mluc": "Multi-localized Unicode",
    "mmod": "Make and model",
    "MSCA": "Microsoft Color Adaptation",
    "MHC2": "Windows Advanced Color metadata",
    "ncl2": "Named color 2",
    "pseq": "Profile sequence description",
    "psid": "Profile sequence identifier",
    "rXYZ": "Red colorant",
    "rTRC": "Red tone reproduction curve",
    "resp": "Output response",
    "rig0": "Perceptual rendering intent gamut",
    "rig2": "ICC-absolute rendering intent gamut",
    "scrd": "Screening description",
    "scrn": "Screening",
    "targ": "CharTarget",
    "tech": "Technology",
    "vcgt": "Video card gamma",
    "view": "Viewing conditions",
    "vued": "Viewing conditions description",
    "wtpt": "Media white point",
}

DEFAULT_TAGS_SAMPLE: List[TagEntry] = [
    TagEntry("cprt", "Copyright", "6D6C756300000000000000010000000C656E5553000000260000001C0043006F0070007900720069006700680074002000280043002900200055007300650072002E0000"),
    TagEntry("rTRC", "Red tone reproduction curve", "63757276000000000000000102330000"),
    TagEntry("gTRC", "Green tone reproduction curve", "63757276000000000000000102330000"),
    TagEntry("bTRC", "Blue tone reproduction curve", "63757276000000000000000102330000"),
    TagEntry("chad", "Chromatic adaptation", "7366333200000000000100000000000000000000000000000001000000000000000000000000000000010000"),
    TagEntry("rXYZ", "Red colorant", "58595A2000000000000069930000366D000004F1"),
    TagEntry("gXYZ", "Green colorant", "58595A200000000000005B8C0000B71700001E84"),
    TagEntry("bXYZ", "Blue colorant", "58595A200000000000002E350000127C0000F354"),
    TagEntry("wtpt", "Media white point", "58595A20000000000000F35100010000000116CC"),
    TagEntry("MSCA", "Microsoft Color Adaptation", "74657874000000007B2741707076657273696F6E273A27312E302E3135322E30272C2744363541646170746564273A547275657D00"),
    TagEntry("lumi", "Luminance", "58595A2000000000005000000050000000500000"),
    TagEntry("MHC2", "Windows Advanced Color metadata", "4D4843320000000000000002000033330050000000000024000000540000006400000074000100000000000000000000000000000000000000010000000000000000000000000000000000000001000000000000736633320000000000000000000100007366333200000000000000000001000073663332000000000000000000010000"),
    TagEntry("desc", "Profile description", "6D6C756300000000000000010000000C656E55530000002C0000001C00440065006600610075006C00740020004400650076006900630065002000500072006F00660069006C0065"),
]


class ScrollableFrame(ttk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = ttk.Frame(self.canvas)
        self.inner.bind("<Configure>", self._update_region)
        self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.bind("<Configure>", lambda e: self._toggle_scrollbar())

    def _update_region(self, _=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self._toggle_scrollbar()

    def _toggle_scrollbar(self):
        bbox = self.canvas.bbox("all")
        if not bbox:
            return
        needs_scroll = bbox[3] - bbox[1] > self.canvas.winfo_height()
        if needs_scroll:
            if not self.scrollbar.winfo_ismapped():
                self.scrollbar.pack(side="right", fill="y")
        else:
            if self.scrollbar.winfo_ismapped():
                self.scrollbar.pack_forget()

    def update_scroll(self):
        self._update_region()


class ICCBuilderApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("MHC ICC Profile Maker")
        self.header_mode = "human"
        self.workspace_mode = "hex"
        self.workspace_kind = None  # None, "mluc", "xyz"
        self.header_vars: Dict[str, tk.StringVar] = {}
        self.header_values_hex: Dict[str, str] = default_header_values_hex()
        self.header_widgets: Dict[str, tk.Widget] = {}
        self.tags: List[TagEntry] = [TagEntry(t.signature, t.description, t.data_hex) for t in DEFAULT_TAGS_SAMPLE]
        self.selected_tag: TagEntry | None = None
        self._build_menu()
        self._build_layout()
        self.refresh_tag_table()

    def _build_menu(self):
        menu = tk.Menu(self.root)
        file_menu = tk.Menu(menu, tearoff=False)
        file_menu.add_command(label="New Profile", command=self.reset_profile)
        file_menu.add_command(label="Load ICC…", command=self.load_profile)
        file_menu.add_command(label="Save ICC…", command=self.save_profile)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        menu.add_cascade(label="File", menu=file_menu)

        help_menu = tk.Menu(menu, tearoff=False)
        help_menu.add_command(label="About", command=self.show_about)
        menu.add_cascade(label="Help", menu=help_menu)
        self.root.config(menu=menu)

    def _build_layout(self):
        container = ttk.Frame(self.root)
        container.pack(fill="both", expand=True, padx=6, pady=6)

        header_frame = ttk.Labelframe(container, text="Header Fields", width=600)
        tags_frame = ttk.Labelframe(container, text="Tag Table", width=500)
        editor_frame = ttk.Labelframe(container, text="Tag Workspace", width=420)

        header_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        tags_frame.grid(row=0, column=1, sticky="nsew", padx=(0, 6))
        editor_frame.grid(row=0, column=2, sticky="nsew")

        container.columnconfigure(0, minsize=560, weight=0)
        container.columnconfigure(1, minsize=480, weight=0)
        container.columnconfigure(2, minsize=360, weight=1)
        container.rowconfigure(0, weight=1)

        self._build_header_fields(header_frame)
        self._build_tag_list(tags_frame)
        self._build_tag_editor(editor_frame)

    def _build_header_fields(self, parent: ttk.Labelframe):
        self.header_container = ttk.Frame(parent)
        self.header_container.pack(fill="both", expand=True)
        self.render_header_fields()

    def render_header_fields(self):
        for child in self.header_container.winfo_children():
            child.destroy()

        top = ttk.Frame(self.header_container)
        top.pack(fill="x", padx=4, pady=4)
        ttk.Label(top, text=f"Mode: {'Human' if self.header_mode=='human' else 'Hex'}").pack(side="left")
        ttk.Button(
            top,
            text="Show Hex" if self.header_mode == "human" else "Show Human",
            command=self.toggle_header_mode,
        ).pack(side="right")

        scroll = ScrollableFrame(self.header_container)
        scroll.pack(fill="both", expand=True)

        self.header_vars.clear()
        self.header_widgets.clear()

        row = 0
        for field in HEADER_FIELDS:
            if field.get("hidden"):
                continue

            label = ttk.Label(scroll.inner, text=field["label"])
            label.grid(row=row, column=0, sticky="w", padx=4, pady=2)
            hex_value = self.header_values_hex[field["key"]]

            # Default widget and value handling
            widget = None
            var: tk.Variable | Tuple[tk.Variable, ...]

            if field["type"] == "choice" and self.header_mode == "human":
                if hex_value == "00000000":
                    sig = "0000"
                    desc = field["choices"].get("0000", "Empty (zero)")
                else:
                    sig = hex_to_sig(hex_value)
                    desc = field["choices"].get(sig, "Unknown choice")
                display_value = f"{sig} - {desc}"
                var = tk.StringVar(value=display_value)
                values = [f"{sig} - {desc}" for sig, desc in field["choices"].items()]
                widget = ttk.Combobox(scroll.inner, textvariable=var, values=values, state="readonly", width=26)

            elif field["type"] == "size":
                display_value = str(int(hex_value, 16)) if self.header_mode == "human" else hex_value
                var = tk.StringVar(value=display_value)
                widget = ttk.Entry(scroll.inner, textvariable=var, width=32, state="disabled")

            elif field["type"] == "datetime-fixed":
                display_value = hex_to_datetime_text(hex_value) if self.header_mode == "human" else hex_value
                var = tk.StringVar(value=display_value)
                widget = ttk.Entry(scroll.inner, textvariable=var, width=40, state="disabled")

            elif field["type"] == "flags" and self.header_mode == "human":
                emb, indep = decode_flags(hex_value)
                var_emb = tk.StringVar(value=emb)
                var_indep = tk.StringVar(value=indep)
                frame = ttk.Frame(scroll.inner)
                ttk.Combobox(frame, textvariable=var_emb, values=["Embedded", "Not embedded"], state="readonly", width=14).pack(side="left", padx=(0, 6))
                ttk.Combobox(frame, textvariable=var_indep, values=["Independent", "Not independent"], state="readonly", width=16).pack(side="left")
                widget = frame
                var = (var_emb, var_indep)

            elif field["type"] == "attributes" and self.header_mode == "human":
                ref, gloss, pol, color = decode_attributes(hex_value)
                options = {
                    "ref": ["Reflective", "Transparency"],
                    "gloss": ["Glossy", "Matte"],
                    "pol": ["Positive", "Negative"],
                    "color": ["Color", "Black & white"],
                }
                vars_tuple = (
                    tk.StringVar(value=ref),
                    tk.StringVar(value=gloss),
                    tk.StringVar(value=pol),
                    tk.StringVar(value=color),
                )
                frame = ttk.Frame(scroll.inner)
                ttk.Combobox(frame, textvariable=vars_tuple[0], values=options["ref"], state="readonly", width=12).pack(side="left", padx=(0, 4))
                ttk.Combobox(frame, textvariable=vars_tuple[1], values=options["gloss"], state="readonly", width=12).pack(side="left", padx=(0, 4))
                ttk.Combobox(frame, textvariable=vars_tuple[2], values=options["pol"], state="readonly", width=12).pack(side="left", padx=(0, 4))
                ttk.Combobox(frame, textvariable=vars_tuple[3], values=options["color"], state="readonly", width=14).pack(side="left", padx=(0, 4))
                widget = frame
                var = vars_tuple

            elif field["type"] == "illuminant" and self.header_mode == "human":
                x, y, z = hex_to_xyz_components(hex_value)
                vars_tuple = (
                    tk.StringVar(value=f"{x:.6f}"),
                    tk.StringVar(value=f"{y:.6f}"),
                    tk.StringVar(value=f"{z:.6f}"),
                )
                d50_vals = hex_to_xyz_components(next(f["default_hex"] for f in HEADER_FIELDS if f["key"] == "illuminant"))
                frame = ttk.Frame(scroll.inner)
                ttk.Label(frame, text="X=").pack(side="left")
                ttk.Entry(frame, textvariable=vars_tuple[0], width=8).pack(side="left", padx=(2, 6))
                ttk.Label(frame, text="Y=").pack(side="left")
                ttk.Entry(frame, textvariable=vars_tuple[1], width=8).pack(side="left", padx=(2, 6))
                ttk.Label(frame, text="Z=").pack(side="left")
                ttk.Entry(frame, textvariable=vars_tuple[2], width=8).pack(side="left", padx=(2, 6))
                ttk.Button(
                    frame,
                    text="D50",
                    command=lambda v=vars_tuple, d=d50_vals: [v[0].set(f"{d[0]:.4f}"), v[1].set(f"{d[1]:.4f}"), v[2].set(f"{d[2]:.4f}")],
                ).pack(side="left", padx=(6, 0))
                widget = frame
                var = vars_tuple

            elif field["type"] in {"sig-fixed"}:
                display_value = hex_value if self.header_mode == "hex" else hex_to_human(field, hex_value)
                var = tk.StringVar(value=display_value)
                widget = ttk.Entry(scroll.inner, textvariable=var, width=40, state="disabled")

            elif field["type"] == "profile_id":
                display_value = hex_value if self.header_mode == "hex" else hex_to_human(field, hex_value)
                var = tk.StringVar(value=display_value)
                widget = ttk.Entry(scroll.inner, textvariable=var, width=40, state="disabled")

            elif field["type"] == "intent" and self.header_mode == "human":
                val = hex_to_human(field, hex_value)
                var = tk.StringVar(value=val)
                widget = ttk.Combobox(
                    scroll.inner,
                    textvariable=var,
                    values=list(RENDERING_INTENTS.values()),
                    state="readonly",
                    width=30,
                )

            else:
                display_value = hex_value if self.header_mode == "hex" else hex_to_human(field, hex_value)
                var = tk.StringVar(value=display_value)
                widget = ttk.Entry(scroll.inner, textvariable=var, width=32)

            widget.grid(row=row, column=1, sticky="ew", padx=4, pady=2)
            scroll.inner.columnconfigure(1, weight=1)
            self.header_vars[field["key"]] = var
            self.header_widgets[field["key"]] = widget
            row += 1

        scroll.update_scroll()

        # Footnotes
        foot = ttk.Label(
            self.header_container,
            text="Creation date/time uses your local clock when saved.\nProfile ID is computed as ICC MD5 on save.",
            foreground="gray40",
            anchor="w",
            justify="left",
            wraplength=520,
        )
        foot.pack(fill="x", padx=6, pady=4)

    def toggle_header_mode(self):
        try:
            self.header_values_hex = self.collect_header_hex()
        except ValueError as exc:
            messagebox.showerror("Invalid header field", str(exc))
            return
        self.header_mode = "hex" if self.header_mode == "human" else "human"
        self.render_header_fields()

    def _build_tag_list(self, parent: ttk.Labelframe):
        search_frame = ttk.Frame(parent)
        search_frame.pack(fill="x", padx=4, pady=4)
        ttk.Label(search_frame, text="Search tags").pack(side="left")
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        search_entry.pack(side="left", fill="x", expand=True, padx=4)
        search_entry.bind("<KeyRelease>", lambda _: self.refresh_search_results())
        ttk.Button(search_frame, text="Add Selected", command=self.add_from_search).pack(side="left", padx=2)

        self.search_list = tk.Listbox(parent, height=6)
        self.search_list.pack(fill="x", padx=4, pady=(0, 6))
        self.refresh_search_results()

        columns = ("index", "signature", "offset", "size")
        self.tag_table = ttk.Treeview(parent, columns=columns, show="headings", selectmode="browse", height=14)
        self.tag_table.heading("index", text="#")
        self.tag_table.heading("signature", text="Signature")
        self.tag_table.heading("offset", text="Offset")
        self.tag_table.heading("size", text="Size")
        self.tag_table.column("index", width=40, anchor="center")
        self.tag_table.column("signature", width=280, anchor="w")
        self.tag_table.column("offset", width=140, anchor="center")
        self.tag_table.column("size", width=140, anchor="center")
        self.tag_table.pack(fill="both", expand=True, padx=4, pady=4)
        self.tag_table.bind("<<TreeviewSelect>>", lambda _: self.on_tag_selected())

        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill="x", padx=4, pady=4)
        ttk.Button(btn_frame, text="Move Up", command=lambda: self.reorder_tag(-1)).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Move Down", command=lambda: self.reorder_tag(1)).pack(side="left", padx=2)
        self.remove_btn = ttk.Button(btn_frame, text="Remove", command=self.remove_tag)
        self.remove_btn.pack(side="left", padx=2)

    def _build_tag_editor(self, parent: ttk.Labelframe):
        top = ttk.Frame(parent)
        top.pack(fill="x", padx=4, pady=4)
        top.columnconfigure(0, weight=1)
        self.tag_title = ttk.Label(top, text="Select a tag to edit")
        self.tag_title.grid(row=0, column=0, sticky="w")
        self.mode_toggle_btn = ttk.Button(top, text="Human/Hex", command=self.toggle_workspace_mode, state="disabled")
        self.mode_toggle_btn.grid(row=0, column=1, sticky="e", padx=4)
        self.identity_btn = ttk.Button(top, text="Identity chad", command=self.apply_identity_chad, state="disabled")
        self.identity_btn.grid(row=0, column=2, sticky="e", padx=4)
        ttk.Button(top, text="Apply Changes", command=self.apply_tag_changes).grid(row=0, column=3, sticky="e", padx=4)

        self.workspace_container = ttk.Frame(parent)
        self.workspace_container.pack(fill="both", expand=True, padx=4, pady=4)

        # Hex workspace
        self.hex_frame = ttk.Frame(self.workspace_container)
        header_bar = ttk.Frame(self.hex_frame)
        header_bar.pack(fill="x", pady=(0, 2))
        ttk.Label(header_bar, text=" " * 6, font=("Courier New", 10), width=6).pack(side="left", padx=(0, 8))
        self.hex_header = ttk.Label(header_bar, text="", font=("Courier New", 10))
        self.hex_header.pack(side="left")

        body = ttk.Frame(self.hex_frame)
        body.pack(fill="both", expand=True)

        self.offset_text = tk.Text(body, width=6, height=25, wrap="none", font=("Courier New", 10))
        self.offset_text.configure(state="disabled")
        self.offset_text.pack(side="left", fill="y")

        scrollbar = ttk.Scrollbar(body, orient="vertical")
        scrollbar.pack(side="right", fill="y")

        self.hex_text = tk.Text(body, height=25, wrap="none", font=("Courier New", 10), yscrollcommand=scrollbar.set)
        self.hex_text.pack(side="left", fill="both", expand=True)
        self.hex_text.configure(state="disabled")
        scrollbar.config(command=self._sync_scroll)
        self.offset_text.config(yscrollcommand=scrollbar.set)

        # Human mluc workspace
        self.mluc_frame = ttk.Frame(self.workspace_container)
        mluc_top = ttk.Frame(self.mluc_frame)
        mluc_top.pack(fill="x", pady=(0, 6))
        self.mluc_total = ttk.Label(mluc_top, text="Records: 0")
        self.mluc_total.pack(side="left", padx=(0, 8))
        self.mluc_index_label = ttk.Label(mluc_top, text="Index: -")
        self.mluc_index_label.pack(side="left", padx=(0, 8))
        ttk.Button(mluc_top, text="Add record", command=self.add_mluc_record).pack(side="right")
        self.mluc_combo = ttk.Combobox(mluc_top, state="readonly", width=24)
        self.mluc_combo.pack(side="right", padx=(8, 8))
        self.mluc_combo.bind("<<ComboboxSelected>>", lambda e: self.on_mluc_selected())

        form = ttk.Frame(self.mluc_frame)
        form.pack(fill="x", pady=4)

        ttk.Label(form, text="Language (2 chars):").grid(row=0, column=0, sticky="w", padx=4, pady=2)
        self.mluc_lang = tk.StringVar()
        ttk.Entry(form, textvariable=self.mluc_lang, width=8).grid(row=0, column=1, sticky="w", padx=4)
        self.mluc_lang_info = ttk.Label(form, text="")
        self.mluc_lang_info.grid(row=0, column=2, sticky="w", padx=4)

        ttk.Label(form, text="Country (2 chars):").grid(row=1, column=0, sticky="w", padx=4, pady=2)
        self.mluc_country = tk.StringVar()
        ttk.Entry(form, textvariable=self.mluc_country, width=8).grid(row=1, column=1, sticky="w", padx=4)
        self.mluc_country_info = ttk.Label(form, text="")
        self.mluc_country_info.grid(row=1, column=2, sticky="w", padx=4)

        ttk.Label(form, text="Length:").grid(row=2, column=0, sticky="w", padx=4, pady=2)
        self.mluc_length_info = ttk.Label(form, text="")
        self.mluc_length_info.grid(row=2, column=1, sticky="w", padx=4)

        ttk.Label(form, text="Offset:").grid(row=3, column=0, sticky="w", padx=4, pady=2)
        self.mluc_offset_info = ttk.Label(form, text="")
        self.mluc_offset_info.grid(row=3, column=1, sticky="w", padx=4)

        ttk.Label(self.mluc_frame, text="Content (Unicode):").pack(anchor="w", padx=4, pady=(6, 2))
        self.mluc_text = tk.Text(self.mluc_frame, height=10, wrap="word")
        self.mluc_text.pack(fill="both", expand=True, padx=4, pady=(0, 4))

        # Human luminance workspace
        self.lumi_frame = ttk.Frame(self.workspace_container)
        lumi_row = ttk.Frame(self.lumi_frame)
        lumi_row.pack(fill="x", pady=6)
        ttk.Label(lumi_row, text="Luminance (cd/m²):").pack(side="left", padx=4)
        self.lumi_value = tk.StringVar()
        ttk.Entry(lumi_row, textvariable=self.lumi_value, width=16).pack(side="left", padx=4)
        self.lumi_xyz_label = ttk.Label(self.lumi_frame, text="XYZ: -")
        self.lumi_xyz_label.pack(anchor="w", padx=4, pady=(4, 2))

        # Human MSCA workspace (textType) with warning
        self.msca_frame = ttk.Frame(self.workspace_container)
        warn = ttk.Label(self.msca_frame, text="Warning: MSCA is a Microsoft private tag. Editing may break compatibility.", foreground="red")
        warn.pack(anchor="w", padx=4, pady=(4, 6))
        ttk.Label(self.msca_frame, text="Content (ASCII):").pack(anchor="w", padx=4, pady=(0, 2))
        self.msca_text = tk.Text(self.msca_frame, height=10, wrap="word")
        self.msca_text.pack(fill="both", expand=True, padx=4, pady=(0, 4))

        # Human MHC2 workspace
        self.mhc2_frame = ttk.Frame(self.workspace_container)
        mhc2_form = ttk.Frame(self.mhc2_frame)
        mhc2_form.pack(fill="x", pady=4)
        ttk.Label(mhc2_form, text="Min luminance (nits):").grid(row=0, column=0, sticky="w", padx=4, pady=2)
        ttk.Label(mhc2_form, text="Peak luminance (nits):").grid(row=1, column=0, sticky="w", padx=4, pady=2)
        ttk.Label(mhc2_form, text="Max full frame luminance (nits):").grid(row=2, column=0, sticky="w", padx=4, pady=2)

        self.mhc2_min = tk.StringVar()
        self.mhc2_peak = tk.StringVar()
        self.mhc2_max_full = tk.StringVar()
        self.mhc2_matrix_off = tk.StringVar()
        self.mhc2_lut_r = tk.StringVar()
        self.mhc2_lut_g = tk.StringVar()
        self.mhc2_lut_b = tk.StringVar()
        self.mhc2_entries = tk.StringVar()

        ttk.Entry(mhc2_form, textvariable=self.mhc2_min, width=16).grid(row=0, column=1, sticky="w", padx=4)
        ttk.Entry(mhc2_form, textvariable=self.mhc2_peak, width=16).grid(row=1, column=1, sticky="w", padx=4)
        ttk.Entry(mhc2_form, textvariable=self.mhc2_max_full, width=16, state="disabled").grid(row=2, column=1, sticky="w", padx=4)

        matrix_group = ttk.LabelFrame(self.mhc2_frame, text="Matrix (3x4 XYZ->XYZ)")
        matrix_group.pack(fill="x", padx=4, pady=(8, 4))
        offset_row = ttk.Frame(matrix_group)
        offset_row.pack(anchor="w", padx=4, pady=(4, 2))
        ttk.Label(offset_row, text="Matrix offset:").pack(side="left", padx=(0, 4))
        ttk.Entry(offset_row, textvariable=self.mhc2_matrix_off, width=16, state="disabled").pack(side="left")
        matrix_table = ttk.Frame(matrix_group)
        matrix_table.pack(padx=4, pady=(2, 6), anchor="w")
        self.mhc2_matrix_vars = []
        for r in range(3):
            row_vars = []
            for c in range(4):
                var = tk.StringVar()
                ttk.Entry(matrix_table, textvariable=var, width=10).grid(row=r, column=c, padx=2, pady=2)
                row_vars.append(var)
            self.mhc2_matrix_vars.append(row_vars)
        btns = ttk.Frame(matrix_group)
        btns.pack(fill="x", padx=4, pady=(0, 6))
        ttk.Button(btns, text="Load matrix from CSV…", command=self.load_mhc2_matrix_csv).pack(side="left", padx=(0, 6))
        ttk.Button(btns, text="Apply Identity Matrix", command=self.apply_mhc2_identity_matrix).pack(side="left")
        ttk.Button(btns, text="Four Color Matrix Calculator", command=self.show_four_color_matrix_calculator).pack(side="left", padx=(6, 0))

        lut_frame = ttk.LabelFrame(self.mhc2_frame, text="1DLUT")
        lut_frame.pack(fill="x", padx=4, pady=(4, 4))
        ttk.Label(lut_frame, text="R offset:").grid(row=0, column=0, sticky="w", padx=4, pady=2)
        ttk.Entry(lut_frame, textvariable=self.mhc2_lut_r, width=18, state="disabled").grid(row=0, column=1, padx=4)
        ttk.Label(lut_frame, text="G offset:").grid(row=1, column=0, sticky="w", padx=4, pady=2)
        ttk.Entry(lut_frame, textvariable=self.mhc2_lut_g, width=18, state="disabled").grid(row=1, column=1, padx=4)
        ttk.Label(lut_frame, text="B offset:").grid(row=2, column=0, sticky="w", padx=4, pady=2)
        ttk.Entry(lut_frame, textvariable=self.mhc2_lut_b, width=18, state="disabled").grid(row=2, column=1, padx=4)
        ttk.Label(lut_frame, text="Entries:").grid(row=3, column=0, sticky="w", padx=4, pady=2)
        ttk.Entry(lut_frame, textvariable=self.mhc2_entries, width=10, state="disabled").grid(row=3, column=1, padx=4, sticky="w")
        ttk.Button(lut_frame, text="Load RGB 3x1DLUT CSV…", command=self.load_mhc2_lut_csv).grid(row=4, column=0, columnspan=2, sticky="w", padx=4, pady=(4, 2))
        ttk.Button(lut_frame, text="Apply Identity 1DLUT", command=self.apply_mhc2_identity_lut).grid(row=5, column=0, columnspan=2, sticky="w", padx=4, pady=(2, 4))

        # Preview table (first five, ellipsis, last five rows, 3 columns)
        preview = ttk.LabelFrame(lut_frame, text="Preview (normalized)")
        preview.grid(row=0, column=2, rowspan=6, padx=(12, 4), pady=4, sticky="nsew")
        header_row = ttk.Frame(preview)
        header_row.pack(anchor="w", padx=4, pady=(4, 2))
        ttk.Label(header_row, text="", width=6).grid(row=0, column=0, padx=(0, 4))
        for i, lbl in enumerate(["R", "G", "B"], start=1):
            ttk.Label(header_row, text=lbl, width=10).grid(row=0, column=i, padx=2)
        self.mhc2_preview_idx_vars = [tk.StringVar() for _ in range(11)]
        self.mhc2_preview_vars = [[tk.StringVar() for _ in range(3)] for _ in range(11)]
        self.mhc2_preview_rows = []
        for r in range(11):
            row_frame = ttk.Frame(preview)
            row_frame.pack(anchor="w", padx=4, pady=1)
            self.mhc2_preview_rows.append(row_frame)
            ttk.Label(row_frame, textvariable=self.mhc2_preview_idx_vars[r], width=6).grid(row=0, column=0, padx=(0, 4))
            for c in range(3):
                ttk.Entry(row_frame, textvariable=self.mhc2_preview_vars[r][c], width=10, state="readonly").grid(row=0, column=c + 1, padx=2)
        self.mhc2_status = ttk.Label(self.mhc2_frame, text="", foreground="green")
        self.mhc2_status.pack_forget()

        # Human TRC workspace
        self.trc_frame = ttk.Frame(self.workspace_container)
        trc_top = ttk.Frame(self.trc_frame)
        trc_top.pack(fill="x", pady=4)
        self.trc_info = ttk.Label(trc_top, text="TRC info: -")
        self.trc_info.pack(side="left", padx=4)

        trc_mid = ttk.Frame(self.trc_frame)
        trc_mid.pack(fill="x", pady=4)
        ttk.Label(trc_mid, text="Presets:").pack(side="left", padx=4)
        self.trc_gamma_combo = ttk.Combobox(
            trc_mid,
            state="readonly",
            width=16,
            values=["Gamma=1.8", "Gamma=2.0", "Gamma=2.2", "Gamma=2.4", "Gamma=2.6", "Gamma=2.8", "sRGB"],
        )
        self.trc_gamma_combo.pack(side="left", padx=4)
        ttk.Button(trc_mid, text="Apply preset", command=self.apply_trc_gamma_preset).pack(side="left", padx=4)
        ttk.Button(trc_mid, text="Load curve from file…", command=self.load_trc_from_file).pack(side="left", padx=4)
        self.trc_status = ttk.Label(self.trc_frame, text="", foreground="green")
        self.trc_status.pack(anchor="w", padx=4, pady=(2, 0))

        # Human XYZ workspace
        self.xyz_frame = ttk.Frame(self.workspace_container)
        xyz_form = ttk.Frame(self.xyz_frame)
        xyz_form.pack(fill="x", pady=6)
        ttk.Label(xyz_form, text="X:").grid(row=0, column=0, sticky="w", padx=4, pady=2)
        ttk.Label(xyz_form, text="Y:").grid(row=1, column=0, sticky="w", padx=4, pady=2)
        ttk.Label(xyz_form, text="Z:").grid(row=2, column=0, sticky="w", padx=4, pady=2)
        self.xyz_x = tk.StringVar()
        self.xyz_y = tk.StringVar()
        self.xyz_z = tk.StringVar()
        ttk.Entry(xyz_form, textvariable=self.xyz_x, width=18).grid(row=0, column=1, sticky="w", padx=4)
        ttk.Entry(xyz_form, textvariable=self.xyz_y, width=18).grid(row=1, column=1, sticky="w", padx=4)
        ttk.Entry(xyz_form, textvariable=self.xyz_z, width=18).grid(row=2, column=1, sticky="w", padx=4)

        # xyY inputs
        ttk.Label(xyz_form, text="x:").grid(row=0, column=2, sticky="w", padx=12, pady=2)
        ttk.Label(xyz_form, text="y:").grid(row=1, column=2, sticky="w", padx=12, pady=2)
        ttk.Label(xyz_form, text="Y (luma):").grid(row=2, column=2, sticky="w", padx=12, pady=2)
        self.xy_input_x = tk.StringVar()
        self.xy_input_y = tk.StringVar()
        self.xy_input_Y = tk.StringVar()
        ttk.Entry(xyz_form, textvariable=self.xy_input_x, width=12).grid(row=0, column=3, sticky="w", padx=4)
        ttk.Entry(xyz_form, textvariable=self.xy_input_y, width=12).grid(row=1, column=3, sticky="w", padx=4)
        ttk.Entry(xyz_form, textvariable=self.xy_input_Y, width=12).grid(row=2, column=3, sticky="w", padx=4)
        ttk.Button(xyz_form, text="xyY -> XYZ", command=self.convert_xyy_to_xyz).grid(row=0, column=4, rowspan=3, padx=8)

        ttk.Label(xyz_form, text="White level:").grid(row=3, column=2, sticky="w", padx=12, pady=2)
        self.white_level = tk.StringVar(value="1.0")
        ttk.Entry(xyz_form, textvariable=self.white_level, width=12).grid(row=3, column=3, sticky="w", padx=4)

        ttk.Label(self.xyz_frame, text="Chromaticity (derived):").pack(anchor="w", padx=4, pady=(8, 2))
        xy_line = ttk.Frame(self.xyz_frame)
        xy_line.pack(fill="x", padx=4)
        ttk.Label(xy_line, text="x:").pack(side="left")
        self.xyz_x_chroma = ttk.Label(xy_line, text="-")
        self.xyz_x_chroma.pack(side="left", padx=(2, 12))
        ttk.Label(xy_line, text="y:").pack(side="left")
        self.xyz_y_chroma = ttk.Label(xy_line, text="-")
        self.xyz_y_chroma.pack(side="left", padx=(2, 12))

        quick_line = ttk.Frame(self.xyz_frame)
        quick_line.pack(fill="x", padx=4, pady=(10, 2))
        ttk.Label(quick_line, text="Quick fill:").pack(side="left")
        self.xyz_quick = ttk.Combobox(quick_line, state="readonly", width=28)
        self.xyz_quick.pack(side="left", padx=6)
        ttk.Button(quick_line, text="Apply", command=self.apply_xyz_quick_fill).pack(side="left")

        ttk.Button(parent, text="Save ICC Profile…", command=self.save_profile).pack(side="right", padx=8, pady=6)
        self.show_hex_workspace()

    def reset_profile(self):
        self.header_mode = "human"
        self.header_values_hex = default_header_values_hex()
        self.render_header_fields()
        self.tags = [TagEntry(t.signature, t.description, t.data_hex) for t in DEFAULT_TAGS_SAMPLE]
        self.refresh_tag_table()
        self.refresh_search_results()
        self.hex_text.delete("1.0", tk.END)
        self.tag_title.config(text="Select a tag to edit")

    def refresh_search_results(self):
        query = self.search_var.get().lower()
        existing = {t.signature for t in self.tags}
        self.search_list.delete(0, tk.END)
        for sig, desc in sorted(KNOWN_TAG_LIBRARY.items()):
            if sig in existing:
                continue
            if query in sig.lower() or query in desc.lower():
                self.search_list.insert(tk.END, f"{sig} - {desc}")

    def add_from_search(self):
        selection = self.search_list.get(tk.ACTIVE)
        if not selection:
            return
        sig = selection.split(" - ")[0]
        if any(t.signature == sig for t in self.tags):
            messagebox.showinfo("Tag already present", f"The tag {sig} is already in the table.")
            return
        default_data = "(Add hex for tag here)"
        if sig in KNOWN_TAG_LIBRARY:
            default_data = ""
        self.tags.append(TagEntry(sig, KNOWN_TAG_LIBRARY.get(sig, "Custom tag"), default_data))
        self.refresh_tag_table(select_signature=sig)
        self.refresh_search_results()

    def reorder_tag(self, delta: int):
        if not self.selected_tag:
            return
        idx = self.tags.index(self.selected_tag)
        new_idx = idx + delta
        if new_idx < 0 or new_idx >= len(self.tags):
            return
        self.tags[idx], self.tags[new_idx] = self.tags[new_idx], self.tags[idx]
        self.refresh_tag_table(select_signature=self.selected_tag.signature)

    def remove_tag(self):
        if not self.selected_tag:
            return
        self.tags = [t for t in self.tags if t is not self.selected_tag]
        self.selected_tag = None
        self.refresh_tag_table()
        self.refresh_search_results()
        self.hex_text.delete("1.0", tk.END)
        self.tag_title.config(text="Select a tag to edit")
        self.update_remove_state(None)
        self.show_hex_workspace()

    def on_tag_selected(self):
        selection = self.tag_table.selection()
        if not selection:
            self.update_remove_state(None)
            return
        sig = selection[0]
        tag = next((t for t in self.tags if t.signature == sig), None)
        if not tag:
            self.update_remove_state(None)
            return
        self.selected_tag = tag
        self.tag_title.config(text=f"Editing {tag.signature} ({tag.description})")
        if tag.signature in {"cprt", "desc"}:
            self.mode_toggle_btn.state(["!disabled"])
            self.workspace_kind = "mluc"
            self.workspace_mode = "human"
            self.render_mluc_workspace(tag)
            self.show_mluc_workspace()
        elif tag.signature in {"rXYZ", "gXYZ", "bXYZ", "wtpt"}:
            self.mode_toggle_btn.state(["!disabled"])
            self.workspace_kind = "xyz"
            self.workspace_mode = "human"
            self.render_xyz_workspace(tag)
            self.show_xyz_workspace()
        elif tag.signature == "lumi":
            self.mode_toggle_btn.state(["!disabled"])
            self.workspace_kind = "lumi"
            self.workspace_mode = "human"
            self.render_lumi_workspace(tag)
            self.show_lumi_workspace()
        elif tag.signature == "MSCA":
            self.mode_toggle_btn.state(["!disabled"])
            self.workspace_kind = "msca"
            self.workspace_mode = "human"
            self.render_msca_workspace(tag)
            self.show_msca_workspace()
        elif tag.signature == "MHC2":
            self.mode_toggle_btn.state(["!disabled"])
            self.workspace_kind = "mhc2"
            self.workspace_mode = "human"
            self.render_mhc2_workspace(tag)
            self.show_mhc2_workspace()
        elif tag.signature in {"rTRC", "gTRC", "bTRC"}:
            self.mode_toggle_btn.state(["!disabled"])
            self.workspace_kind = "trc"
            self.workspace_mode = "human"
            self.render_trc_workspace(tag)
            self.show_trc_workspace()
        else:
            self.mode_toggle_btn.state(["disabled"])
            self.workspace_kind = None
            self.workspace_mode = "hex"
            self.render_hex_view(tag.data_bytes())
            self.show_hex_workspace()
        self.identity_btn.state(["!disabled"] if tag.signature == "chad" else ["disabled"])
        if tag.signature == "chad":
            if not self.identity_btn.winfo_ismapped():
                self.identity_btn.grid()
        else:
            self.identity_btn.grid_remove()
        self.update_remove_state(tag.signature)

    def apply_tag_changes(self):
        if not self.selected_tag:
            messagebox.showinfo("No tag selected", "Choose a tag from the table first.")
            return
        if self.selected_tag.signature in {"cprt", "desc"} and self.workspace_kind == "mluc" and self.workspace_mode == "human":
            try:
                self.update_mluc_record_from_ui()
                new_bytes = self.build_mluc_bytes(self.mluc_records)
            except Exception as exc:
                messagebox.showerror("Invalid data", str(exc))
                return
            self.selected_tag.data_hex = new_bytes.hex().upper()
            self.render_mluc_workspace(self.selected_tag, refresh_only=True)
        elif self.selected_tag.signature in {"rXYZ", "gXYZ", "bXYZ", "wtpt"} and self.workspace_kind == "xyz" and self.workspace_mode == "human":
            try:
                x = float(self.xyz_x.get())
                y = float(self.xyz_y.get())
                z = float(self.xyz_z.get())
            except Exception:
                messagebox.showerror("Invalid XYZ", "X, Y, Z must be decimal numbers.")
                return
            new_bytes = self.build_xyz_bytes(x, y, z)
            self.selected_tag.data_hex = new_bytes.hex().upper()
            self.render_xyz_workspace(self.selected_tag)
        elif self.selected_tag.signature == "lumi" and self.workspace_kind == "lumi" and self.workspace_mode == "human":
            try:
                val = float(self.lumi_value.get())
            except Exception:
                messagebox.showerror("Invalid luminance", "Luminance must be numeric.")
                return
            new_bytes = self.build_xyz_bytes(val, val, val)
            self.selected_tag.data_hex = new_bytes.hex().upper()
            self.render_lumi_workspace(self.selected_tag)
        elif self.selected_tag.signature == "MSCA" and self.workspace_kind == "msca" and self.workspace_mode == "human":
            content = self.msca_text.get("1.0", tk.END).rstrip("\n")
            new_bytes = self.build_text_type(content)
            self.selected_tag.data_hex = new_bytes.hex().upper()
            self.render_msca_workspace(self.selected_tag)
        elif self.selected_tag.signature == "MSCA" and self.workspace_kind == "msca" and self.workspace_mode == "human":
            content = self.msca_text.get("1.0", tk.END).rstrip("\n")
            new_bytes = self.build_text_type(content)
            self.selected_tag.data_hex = new_bytes.hex().upper()
            self.render_msca_workspace(self.selected_tag)
        elif self.selected_tag.signature == "MHC2" and self.workspace_kind == "mhc2" and self.workspace_mode == "human":
            try:
                min_nits = float(self.mhc2_min.get())
                peak_nits = float(self.mhc2_peak.get())
                entries = int(self.mhc2_entries.get())
            except Exception:
                messagebox.showerror("Invalid MHC2", "Please enter valid numeric values.")
                return
            self.rebuild_mhc2_from_ui(min_nits, peak_nits, entries, status_msg="Updated MHC2.")
        elif self.selected_tag.signature in {"rTRC", "gTRC", "bTRC"} and self.workspace_kind == "trc" and self.workspace_mode == "human":
            new_bytes = self.build_trc_bytes(self.trc_values)
            new_hex = new_bytes.hex().upper()
            self.update_shared_trc_curves(new_hex)
            self.render_trc_workspace(self.selected_tag)
        else:
            content = self.hex_text.get("1.0", tk.END)
            try:
                new_bytes = self.parse_hex_view(content)
            except Exception as exc:
                messagebox.showerror("Invalid hex", str(exc))
                return
            self.selected_tag.data_hex = new_bytes.hex().upper()
        self.refresh_tag_table(select_signature=self.selected_tag.signature)

    def render_hex_view(self, data: bytes):
        header_groups = [" ".join([f"{x:02X}" for x in range(g, g + 4)]) for g in range(0x0, 0x10, 4)]
        header = "  ".join(header_groups)
        self.hex_header.config(text=header)

        offset_lines = []
        hex_lines = []
        for i in range(0, len(data), 16):
            chunk = data[i : i + 16]
            hex_pairs = [f"{b:02X}" for b in chunk]
            grouped = []
            for g in range(0, len(hex_pairs), 4):
                grouped.append(" ".join(hex_pairs[g : g + 4]))
            hex_str = "  ".join(grouped)
            offset_lines.append(f"{i:04X}")
            hex_lines.append(hex_str)

        offset_display = "\n".join(offset_lines)
        hex_display = "\n".join(hex_lines)

        self.offset_text.configure(state="normal")
        self.offset_text.delete("1.0", tk.END)
        self.offset_text.insert(tk.END, offset_display)
        self.offset_text.configure(state="disabled")

        self.hex_text.configure(state="normal")
        self.hex_text.delete("1.0", tk.END)
        self.hex_text.insert(tk.END, hex_display)
        self.hex_text.configure(state="normal")

    def parse_hex_view(self, content: str) -> bytes:
        data_bytes = bytearray()
        for line in content.strip().splitlines():
            hex_parts = line.strip().split()
            for part in hex_parts:
                if len(part) != 2:
                    continue
                data_bytes.append(int(part, 16))
        return bytes(data_bytes)

    def _sync_scroll(self, *args):
        self.hex_text.yview(*args)
        self.offset_text.yview(*args)
        # Update scrollbar positions on both widgets
        if args and args[0] == "moveto":
            pos = args[1]
            self.offset_text.yview_moveto(pos)
            self.hex_text.yview_moveto(pos)

    def show_hex_workspace(self):
        self.mluc_frame.pack_forget()
        self.xyz_frame.pack_forget()
        self.lumi_frame.pack_forget()
        self.msca_frame.pack_forget()
        self.mhc2_frame.pack_forget()
        self.trc_frame.pack_forget()
        self.hex_frame.pack(fill="both", expand=True)
        self.workspace_mode = "hex"
        if self.workspace_kind in {"mluc", "xyz"}:
            self.mode_toggle_btn.config(text="Switch to Human")
        else:
            self.mode_toggle_btn.config(text="Human/Hex")

    def show_mluc_workspace(self):
        self.hex_frame.pack_forget()
        self.xyz_frame.pack_forget()
        self.lumi_frame.pack_forget()
        self.msca_frame.pack_forget()
        self.mhc2_frame.pack_forget()
        self.trc_frame.pack_forget()
        self.mluc_frame.pack(fill="both", expand=True)
        self.workspace_mode = "human"
        self.workspace_kind = "mluc"
        self.mode_toggle_btn.config(text="Switch to Hex")

    def show_xyz_workspace(self):
        self.hex_frame.pack_forget()
        self.mluc_frame.pack_forget()
        self.lumi_frame.pack_forget()
        self.msca_frame.pack_forget()
        self.mhc2_frame.pack_forget()
        self.trc_frame.pack_forget()
        self.xyz_frame.pack(fill="both", expand=True)
        self.workspace_mode = "human"
        self.workspace_kind = "xyz"
        self.mode_toggle_btn.config(text="Switch to Hex")

    def show_lumi_workspace(self):
        self.hex_frame.pack_forget()
        self.mluc_frame.pack_forget()
        self.xyz_frame.pack_forget()
        self.msca_frame.pack_forget()
        self.mhc2_frame.pack_forget()
        self.trc_frame.pack_forget()
        self.lumi_frame.pack(fill="both", expand=True)
        self.workspace_mode = "human"
        self.workspace_kind = "lumi"
        self.mode_toggle_btn.config(text="Switch to Hex")

    def show_msca_workspace(self):
        self.hex_frame.pack_forget()
        self.mluc_frame.pack_forget()
        self.xyz_frame.pack_forget()
        self.lumi_frame.pack_forget()
        self.mhc2_frame.pack_forget()
        self.msca_frame.pack(fill="both", expand=True)
        self.workspace_mode = "human"
        self.workspace_kind = "msca"
        self.mode_toggle_btn.config(text="Switch to Hex")

    def show_trc_workspace(self):
        self.hex_frame.pack_forget()
        self.mluc_frame.pack_forget()
        self.xyz_frame.pack_forget()
        self.lumi_frame.pack_forget()
        self.msca_frame.pack_forget()
        self.mhc2_frame.pack_forget()
        self.trc_frame.pack(fill="both", expand=True)
        self.workspace_mode = "human"
        self.workspace_kind = "trc"
        self.mode_toggle_btn.config(text="Switch to Hex")

    def show_mhc2_workspace(self):
        self.hex_frame.pack_forget()
        self.mluc_frame.pack_forget()
        self.xyz_frame.pack_forget()
        self.lumi_frame.pack_forget()
        self.msca_frame.pack_forget()
        self.trc_frame.pack_forget()
        self.mhc2_frame.pack(fill="both", expand=True)
        self.workspace_mode = "human"
        self.workspace_kind = "mhc2"
        self.mode_toggle_btn.config(text="Switch to Hex")

    def toggle_workspace_mode(self):
        if not self.selected_tag or self.workspace_kind not in {"mluc", "xyz", "lumi", "msca", "trc", "mhc2"}:
            return
        if self.workspace_mode == "human":
            self.show_hex_workspace()
            self.render_hex_view(self.selected_tag.data_bytes())
        else:
            if self.workspace_kind == "mluc":
                self.show_mluc_workspace()
                self.render_mluc_workspace(self.selected_tag)
            elif self.workspace_kind == "xyz":
                self.show_xyz_workspace()
                self.render_xyz_workspace(self.selected_tag)
            elif self.workspace_kind == "lumi":
                self.show_lumi_workspace()
                self.render_lumi_workspace(self.selected_tag)
            elif self.workspace_kind == "msca":
                self.show_msca_workspace()
                self.render_msca_workspace(self.selected_tag)
            elif self.workspace_kind == "mhc2":
                self.show_mhc2_workspace()
                self.render_mhc2_workspace(self.selected_tag)
            elif self.workspace_kind == "trc":
                self.show_trc_workspace()
                self.render_trc_workspace(self.selected_tag)

    def apply_identity_chad(self):
        if not self.selected_tag or self.selected_tag.signature != "chad":
            return
        self.selected_tag.data_hex = chad_identity_bytes().hex().upper()
        self.render_hex_view(self.selected_tag.data_bytes())
        self.refresh_tag_table(select_signature="chad")

    def render_mluc_workspace(self, tag: TagEntry, refresh_only: bool = False):
        try:
            records = self.parse_mluc(tag.data_bytes())
        except Exception as exc:
            messagebox.showerror("Invalid mluc", f"Failed to parse multiLocalizedUnicodeType:\n{exc}")
            self.show_hex_workspace()
            self.render_hex_view(tag.data_bytes())
            return
        self.mluc_records = records
        if refresh_only:
            layout = self.compute_mluc_layout(self.mluc_records)
        else:
            layout = None
        self.mluc_combo["values"] = [f"Record {i+1}: {r['lang']}-{r['country']}" for i, r in enumerate(self.mluc_records)]
        if self.mluc_records:
            self.mluc_combo.current(0)
            self.load_mluc_record(0, layout)
        else:
            self.mluc_combo.set("")
            self.mluc_total.config(text="Records: 0")
            self.mluc_index_label.config(text="Index: -")
            self.mluc_lang.set("")
            self.mluc_country.set("")
            self.mluc_length_info.config(text="")
            self.mluc_offset_info.config(text="")
            self.mluc_text.delete("1.0", tk.END)

    def load_mluc_record(self, idx: int, layout=None):
        if idx < 0 or idx >= len(self.mluc_records):
            return
        rec = self.mluc_records[idx]
        if layout is None:
            layout = self.compute_mluc_layout(self.mluc_records)
        meta = layout[idx]
        self.mluc_total.config(text=f"Records: {len(self.mluc_records)}")
        self.mluc_index_label.config(text=f"Index: {idx+1}")
        self.mluc_lang.set(rec["lang"])
        self.mluc_country.set(rec["country"])
        self.mluc_lang_info.config(text=f"{rec['lang'].encode().hex().upper()}")
        self.mluc_country_info.config(text=f"{rec['country'].encode().hex().upper()}")
        self.mluc_length_info.config(text=f"{meta['length']} (0x{meta['length']:X})")
        self.mluc_offset_info.config(text=f"{meta['offset']} (0x{meta['offset']:X})")
        self.mluc_text.delete("1.0", tk.END)
        self.mluc_text.insert(tk.END, rec["text"])

    def on_mluc_selected(self):
        if not hasattr(self, "mluc_records"):
            return
        sel = self.mluc_combo.current()
        if sel < 0:
            return
        layout = self.compute_mluc_layout(self.mluc_records)
        self.load_mluc_record(sel, layout)

    def add_mluc_record(self):
        if not hasattr(self, "mluc_records"):
            self.mluc_records = []
        self.mluc_records.append({"lang": "en", "country": "US", "text": ""})
        self.mluc_combo["values"] = [f"Record {i+1}: {r['lang']}-{r['country']}" for i, r in enumerate(self.mluc_records)]
        self.mluc_combo.current(len(self.mluc_records) - 1)
        layout = self.compute_mluc_layout(self.mluc_records)
        self.load_mluc_record(len(self.mluc_records) - 1, layout)

    def update_mluc_record_from_ui(self):
        sel = self.mluc_combo.current()
        if sel < 0 or sel >= len(self.mluc_records):
            raise ValueError("No record selected.")
        lang = self.mluc_lang.get().strip()
        country = self.mluc_country.get().strip()
        if len(lang) != 2 or len(country) != 2:
            raise ValueError("Language and country codes must be 2 characters.")
        self.mluc_records[sel]["lang"] = lang
        self.mluc_records[sel]["country"] = country
        self.mluc_records[sel]["text"] = self.mluc_text.get("1.0", tk.END).rstrip("\n")
        self.mluc_combo["values"] = [f"Record {i+1}: {r['lang']}-{r['country']}" for i, r in enumerate(self.mluc_records)]

    def render_xyz_workspace(self, tag: TagEntry):
        try:
            x, y, z = self.parse_xyz(tag.data_bytes())
        except Exception as exc:
            messagebox.showerror("Invalid XYZ", f"Failed to parse XYZ tag:\n{exc}")
            self.show_hex_workspace()
            self.render_hex_view(tag.data_bytes())
            return
        self.xyz_x.set(f"{x:.6f}")
        self.xyz_y.set(f"{y:.6f}")
        self.xyz_z.set(f"{z:.6f}")
        self.update_chromaticity_labels(x, y, z)
        self.populate_xy_inputs_from_xyz(x, y, z)
        self.load_xyz_quick_options(tag.signature)

    def render_lumi_workspace(self, tag: TagEntry):
        try:
            x, y, z = self.parse_xyz(tag.data_bytes())
        except Exception as exc:
            messagebox.showerror("Invalid luminance", f"Failed to parse luminance tag:\n{exc}")
            self.show_hex_workspace()
            self.render_hex_view(tag.data_bytes())
            return
        self.lumi_value.set(f"{y:.6f}")
        self.lumi_xyz_label.config(text=f"XYZ = {x:.6f}, {y:.6f}, {z:.6f}")

    def render_msca_workspace(self, tag: TagEntry):
        try:
            text = self.parse_text_type(tag.data_bytes())
        except Exception as exc:
            messagebox.showerror("Invalid MSCA", f"Failed to parse MSCA textType:\n{exc}")
            self.show_hex_workspace()
            self.render_hex_view(tag.data_bytes())
            return
        self.msca_text.delete("1.0", tk.END)
        self.msca_text.insert(tk.END, text)

    def render_mhc2_workspace(self, tag: TagEntry, status: str | None = None, popup: bool = True):
        try:
            parsed = self.parse_mhc2(tag.data_bytes())
        except Exception as exc:
            messagebox.showerror("Invalid MHC2", f"Failed to parse MHC2 tag:\n{exc}")
            self.show_hex_workspace()
            self.render_hex_view(tag.data_bytes())
            return
        self.mhc2_min.set(f"{parsed['min_nits']:.4f}")
        self.mhc2_peak.set(f"{parsed['peak_nits']:.4f}")
        self.mhc2_matrix_off.set(f"{parsed['matrix_off']} (0x{parsed['matrix_off']:X})")
        self.mhc2_lut_r.set(f"{parsed['lut_r_off']} (0x{parsed['lut_r_off']:X})")
        self.mhc2_lut_g.set(f"{parsed['lut_g_off']} (0x{parsed['lut_g_off']:X})")
        self.mhc2_lut_b.set(f"{parsed['lut_b_off']} (0x{parsed['lut_b_off']:X})")
        self.mhc2_entries.set(str(parsed["lut_entries"]))
        self.mhc2_max_full.set(parsed["max_full_lumi"])
        # populate matrix fields
        matrix_vals = parsed.get("matrix") or identity_matrix12()
        for idx, val in enumerate(matrix_vals):
            r, c = divmod(idx, 4)
            self.mhc2_matrix_vars[r][c].set(f"{val:.6f}")
        self.mhc2_lut_values = parsed.get("lut_values", None)
        self.update_mhc2_lut_preview(parsed.get("lut_values"), parsed.get("lut_entries", 0))
        if popup and status is not None and status:
            messagebox.showinfo("MHC2", status)

    def render_trc_workspace(self, tag: TagEntry):
        try:
            info = self.parse_trc(tag.data_bytes())
        except Exception as exc:
            messagebox.showerror("Invalid TRC", f"Failed to parse TRC:\n{exc}")
            self.show_hex_workspace()
            self.render_hex_view(tag.data_bytes())
            return
        self.trc_values = info["values"]
        self.trc_source_hex = tag.data_hex
        if info["gamma"] is not None:
            self.trc_gamma_combo.set("")  # show only user selection
            self.trc_info.config(text=f"TRC: entry count=1 (Gamma={info['gamma']:.1f})")
        else:
            self.trc_info.config(text=f"TRC: curve (count={len(self.trc_values)})")
        self.trc_status.config(text="")


    def update_chromaticity_labels(self, x: float, y: float, z: float):
        total = x + y + z
        if total <= 0:
            x_chroma = y_chroma = 0.0
        else:
            x_chroma = x / total
        y_chroma = y / total
        self.xyz_x_chroma.config(text=f"{x_chroma:.6f}")
        self.xyz_y_chroma.config(text=f"{y_chroma:.6f}")

    def update_shared_trc_curves(self, new_hex: str):
        original = getattr(self, "trc_source_hex", None) or (self.selected_tag.data_hex if self.selected_tag else None)
        for tag in self.tags:
            if tag.signature in {"rTRC", "gTRC", "bTRC"}:
                if original is None or tag.data_hex == original:
                    tag.data_hex = new_hex
        if self.selected_tag:
            self.trc_source_hex = new_hex

    def parse_xyz(self, data: bytes):
        if len(data) < 20 or data[:4] != b"XYZ ":
            raise ValueError("Not an XYZ type tag")
        sig, x_raw, y_raw, z_raw = struct.unpack(">4s4xiii", data[:20])
        return (from_s15fixed16(x_raw), from_s15fixed16(y_raw), from_s15fixed16(z_raw))

    def build_xyz_bytes(self, x: float, y: float, z: float) -> bytes:
        return struct.pack(">4s4xiii", b"XYZ ", to_s15fixed16(x), to_s15fixed16(y), to_s15fixed16(z))

    def parse_text_type(self, data: bytes) -> str:
        if len(data) < 8 or data[:4] != b"text":
            raise ValueError("Not a textType")
        return data[8:].rstrip(b"\x00").decode("ascii", errors="replace")

    def build_text_type(self, content: str) -> bytes:
        payload = content.encode("ascii", errors="replace")
        blob = b"text" + b"\x00" * 4 + payload
        while len(blob) % 4:
            blob += b"\x00"
        return blob

    def parse_mhc2(self, data: bytes):
        if len(data) < 36 or data[:4] != b"MHC2":
            raise ValueError("Not an MHC2 tag")
        sig, reserved = struct.unpack_from(">4sI", data, 0)
        count = struct.unpack_from(">I", data, 8)[0]
        min_raw = struct.unpack_from(">i", data, 12)[0]
        peak_raw = struct.unpack_from(">i", data, 16)[0]
        matrix_off = struct.unpack_from(">I", data, 20)[0]
        lut_r = struct.unpack_from(">I", data, 24)[0]
        lut_g = struct.unpack_from(">I", data, 28)[0]
        lut_b = struct.unpack_from(">I", data, 32)[0]
        min_nits = from_s15fixed16(min_raw)
        peak_nits = from_s15fixed16(peak_raw)

        matrix_vals = None
        # Matrix is 12 s15Fixed16 numbers (3x4) without a type signature
        if matrix_off and matrix_off + 48 <= len(data):
            m_data = data[matrix_off : matrix_off + 48]
            vals = struct.unpack(">" + "i" * 12, m_data)
            matrix_vals = [from_s15fixed16(v) for v in vals]

        lut_values = None
        if count > 0:
            lut_values = []
            for off in (lut_r, lut_g, lut_b):
                if off and off + 8 + count * 4 <= len(data) and data[off : off + 4] == b"sf32":
                    raw = data[off + 8 : off + 8 + count * 4]
                    vals = struct.unpack(">" + "i" * count, raw)
                    lut_values.append([from_s15fixed16(v) for v in vals])
                else:
                    lut_values.append([])

        # derive max full frame from lumi tag
        max_full = "-"
        lumi_tag = next((t for t in self.tags if t.signature == "lumi"), None)
        if lumi_tag:
            try:
                _, y, _ = self.parse_xyz(lumi_tag.data_bytes())
                max_full = f"{y:.6f}"
            except Exception:
                max_full = "N/A"
        return {
            "count": count,
            "min_nits": min_nits,
            "peak_nits": peak_nits,
            "matrix_off": matrix_off,
            "lut_r_off": lut_r,
            "lut_g_off": lut_g,
            "lut_b_off": lut_b,
            "lut_entries": count,
            "max_full_lumi": max_full,
            "matrix": matrix_vals,
            "lut_values": lut_values,
            "raw": data,
        }

    def build_mhc2_bytes(self, min_nits: float, peak_nits: float, lut_entries: int) -> bytes:
        count = max(0, lut_entries)

        # Build matrix block (12 s15Fixed16 values, no signature)
        matrix_vals = []
        for r in range(3):
            for c in range(4):
                try:
                    v = float(self.mhc2_matrix_vars[r][c].get())
                except Exception:
                    v = 0.0
                matrix_vals.append(to_s15fixed16(v))
        matrix_block = struct.pack(">" + "i" * 12, *matrix_vals)

        # Build LUT blocks
        lut_blocks = []
        if count > 0:
            lut_lists = self.mhc2_lut_values if getattr(self, "mhc2_lut_values", None) else None
            if not lut_lists or len(lut_lists) != 3 or any(len(ch) != count for ch in lut_lists):
                # identity default
                lut_lists = [[i / (count - 1 if count > 1 else 1) for i in range(count)] for _ in range(3)]
            for ch_vals in lut_lists:
                ints = [to_s15fixed16(v) for v in ch_vals]
                lut_blocks.append(b"sf32" + b"\x00" * 4 + struct.pack(">" + "i" * count, *ints))

        # Compute offsets (all relative to start of MHC2 structure)
        matrix_off_new = 36
        lut_r_off_new = matrix_off_new + len(matrix_block) if count > 0 else 0
        lut_g_off_new = lut_r_off_new + (len(lut_blocks[0]) if count > 0 else 0) if count > 0 else 0
        lut_b_off_new = lut_g_off_new + (len(lut_blocks[1]) if count > 0 else 0) if count > 0 else 0

        header = struct.pack(
            ">4sI I i i I I I I",
            b"MHC2",
            0,
            count,
            to_s15fixed16(min_nits),
            to_s15fixed16(peak_nits),
            matrix_off_new,
            lut_r_off_new,
            lut_g_off_new,
            lut_b_off_new,
        )

        body = bytearray()
        body.extend(matrix_block)
        for block in lut_blocks:
            body.extend(block)
        return header + body

    def update_mhc2_lut_preview(self, lut_values, count: int):
        # rows: first five, ellipsis, last five
        for r in range(11):
            for c in range(3):
                self.mhc2_preview_vars[r][c].set("")
            self.mhc2_preview_idx_vars[r].set("")
        if not lut_values or count <= 0:
            return
        if count <= 5:
            rows_to_fill = count
            for r in range(rows_to_fill):
                self.mhc2_preview_idx_vars[r].set(f"{r}")
                for c in range(3):
                    try:
                        val = lut_values[c][r]
                        self.mhc2_preview_vars[r][c].set(f"{val:.6f}")
                    except Exception:
                        self.mhc2_preview_vars[r][c].set("")
            return

        # first five
        for r in range(5):
            self.mhc2_preview_idx_vars[r].set(f"{r}")
            for c in range(3):
                try:
                    val = lut_values[c][r]
                    self.mhc2_preview_vars[r][c].set(f"{val:.6f}")
                except Exception:
                    self.mhc2_preview_vars[r][c].set("")
        # ellipsis row
        self.mhc2_preview_idx_vars[5].set("...")
        for c in range(3):
            self.mhc2_preview_vars[5][c].set("...")

        # last five
        start_last = max(count - 5, 0)
        rows_idx = 6
        for idx in range(start_last, start_last + 5):
            if idx >= count:
                break
            self.mhc2_preview_idx_vars[rows_idx].set(f"{idx}")
            for c in range(3):
                try:
                    val = lut_values[c][idx]
                    self.mhc2_preview_vars[rows_idx][c].set(f"{val:.6f}")
                except Exception:
                    self.mhc2_preview_vars[rows_idx][c].set("")
            rows_idx += 1

    def rebuild_mhc2_from_ui(self, min_nits: float, peak_nits: float, entries: int, status_msg: str = "Updated MHC2.", popup: bool = True):
        if not self.selected_tag or self.selected_tag.signature != "MHC2":
            return
        try:
            new_bytes = self.build_mhc2_bytes(min_nits, peak_nits, entries)
        except Exception as exc:
            messagebox.showerror("Invalid MHC2", f"Failed to rebuild MHC2:\n{exc}")
            return
        self.selected_tag.data_hex = new_bytes.hex().upper()
        # Refresh UI and offsets with the rebuilt data
        self.render_mhc2_workspace(self.selected_tag, status=status_msg, popup=popup)
        self.refresh_tag_table(select_signature="MHC2")
        if self.workspace_mode == "hex":
            self.render_hex_view(self.selected_tag.data_bytes())

    def parse_trc(self, data: bytes):
        if len(data) < 12 or data[:4] != b"curv":
            raise ValueError("Not a curveType")
        count = struct.unpack(">I", data[8:12])[0]
        if count == 0:
            raise ValueError("TRC count cannot be zero")
        values = []
        offset = 12
        for _ in range(count):
            if offset + 2 > len(data):
                raise ValueError("TRC data truncated")
            val = struct.unpack(">H", data[offset : offset + 2])[0]
            values.append(val)
            offset += 2
        gamma = values[0] / 256.0 if count == 1 else None
        return {"values": values, "gamma": gamma}

    def build_trc_bytes(self, values: List[int]) -> bytes:
        count = len(values)
        # Special case: gamma encoded as u8Fixed8 with count=1, followed by two zero bytes to align to 4-byte count field
        if count == 1:
            gamma_fixed = max(0, min(65535, int(values[0])))
            return struct.pack(">4s4xI", b"curv", 1) + struct.pack(">H", gamma_fixed) + b"\x00\x00"
        blob = struct.pack(">4s4xI", b"curv", count)
        for v in values:
            blob += struct.pack(">H", max(0, min(65535, int(v))))
        return blob

    def load_mhc2_matrix_csv(self):
        path = filedialog.askopenfilename(
            title="Load MHC2 matrix CSV",
            filetypes=[("CSV files", "*.csv"), ("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            import csv
            with open(path, "r", encoding="utf-8-sig") as f:
                rows = list(csv.reader(f))
            flat = []
            for row in rows:
                for cell in row:
                    cell = cell.strip()
                    if cell:
                        flat.append(float(cell))
            if len(flat) < 12:
                raise ValueError("Need 12 numeric values for 3x4 matrix.")
            flat = flat[:12]
            idx = 0
            for r in range(3):
                for c in range(4):
                    self.mhc2_matrix_vars[r][c].set(f"{flat[idx]:.6f}")
                    idx += 1
            # rebuild tag to reflect new matrix
            try:
                min_nits = float(self.mhc2_min.get() or 0)
                peak_nits = float(self.mhc2_peak.get() or 0)
                entries = int(self.mhc2_entries.get() or 0)
            except Exception:
                min_nits = peak_nits = 0.0
                entries = 0
            self.rebuild_mhc2_from_ui(min_nits, peak_nits, entries, status_msg="Matrix updated successfully.")
        except Exception as exc:
            messagebox.showerror("Load failed", f"Could not load matrix:\n{exc}")

    def apply_mhc2_identity_matrix(self):
        vals = identity_matrix12()
        idx = 0
        for r in range(3):
            for c in range(4):
                self.mhc2_matrix_vars[r][c].set(f"{vals[idx]:.6f}")
                idx += 1
        self.rebuild_mhc2_from_ui(
            float(self.mhc2_min.get() or 0),
            float(self.mhc2_peak.get() or 0),
            int(self.mhc2_entries.get() or 0),
            status_msg="Matrix updated successfully.",
        )

    def load_mhc2_lut_csv(self):
        path = filedialog.askopenfilename(
            title="Load RGB LUT CSV",
            filetypes=[("CSV files", "*.csv"), ("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            import csv

            rows = []
            with open(path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                for row in reader:
                    if not row:
                        continue
                    rows.append(row)
            values_r, values_g, values_b = [], [], []
            for row in rows:
                if len(row) < 3:
                    continue
                values_r.append(float(row[0]))
                values_g.append(float(row[1]))
                values_b.append(float(row[2]))
            n = len(values_r)
            if n == 0 or n > 4096:
                raise ValueError("Entry count must be between 1 and 4096.")
            max_val = max(max(values_r), max(values_g), max(values_b))
            if max_val <= 1.0:
                norm = 1.0
            elif max_val <= 255:
                norm = 255.0
            elif max_val <= 1023:
                norm = 1023.0
            elif max_val <= 4095:
                norm = 4095.0
            else:
                norm = 65535.0
            lut = []
            for channel in (values_r, values_g, values_b):
                normed = [v / norm for v in channel]
                lut.append(normed)
            self.mhc2_lut_values = lut
            self.mhc2_entries.set(str(n))
            # rebuild tag with new LUT and current header/min/peak/matrix fields
            try:
                min_nits = float(self.mhc2_min.get())
                peak_nits = float(self.mhc2_peak.get())
                entries = n
            except Exception:
                min_nits = 0.0
                peak_nits = 0.0
                entries = n
            self.rebuild_mhc2_from_ui(min_nits, peak_nits, entries, status_msg="1DLUT updated successfully.")
        except Exception as exc:
            messagebox.showerror("Load failed", f"Could not load LUT:\n{exc}")

    def apply_mhc2_identity_lut(self):
        # Identity transform with two entries [0.0, 1.0] per channel
        identity = [[0.0, 1.0], [0.0, 1.0], [0.0, 1.0]]
        self.mhc2_lut_values = identity
        self.mhc2_entries.set("2")
        self.rebuild_mhc2_from_ui(
            float(self.mhc2_min.get() or 0),
            float(self.mhc2_peak.get() or 0),
            2,
            status_msg="1DLUT updated successfully.",
        )

    def show_four_color_matrix_calculator(self):
        win = tk.Toplevel(self.root)
        win.title("Four Color Matrix Calculator")
        win.minsize(620, 360)
        mode_state = {"mode": "XYZ"}  # XYZ or xyY
        win.transient(self.root)
        win.lift()
        win.attributes("-topmost", True)

        def restore_topmost():
            try:
                win.attributes("-topmost", True)
                win.lift()
            except Exception:
                pass

        def disable_topmost_on_main_focus(_event=None):
            try:
                win.attributes("-topmost", False)
            except Exception:
                pass

        self.root.bind("<FocusIn>", disable_topmost_on_main_focus, add="+")
        win.bind("<FocusIn>", lambda e: restore_topmost())

        def build_table(parent, title, with_loader=False, with_quick=False):
            lf = ttk.LabelFrame(parent, text=title)
            lf.pack(side="left", expand=True, fill="both", padx=6, pady=6)
            header_labels = []
            # headers
            ttk.Label(lf, text="", width=6).grid(row=0, column=0, padx=(4, 4), pady=4)
            for i, col in enumerate(["X", "Y", "Z"], start=1):
                lbl = ttk.Label(lf, text=col, width=10)
                lbl.grid(row=0, column=i, padx=4, pady=4)
                header_labels.append(lbl)
            rows = []
            for r, row_name in enumerate(["W", "R", "G", "B"], start=1):
                ttk.Label(lf, text=row_name, width=6).grid(row=r, column=0, padx=(4, 4), pady=2, sticky="e")
                row_entries = []
                for c in range(1, 4):
                    var = tk.StringVar(value="0")
                    ttk.Entry(lf, textvariable=var, width=12).grid(row=r, column=c, padx=4, pady=2)
                    row_entries.append(var)
                rows.append(row_entries)
            ctrl_row = 6
            load_btn = None
            quick_combo = None
            quick_btn = None
            if with_loader:
                load_btn = ttk.Button(lf, text="Load CSV…")
                load_btn.grid(row=ctrl_row, column=0, columnspan=2, sticky="w", padx=4, pady=(8, 2))
            if with_quick:
                quick_combo = ttk.Combobox(lf, state="readonly", width=20, values=["sRGB", "BT.709", "Adobe RGB", "Display P3", "DCI-P3", "BT.2020"])
                quick_combo.grid(row=ctrl_row, column=2, sticky="w", padx=4, pady=(8, 2))
                quick_btn = ttk.Button(lf, text="Quick fill", state="normal")
                quick_btn.grid(row=ctrl_row, column=3, sticky="w", padx=4, pady=(8, 2))
            return {"frame": lf, "headers": header_labels, "rows": rows, "load_btn": load_btn, "quick_combo": quick_combo, "quick_btn": quick_btn}

        def set_header_mode(table_info, mode):
            labels = {"XYZ": ["X", "Y", "Z"], "xyY": ["x", "y", "Y"]}
            for lbl, text in zip(table_info["headers"], labels[mode]):
                lbl.config(text=text)

        def parse_table(rows):
            arr = []
            for r in rows:
                vals = []
                for var in r:
                    try:
                        vals.append(float(var.get()))
                    except Exception:
                        vals.append(0.0)
                arr.append(vals)
            return np.array(arr, dtype=float)

        def fill_table(rows, arr):
            for r_idx, r in enumerate(rows):
                for c_idx, var in enumerate(r):
                    try:
                        var.set(f"{arr[r_idx, c_idx]:.6f}")
                    except Exception:
                        var.set("0")

        def convert_rows(rows, from_mode, to_mode):
            arr = parse_table(rows)
            converted = np.zeros_like(arr)
            if from_mode == to_mode:
                return
            if from_mode == "XYZ" and to_mode == "xyY":
                for i in range(arr.shape[0]):
                    X, Yv, Z = arr[i]
                    if X == 0 and Yv == 0 and Z == 0:
                        converted[i] = [0, 0, 0]
                        continue
                    x, y, Yc = XYZ_to_xyY_custom((X, Yv, Z))
                    converted[i] = [x, y, Yc]
            elif from_mode == "xyY" and to_mode == "XYZ":
                for i in range(arr.shape[0]):
                    x, y, Yc = arr[i]
                    try:
                        X, Yv, Z = xyY_to_XYZ_custom((x, y, Yc))
                    except Exception:
                        X = Yv = Z = 0.0
                    converted[i] = [float(X), float(Yv), float(Z)]
            fill_table(rows, converted)

        def toggle_mode():
            cur = mode_state["mode"]
            new_mode = "xyY" if cur == "XYZ" else "XYZ"
            convert_rows(measured_table["rows"], cur, new_mode)
            convert_rows(target_table["rows"], cur, new_mode)
            mode_state["mode"] = new_mode
            switch_btn.config(text="Switch to XYZ" if new_mode == "xyY" else "Switch to xyY")
            set_header_mode(measured_table, new_mode)
            set_header_mode(target_table, new_mode)

        def apply_quick_fill(choice):
            if not choice:
                return
            cs_key = {
                "sRGB": "sRGB",
                "Display P3": "P3-D65",
                "Adobe RGB": "Adobe RGB (1998)",
                "BT.2020": "ITU-R BT.2020",
                "BT.709": "ITU-R BT.709",
                "DCI-P3": "DCI-P3",
            }[choice]
            w_xyz = np.asarray(rgb_whitepoint_xyz(cs_key), dtype=float)
            w_xyz = w_xyz / (w_xyz[1] if w_xyz[1] != 0 else 1.0)
            r_vec = np.asarray(rgb_primary_from_matrix(cs_key, "r"), dtype=float)
            g_vec = np.asarray(rgb_primary_from_matrix(cs_key, "g"), dtype=float)
            b_vec = np.asarray(rgb_primary_from_matrix(cs_key, "b"), dtype=float)
            target_xyz = np.vstack([w_xyz, r_vec, g_vec, b_vec])
            if mode_state["mode"] == "xyY":
                xyY_vals = []
                for row in target_xyz:
                    x, y, Yc = XYZ_to_xyY_custom(tuple(row))
                    xyY_vals.append([x, y, Yc])
                target_xyz = np.asarray(xyY_vals, dtype=float)
            fill_table(target_table["rows"], target_xyz)

        def load_table_csv(rows):
            path = filedialog.askopenfilename(
                title="Load 4x3 CSV",
                filetypes=[("CSV files", "*.csv"), ("Text files", "*.txt"), ("All files", "*.*")],
            )
            if not path:
                return
            try:
                import csv

                with open(path, "r", encoding="utf-8-sig") as f:
                    reader = csv.reader(f)
                    vals = []
                    for row in reader:
                        if not row:
                            continue
                        vals.append([float(cell.strip()) for cell in row[:3]])
                if len(vals) < 4:
                    raise ValueError("Need 4 rows (W,R,G,B).")
                arr = np.zeros((4, 3), dtype=float)
                for i in range(4):
                    arr[i] = vals[i]
                fill_table(rows, arr)
                restore_topmost()
            except Exception as exc:
                messagebox.showerror("Load failed", f"Could not load CSV:\n{exc}")

        def calculate_matrix():
            from_mode = mode_state["mode"]
            meas_arr = parse_table(measured_table["rows"])
            targ_arr = parse_table(target_table["rows"])
            # convert to XYZ for math
            if from_mode == "xyY":
                meas_xyz = np.array([xyY_to_XYZ_custom(row) for row in meas_arr], dtype=float)
                targ_xyz = np.array([xyY_to_XYZ_custom(row) for row in targ_arr], dtype=float)
            else:
                meas_xyz = meas_arr
                targ_xyz = targ_arr
            # normalize by respective white Y
            meas_white_Y = meas_xyz[0, 1] if meas_xyz[0, 1] != 0 else 1.0
            targ_white_Y = targ_xyz[0, 1] if targ_xyz[0, 1] != 0 else 1.0
            meas_norm = meas_xyz / meas_white_Y
            targ_norm = targ_xyz / targ_white_Y
            # least squares M (3x3) such that meas_norm @ M ≈ targ_norm
            try:
                M, _, _, _ = np.linalg.lstsq(meas_norm, targ_norm, rcond=None)
            except Exception as exc:
                messagebox.showerror("Calculation failed", str(exc))
                return
            # build 3x4 matrix with last column zeros
            full_mat = np.zeros((3, 4), dtype=float)
            full_mat[:, :3] = M.T  # align rows as XYZ out per row
            flat = full_mat.flatten().tolist()
            idx = 0
            for r in range(3):
                for c in range(4):
                    self.mhc2_matrix_vars[r][c].set(f"{flat[idx]:.6f}")
                    idx += 1
            # rebuild tag
            self.rebuild_mhc2_from_ui(
                float(self.mhc2_min.get() or 0),
                float(self.mhc2_peak.get() or 0),
                int(self.mhc2_entries.get() or 0),
                status_msg="Matrix calculated and updated successfully.",
                popup=False,
            )
            messagebox.showinfo("Success", "Matrix calculated and updated successfully.")
            restore_topmost()

        container = ttk.Frame(win)
        container.pack(fill="both", expand=True)
        measured_table = build_table(container, "Measured", with_loader=True, with_quick=False)
        target_table = build_table(container, "Target", with_loader=True, with_quick=True)

        # wire buttons
        switch_btn = ttk.Button(win, text="Switch to xyY", command=toggle_mode)
        switch_btn.pack(pady=(4, 0))
        if measured_table["load_btn"]:
            measured_table["load_btn"].configure(command=lambda: load_table_csv(measured_table["rows"]))
        if target_table["load_btn"]:
            target_table["load_btn"].configure(command=lambda: load_table_csv(target_table["rows"]))
        if target_table["quick_btn"]:
            target_table["quick_btn"].configure(command=lambda: apply_quick_fill(target_table["quick_combo"].get()))

        ttk.Button(win, text="Calculate", command=calculate_matrix).pack(pady=6)

        set_header_mode(measured_table, mode_state["mode"])
        set_header_mode(target_table, mode_state["mode"])

    def apply_trc_gamma_preset(self):
        sel = self.trc_gamma_combo.get()
        if not sel:
            return
        try:
            if sel.lower().startswith("srgb"):
                self.apply_trc_srgb()
                return
            gamma_val = float(sel.replace("Gamma=", ""))
        except Exception:
            return
        self.apply_trc_gamma_value(gamma_val)

    def apply_trc_gamma_value(self, gamma_val: float):
        # For gamma, curveType uses count=1 with u8Fixed8
        fixed = int(round(gamma_val * 256))
        self.trc_values = [fixed]
        self.trc_info.config(text=f"TRC: entry count=1 (Gamma={gamma_val:.1f})")
        if self.selected_tag and self.selected_tag.signature in {"rTRC", "gTRC", "bTRC"}:
            new_hex = self.build_trc_bytes(self.trc_values).hex().upper()
            self.update_shared_trc_curves(new_hex)
            if self.workspace_mode == "hex":
                self.render_hex_view(self.selected_tag.data_bytes())

    def apply_trc_srgb(self):
        # Generate 1024-entry sRGB curve per ICC recommendation
        values = []
        for i in range(1024):
            x = i / 1023.0
            if x <= 0.04045:
                y = x / 12.92
            else:
                y = ((x + 0.055) / 1.055) ** 2.4
            values.append(int(round(y * 65535)))
        self.trc_values = values
        self.trc_info.config(text=f"TRC: sRGB curve (count={len(values)})")
        if self.selected_tag and self.selected_tag.signature in {"rTRC", "gTRC", "bTRC"}:
            new_hex = self.build_trc_bytes(self.trc_values).hex().upper()
            self.update_shared_trc_curves(new_hex)
            if self.workspace_mode == "hex":
                self.render_hex_view(self.selected_tag.data_bytes())

    def load_trc_from_file(self):
        path = filedialog.askopenfilename(
            title="Load TRC curve file",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception as exc:
            messagebox.showerror("Load failed", f"Could not load TRC file:\n{exc}")
            return
        values = []
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("Data_Type") or line.startswith("Count"):
                continue
            parts = line.split()
            if len(parts) == 2:
                val = int(parts[1])
            else:
                val = int(parts[0])
            values.append(val)
        if not values:
            messagebox.showerror("Load failed", "No values found in file.")
            return
        self.trc_values = values
        self.trc_info.config(text=f"TRC: loaded curve (count={len(values)})")
        self.trc_status.config(text="Loaded successfully.")
        if self.selected_tag and self.selected_tag.signature in {"rTRC", "gTRC", "bTRC"}:
            new_hex = self.build_trc_bytes(self.trc_values).hex().upper()
            self.update_shared_trc_curves(new_hex)
            if self.workspace_mode == "hex":
                self.render_hex_view(self.selected_tag.data_bytes())

    def populate_xy_inputs_from_xyz(self, x: float, y: float, z: float):
        total = x + y + z
        if total <= 0:
            self.xy_input_x.set("0.0")
            self.xy_input_y.set("0.0")
            self.xy_input_Y.set(f"{y:.6f}")
            return
        self.xy_input_x.set("")
        self.xy_input_y.set("")
        self.xy_input_Y.set("")

    def convert_xyy_to_xyz(self):
        try:
            x = float(self.xy_input_x.get())
            y = float(self.xy_input_y.get())
            big_y = float(self.xy_input_Y.get())
            white_level = float(self.white_level.get())
        except Exception:
            messagebox.showerror("Invalid xyY", "x, y, Y and white level must be numeric.")
            return
        if white_level <= 0:
            messagebox.showerror("Invalid white level", "White level must be > 0.")
            return
        try:
            XYZ = xyY_to_XYZ_custom((x, y, big_y))
        except Exception as exc:
            messagebox.showerror("Conversion failed", str(exc))
            return
        X, Y_val, Z = [float(v) for v in XYZ]
        # Normalize by white level (division)
        X /= white_level
        Y_val /= white_level
        Z /= white_level
        self.xyz_x.set(f"{X:.6f}")
        self.xyz_y.set(f"{Y_val:.6f}")
        self.xyz_z.set(f"{Z:.6f}")
        self.update_chromaticity_labels(X, Y_val, Z)

    def load_xyz_quick_options(self, sig: str):
        if sig == "wtpt":
            options = ["D50", "D55", "D60", "D65", "D75"]
        else:
            options = ["sRGB", "BT.709", "Adobe RGB", "Display P3", "DCI-P3", "BT.2020"]
        self.xyz_quick["values"] = options
        self.xyz_quick.set("")

    def apply_xyz_quick_fill(self):
        choice = self.xyz_quick.get()
        if not choice or not self.selected_tag:
            return
        sig = self.selected_tag.signature
        try:
            if choice in {"D50", "D55", "D60", "D65", "D75"}:
                xy = ILLUMINANTS[choice]
                XYZ = xy_to_XYZ_custom(xy)
            else:
                cs_key = {
                    "sRGB": "sRGB",
                    "Display P3": "P3-D65",
                    "Adobe RGB": "Adobe RGB (1998)",
                    "BT.2020": "ITU-R BT.2020",
                    "BT.709": "ITU-R BT.709",
                    "DCI-P3": "DCI-P3",
                }[choice]
                if sig == "rXYZ":
                    XYZ = rgb_primary_from_matrix(cs_key, "r")
                elif sig == "gXYZ":
                    XYZ = rgb_primary_from_matrix(cs_key, "g")
                elif sig == "bXYZ":
                    XYZ = rgb_primary_from_matrix(cs_key, "b")
                else:
                    XYZ = rgb_whitepoint_xyz(cs_key)
            X, Y_val, Z = [float(v) for v in XYZ]
            # For wtpt, normalize to Y=1. For primaries, preserve luminance coefficients as-is.
            if sig == "wtpt" and Y_val != 0:
                factor = 1.0 / Y_val
                X *= factor
                Y_val *= factor
                Z *= factor
            self.xyz_x.set(f"{X:.6f}")
            self.xyz_y.set(f"{Y_val:.6f}")
            self.xyz_z.set(f"{Z:.6f}")
            self.update_chromaticity_labels(X, Y_val, Z)
            self.populate_xy_inputs_from_xyz(X, Y_val, Z)
        except Exception as exc:
            messagebox.showerror("Quick fill failed", str(exc))

    def parse_mluc(self, data: bytes):
        if len(data) < 16:
            raise ValueError("mluc too small")
        sig = data[:4]
        if sig != b"mluc":
            raise ValueError("Tag is not mluc type")
        _, _reserved, num_recs, rec_size_field = struct.unpack(">4sIII", data[:16])
        rec_size = rec_size_field if rec_size_field >= 12 else 12
        records = []
        for i in range(num_recs):
            base = 16 + i * rec_size
            if base + 12 > len(data):
                raise ValueError("Record truncated")
            lang = data[base : base + 2].decode("ascii", errors="replace")
            country = data[base + 2 : base + 4].decode("ascii", errors="replace")
            length, offset = struct.unpack(">II", data[base + 4 : base + 12])
            if offset + length > len(data):
                raise ValueError(f"Record {i+1} string out of bounds")
            text_bytes = data[offset : offset + length]
            text = text_bytes.decode("utf-16be", errors="replace")
            records.append({"lang": lang, "country": country, "text": text, "length": length, "offset": offset})
        return records

    def compute_mluc_layout(self, records):
        header = 16
        table_size = len(records) * 12
        offset = header + table_size
        layout = []
        for rec in records:
            text_bytes = rec["text"].encode("utf-16be")
            length = len(text_bytes)
            layout.append({"length": length, "offset": offset})
            offset += length
            pad = (4 - (offset % 4)) % 4
            offset += pad
        return layout

    def build_mluc_bytes(self, records):
        layout = self.compute_mluc_layout(records)
        header = struct.pack(">4sIII", b"mluc", 0, len(records), 12)
        table = bytearray()
        data = bytearray()
        for rec, meta in zip(records, layout):
            table.extend(rec["lang"].encode("ascii", errors="replace")[:2].ljust(2, b" "))
            table.extend(rec["country"].encode("ascii", errors="replace")[:2].ljust(2, b" "))
            table.extend(struct.pack(">II", meta["length"], meta["offset"]))
            text_bytes = rec["text"].encode("utf-16be")
            data.extend(text_bytes)
            pad = (4 - (len(data) % 4)) % 4
            if pad:
                data.extend(b"\x00" * pad)
        return header + table + data

    def refresh_tag_table(self, select_signature: str | None = None):
        self.compute_offsets()
        self.tag_table.delete(*self.tag_table.get_children())
        for idx, tag in enumerate(self.tags, start=0):
            offset_disp = f"{tag.offset} (0x{tag.offset:X})"
            size_disp = f"{tag.size()} (0x{tag.size():X})"
            self.tag_table.insert(
                "",
                "end",
                iid=tag.signature,
                values=(idx, f"{tag.signature} - {tag.description}", offset_disp, size_disp),
            )
        if select_signature and select_signature in self.tag_table.get_children():
            self.tag_table.selection_set(select_signature)
            self.tag_table.see(select_signature)
        self.update_profile_size_display()
        self.update_remove_state(select_signature)

    def compute_offsets(self):
        layout, _, _ = self._layout_tags()
        for tag, off, _ in layout:
            tag.offset = off

    def collect_header_hex(self) -> Dict[str, str]:
        hex_map: Dict[str, str] = {}
        for field in HEADER_FIELDS:
            if field.get("hidden"):
                hex_map[field["key"]] = self.header_values_hex[field["key"]]
                continue
            key = field["key"]
            var = self.header_vars.get(key)

            if field["type"] == "flags" and self.header_mode == "human":
                emb, indep = (v.get() for v in var)  # type: ignore
                hex_map[key] = encode_flags(emb, indep)  # type: ignore[arg-type]
                continue

            if field["type"] == "attributes" and self.header_mode == "human":
                vals = [v.get() for v in var]  # type: ignore
                hex_map[key] = encode_attributes(*vals)  # type: ignore[arg-type]
                continue

            if field["type"] == "illuminant" and self.header_mode == "human":
                x, y, z = (float(v.get()) for v in var)  # type: ignore
                hex_map[key] = xyz_components_to_hex(x, y, z)
                continue

            if isinstance(var, tuple):
                # Should not happen for other types
                hex_map[key] = self.header_values_hex.get(key, field["default_hex"])
                continue

            value = var.get()
            if field["type"] in {"size", "datetime-fixed", "profile_id"} and self.header_mode == "human":
                # keep existing stored hex; these are auto-managed
                hex_map[key] = self.header_values_hex.get(key, field["default_hex"])
                continue

            if self.header_mode == "human":
                hex_value = human_to_hex(field, value)
            else:
                hex_value = normalize_hex_length(field, value)
            hex_map[key] = hex_value
        return hex_map

    def build_header_bytes(self, size_override: int) -> bytes:
        header_hex = dict(self.header_values_hex)
        header_hex["size"] = int_to_hex(size_override, 4)
        header_bytes = b""
        for field in HEADER_FIELDS:
            hex_value = header_hex[field["key"]]
            if field["type"] == "hex":
                cleaned = clean_hex(hex_value)
            else:
                cleaned = hex_value
            field_bytes = bytes.fromhex(cleaned[: field["length"] * 2])
            if len(field_bytes) < field["length"]:
                field_bytes = field_bytes.ljust(field["length"], b"\x00")
            header_bytes += field_bytes
        if len(header_bytes) != 128:
            raise ValueError(f"Header must be 128 bytes, got {len(header_bytes)}.")
        return header_bytes

    def build_profile_bytes(self) -> bytes:
        layout, data_blocks, total_size = self._layout_tags()

        # Pull latest edits from UI
        self.header_values_hex = self.collect_header_hex()
        # Auto-updated fields
        self.header_values_hex["size"] = int_to_hex(total_size, 4)
        now = datetime.now()
        now_text = now.strftime("%Y-%m-%d %H:%M:%S")
        self.header_values_hex["date_time"] = datetime_text_to_hex(now_text)
        self.header_values_hex["profile_id"] = "00" * 16

        header = self.build_header_bytes(total_size)

        tag_table = struct.pack(">I", len(self.tags))
        for tag, offset, size in layout:
            tag_table += struct.pack(">4sII", tag.signature.encode("ascii"), offset, size)

        profile = bytearray(header + tag_table + data_blocks)
        if len(profile) != total_size:
            raise ValueError("Profile size mismatch while building ICC.")

        # Compute profile ID (MD5) with profile_id set to zeroes
        digest = hashlib.md5(profile).digest()
        profile[84:100] = digest
        digest_hex = digest.hex().upper()
        self.header_values_hex["profile_id"] = digest_hex

        # Sync displayed fields that are auto-managed
        if self.header_mode == "human":
            if isinstance(self.header_vars.get("size"), tk.Variable):
                self.header_vars["size"].set(str(total_size))
            if isinstance(self.header_vars.get("date_time"), tk.Variable):
                self.header_vars["date_time"].set(now_text)
            if isinstance(self.header_vars.get("profile_id"), tk.Variable):
                self.header_vars["profile_id"].set(digest_hex)
        else:
            if isinstance(self.header_vars.get("size"), tk.Variable):
                self.header_vars["size"].set(int_to_hex(total_size, 4))
            if isinstance(self.header_vars.get("date_time"), tk.Variable):
                self.header_vars["date_time"].set(self.header_values_hex["date_time"])
            if isinstance(self.header_vars.get("profile_id"), tk.Variable):
                self.header_vars["profile_id"].set(digest_hex)

        return bytes(profile)

    def _layout_tags(self):
        tag_table_size = 4 + len(self.tags) * 12
        base_offset = 128 + tag_table_size
        data_blocks = bytearray()
        data_offsets: Dict[bytes, int] = {}
        layout: List[Tuple[TagEntry, int, int]] = []
        offset_cursor = base_offset

        for tag in self.tags:
            data = tag.data_bytes()
            existing_offset = data_offsets.get(data)
            if existing_offset is not None:
                layout.append((tag, existing_offset, len(data)))
                continue

            tag_offset = offset_cursor
            data_offsets[data] = tag_offset
            layout.append((tag, tag_offset, len(data)))

            data_blocks.extend(data)
            offset_cursor += len(data)
            pad = (4 - (offset_cursor % 4)) % 4
            if pad:
                data_blocks.extend(b"\x00" * pad)
                offset_cursor += pad

        total_size = offset_cursor
        return layout, bytes(data_blocks), total_size

    def update_profile_size_display(self):
        try:
            _, _, total_size = self._layout_tags()
        except Exception:
            return
        self.header_values_hex["size"] = int_to_hex(total_size, 4)
        if isinstance(self.header_vars.get("size"), tk.Variable):
            if self.header_mode == "human":
                self.header_vars["size"].set(str(total_size))
            else:
                self.header_vars["size"].set(self.header_values_hex["size"])

    def update_remove_state(self, sig: str | None):
        if not hasattr(self, "remove_btn"):
            return
        if not sig:
            self.remove_btn.state(["disabled"])
        else:
            self.remove_btn.state(["!disabled"])
        if hasattr(self, "identity_btn"):
            if sig == "chad":
                self.identity_btn.state(["!disabled"])
                if not self.identity_btn.winfo_ismapped():
                    self.identity_btn.grid()
            else:
                self.identity_btn.state(["disabled"])
                self.identity_btn.grid_remove()

    def load_profile(self):
        path = filedialog.askopenfilename(
            filetypes=[("ICC profile", "*.icc *.icm"), ("All files", "*.*")],
            title="Load ICC Profile",
        )
        if not path:
            return
        try:
            data = Path(path).read_bytes()
            if len(data) < 132:
                raise ValueError("File too small to be a valid ICC profile.")
            size_field = int.from_bytes(data[0:4], "big")
            header_hex: Dict[str, str] = {}
            pos = 0
            for field in HEADER_FIELDS:
                length = field["length"]
                raw = data[pos : pos + length]
                if len(raw) != length:
                    raise ValueError(f"Header field {field['key']} truncated.")
                header_hex[field["key"]] = raw.hex().upper()
                pos += length
            if header_hex.get("acsp") != "61637370":
                raise ValueError("Missing required 'acsp' signature.")

            tag_count = struct.unpack_from(">I", data, 128)[0]
            tag_table_end = 132 + tag_count * 12
            if tag_table_end > len(data):
                raise ValueError("Tag table exceeds file size.")
            tags: List[TagEntry] = []
            for i in range(tag_count):
                sig_bytes, offset, size = struct.unpack_from(">4sII", data, 132 + i * 12)
                sig = sig_bytes.decode("ascii", errors="replace")
                if offset + size > len(data):
                    raise ValueError(f"Tag {sig} out of bounds (offset {offset}, size {size}).")
                if offset < tag_table_end:
                    raise ValueError(f"Tag {sig} overlaps header/tag table (offset {offset}).")
                chunk = data[offset : offset + size]
                if len(chunk) != size:
                    raise ValueError(f"Tag {sig} size mismatch (expected {size}, found {len(chunk)}).")
                tags.append(
                    TagEntry(
                        sig,
                        KNOWN_TAG_LIBRARY.get(sig, "Custom tag"),
                        chunk.hex().upper(),
                        offset=offset,
                    )
                )

            header_hex["size"] = int_to_hex(len(data), 4)
            self.header_values_hex = header_hex
            self.header_mode = "human"
            self.render_header_fields()
            self.tags = tags
            self.refresh_tag_table()
            self.refresh_search_results()
            self.hex_text.delete("1.0", tk.END)
            self.tag_title.config(text="Select a tag to edit")
            messagebox.showinfo("Loaded", f"Loaded ICC profile:\n{path}")
        except Exception as exc:
            messagebox.showerror("Load failed", f"Could not load ICC profile:\n{exc}")

    def save_profile(self):
        try:
            data = self.build_profile_bytes()
        except Exception as exc:
            messagebox.showerror("Build failed", f"Could not build ICC profile:\n{exc}")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".icc",
            filetypes=[("ICC profile", "*.icc"), ("All files", "*.*")],
            title="Save MHC ICC Profile",
        )
        if not path:
            return
        with open(path, "wb") as f:
            f.write(data)
        messagebox.showinfo("Saved", f"Profile saved to:\n{path}")

    def show_about(self):
        msg = (
            "MHC ICC Profile Maker\n"
            "Version: V0.91\n"
            "\n"
            "Build custom ICC v4 profiles with Windows Advanced Color (MHC2) data.\n"
            "Project repository: https://github.com/ttys001/MHC-ICC-Profile-Maker\n"
            "License: GPL-3.0-or-later. Redistribution requires sharing source and license.\n"
        )
        messagebox.showinfo("About", msg)


def main():
    root = tk.Tk()
    app = ICCBuilderApp(root)
    root.minsize(1200, 650)
    root.mainloop()


if __name__ == "__main__":
    main()
