import hashlib
import math
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
import tkinter as tk
from unittest.mock import patch

from mhc_icc_gui import (
    ICCBuilderApp,
    calculate_color_matrix,
    calculate_profile_id,
    least_squares_4x3,
    parse_profile_bytes,
    read_mhc2_lut,
    read_mhc2_matrix,
    read_numeric_csv,
    resample_mhc2_lut,
    xyY_to_XYZ_custom,
)


class LutTests(unittest.TestCase):
    def read_fixture(self, text, suffix):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ("lut" + suffix)
            path.write_text(text, encoding="utf-8-sig")
            return read_mhc2_lut(str(path))

    def test_csv_counts_and_domains(self):
        for count in (1, 2, 3, 17, 33, 65, 101, 128, 257, 511, 1000, 2047, 4095, 4096):
            with self.subTest(count=count):
                lut = self.read_fixture("0.1,0.2,0.3\n" * count, ".csv")
                self.assertEqual(lut, [[v] * count for v in (0.1, 0.2, 0.3)])
        for maximum in (1, 255, 1023, 4095, 65535):
            for delimiter in (",", ";", "\t"):
                with self.subTest(maximum=maximum, delimiter=delimiter):
                    lut = self.read_fixture("# comment\n\n" + delimiter.join(map(str, (0, maximum / 2, maximum))), ".csv")
                    self.assertEqual(lut, [[0], [0.5], [1]])
        for text in ("", "0,0,0\n" * 4097, "nan,0,0", "0,inf,0", "-1,0,0", "65536,0,0", "0,0"):
            with self.subTest(text=text[:30]), self.assertRaises(ValueError):
                self.read_fixture(text, ".csv")

    def test_cube(self):
        for count in (1, 65, 101, 4096):
            text = f'TITLE "Calibration"\n# comment\nLUT_1D_SIZE {count}\nDOMAIN_MIN 0 0 0\nDOMAIN_MAX 1 1 1\n\n' + "0.1 0.5 0.9725 # sample\n" * count
            self.assertEqual(self.read_fixture(text, ".cube"), [[v] * count for v in (0.1, 0.5, 0.9725)])
        self.assertEqual(self.read_fixture("LUT_1D_SIZE 1\n0 0 0", ".unknown"), [[0]] * 3)
        for text in ("0 0 0", "LUT_1D_SIZE 2\n0 0 0", "LUT_1D_SIZE 4097", "LUT_1D_SIZE 0",
                     "LUT_1D_SIZE 1\n0 0", "LUT_1D_SIZE 1\n0 0 0 0", "LUT_1D_SIZE 1\n0 no 0",
                     "LUT_1D_SIZE 1\n1.1 0 0", "LUT_1D_SIZE 1\nnan 0 0",
                     "LUT_1D_SIZE 1\nDOMAIN_MIN -1 0 0\n0 0 0",
                     "LUT_1D_SIZE 1\nDOMAIN_MAX 0 0 0\n0 0 0",
                     "LUT_1D_SIZE 1\nDOMAIN_MAX nan 1 1\n0 0 0"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                self.read_fixture(text, ".cube")

    def test_cube_full_range_input_units_preserve_output(self):
        rows = "0 0 0\n0.5 0.49 0.51\n1 0.98 0.99\n"
        expected = [[0, 0.5, 1], [0, 0.49, 0.98], [0, 0.51, 0.99]]
        domains = ["", "DOMAIN_MIN 0 0 0", "DOMAIN_MAX 2 2 2"]
        for maximum in (1, 255, 1023, 4095, 65535, 10000, 0.5, 1e-12):
            iridas = f"DOMAIN_MIN 0 0 0\nDOMAIN_MAX {maximum} {maximum} {maximum}\n"
            resolve = f"LUT_1D_INPUT_RANGE 0 {maximum}\n"
            domains.extend((iridas, resolve, iridas + resolve))
        domains.extend(("DOMAIN_MIN 1e-12 0 0\nDOMAIN_MAX 1 1 1",
                        "DOMAIN_MAX 1023 1023.0000000001 1023\nLUT_1D_INPUT_RANGE 0 1023"))
        for domain in domains:
            with self.subTest(domain=domain):
                text = '# DaVinci Resolve / IRIDAS 1D\nTITLE "Calibration"\nLUT_1D_SIZE 3\n' + domain + "\n" + rows
                self.assertEqual(self.read_fixture(text, ".cube"), expected)

    def test_cube_invalid_input_domains(self):
        domains = ("LUT_1D_INPUT_RANGE 64 940", "LUT_1D_INPUT_RANGE 16 235",
                   "LUT_1D_INPUT_RANGE 0.1 1", "LUT_1D_INPUT_RANGE -0.125 1.125",
                   "DOMAIN_MIN 64 64 64\nDOMAIN_MAX 940 940 940",
                   "DOMAIN_MAX 1023 4095 65535", "DOMAIN_MIN 0 0.1 0",
                   "DOMAIN_MAX 1023 1023 1023\nLUT_1D_INPUT_RANGE 0 1",
                   "DOMAIN_MIN 0 0 0\nLUT_1D_INPUT_RANGE 0 1023",
                   "LUT_1D_INPUT_RANGE 0 0", "LUT_1D_INPUT_RANGE 0 -1",
                   "LUT_1D_INPUT_RANGE 1e-10 1e-11", "DOMAIN_MAX -1 -1 -1",
                   "DOMAIN_MIN nan 0 0", "DOMAIN_MAX inf inf inf",
                   "LUT_1D_INPUT_RANGE nan 1", "LUT_1D_INPUT_RANGE 0 inf",
                   "LUT_1D_INPUT_RANGE 0", "LUT_1D_INPUT_RANGE 0 1 2",
                   "DOMAIN_MIN 0 0", "DOMAIN_MAX 1 1 1 1",
                   "LUT_1D_INPUT_RANGE 0 1\nLUT_1D_INPUT_RANGE 0 1")
        for domain in domains:
            with self.subTest(domain=domain), self.assertRaises(ValueError):
                self.read_fixture("LUT_1D_SIZE 1\n" + domain + "\n0 0 0", ".cube")
        for row in ("0 0 1023", "-0.01 0 0", "0 nan 0", "0 0 inf"):
            with self.subTest(row=row), self.assertRaises(ValueError):
                self.read_fixture("LUT_1D_SIZE 1\nLUT_1D_INPUT_RANGE 0 1023\n" + row, ".cube")

    def test_colourspace_quantel_type2_headers(self):
        # Same header structure as the supplied ColourSpace Unity 12-bit export.
        for count, maximum in ((1, 65535), (65, 1023), (101, 65535), (4096, 4095)):
            text = ("# Authors: Light Illusion\n# RGB\ntable type\t2\n\n"
                    f"gMax\t{maximum}\ngSize\t{count}\nR\tG\tB\n"
                    + "\n".join(f"{i} {i} {i}" for i in range(count)))
            with self.subTest(count=count, maximum=maximum):
                expected = [[i / maximum for i in range(count)]] * 3
                self.assertEqual(self.read_fixture(text, ".txt"), expected)
        for header in ("table type2\ngMax 511\ngSize 2", "# table type 2\n#gMax 511\n#gSize 2",
                       "table type 2 # comment\ngMax 511 # comment\ngSize 2 # comment"):
            self.assertEqual(self.read_fixture(header + "\n511 511 511\n0 0 0", ".txt"), [[1, 0]] * 3)
        for text in ("gMax 1023\nmax value 65535\n0 0 0", "gMax 0\n0 0 0",
                     "gMax nan\n0 0 0", "gMax 1023\n0 0 1024", "gMax bad\n0 0 0",
                     "gSize 2\n0 0 0", "gSize 1\ngSize 2\n0 0 0",
                     "gSize 0\n0 0 0", "gSize 1.5\n0 0 0", "gSize\n0 0 0",
                     "table type 1\n0 0 0", "table type 3\n0 0 0", "table type bad\n0 0 0"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                self.read_fixture(text, ".txt")
        text = "table type 2\ngMax 65535\ngSize 65536\nR G B\n" + "\n".join(f"{i} {i} {i}" for i in range(65536))
        with self.assertRaisesRegex(ValueError, "65536 entries; MHC2 supports 1–4096"):
            self.read_fixture(text, ".txt")

    def test_quantel_metadata_and_counts(self):
        for count in (65, 101, 256, 4096):
            for maximum in (1023, 65535):
                text = f"# ColourSpace Quantel 1D\nVersion 1\n#max value {maximum}\nR G B\n\n" + "0 100 200\n" * count
                self.assertEqual(self.read_fixture(text, ".txt"), [[v / maximum] * count for v in (0, 100, 200)])
        for metadata in ("bit depth 10", "range 0 1023", "range 0-1023", "max value: 1023"):
            self.assertEqual(self.read_fixture(metadata + "\n0 100 200", ".txt"), [[0], [100 / 1023], [200 / 1023]])
        self.assertEqual(self.read_fixture("ColourSpace\n0 100 255", ".txt"), [[0], [100 / 255], [1]])
        for text in ("", "0 0 0\n" * 4097, "max value 1023\n0 0 1024", "max value nan\n0 0 0",
                     "max value 0\n0 0 0", "max value 1023\nbit depth 16\n0 0 0",
                     "0 bad 0\n0 0 0", "0 0", "0 0 0\nbad data", "0 nan 0"):
            with self.subTest(text=text[:60]), self.assertRaises(ValueError):
                self.read_fixture(text, ".txt")

    def test_3d_rejected_even_with_small_table_or_wrong_extension(self):
        for marker in ("LUT_3D_SIZE 2", "LUT_3D_INPUT_RANGE 0 1", "LUT_1D_SIZE 2\nLUT_3D_SIZE 2",
                       "LUT3D", "cube size 2", "#cube data", "#vertices 2", "SAM cube 2"):
            for suffix in (".cube", ".txt", ".csv", ".unknown"):
                with self.subTest(marker=marker, suffix=suffix), self.assertRaisesRegex(ValueError, "Only RGB 1D"):
                    self.read_fixture(marker + "\n0 0 0\n" * 8, suffix)

    def test_pchip_identity_and_arbitrary_counts(self):
        for count, target in ((2, 17), (3, 65), (65, 4096), (101, 4096), (257, 1000), (1000, 4096)):
            lut = [[i / (count - 1) for i in range(count)]] * 3
            result = resample_mhc2_lut(lut, target)
            self.assertEqual([len(ch) for ch in result], [target] * 3)
            for channel in result:
                for i, value in enumerate(channel):
                    self.assertAlmostEqual(value, i / (target - 1), places=14)

    def test_pchip_shapes_and_endpoints(self):
        for channel in ([0.03 + 0.9425 * (i / 64) ** 2.2 for i in range(65)],
                        [0.9, 0.8, 0.8, 0.2, 0.1], [0.1, 0.8, 0.2, 0.2, 0.9], [0.37] * 17):
            output = resample_mhc2_lut([channel] * 3, 4096)[0]
            self.assertEqual((output[0], output[-1]), (channel[0], channel[-1]))
            for j, value in enumerate(output):
                index = min(j * (len(channel) - 1) // 4095, len(channel) - 2)
                self.assertGreaterEqual(value + 1e-14, min(channel[index:index + 2]))
                self.assertLessEqual(value - 1e-14, max(channel[index:index + 2]))
                self.assertTrue(math.isfinite(value) and 0 <= value <= 1)
            if all(a <= b for a, b in zip(channel, channel[1:])):
                self.assertTrue(all(a <= b + 1e-14 for a, b in zip(output, output[1:])))
            if all(a >= b for a, b in zip(channel, channel[1:])):
                self.assertTrue(all(a + 1e-14 >= b for a, b in zip(output, output[1:])))
        # Independent exact Hermite values: slopes [0, 3/8, 1] for [0, 1/4, 1].
        self.assertEqual(resample_mhc2_lut([[0, 0.25, 1]] * 3, 5)[0], [0, 0.078125, 0.25, 0.546875, 1])

    def test_pchip_special_cases_and_validation(self):
        self.assertEqual(resample_mhc2_lut([[0.37] * 17] * 3, 4096), [[0.37] * 4096] * 3)
        self.assertEqual(resample_mhc2_lut([[0.1], [0.2], [0.3]], 17), [[v] * 17 for v in (0.1, 0.2, 0.3)])
        lut = [[0.1, 0.4, 0.9725], [0.02, 0.5, 1], [0.03, 0.6, 0.9812]]
        self.assertEqual(resample_mhc2_lut(lut, 3), lut)
        self.assertEqual(resample_mhc2_lut(lut, 1), [[ch[0]] for ch in lut])
        output = resample_mhc2_lut([[0.2, 0.8]] * 3, 7)[0]
        for i, value in enumerate(output):
            self.assertAlmostEqual(value, 0.2 + i * 0.1)
        for target in (0, 4097, 2.5):
            with self.assertRaises(ValueError):
                resample_mhc2_lut(lut, target)
        for invalid in ([], [[], [], []], [[0], [0, 1], [0]], [[math.nan]] * 3, [[-0.01]] * 3, [[1.01]] * 3):
            with self.assertRaises(ValueError):
                resample_mhc2_lut(invalid, 17)


class ProfileMakerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = tk.Tk()
        cls.root.withdraw()
        cls.app = ICCBuilderApp(cls.root)

    @classmethod
    def tearDownClass(cls):
        cls.root.destroy()

    def test_cube_input_units_produce_identical_mhc2_bytes(self):
        self.app.reset_profile()
        self.addCleanup(self.app.reset_profile)
        tag = next(t for t in self.app.tags if t.signature == "MHC2")
        self.app.render_mhc2_workspace(tag)
        outputs = []
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "range.cube"
            for declaration in ("LUT_1D_INPUT_RANGE 0 1", "LUT_1D_INPUT_RANGE 0 1023",
                                "DOMAIN_MIN 0 0 0\nDOMAIN_MAX 65535 65535 65535"):
                path.write_text("LUT_1D_SIZE 3\n" + declaration + "\n0 0 0\n0.5 0.49 0.51\n1 0.98 0.99\n", encoding="utf-8")
                self.app.mhc2_lut_values = read_mhc2_lut(str(path))
                outputs.append(self.app.build_mhc2_bytes(0.2, 80, 3))
        self.assertEqual(outputs, [outputs[0]] * 3)
        self.assertEqual(self.app.parse_mhc2(outputs[0])["lut_entries"], 3)

    def test_default_profile_is_structurally_valid(self):
        profile = self.app.build_profile_bytes()
        header, tags = parse_profile_bytes(profile)
        self.assertEqual(int(header["size"], 16), len(profile))
        self.assertEqual(profile[84:100], calculate_profile_id(profile))
        self.assertEqual(len({tag.signature for tag in tags}), len(tags))

        by_signature = {tag.signature: tag for tag in tags}
        self.assertEqual(by_signature["rTRC"].size(), 16)
        self.assertEqual(by_signature["MHC2"].size(), 132)
        self.assertEqual(
            self.app.parse_text_type(by_signature["MSCA"].data_bytes()),
            "{'Appversion':'1.0.152.0','D65Adapted':True}",
        )
        mhc2 = self.app.parse_mhc2(by_signature["MHC2"].data_bytes())
        self.assertEqual(mhc2["lut_entries"], 2)
        self.assertEqual(mhc2["matrix_off"], 36)
        self.assertEqual(
            [mhc2["lut_r_off"], mhc2["lut_g_off"], mhc2["lut_b_off"]],
            [84, 100, 116],
        )

    def test_import_resample_gui_and_arbitrary_profile_roundtrip(self):
        self.app.reset_profile()
        tag = next(tag for tag in self.app.tags if tag.signature == "MHC2")
        self.app.selected_tag = tag
        self.app.render_mhc2_workspace(tag)
        self.addCleanup(self.app.reset_profile)
        with tempfile.TemporaryDirectory() as directory, patch("mhc_icc_gui.messagebox.showinfo"):
            for count in (1, 2, 3, 17, 65, 101, 257, 1000, 4095, 4096):
                path = Path(directory) / "lut.csv"
                source = [[0.01 + end * (i / max(1, count - 1)) ** 2 for i in range(count)] for end in (0.9625, 0.99, 0.9712)]
                path.write_text("\n".join(",".join(str(ch[i]) for ch in source) for i in range(count)), encoding="utf-8")
                with patch("mhc_icc_gui.filedialog.askopenfilename", return_value=str(path)):
                    self.app.load_mhc2_lut()
                self.root.update()  # Include queued selection events in precision checks.
                self.assertEqual(self.app.mhc2_lut_values, source)
                self.assertEqual(self.app.mhc2_entries.get(), str(count))
                _, tags = parse_profile_bytes(self.app.build_profile_bytes())
                parsed = self.app.parse_mhc2(next(t for t in tags if t.signature == "MHC2").data_bytes())
                self.assertEqual(parsed["lut_entries"], count)
                for actual, expected in zip(parsed["lut_values"], source):
                    for a, b in zip(actual, expected):
                        self.assertLessEqual(abs(a - b), 0.5 / 65536)
            before = tag.data_bytes()
            for target in (None, count):
                with patch("mhc_icc_gui.simpledialog.askinteger", return_value=target):
                    self.app.resample_mhc2_lut()
                self.assertEqual(tag.data_bytes(), before)
                self.assertEqual(self.app.mhc2_lut_values, source)
            with patch("mhc_icc_gui.simpledialog.askinteger", return_value=101):
                self.app.resample_mhc2_lut()
            self.root.update()
            self.assertEqual(self.app.mhc2_entries.get(), "101")
            expected = resample_mhc2_lut(source, 101)
            self.assertEqual(self.app.mhc2_lut_values, expected)
            self.assertEqual(self.app.mhc2_preview_idx_vars[-1].get(), "100")
            # Failed field validation must leave the LUT and serialized tag intact.
            before = tag.data_bytes()
            self.app.mhc2_peak.set("invalid")
            with patch("mhc_icc_gui.messagebox.showerror"), patch("mhc_icc_gui.simpledialog.askinteger", return_value=65):
                self.app.resample_mhc2_lut()
            self.assertEqual(tag.data_bytes(), before)
            self.assertEqual(self.app.mhc2_lut_values, expected)
            self.assertEqual(self.app.mhc2_entries.get(), "101")
            # Raw edits invalidate the float cache.
            self.app.mhc2_lut_values = [[0.25, 0.75]] * 3
            tag.data_hex = self.app.build_mhc2_bytes(0.2, 80, 2).hex().upper()
            self.app.render_mhc2_workspace(tag)
            self.assertEqual(self.app.mhc2_lut_values, [[0.25, 0.75]] * 3)

    def test_all_sample_profiles_parse(self):
        profiles = sorted(Path("samples").rglob("*.icc"))
        self.assertTrue(profiles)
        for path in profiles:
            with self.subTest(path=path):
                _, tags = parse_profile_bytes(path.read_bytes())
                mhc2 = next(tag for tag in tags if tag.signature == "MHC2")
                self.app.parse_mhc2(mhc2.data_bytes())

    def test_csv_fixtures_and_stdlib_matrix_solver(self):
        fixture = Path("samples/simple example")
        measured = [row[:3] for row in read_numeric_csv(str(fixture / "measured.csv"))][:4]
        target = [row[:3] for row in read_numeric_csv(str(fixture / "target.csv"))][:4]
        matrix = calculate_color_matrix(measured, target, values_are_xyy=True)
        expected = (
            (0.69192573, 0.26112058, 0.02883066, 0.0),
            (-0.03935457, 1.02367934, 0.01162565, 0.0),
            (-0.02546081, 0.13672490, 0.89415441, 0.0),
        )
        for actual_row, expected_row in zip(matrix, expected):
            for actual, wanted in zip(actual_row, expected_row):
                self.assertAlmostEqual(actual, wanted, places=7)

        lut = read_mhc2_lut(str(fixture / "1DLUT.csv"))
        self.assertEqual([len(channel) for channel in lut], [4096] * 3)
        self.assertTrue(all(0 <= value <= 1 for channel in lut for value in channel))

    def test_local_only_fixtures_when_present(self):
        fixture = Path("samples/sample")
        if not fixture.is_dir():
            return
        self.assertEqual(
            read_mhc2_matrix(str(fixture / "matrix.csv")),
            [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0]],
        )
        lut = read_mhc2_lut(str(fixture / "1DLUT.csv"))
        self.assertEqual([len(channel) for channel in lut], [4096] * 3)

    def test_sample_round_trips_preserve_tag_data(self):
        for path in sorted(Path("samples").rglob("*.icc")):
            with self.subTest(path=path):
                header, tags = parse_profile_bytes(path.read_bytes())
                original = {tag.signature: tag.data_bytes() for tag in tags}
                self.app.header_values_hex = header
                self.app.header_mode = "human"
                self.app.render_header_fields()
                self.app.tags = tags
                rebuilt = self.app.build_profile_bytes()
                _, rebuilt_tags = parse_profile_bytes(rebuilt)
                self.assertEqual({tag.signature: tag.data_bytes() for tag in rebuilt_tags}, original)
                self.assertEqual(rebuilt[84:100], calculate_profile_id(rebuilt))
        self.app.reset_profile()

    def test_invalid_matrix_and_hex_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "full-rank"):
            calculate_color_matrix([[0.0, 1.0, 0.0]] * 4, [[0.0, 1.0, 0.0]] * 4, False)
        near_singular = [
            [0.23122140808778602, 0.20083863241888641, -0.1435795443245664],
            [-0.6009348647506397, -0.5219712889624587, 0.3731572911788153],
            [0.18566101282254835, 0.16126492880425075, -0.11528830324838335],
            [0.1349861546854935, 0.1172488089253348, -0.08382117588080039],
        ]
        target = [
            [0.3131992040260024, -1.4892773731328215, -0.5448691737581977],
            [-0.4833123986084571, -0.2621545059158811, 2.2842920645436737],
            [-0.3772873047494678, 0.4773366654260695, 1.6553333534166312],
            [0.5036535334860688, 0.43187757240443414, 1.2979587079303478],
        ]
        with self.assertRaisesRegex(ValueError, "singular"):
            least_squares_4x3(near_singular, target)
        self.assertEqual(self.app.parse_hex_view("00 0000 11"), b"\x00\x00\x00\x11")
        with self.assertRaises(ValueError):
            self.app.parse_hex_view("00 GG")
        with self.assertRaisesRegex(ValueError, "must not be zero"):
            xyY_to_XYZ_custom((0.3, 0.0, 1.0))

    def test_identity_trc_and_new_profile_state(self):
        identity = self.app.build_trc_bytes([])
        self.assertEqual(self.app.parse_trc(identity)["values"], [])
        self.app.selected_tag = self.app.tags[0]
        self.app.workspace_kind = "mluc"
        self.app.reset_profile()
        self.assertIsNone(self.app.selected_tag)
        self.assertIsNone(self.app.workspace_kind)

    def test_identity_lut_refreshes_offsets_and_preview(self):
        self.app.reset_profile()
        mhc2 = next(tag for tag in self.app.tags if tag.signature == "MHC2")
        self.app.selected_tag = mhc2
        self.app.render_mhc2_workspace(mhc2)
        with patch("mhc_icc_gui.messagebox.showinfo"):
            self.app.apply_mhc2_identity_lut()

        parsed = self.app.parse_mhc2(mhc2.data_bytes())
        self.assertEqual(parsed["lut_entries"], 2)
        self.assertEqual(parsed["matrix_off"], 36)
        self.assertEqual(
            [parsed["lut_r_off"], parsed["lut_g_off"], parsed["lut_b_off"]],
            [84, 100, 116],
        )
        self.assertEqual([var.get() for var in self.app.mhc2_preview_idx_vars[:2]], ["0", "1"])
        self.assertEqual(
            [[var.get() for var in row] for row in self.app.mhc2_preview_vars[:2]],
            [["0.000000"] * 3, ["1.000000"] * 3],
        )
        self.app.reset_profile()

    def test_mhc2_workspace_fits_default_window(self):
        self.root.geometry("1200x800")
        self.app.reset_profile()
        tag = next(t for t in self.app.tags if t.signature == "MHC2")
        self.app.selected_tag = tag
        self.app.render_mhc2_workspace(tag)
        self.app.show_mhc2_workspace()
        self.root.deiconify()
        try:
            self.root.update()
            self.assertLessEqual(self.app.mhc2_frame.winfo_reqheight(), self.app.mhc2_scroll.canvas.winfo_height())
            self.assertLessEqual(self.app.mhc2_frame.winfo_reqwidth(), self.app.mhc2_scroll.canvas.winfo_width())
        finally:
            self.root.withdraw()
            self.app.reset_profile()

    def test_v092_profile_bytes_for_defaults_and_csv(self):
        class FixedDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                return cls(2026, 1, 2, 3, 4, 5, tzinfo=tz)

        def profile_sha256():
            with patch("mhc_icc_gui.datetime", FixedDateTime):
                return hashlib.sha256(self.app.build_profile_bytes()).hexdigest()

        self.app.reset_profile()
        self.assertEqual(
            profile_sha256(),
            "030dae22ae3c3b7247b0b818bb4be4d87d8d03208686502e45fd1170bef2e148",
        )

        fixture = Path("samples/simple example")
        mhc2 = next(tag for tag in self.app.tags if tag.signature == "MHC2")
        self.app.selected_tag = mhc2
        self.app.render_mhc2_workspace(mhc2)
        matrix = read_mhc2_matrix(str(fixture / "matrix.csv"))
        for row, values in zip(self.app.mhc2_matrix_vars, matrix):
            for variable, value in zip(row, values):
                variable.set(f"{value:.6f}")
        self.app.mhc2_lut_values = read_mhc2_lut(str(fixture / "1DLUT.csv"))
        self.app.mhc2_entries.set(str(len(self.app.mhc2_lut_values[0])))
        self.app.rebuild_mhc2_from_ui(
            float(self.app.mhc2_min.get()),
            float(self.app.mhc2_peak.get()),
            len(self.app.mhc2_lut_values[0]),
            popup=False,
        )
        self.assertEqual(
            profile_sha256(),
            "c6c671cfbc370c8d222b4b41cd826cea0a6bdac3621937b725172d4afc5e2f71",
        )
        self.app.reset_profile()


if __name__ == "__main__":
    unittest.main()
