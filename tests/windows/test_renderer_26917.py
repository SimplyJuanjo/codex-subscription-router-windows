"""Fail-closed source and native binding tests for the 26.917 Windows profile."""
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import patch_windows_app as patcher
import windows_renderer_26917 as renderer


class Renderer26917Tests(unittest.TestCase):
    def test_menu_bindings_fail_closed(self):
        menu = '(0,M4.jsx)(Jr,{leftIconAsset:Ge,"aria-label":e,className:`opacity-50`,disabled:n,onSelect:r,children:h},`email`)'
        self.assertEqual(renderer.account_menu_item_alias(menu), "Jr")
        for invalid in (menu * 2, menu.replace("M4", "d6"), "const Jr={};"):
            with self.assertRaises(RuntimeError):
                renderer.account_menu_item_alias(invalid)
        usage = 'Nj(o,uIo,{defaultResetCreditsOpen:!0,initialAvailableCount:Xe,isRateLimitReached:!1})'
        self.assertEqual(renderer.usage_modal_opener_alias(usage, "uIo"), "Nj")
        with self.assertRaises(RuntimeError):
            renderer.usage_modal_opener_alias(usage * 2, "uIo")

    def test_source_identity_is_pinned(self):
        fields = patcher.TESTED_SOURCE_BUILDS["26.917.6896.0"]
        patcher.validate_approved_source(SimpleNamespace(package_version="26.917.6896.0", **fields), False)
        for field in fields:
            with self.subTest(field=field):
                source = SimpleNamespace(package_version="26.917.6896.0", **fields)
                setattr(source, field, "unreviewed")
                with self.assertRaises(RuntimeError):
                    patcher.validate_approved_source(source, False)

    def test_signed_executables_remain_unchanged(self):
        desktop = patcher.TESTED_SOURCE_BUILDS["26.917.6896.0"]["chatgpt_sha256"]
        chrome = "409115f942131f9420ad699010a0792e6c4e84ae054da832b398a7f8764a4394"
        with patch.object(patcher, "sha256_file", side_effect=[desktop, chrome, chrome, desktop]):
            self.assertIsNone(patcher.rebind_desktop_integrity(Path("stage"), Path("source")))
        with patch.object(patcher, "sha256_file", side_effect=[desktop, chrome, "changed"]):
            with self.assertRaisesRegex(RuntimeError, "byte-for-byte"):
                patcher.rebind_desktop_integrity(Path("stage"), Path("source"))

    def test_native_and_appshots_profile(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "package.json").write_text(json.dumps({"version": "26.917.51856"}))
            assets = root / "webview/assets"
            assets.mkdir(parents=True)
            (assets / "app-primary-fixture.js").touch()
            self.assertEqual(patcher._native_anchor(root, "oY sY jq Oq Fy yJ bJ Mq i r"), "S4 C4 q0 W0 IS F2 I2 J0 s o")
            verifier = (ROOT / "scripts/verify_windows_build.ps1").read_text()
            for anchor in ("function oY(e){return}", "function sY(e){return}",
                           "function yJ(e){if(process.platform===`win32`)return process.env.CODEX_MUX_HOME?[(0,i.join)(process.env.CODEX_MUX_HOME,Mq)]:[];"):
                self.assertIn(patcher._native_anchor(root, anchor), verifier)
            build = root / ".vite/build"
            build.mkdir(parents=True)
            main = build / "main-fixture.js"
            main.write_text('re=_?Jit(m):null,U=new Lit;P&&W.windowsCaptureNativeBridge==null&&(a.appshotsEnabled=!1),Le.setDesktopFeatureAvailability(a);')
            patcher.patch_windows_appshots_gate(root)
            self.assertFalse(patcher.verify_windows_appshots_contract(root)["defaultEnabled"])
            with self.assertRaises(RuntimeError):
                patcher.patch_windows_appshots_gate(root)


if __name__ == "__main__":
    unittest.main()
