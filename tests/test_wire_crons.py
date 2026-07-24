import unittest
from unittest import mock

import importlib.util
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = importlib.util.spec_from_file_location(
    "wire_crons", os.path.join(REPO, "scripts", "wire-crons.py")
)
wire_crons = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(wire_crons)


class WireCronsProfileScopingTests(unittest.TestCase):
    def test_apply_uses_profile_flag(self):
        crons = wire_crons.get_crons("hr", "hr-manager")
        with mock.patch.object(wire_crons.subprocess, "run") as run:
            run.return_value = mock.Mock(returncode=0, stderr="", stdout="ok")
            applied, failed = wire_crons.apply_crons(crons, "local", "hr-manager")
        self.assertEqual(failed, 0)
        self.assertEqual(applied, len(crons))
        # Every created command must include the profile pre-parser flag
        for call in run.call_args_list:
            args = call.args[0]
            self.assertEqual(args[0], "hermes")
            self.assertEqual(args[1], "-p")
            self.assertEqual(args[2], "hr-manager")

    def test_apply_exits_nonzero_on_failure(self):
        crons = wire_crons.get_crons("base", "base")
        with mock.patch.object(wire_crons.subprocess, "run") as run:
            run.return_value = mock.Mock(returncode=1, stderr="boom", stdout="")
            applied, failed = wire_crons.apply_crons(crons, "local", "base")
        self.assertEqual(failed, len(crons))
        self.assertEqual(applied, 0)

    def test_prompt_path_uses_resolved_hermes_home(self):
        crons = wire_crons.get_crons("hr", "hr-manager")
        for c in crons:
            if "scrum.yaml" in c["prompt"]:
                self.assertIn(wire_crons.HERMES_HOME, c["prompt"])
                self.assertNotIn("~/.hermes", c["prompt"])

    def test_list_commands_are_profile_scoped(self):
        crons = wire_crons.get_crons("finance", "finance-manager")
        commands = wire_crons.format_cron_commands(crons, "local", "finance-manager")
        for cmd in commands:
            self.assertIn("hermes -p finance-manager cron create", cmd)


if __name__ == "__main__":
    unittest.main()
