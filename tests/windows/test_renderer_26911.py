"""Synthetic coverage of the exact September 11 desktop profile."""
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
import windows_renderer_26903 as renderer


class Renderer26911Tests(unittest.TestCase):
    def test_menu_and_usage_bindings_fail_closed(self):
        menu = '(0,Bq.jsx)(Tu,{leftIconAsset:bE,"aria-label":e,className:`opacity-50`,disabled:n,onSelect:r,children:p},`email`)'
        self.assertEqual(renderer.account_menu_item_alias(menu, latest=True), "Tu")
        for invalid in (menu * 2, menu.replace("Bq", "Gz"), "const Tu={};"):
            with self.assertRaises(RuntimeError):
                renderer.account_menu_item_alias(invalid, latest=True)
        usage = 'hu(i,uV,{defaultResetCreditsOpen:!0,initialAvailableCount:Ne,isRateLimitReached:!1})'
        self.assertEqual(renderer.usage_modal_opener_alias(usage, "uV"), "hu")
        with self.assertRaises(RuntimeError):
            renderer.usage_modal_opener_alias(usage * 2, "uV")

    def test_every_source_identity_field_is_pinned(self):
        fields = patcher.TESTED_SOURCE_BUILDS["26.911.7940.0"]
        patcher.validate_approved_source(SimpleNamespace(package_version="26.911.7940.0", **fields), False)
        for field in fields:
            with self.subTest(field=field):
                source = SimpleNamespace(package_version="26.911.7940.0", **fields)
                setattr(source, field, "unreviewed")
                with self.assertRaises(RuntimeError):
                    patcher.validate_approved_source(source, False)

    def test_signed_executables_and_runtime_remain_unchanged(self):
        desktop = patcher.TESTED_SOURCE_BUILDS["26.911.7940.0"]["chatgpt_sha256"]
        chrome = "2f43617a6e7dbdf2d784212cb1b98bebda0a6e9afb583d14d9c9bafd37b78a31"
        with patch.object(patcher, "sha256_file", side_effect=[desktop, chrome, chrome, desktop]):
            self.assertIsNone(patcher.rebind_desktop_integrity(Path("stage"), Path("source")))
        with patch.object(patcher, "sha256_file", side_effect=[desktop, chrome, "changed"]):
            with self.assertRaisesRegex(RuntimeError, "byte-for-byte"):
                patcher.rebind_desktop_integrity(Path("stage"), Path("source"))

    def test_native_isolation_and_appshots_profile(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "package.json").write_text(json.dumps({"version": "26.911.61220"}))
            assets = root / "webview/assets"
            assets.mkdir(parents=True)
            (assets / "app-primary-fixture.js").touch()
            self.assertEqual(patcher._native_anchor(root, "oY sY jq Oq Fy yJ bJ Mq i r"), "V$ H$ fQ lQ Kb e$ t$ pQ s o")
            verifier = (ROOT / "scripts/verify_windows_build.ps1").read_text()
            for anchor in ("function oY(e){return}", "function sY(e){return}",
                           "function yJ(e){if(process.platform===`win32`)return process.env.CODEX_MUX_HOME?[(0,i.join)(process.env.CODEX_MUX_HOME,Mq)]:[];"):
                self.assertIn(patcher._native_anchor(root, anchor), verifier)
            build = root / ".vite/build"
            build.mkdir(parents=True)
            main = build / "main-fixture.js"
            main.write_text('ae=v?M3e(h):null,oe=new x3e;I&&W.windowsCaptureNativeBridge==null&&(a.appshotsEnabled=!1),ze.setDesktopFeatureAvailability(a);')
            patcher.patch_windows_appshots_gate(root)
            contract = patcher.verify_windows_appshots_contract(root)
            self.assertFalse(contract["defaultEnabled"])
            self.assertNotIn("appshotsEnabled=!0", main.read_text())
            with self.assertRaises(RuntimeError):
                patcher.patch_windows_appshots_gate(root)


if __name__ == "__main__":
    unittest.main()
