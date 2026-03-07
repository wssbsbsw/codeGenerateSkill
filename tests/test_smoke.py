from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from codegen.parser import parse_config
from codegen.render import CodeRenderer
from codegen.writer import write_project


class CodegenSmokeTest(unittest.TestCase):
    def test_parse_render_and_write_sample(self) -> None:
        root = Path(__file__).resolve().parents[1]
        sample = root / "examples" / "sample.json"
        payload = json.loads(sample.read_text(encoding="utf-8"))

        project = parse_config(payload)
        renderer = CodeRenderer()
        files = renderer.render_project(project)

        self.assertIn("pom.xml", files)
        self.assertIn("src/main/resources/application.yml", files)
        self.assertIn("src/main/resources/init.sql", files)
        self.assertIn(
            f"src/main/java/{project.base_package_path}/controller/OrderController.java",
            files,
        )

        with tempfile.TemporaryDirectory() as tmp:
            root_dir = Path(tmp) / project.artifact_id
            write_project(root_dir, files, overwrite=True)
            self.assertTrue((root_dir / "pom.xml").exists())
            self.assertTrue((root_dir / "src/main/resources/application.yml").exists())
            self.assertTrue((root_dir / "src/main/resources/init.sql").exists())


if __name__ == "__main__":
    unittest.main()
