from __future__ import annotations

import json
import unittest
from pathlib import Path

from codegen.parser import ConfigError, parse_config


class ParserTest(unittest.TestCase):
    def setUp(self) -> None:
        root = Path(__file__).resolve().parents[1]
        self.sample_payload = json.loads(
            (root / "examples" / "sample.json").read_text(encoding="utf-8")
        )
        self.student_class_payload = json.loads(
            (root / "examples" / "student_class_management.json").read_text(
                encoding="utf-8"
            )
        )

    def test_like_on_non_string_should_fail(self) -> None:
        broken = json.loads(json.dumps(self.sample_payload))
        broken["tables"][0]["queryableFields"] = [
            {"name": "status", "operator": "LIKE"}
        ]

        with self.assertRaises(ConfigError):
            parse_config(broken)

    def test_range_on_string_should_fail(self) -> None:
        broken = json.loads(json.dumps(self.sample_payload))
        broken["tables"][0]["queryableFields"] = [
            {"name": "username", "operator": "GE"}
        ]

        with self.assertRaises(ConfigError):
            parse_config(broken)

    def test_invalid_index_field_should_fail(self) -> None:
        broken = json.loads(json.dumps(self.student_class_payload))
        broken["tables"][1]["indexes"] = [{"columns": ["missing_column"]}]

        with self.assertRaises(ConfigError):
            parse_config(broken)

    def test_invalid_foreign_key_reference_should_fail(self) -> None:
        broken = json.loads(json.dumps(self.student_class_payload))
        broken["tables"][1]["foreignKeys"] = [
            {
                "columns": ["class_id"],
                "refTable": "classes",
                "refColumns": ["missing_id"],
            }
        ]

        with self.assertRaises(ConfigError):
            parse_config(broken)

    def test_invalid_sortable_field_should_fail(self) -> None:
        broken = json.loads(json.dumps(self.sample_payload))
        broken["tables"][1]["sortableFields"] = ["missing_field"]

        with self.assertRaises(ConfigError):
            parse_config(broken)

    def test_relation_filter_param_keeps_camel_case(self) -> None:
        project = parse_config(self.sample_payload)

        self.assertEqual(project.relations[0].filters[0].param_name, "orderNo")
        self.assertEqual(project.relations[0].filters[1].param_name, "username")

    def test_parse_explicit_indexes_foreign_keys_and_sorting(self) -> None:
        project = parse_config(self.student_class_payload)
        classes_table = next(item for item in project.tables if item.name == "classes")
        students_table = next(
            item for item in project.tables if item.name == "students"
        )
        relation = project.relations[0]

        self.assertEqual(project.datasource["databaseName"], "student_class_demo")
        self.assertTrue(classes_table.infer_indexes)
        self.assertTrue(students_table.infer_foreign_keys)
        self.assertGreaterEqual(len(students_table.indexes), 1)
        self.assertGreaterEqual(len(students_table.foreign_keys), 1)
        self.assertEqual(students_table.sortable_fields[0].request_name, "studentName")
        self.assertEqual(relation.sortable_fields[0].request_name, "studentName")


if __name__ == "__main__":
    unittest.main()
