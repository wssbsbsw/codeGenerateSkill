from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .parser import ConfigError, load_config, parse_config
from .render import CodeRenderer
from .writer import write_project


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="codegen",
        description="Generate Spring Boot 2 + MyBatis-Plus CRUD project from JSON config",
    )
    parser.add_argument(
        "-c", "--config", required=True, help="Path to config JSON file"
    )
    parser.add_argument("-o", "--output", required=True, help="Output directory")
    parser.add_argument(
        "--force",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Overwrite existing files (default: true)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    config_path = Path(args.config).expanduser().resolve()
    if not config_path.exists():
        print(f"Config file not found: {config_path}", file=sys.stderr)
        return 2

    try:
        payload = load_config(config_path)
        project = parse_config(payload)
    except ConfigError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except Exception:  # pragma: no cover
        print("Failed to read config.", file=sys.stderr)
        return 1

    output_dir = Path(args.output).expanduser().resolve()
    project_root = output_dir / project.artifact_id

    try:
        renderer = CodeRenderer()
        files = renderer.render_project(project)
        write_project(project_root, files, overwrite=args.force)
    except Exception:  # pragma: no cover
        print("Failed to generate project.", file=sys.stderr)
        return 1

    print(f"Generated project: {project_root}")
    print(f"Files: {len(files)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
