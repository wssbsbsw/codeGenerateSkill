from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import re
from typing import Dict, Iterable, List, cast

from jinja2 import Environment, FileSystemLoader

from .ir import (
    ForeignKeyIR,
    IndexIR,
    ProjectIR,
    QueryableFieldIR,
    RelationFilterIR,
    RelationIR,
    SortableFieldIR,
    TableIR,
)
from .type_mapping import db_type_length, java_import, snake_to_camel

TEMPLATE_ROOT = Path(__file__).resolve().parent / "templates"

ANNOTATION_IMPORTS = {
    "Max": "javax.validation.constraints.Max",
    "Min": "javax.validation.constraints.Min",
    "NotBlank": "javax.validation.constraints.NotBlank",
    "NotNull": "javax.validation.constraints.NotNull",
    "Pattern": "javax.validation.constraints.Pattern",
    "Size": "javax.validation.constraints.Size",
}


class CodeRenderer:
    def __init__(self) -> None:
        self.env = Environment(
            loader=FileSystemLoader(str(TEMPLATE_ROOT)),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
        )

    def render_project(self, project: ProjectIR) -> Dict[str, str]:
        files: Dict[str, str] = {}
        java_root = f"src/main/java/{project.base_package_path}"
        resource_root = "src/main/resources"

        base_context = {
            "project": project,
            "package": project.base_package,
            "datasource_placeholders": self._datasource_placeholders(project),
            "insert_fill_fields": self._auto_fill_fields(project, mode="insert"),
            "update_fill_fields": self._auto_fill_fields(project, mode="update"),
            "auto_fill_imports": self._auto_fill_imports(project),
        }

        files["pom.xml"] = self._render("pom.xml.j2", **base_context)
        files[f"{resource_root}/application.yml"] = self._render(
            "resources/application.yml.j2", **base_context
        )
        files[f"{resource_root}/init.sql"] = self._render_init_sql(project)
        files[f"{java_root}/{project.application_class_name}.java"] = self._render(
            "app/Application.java.j2", **base_context
        )
        files[f"{java_root}/config/MybatisPlusConfig.java"] = self._render(
            "config/MybatisPlusConfig.java.j2", **base_context
        )
        files[f"{java_root}/config/MybatisMetaObjectHandler.java"] = self._render(
            "config/MybatisMetaObjectHandler.java.j2", **base_context
        )
        files[f"{java_root}/common/Result.java"] = self._render(
            "common/Result.java.j2", **base_context
        )
        files[f"{java_root}/common/ErrorCode.java"] = self._render(
            "common/ErrorCode.java.j2", **base_context
        )
        files[f"{java_root}/common/PageResult.java"] = self._render(
            "common/PageResult.java.j2", **base_context
        )
        files[f"{java_root}/exception/BizException.java"] = self._render(
            "exception/BizException.java.j2", **base_context
        )
        files[f"{java_root}/exception/NotFoundException.java"] = self._render(
            "exception/NotFoundException.java.j2", **base_context
        )
        files[f"{java_root}/exception/GlobalExceptionHandler.java"] = self._render(
            "common/GlobalExceptionHandler.java.j2", **base_context
        )

        relation_groups = self._group_relations(project.relations)

        for table in project.tables:
            table_relations = relation_groups.get(table.name, [])
            create_dto_fields = self._request_dto_fields(table, mode="create")
            update_dto_fields = self._request_dto_fields(table, mode="update")
            query_dto_fields = self._query_dto_fields(
                table.queryable_fields,
                table.sortable_fields,
            )
            sortable_fields = [
                self._sortable_field_context(item) for item in table.sortable_fields
            ]
            table_context = {
                **base_context,
                "table": table,
                "table_relations": table_relations,
                "entity_imports": self._java_imports(
                    field.java_type for field in table.fields
                ),
                "query_fields": self._query_field_contexts(table.queryable_fields),
                "sortable_fields": sortable_fields,
                "has_sorting": bool(sortable_fields),
                "relation_methods": [
                    {
                        "method_name": relation.method_name,
                        "dto_name": relation.dto_name,
                        "query_name": relation.query_name,
                        "endpoint_name": relation.name,
                    }
                    for relation in table_relations
                ],
                "mapper_relation_context": [
                    self._relation_mapper_context(relation)
                    for relation in table_relations
                ],
            }

            files[f"{java_root}/entity/{table.entity_name}.java"] = self._render(
                "entity/Entity.java.j2", **table_context
            )
            files[f"{java_root}/mapper/{table.mapper_name}.java"] = self._render(
                "mapper/Mapper.java.j2", **table_context
            )
            files[f"{resource_root}/mapper/{table.mapper_name}.xml"] = self._render(
                "mapper/Mapper.xml.j2", **table_context
            )
            files[f"{java_root}/service/{table.service_name}.java"] = self._render(
                "service/Service.java.j2", **table_context
            )
            files[f"{java_root}/service/impl/{table.service_impl_name}.java"] = (
                self._render("service_impl/ServiceImpl.java.j2", **table_context)
            )
            files[f"{java_root}/controller/{table.controller_name}.java"] = (
                self._render("controller/Controller.java.j2", **table_context)
            )
            files[f"{java_root}/dto/{table.create_dto_name}.java"] = self._render(
                "dto/CreateRequest.java.j2",
                **table_context,
                dto_name=table.create_dto_name,
                dto_fields=create_dto_fields,
                dto_imports=self._dto_imports(create_dto_fields),
            )
            files[f"{java_root}/dto/{table.update_dto_name}.java"] = self._render(
                "dto/UpdateRequest.java.j2",
                **table_context,
                dto_name=table.update_dto_name,
                dto_fields=update_dto_fields,
                dto_imports=self._dto_imports(update_dto_fields),
            )
            files[f"{java_root}/dto/{table.query_dto_name}.java"] = self._render(
                "dto/QueryRequest.java.j2",
                **table_context,
                dto_name=table.query_dto_name,
                dto_fields=query_dto_fields,
                dto_imports=self._dto_imports(query_dto_fields),
            )

        for relation in project.relations:
            relation_query_fields = self._relation_query_dto_fields(relation)
            relation_context = {
                **base_context,
                "relation": relation,
                "dto_imports": self._java_imports(
                    item.java_type for item in relation.select_items
                ),
                "query_imports": self._dto_imports(relation_query_fields),
                "query_fields": relation_query_fields,
            }
            files[f"{java_root}/dto/{relation.dto_name}.java"] = self._render(
                "dto/RelationDto.java.j2", **relation_context
            )
            files[f"{java_root}/dto/{relation.query_name}.java"] = self._render(
                "dto/RelationQuery.java.j2", **relation_context
            )

        return files

    def _render(self, template_name: str, **context: object) -> str:
        template = self.env.get_template(template_name)
        return template.render(**context)

    def _datasource_placeholders(self, project: ProjectIR) -> Dict[str, str]:
        datasource = project.datasource
        return {
            "url": self._env_placeholder("DB_URL", datasource["url"]),
            "username": self._env_placeholder("DB_USERNAME", datasource["username"]),
            "password": self._env_placeholder("DB_PASSWORD", datasource["password"]),
            "driver_class_name": self._env_placeholder(
                "DB_DRIVER_CLASS_NAME",
                datasource["driverClassName"],
            ),
        }

    def _env_placeholder(self, env_name: str, default_value: str) -> str:
        escaped_default = str(default_value).replace('"', '\\"')
        return f"${{{env_name}:{escaped_default}}}"

    def _request_dto_fields(self, table: TableIR, mode: str) -> List[Dict[str, object]]:
        fields: List[Dict[str, object]] = []
        for field in table.fields:
            if field.is_primary or field.logic_delete or field.auto_fill:
                continue

            annotations: List[str] = []
            annotation_types: List[str] = []
            field_name = field.property_name
            max_length = db_type_length(field.db_type)

            if mode == "create" and not field.nullable:
                if field.java_type == "String":
                    annotations.append(
                        f'@NotBlank(message = "{field_name} must not be blank")'
                    )
                    annotation_types.append("NotBlank")
                else:
                    annotations.append(
                        f'@NotNull(message = "{field_name} must not be null")'
                    )
                    annotation_types.append("NotNull")

            if field.java_type == "String" and max_length is not None:
                annotations.append(
                    f'@Size(max = {max_length}, message = "{field_name} length must be <= {max_length}")'
                )
                annotation_types.append("Size")

            fields.append(
                {
                    "java_type": field.java_type,
                    "property_name": field.property_name,
                    "annotations": annotations,
                    "annotation_types": annotation_types,
                    "default_value": None,
                }
            )

        return fields

    def _query_dto_fields(
        self,
        queryable_fields: Iterable[QueryableFieldIR | RelationFilterIR],
        sortable_fields: Iterable[SortableFieldIR],
    ) -> List[Dict[str, object]]:
        sortable_field_list = list(sortable_fields)
        fields = [
            {
                "java_type": "Long",
                "property_name": "page",
                "annotations": ['@Min(value = 1, message = "page must be >= 1")'],
                "annotation_types": ["Min"],
                "default_value": "1L",
            },
            {
                "java_type": "Long",
                "property_name": "size",
                "annotations": [
                    '@Min(value = 1, message = "size must be >= 1")',
                    '@Max(value = 200, message = "size must be <= 200")',
                ],
                "annotation_types": ["Min", "Max"],
                "default_value": "20L",
            },
        ]

        for item in queryable_fields:
            fields.append(
                {
                    "java_type": item.java_type,
                    "property_name": item.property_name,
                    "annotations": [],
                    "annotation_types": [],
                    "default_value": None,
                }
            )

        if sortable_field_list:
            fields.append(
                {
                    "java_type": "String",
                    "property_name": "sortBy",
                    "annotations": [],
                    "annotation_types": [],
                    "default_value": None,
                }
            )
            fields.append(
                {
                    "java_type": "String",
                    "property_name": "sortDir",
                    "annotations": [
                        '@Pattern(regexp = "ASC|DESC|asc|desc", message = "sortDir must be ASC or DESC")'
                    ],
                    "annotation_types": ["Pattern"],
                    "default_value": None,
                }
            )

        return fields

    def _relation_query_dto_fields(
        self, relation: RelationIR
    ) -> List[Dict[str, object]]:
        fields = self._query_dto_fields([], relation.sortable_fields)
        insert_at = 2
        for item in relation.filters:
            fields.insert(
                insert_at,
                {
                    "java_type": item.java_type,
                    "property_name": item.param_name,
                    "annotations": [],
                    "annotation_types": [],
                    "default_value": None,
                },
            )
            insert_at += 1
        return fields

    def _dto_imports(self, dto_fields: Iterable[Dict[str, object]]) -> List[str]:
        imports = set()
        for field in dto_fields:
            imported = java_import(str(field["java_type"]))
            if imported:
                imports.add(imported)
            annotation_types = cast(List[str], field["annotation_types"])
            for annotation_type in annotation_types:
                imported = ANNOTATION_IMPORTS.get(str(annotation_type))
                if imported:
                    imports.add(imported)
        return sorted(imports)

    def _query_field_contexts(
        self,
        queryable_fields: Iterable[QueryableFieldIR],
    ) -> List[Dict[str, object]]:
        fields: List[Dict[str, object]] = []
        for item in queryable_fields:
            fields.append(
                {
                    "property_name": item.property_name,
                    "column_name": item.column_name,
                    "java_type": item.java_type,
                    "operator": item.operator,
                    "is_string": item.java_type == "String",
                    "method_suffix": item.property_name[:1].upper()
                    + item.property_name[1:],
                }
            )
        return fields

    def _sortable_field_context(
        self, sortable_field: SortableFieldIR
    ) -> Dict[str, object]:
        return {
            "request_name": sortable_field.request_name,
            "column_name": sortable_field.column_name,
            "property_name": sortable_field.property_name,
            "java_type": sortable_field.java_type,
            "method_suffix": sortable_field.property_name[:1].upper()
            + sortable_field.property_name[1:],
            "side": sortable_field.side,
        }

    def _auto_fill_imports(self, project: ProjectIR) -> List[str]:
        imports = set()
        for field in self._auto_fill_fields(project, mode="insert"):
            imported = java_import(str(field["java_type"]))
            if imported:
                imports.add(imported)
        for field in self._auto_fill_fields(project, mode="update"):
            imported = java_import(str(field["java_type"]))
            if imported:
                imports.add(imported)
        return sorted(imports)

    def _auto_fill_fields(self, project: ProjectIR, mode: str) -> List[Dict[str, str]]:
        fields: List[Dict[str, str]] = []
        seen_keys: set[tuple[str, str, str]] = set()
        for table in project.tables:
            for field in table.fields:
                if not field.auto_fill:
                    continue
                if mode == "insert" and field.auto_fill not in {
                    "INSERT",
                    "INSERT_UPDATE",
                }:
                    continue
                if mode == "update" and field.auto_fill not in {
                    "UPDATE",
                    "INSERT_UPDATE",
                }:
                    continue

                value_expression = self._auto_fill_value_expression(field.java_type)
                if value_expression is None:
                    continue

                key = (field.property_name, field.java_type, mode)
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                fields.append(
                    {
                        "property_name": field.property_name,
                        "java_type": field.java_type,
                        "value_expression": value_expression,
                    }
                )
        return fields

    def _auto_fill_value_expression(self, java_type: str) -> str | None:
        if java_type == "LocalDateTime":
            return "LocalDateTime.now()"
        if java_type == "LocalDate":
            return "LocalDate.now()"
        return None

    def _render_init_sql(self, project: ProjectIR) -> str:
        sections: List[str] = []
        database_name = project.datasource.get(
            "databaseName"
        ) or self._database_name_from_url(project.datasource.get("url", ""))
        if database_name:
            sections.append(
                f"CREATE DATABASE IF NOT EXISTS `{database_name}` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
            )
            sections.append(f"USE `{database_name}`;")

        for table in project.tables:
            column_lines: List[str] = []
            for field in table.fields:
                parts = [f"`{field.column_name}`", field.db_type]
                if not field.nullable:
                    parts.append("NOT NULL")
                if field.is_primary and field.id_type == "AUTO":
                    parts.append("AUTO_INCREMENT")
                if field.comment:
                    escaped_comment = field.comment.replace("'", "''")
                    parts.append(f"COMMENT '{escaped_comment}'")
                column_lines.append("  " + " ".join(parts))

            column_lines.append(f"  PRIMARY KEY (`{table.primary_key_column}`)")
            for field in table.fields:
                if field.unique:
                    column_lines.append(
                        f"  UNIQUE KEY `uk_{table.name}_{field.column_name}` (`{field.column_name}`)"
                    )
            for index_line in self._index_lines(project, table):
                column_lines.append(index_line)
            for foreign_key_line in self._foreign_key_lines(project, table):
                column_lines.append(foreign_key_line)

            suffix = " ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"
            if table.comment:
                escaped_table_comment = table.comment.replace("'", "''")
                suffix += f" COMMENT='{escaped_table_comment}'"

            body = ",\n".join(column_lines)
            sections.append(
                f"CREATE TABLE IF NOT EXISTS `{table.name}` (\n{body}\n){suffix};"
            )

            if table.seed_data:
                sections.append(self._render_seed_data(table))

        return "\n\n".join(sections) + "\n"

    def _render_seed_data(self, table: TableIR) -> str:
        rows: List[str] = []
        ordered_columns = [field.column_name for field in table.fields]
        for seed_row in table.seed_data:
            columns = [
                column_name
                for column_name in ordered_columns
                if column_name in seed_row
            ]
            if not columns:
                continue
            rendered_columns = ", ".join(f"`{column_name}`" for column_name in columns)
            rendered_values = ", ".join(
                self._sql_literal(seed_row[column_name]) for column_name in columns
            )
            rows.append(
                f"INSERT INTO `{table.name}` ({rendered_columns}) VALUES ({rendered_values});"
            )
        return "\n".join(rows)

    def _sql_literal(self, value: object) -> str:
        if value is None:
            return "NULL"
        if isinstance(value, bool):
            return "1" if value else "0"
        if isinstance(value, (int, float)):
            return str(value)
        escaped = str(value).replace("'", "''")
        return f"'{escaped}'"

    def _database_name_from_url(self, datasource_url: str) -> str | None:
        match = re.search(r"jdbc:[^:]+://[^/]+/([^?;]+)", datasource_url)
        if not match:
            return None
        database_name = match.group(1).strip()
        return database_name or None

    def _index_lines(self, project: ProjectIR, table: TableIR) -> List[str]:
        lines: List[str] = []
        for index in self._merged_indexes(project, table):
            index_columns = ", ".join(
                f"`{column_name}`" for column_name in index.columns
            )
            prefix = "UNIQUE KEY" if index.unique else "KEY"
            lines.append(f"  {prefix} `{index.name}` ({index_columns})")
        return lines

    def _foreign_key_lines(self, project: ProjectIR, table: TableIR) -> List[str]:
        lines: List[str] = []
        for foreign_key in self._merged_foreign_keys(project, table):
            left_columns = ", ".join(
                f"`{column_name}`" for column_name in foreign_key.columns
            )
            right_columns = ", ".join(
                f"`{column_name}`" for column_name in foreign_key.ref_columns
            )
            line = (
                "  CONSTRAINT "
                f"`{foreign_key.name}` FOREIGN KEY ({left_columns}) REFERENCES "
                f"`{foreign_key.ref_table}` ({right_columns})"
            )
            if foreign_key.on_delete:
                line += f" ON DELETE {foreign_key.on_delete}"
            if foreign_key.on_update:
                line += f" ON UPDATE {foreign_key.on_update}"
            lines.append(line)

        return lines

    def _merged_indexes(self, project: ProjectIR, table: TableIR) -> List[IndexIR]:
        merged: List[IndexIR] = []
        seen_names: set[str] = set()
        seen_signatures: set[tuple[bool, tuple[str, ...]]] = {
            (True, (field.column_name,)) for field in table.fields if field.unique
        }
        seen_signatures.add((False, (table.primary_key_column,)))

        for index in [*table.indexes, *self._inferred_indexes(project, table)]:
            signature = (index.unique, tuple(index.columns))
            if index.name in seen_names or signature in seen_signatures:
                continue
            seen_names.add(index.name)
            seen_signatures.add(signature)
            merged.append(index)

        return merged

    def _inferred_indexes(self, project: ProjectIR, table: TableIR) -> List[IndexIR]:
        if not table.infer_indexes:
            return []

        table_fields = {field.column_name: field for field in table.fields}
        indexed_columns: List[str] = []

        def add_index(column_name: str) -> None:
            field = table_fields.get(column_name)
            if field is None or field.is_primary or field.unique:
                return
            if column_name not in indexed_columns:
                indexed_columns.append(column_name)

        for queryable_field in table.queryable_fields:
            add_index(queryable_field.column_name)

        for relation in project.relations:
            if relation.left_table == table.name:
                for on_clause in relation.on_clauses:
                    add_index(on_clause.left_column)
            if relation.right_table == table.name:
                for on_clause in relation.on_clauses:
                    add_index(on_clause.right_column)
            for relation_filter in relation.filters:
                if relation.left_table == table.name and relation_filter.side == "left":
                    add_index(relation_filter.column_name)
                if (
                    relation.right_table == table.name
                    and relation_filter.side == "right"
                ):
                    add_index(relation_filter.column_name)

        return [
            IndexIR(
                name=f"idx_{table.name}_{column_name}",
                columns=[column_name],
                inferred=True,
            )
            for column_name in indexed_columns
        ]

    def _merged_foreign_keys(
        self,
        project: ProjectIR,
        table: TableIR,
    ) -> List[ForeignKeyIR]:
        merged: List[ForeignKeyIR] = []
        seen_names: set[str] = set()
        seen_signatures: set[tuple[tuple[str, ...], str, tuple[str, ...]]] = set()

        for foreign_key in [
            *table.foreign_keys,
            *self._inferred_foreign_keys(project, table),
        ]:
            signature = (
                tuple(foreign_key.columns),
                foreign_key.ref_table,
                tuple(foreign_key.ref_columns),
            )
            if foreign_key.name in seen_names or signature in seen_signatures:
                continue
            seen_names.add(foreign_key.name)
            seen_signatures.add(signature)
            merged.append(foreign_key)

        return merged

    def _inferred_foreign_keys(
        self,
        project: ProjectIR,
        table: TableIR,
    ) -> List[ForeignKeyIR]:
        if not table.infer_foreign_keys:
            return []

        foreign_keys: List[ForeignKeyIR] = []
        for relation in project.relations:
            if relation.left_table != table.name or not relation.on_clauses:
                continue

            constraint_suffix = re.sub(r"[^a-zA-Z0-9_]+", "_", relation.name).strip("_")
            if not constraint_suffix:
                constraint_suffix = f"{relation.left_table}_{relation.right_table}"

            foreign_keys.append(
                ForeignKeyIR(
                    name=f"fk_{relation.left_table}_{relation.right_table}_{constraint_suffix}",
                    columns=[item.left_column for item in relation.on_clauses],
                    ref_table=relation.right_table,
                    ref_columns=[item.right_column for item in relation.on_clauses],
                    on_delete="RESTRICT",
                    on_update="RESTRICT",
                    inferred=True,
                )
            )

        return foreign_keys

    def _java_imports(self, java_types: Iterable[str]) -> List[str]:
        imports = set()
        for java_type in java_types:
            imported = java_import(java_type)
            if imported:
                imports.add(imported)
        return sorted(imports)

    def _group_relations(
        self, relations: List[RelationIR]
    ) -> Dict[str, List[RelationIR]]:
        grouped: Dict[str, List[RelationIR]] = defaultdict(list)
        for relation in relations:
            grouped[relation.left_table].append(relation)
        return grouped

    def _relation_mapper_context(self, relation: RelationIR) -> Dict[str, object]:
        select_sql: List[str] = []
        for item in relation.select_items:
            alias = "l" if item.side == "left" else "r"
            select_sql.append(f"{alias}.{item.column_name} AS {item.alias}")

        on_sql = [
            f"l.{item.left_column} = r.{item.right_column}"
            for item in relation.on_clauses
        ]

        where_items = []
        for item in relation.filters:
            alias = "l" if item.side == "left" else "r"
            condition = self._relation_condition(
                alias, item.column_name, item.param_name, item.operator
            )
            test = self._relation_test(item.param_name, item.is_string)

            where_items.append(
                {
                    "test": test,
                    "condition": condition,
                }
            )

        query_fields = []
        for item in relation.filters:
            query_fields.append(
                {
                    "param_name": item.param_name,
                    "java_type": item.java_type,
                    "method_suffix": item.param_name[:1].upper() + item.param_name[1:],
                }
            )

        sort_items = [
            {
                "request_name": item.request_name,
                "column_sql": f"{'l' if item.side == 'left' else 'r'}.{item.column_name}",
            }
            for item in relation.sortable_fields
        ]

        return {
            "name": relation.name,
            "method_name": relation.method_name,
            "dto_name": relation.dto_name,
            "query_name": relation.query_name,
            "join_type": relation.join_type,
            "left_table": relation.left_table,
            "right_table": relation.right_table,
            "select_sql": select_sql,
            "on_sql": on_sql,
            "where_items": where_items,
            "query_fields": query_fields,
            "query_field_names": {item["param_name"] for item in query_fields},
            "sort_items": sort_items,
            "has_sorting": bool(sort_items),
            "endpoint_name": snake_to_camel(relation.name),
        }

    def _relation_condition(
        self,
        alias: str,
        column_name: str,
        param_name: str,
        operator: str,
    ) -> str:
        column_ref = f"{alias}.{column_name}"
        param_ref = f"#{{query.{param_name}}}"
        if operator == "LIKE":
            return f"{column_ref} LIKE CONCAT('%', {param_ref}, '%')"
        operator_map = {
            "EQ": "=",
            "NE": "!=",
            "GT": ">",
            "GE": ">=",
            "LT": "<",
            "LE": "<=",
        }
        return f"{column_ref} {operator_map[operator]} {param_ref}"

    def _relation_test(self, param_name: str, is_string: bool) -> str:
        if is_string:
            return f"query.{param_name} != null and query.{param_name} != ''"
        return f"query.{param_name} != null"
