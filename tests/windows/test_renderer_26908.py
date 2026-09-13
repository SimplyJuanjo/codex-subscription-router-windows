"""Offline regressions for the 26.908.40834 renderer and Appshots gates."""
import json
from pathlib import Path
import sys
import tempfile
import unittest.mock
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import patch_windows_app as patcher
import windows_renderer_26903 as renderer


class Renderer26908Tests(unittest.TestCase):
    NATIVE = '(0,Gz.jsx)(kg,{leftIconAsset:lE,"aria-label":e,className:`opacity-50`,disabled:n,onSelect:r,children:p},`email`)'

    def test_native_component_binding(self):
        self.assertEqual(renderer.account_menu_item_alias(self.NATIVE, modern=True), "kg")

    def test_ambiguous_or_old_binding_rejected(self):
        for text in (self.NATIVE * 2, "const kg = {};", self.NATIVE.replace("leftIconAsset", "LeftIcon")):
            with self.assertRaises(RuntimeError):
                renderer.account_menu_item_alias(text, modern=True)

    def test_unknown_version_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "package.json").write_text(json.dumps({"version": "26.999.1"}))
            with self.assertRaisesRegex(RuntimeError, "unsupported split renderer"):
                renderer.patch_renderer(root, "test-only", 55000)

    def test_exact_source_fingerprint_required(self):
        expected = patcher.TESTED_SOURCE_BUILDS["26.908.4834.0"]
        source = SimpleNamespace(package_version="26.908.4834.0", **expected)
        patcher.validate_approved_source(source, False)
        source.asar_sha256 = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "SHA-256"):
            patcher.validate_approved_source(source, False)

    def test_signed_runtime_is_not_rebound(self):
        desktop = patcher.TESTED_SOURCE_BUILDS["26.908.4834.0"]["chatgpt_sha256"]
        chrome = "eff6dbe82270819bc196360ee616cb6c324544dd8266dec46ac8e25d330d60db"
        with unittest.mock.patch.object(patcher, "sha256_file", side_effect=[desktop, chrome, chrome, desktop]):
            self.assertIsNone(patcher.rebind_desktop_integrity(Path("stage"), Path("source")))
        with unittest.mock.patch.object(patcher, "sha256_file", side_effect=[desktop, chrome, "changed"]):
            with self.assertRaisesRegex(RuntimeError, "byte-for-byte"):
                patcher.rebind_desktop_integrity(Path("stage"), Path("source"))

    def test_native_isolation_aliases_and_verifier_stay_in_sync(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "package.json").write_text(json.dumps({"version": "26.908.40834"}))
            assets = root / "webview/assets"
            assets.mkdir(parents=True)
            (assets / "app-primary-fixture.js").touch()
            self.assertEqual(patcher._native_anchor(root, "oY sY jq Oq Fy yJ bJ Mq"), "GQ KQ gZ pZ Bb iQ aQ _Z")
            verifier = (ROOT / "scripts/verify_windows_build.ps1").read_text()
            for anchor in ("function oY(e){return}", "function sY(e){return}",
                           "function yJ(e){if(process.platform===`win32`)return process.env.CODEX_MUX_HOME?[(0,i.join)(process.env.CODEX_MUX_HOME,Mq)]:[];"):
                self.assertIn(patcher._native_anchor(root, anchor), verifier)

    def test_appshots_opt_in_preserves_upstream_availability(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "package.json").write_text(json.dumps({"version": "26.908.40834"}))
            assets = root / "webview/assets"
            assets.mkdir(parents=True)
            (assets / "app-primary-fixture.js").touch()
            build = root / ".vite/build"
            build.mkdir(parents=True)
            main = build / "main-fixture.js"
            main.write_text('ie=y?g4e(g):null,U=new a4e;F&&K.windowsCaptureNativeBridge==null&&(a.appshotsEnabled=!1),Ie.setDesktopFeatureAvailability(a);')
            patcher.patch_windows_appshots_gate(root)
            contract = patcher.verify_windows_appshots_contract(root)
            self.assertFalse(contract["defaultEnabled"])
            text = main.read_text()
            self.assertNotIn("appshotsEnabled=!0", text)
            self.assertIn('!(process.env.CODEX_ROUTER_ENABLE_APPSHOTS==="1")', text)
            with self.assertRaises(RuntimeError):
                patcher.patch_windows_appshots_gate(root)


if __name__ == "__main__":
    unittest.main()
