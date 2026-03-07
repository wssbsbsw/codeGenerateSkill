from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock

from codegen import cli


class CliTest(unittest.TestCase):
    def test_load_failure_does_not_leak_internal_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            config_path.write_text("{}", encoding="utf-8")
            output_dir = Path(tmp) / "out"
            stderr = io.StringIO()

            with mock.patch(
                "codegen.cli.load_config", side_effect=RuntimeError("boom secret")
            ):
                with redirect_stderr(stderr):
                    exit_code = cli.main(
                        [
                            "-c",
                            str(config_path),
                            "-o",
                            str(output_dir),
                        ]
                    )

        self.assertEqual(exit_code, 1)
        self.assertIn("Failed to read config.", stderr.getvalue())
        self.assertNotIn("boom secret", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
