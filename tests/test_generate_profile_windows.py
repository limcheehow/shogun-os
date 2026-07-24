import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "generate-profile.py"
spec = importlib.util.spec_from_file_location("generate_profile", MODULE_PATH)
generate_profile = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(generate_profile)


class GenerateProfileCompatibilityTests(unittest.TestCase):
    def test_project_manager_profile_type_targets_projects_source(self):
        meta = generate_profile.PROFILE_META["project-manager"]
        self.assertEqual(meta["gbrain_source"], "projects")
        self.assertEqual(meta["soul_snippet"], "project-soul")
        self.assertIn("project-soul", generate_profile.SOUL_SNIPPETS)
        self.assertIn("Gorobei", generate_profile.SOUL_SNIPPETS["project-soul"])

    def test_profile_type_default_gbrain_source_is_used(self):
        meta = generate_profile.PROFILE_META["hr"]
        source = generate_profile.resolve_gbrain_source(
            profile_name="hr-manager", meta=meta, explicit=None
        )
        self.assertEqual(source, "hr")

    def test_profile_env_persists_department_source_and_federated_read(self):
        env_text = generate_profile.generate_env_stub(
            "hr-manager", "hr", "hr"
        )
        self.assertIn("GBRAIN_SOURCE=hr", env_text)
        self.assertIn("GBRAIN_FEDERATED_READ=true", env_text)

    def test_active_default_model_is_loaded_for_generated_profiles(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / "config.yaml").write_text(
                "model:\n  default: gpt-test\n  provider: openai-codex\n"
                "providers: {}\nfallback_providers: []\n",
                encoding="utf-8",
            )
            settings = generate_profile.load_profile_runtime_settings(home)
            self.assertEqual(settings["model"]["default"], "gpt-test")
            self.assertEqual(settings["model"]["provider"], "openai-codex")

    def test_windows_gbrain_executable_falls_back_to_bun_install(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            executable = home / ".bun" / "bin" / "gbrain.exe"
            executable.parent.mkdir(parents=True)
            executable.write_bytes(b"")
            with patch.object(generate_profile.shutil, "which", return_value=None):
                result = generate_profile.resolve_gbrain_command(home)
            self.assertEqual(result, executable.as_posix())

    def test_rendered_config_uses_serve_and_active_model(self):
        template = """model: {}\nproviders: {}\nfallback_providers: []\nmcp_servers:\n  gbrain:\n    command: $gbrain_command\n    args: [serve]\n"""
        runtime = {
            "model": {"default": "gpt-test", "provider": "openai-codex"},
            "providers": {},
            "fallback_providers": [],
        }
        rendered = generate_profile.substitute_config(
            template, "hr-manager", "hr", runtime, "C:/tools/gbrain.exe"
        )
        self.assertIn("default: gpt-test", rendered)
        self.assertIn("provider: openai-codex", rendered)
        self.assertIn("command: C:/tools/gbrain.exe", rendered)
        self.assertIn("- serve", rendered)

    def test_force_regeneration_preserves_existing_env_secrets(self):
        existing = "SLACK_BOT_TOKEN=xoxb-secret\nGBRAIN_SOURCE=old\n"
        merged = generate_profile.merge_env_settings(existing, "hr")
        self.assertIn("SLACK_BOT_TOKEN=xoxb-secret", merged)
        self.assertIn("GBRAIN_SOURCE=hr", merged)
        self.assertIn("GBRAIN_FEDERATED_READ=true", merged)
        self.assertNotIn("GBRAIN_SOURCE=old", merged)

    def test_force_write_replaces_existing_profile_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "config.yaml"
            target.write_text("old\n", encoding="utf-8")

            written = generate_profile.write_file_safe(
                target, "new\n", dry_run=False, force=True
            )

            self.assertTrue(written)
            self.assertEqual(target.read_text(encoding="utf-8"), "new\n")

    def test_link_skills_copies_directory_when_windows_symlink_is_denied(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skills_dir = root / "repo-skills"
            source = skills_dir / "company-workflow"
            source.mkdir(parents=True)
            (source / "SKILL.md").write_text("# Company workflow\n", encoding="utf-8")
            profile_dir = root / "profile"

            with patch.object(generate_profile, "SKILLS_DIR", skills_dir), patch.object(
                generate_profile.os,
                "symlink",
                side_effect=OSError(1314, "A required privilege is not held by the client"),
            ):
                generate_profile.link_skills(profile_dir, ["company-workflow"], dry_run=False)

            copied = profile_dir / "skills" / "company-workflow" / "SKILL.md"
            self.assertTrue(copied.is_file())
            self.assertEqual(copied.read_text(encoding="utf-8"), "# Company workflow\n")


if __name__ == "__main__":
    unittest.main()
