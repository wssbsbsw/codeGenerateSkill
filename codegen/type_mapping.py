from __future__ import annotations

import re
from typing import Dict

DB_TO_JAVA: Dict[str, str] = {
    "bigint": "Long",
    "int": "Integer",
    "integer": "Integer",
    "tinyint": "Integer",
    "smallint": "Integer",
    "mediumint": "Integer",
    "varchar": "String",
    "char": "String",
    "text": "String",
    "longtext": "String",
    "datetime": "LocalDateTime",
    "timestamp": "LocalDateTime",
    "date": "LocalDate",
    "decimal": "BigDecimal",
    "numeric": "BigDecimal",
    "double": "Double",
    "float": "Double",
    "bit": "Boolean",
    "boolean": "Boolean",
    "json": "String",
}

JAVA_IMPORTS: Dict[str, str] = {
    "LocalDateTime": "java.time.LocalDateTime",
    "LocalDate": "java.time.LocalDate",
    "BigDecimal": "java.math.BigDecimal",
}


def normalize_db_type(db_type: str) -> str:
    normalized = db_type.strip().lower()
    normalized = re.sub(r"\(.*\)", "", normalized)
    normalized = normalized.split()[0]
    return normalized


def db_to_java(db_type: str) -> str:
    normalized = normalize_db_type(db_type)
    return DB_TO_JAVA.get(normalized, "String")


def db_type_length(db_type: str) -> int | None:
    match = re.search(r"\((\d+)(?:\s*,\s*\d+)?\)", db_type.strip())
    if not match:
        return None
    return int(match.group(1))


def java_import(java_type: str) -> str | None:
    return JAVA_IMPORTS.get(java_type)


def snake_to_camel(text: str) -> str:
    parts = [part for part in re.split(r"[_\-\s]+", text.strip()) if part]
    if not parts:
        return text
    if len(parts) == 1:
        part = parts[0]
        return part[:1].lower() + part[1:]
    head = parts[0].lower()
    tail = "".join(part.capitalize() for part in parts[1:])
    return f"{head}{tail}"


def snake_to_pascal(text: str) -> str:
    parts = re.split(r"[_\-\s]+", text.strip())
    return "".join(part.capitalize() for part in parts if part)
