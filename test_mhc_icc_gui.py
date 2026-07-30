import hashlib
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
    xyY_to_XYZ_custom,
)


class ProfileMakerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = tk.Tk()
        cls.root.withdraw()
        cls.app = ICCBuilderApp(cls.root)

    @classmethod
    def tearDownClass(cls):
        cls.root.destroy()

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
