"""Fail-closed September 15 source profile, with no proprietary fixtures."""
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
import windows_renderer_26915 as renderer


class Renderer26915Tests(unittest.TestCase):
    def test_menu_and_usage_bindings_fail_closed(self):
        menu = '(0,d6.jsx)(QB,{leftIconAsset:Hee,"aria-label":e,className:`opacity-50`,disabled:n,onSelect:r,children:h},`email`)'
        self.assertEqual(renderer.account_menu_item_alias(menu), "QB")
        for invalid in (menu * 2, menu.replace("d6", "Gz"), "const QB={};"):
            with self.assertRaises(RuntimeError):
                renderer.account_menu_item_alias(invalid)
        usage = 'Wj(o,$ms,{defaultResetCreditsOpen:!0,initialAvailableCount:Xe,isRateLimitReached:!1})'
        self.assertEqual(renderer.usage_modal_opener_alias(usage, "$ms"), "Wj")
        with self.assertRaises(RuntimeError):
            renderer.usage_modal_opener_alias(usage * 2, "$ms")

    def test_remapping_is_single_pass_and_exact(self):
        self.assertEqual(renderer.remap("Lo(Q);$n(sr);", {"Lo":"Q", "Q":"$", "$n":"ju", "sr":"il"}), "Q($);ju(il);")
        with self.assertRaises(RuntimeError):
            renderer.remap("someName", {"Name":"changed"})
        with self.assertRaises(RuntimeError):
            renderer.replace("anchor anchor", "anchor", "replacement")

    def test_every_source_identity_field_is_pinned(self):
        fields = patcher.TESTED_SOURCE_BUILDS["26.915.4065.0"]
        patcher.validate_approved_source(SimpleNamespace(package_version="26.915.4065.0", **fields), False)
        for field in fields:
            with self.subTest(field=field):
                source = SimpleNamespace(package_version="26.915.4065.0", **fields)
                setattr(source, field, "unreviewed")
                with self.assertRaises(RuntimeError):
                    patcher.validate_approved_source(source, False)

    def test_signed_executables_and_runtime_remain_unchanged(self):
        desktop = patcher.TESTED_SOURCE_BUILDS["26.915.4065.0"]["chatgpt_sha256"]
        chrome = "e60c43295545cce24a4cfd65b2ba831cdcdc173cbb705cc2b71326a981f51a67"
        with patch.object(patcher, "sha256_file", side_effect=[desktop, chrome, chrome, desktop]):
            self.assertIsNone(patcher.rebind_desktop_integrity(Path("stage"), Path("source")))
        with patch.object(patcher, "sha256_file", side_effect=[desktop, chrome, "changed"]):
            with self.assertRaisesRegex(RuntimeError, "byte-for-byte"):
                patcher.rebind_desktop_integrity(Path("stage"), Path("source"))

    def test_native_isolation_and_appshots_profile(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "package.json").write_text(json.dumps({"version": "26.915.31945"}))
            assets = root / "webview/assets"
            assets.mkdir(parents=True)
            (assets / "app-primary-fixture.js").touch()
            self.assertEqual(patcher._native_anchor(root, "oY sY jq Oq Fy yJ bJ Mq i r"), "V2 H2 f0 l0 qS e2 t2 p0 s o")
            verifier = (ROOT / "scripts/verify_windows_build.ps1").read_text()
            for anchor in ("function oY(e){return}", "function sY(e){return}",
                           "function yJ(e){if(process.platform===`win32`)return process.env.CODEX_MUX_HOME?[(0,i.join)(process.env.CODEX_MUX_HOME,Mq)]:[];"):
                self.assertIn(patcher._native_anchor(root, anchor), verifier)
            build = root / ".vite/build"
            build.mkdir(parents=True)
            main = build / "main-fixture.js"
            main.write_text('ie=_?yit(m):null,H=new cit;P&&U.windowsCaptureNativeBridge==null&&(a.appshotsEnabled=!1),K.setDesktopFeatureAvailability(a);')
            patcher.patch_windows_appshots_gate(root)
            self.assertFalse(patcher.verify_windows_appshots_contract(root)["defaultEnabled"])
            self.assertNotIn("appshotsEnabled=!0", main.read_text())
            with self.assertRaises(RuntimeError):
                patcher.patch_windows_appshots_gate(root)

    def test_bootstrap_and_runtime_paths_preserve_windows_cli_override(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "package.json").write_text(json.dumps({"version":"26.915.31945"}))
            build = root / ".vite/build"
            build.mkdir(parents=True)
            bootstrap = build / "bootstrap-fixture.js"
            original = ('CODEX_ELECTRON_USER_DATA_PATH;CODEX_ELECTRON_USER_DATA_PATH;'
                        'o.app.setName(n.Eo(_j)),o.app.setPath(`userData`,pk({appDataPath:o.app.getPath(`appData`),buildFlavor:_j,env:process.env}));'
                        'process.platform===`win32`&&(delete process.env.CODEX_WINDOWS_REGISTERED_CORE,delete process.env.CODEX_WINDOWS_SANDBOX_PACKAGE_FAMILY,o.app.setAppUserModelId(Ut(_j)));'
                        'enableUpdater:j.shouldIncludeUpdater(d,process.platform,process.env);'
                        'if(await i.initialize(),a&&c&&RA(),a||s){};await i.startUpdaterAfterStartupFailure(),await mj(e);'
                        'function w(){if(process.platform===`win32`)return;e.setAsDefaultProtocolClient(t)};'
                        '!process.env.CODEX_CLI_PATH?.trim();'
                        'if(t===`win32`){let e=n.LOCALAPPDATA??(0,u.join)(r,`AppData`,`Local`);return(0,u.join)(e,`Codex`,`Logs`)}')
            bootstrap.write_text(original)
            (build / "worker.js").write_text('if(t===`win32`){let e=n.LOCALAPPDATA??(0,h.join)(r,`AppData`,`Local`);return(0,h.join)(e,`Codex`,`Logs`)}')
            (build / "src-fixture.js").write_text('function sY(e){let t=process.env.LOCALAPPDATA??(0,s.join)((0,o.homedir)(),`AppData`,`Local`);return(0,s.join)(t,...e)}')
            patcher.verify_windows_integration_isolation(root)
            patcher.patch_windows_bootstrap(root)
            patcher.patch_windows_runtime_paths(root)
            result = bootstrap.read_text()
            self.assertIn('enableUpdater:!1', result)
            self.assertIn('if(a&&c&&RA(),a||s)', result)
            self.assertIn('!process.env.CODEX_CLI_PATH?.trim()', result)
            self.assertIn('delete process.env.CODEX_WINDOWS_REGISTERED_CORE', result)
            self.assertNotIn('await i.initialize()', result)
            self.assertNotIn('await i.startUpdaterAfterStartupFailure()', result)
            self.assertIn('com.openai.codex.subscription-router', result)
            for name in ('bootstrap-fixture.js', 'worker.js', 'src-fixture.js'):
                self.assertIn('process.env.CODEX_MUX_HOME', (build/name).read_text())
            with self.assertRaises(RuntimeError):
                patcher.patch_windows_bootstrap(root)


if __name__ == "__main__":
    unittest.main()
