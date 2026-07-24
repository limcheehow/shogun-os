import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "init-gbrain.sh"


class InitGbrainScriptTests(unittest.TestCase):
    def test_initializer_applies_shared_federation(self):
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('"$GBRAIN_BIN" sources federate shared', text)

    def test_initializer_isolates_legacy_default_source(self):
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('"$GBRAIN_BIN" sources unfederate default', text)


if __name__ == "__main__":
    unittest.main()
