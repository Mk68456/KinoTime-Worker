import json
from pathlib import Path
import tempfile
import unittest

from tools.hosted_worker import load_config


class HostedConfigTests(unittest.TestCase):
    def test_positive_integer_and_hex_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "yougen"
            root.mkdir()
            (root / "provider.session").touch()
            path = root / "bridge.json"
            config = dict(profile="independent", user_id=99, api_id=123,
                          api_hash="Ab" * 16, target="@kinomobi_bot",
                          panel_url="https://example.com", panel_token="x" * 40, instance_id="a" * 32)
            path.write_text(json.dumps(config))
            self.assertEqual(load_config(directory)[0]["session"], str(root / "provider.session"))
            for field, invalid in (("profile", "desktop-copy"), ("user_id", True), ("user_id", 0),
                                   ("api_id", True), ("api_id", -1), ("api_id", 2**31),
                                   ("api_hash", "z" * 32), ("api_hash", "a" * 31)):
                with self.subTest(field=field, invalid=invalid):
                    path.write_text(json.dumps({**config, field: invalid}))
                    with self.assertRaises(ValueError):
                        load_config(directory)
