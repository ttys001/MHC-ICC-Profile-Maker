import hashlib
import re
import struct
import tkinter as tk
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Dict, List, Tuple


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

# Defaults taken from NE160QDM-NM7 BASE.icc to mirror offsets, order, and content
DEFAULT_TAGS_SAMPLE: List[TagEntry] = [
    TagEntry("cprt", "Copyright", "6D6C756300000000000000010000000C656E5553000000480000001C0043006F007000790072006900670068007400200028004300290020004D006900630072006F0073006F0066007400200043006F00720070006F0072006100740069006F006E002E"),
    TagEntry("rTRC", "Red tone reproduction curve", "63757276000000000000000102330000"),
    TagEntry("gTRC", "Green tone reproduction curve", "63757276000000000000000102330000"),
    TagEntry("bTRC", "Blue tone reproduction curve", "63757276000000000000000102330000"),
    TagEntry("chad", "Chromatic adaptation", "7366333200000000000100000000000000000000000000000001000000000000000000000000000000010000"),
    TagEntry("rXYZ", "Red colorant", "58595A20000000000000E78E00006D2900000158"),
    TagEntry("gXYZ", "Green colorant", "58595A200000000000005BC60000EE7200001007"),
    TagEntry("bXYZ", "Blue colorant", "58595A200000000000002FC30000133A0000FAC5"),
    TagEntry("wtpt", "Media white point", "58595A200000000000008A820000919400009E9D"),
    TagEntry("MSCA", "Microsoft Color Adaptation", "74657874000000007B2741707076657273696F6E273A27312E302E3135322E30272C2744363541646170746564273A547275657D00"),
    TagEntry("lumi", "Luminance", "58595A200000000004E2000004E2000004E20000"),
    TagEntry("MHC2", "Windows Advanced Color metadata", "4D48433200000000000000020000000004E2000000000024000000540000006400000074000100000000000000000000000000000000000000010000000000000000000000000000000000000001000000000000736633320000000000000000000100007366333200000000000000000001000073663332000000000000000000010000"),
    TagEntry("desc", "Profile description", "6D6C756300000000000000010000000C656E5553000000300000001C004E004500310036003000510044004D002D004E004D00370020005300440052002000500072006F00660069006C0065"),
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
        self.root.config(menu=menu)

    def _build_layout(self):
        container = ttk.Frame(self.root)
        container.pack(fill="both", expand=True, padx=6, pady=6)

        header_frame = ttk.Labelframe(container, text="Header Fields", width=540)
        tags_frame = ttk.Labelframe(container, text="Tag Table", width=540)
        editor_frame = ttk.Labelframe(container, text="Tag Workspace", width=460)

        header_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        tags_frame.grid(row=0, column=1, sticky="nsew", padx=(0, 6))
        editor_frame.grid(row=0, column=2, sticky="nsew")

        container.columnconfigure(0, minsize=540, weight=1)
        container.columnconfigure(1, minsize=540, weight=1)
        container.columnconfigure(2, minsize=460, weight=0)
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
        self.tag_table.column("signature", width=240, anchor="w")
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
        self.tag_title = ttk.Label(top, text="Select a tag to edit")
        self.tag_title.pack(side="left")
        ttk.Button(top, text="Apply Changes", command=self.apply_tag_changes).pack(side="right", padx=4)

        header_bar = ttk.Frame(parent)
        header_bar.pack(fill="x", padx=4, pady=(0, 2))
        ttk.Label(header_bar, text=" " * 6, font=("Courier New", 10), width=6).pack(side="left", padx=(0, 8))
        self.hex_header = ttk.Label(header_bar, text="", font=("Courier New", 10))
        self.hex_header.pack(side="left")

        body = ttk.Frame(parent)
        body.pack(fill="both", expand=True, padx=4, pady=4)

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

        ttk.Button(parent, text="Save ICC Profile…", command=self.save_profile).pack(side="right", padx=8, pady=6)

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
        self.render_hex_view(tag.data_bytes())
        self.update_remove_state(tag.signature)

    def apply_tag_changes(self):
        if not self.selected_tag:
            messagebox.showinfo("No tag selected", "Choose a tag from the table first.")
            return
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
            messagebox.showinfo("Loaded", f"Loaded ICC profile:\\n{path}")
        except Exception as exc:
            messagebox.showerror("Load failed", f"Could not load ICC profile:\\n{exc}")

    def save_profile(self):
        try:
            data = self.build_profile_bytes()
        except Exception as exc:
            messagebox.showerror("Build failed", f"Could not build ICC profile:\\n{exc}")
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
        messagebox.showinfo("Saved", f"Profile saved to:\\n{path}")


def main():
    root = tk.Tk()
    app = ICCBuilderApp(root)
    root.minsize(1200, 650)
    root.mainloop()


if __name__ == "__main__":
    main()
