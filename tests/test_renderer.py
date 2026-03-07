from __future__ import annotations

import json
import unittest
from pathlib import Path

from codegen.parser import parse_config
from codegen.render import CodeRenderer


class RendererTest(unittest.TestCase):
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

    def test_render_application_uses_env_placeholders(self) -> None:
        project = parse_config(self.sample_payload)
        files = CodeRenderer().render_project(project)

        application_yml = files["src/main/resources/application.yml"]
        self.assertIn(
            'url: "${DB_URL:jdbc:mysql://127.0.0.1:3306/demo?useSSL=false&serverTimezone=UTC&characterEncoding=UTF-8}"',
            application_yml,
        )
        self.assertIn('username: "${DB_USERNAME:root}"', application_yml)
        self.assertIn('password: "${DB_PASSWORD:root}"', application_yml)

    def test_render_create_and_update_dto_validation_annotations(self) -> None:
        project = parse_config(self.student_class_payload)
        files = CodeRenderer().render_project(project)

        create_dto = files[
            "src/main/java/com/example/school/dto/StudentCreateRequest.java"
        ]
        update_dto = files[
            "src/main/java/com/example/school/dto/StudentUpdateRequest.java"
        ]

        self.assertIn("import javax.validation.constraints.NotBlank;", create_dto)
        self.assertIn("import javax.validation.constraints.NotNull;", create_dto)
        self.assertIn("import javax.validation.constraints.Size;", create_dto)
        self.assertIn('@NotBlank(message = "studentNo must not be blank")', create_dto)
        self.assertIn(
            '@Size(max = 32, message = "studentNo length must be <= 32")', create_dto
        )
        self.assertIn('@NotNull(message = "classId must not be null")', create_dto)
        self.assertNotIn("createdAt", create_dto)
        self.assertNotIn("updatedAt", create_dto)
        self.assertIn(
            '@Size(max = 32, message = "studentNo length must be <= 32")', update_dto
        )
        self.assertNotIn("@NotBlank", update_dto)

    def test_render_query_dto_supports_sorting_and_validation(self) -> None:
        project = parse_config(self.student_class_payload)
        files = CodeRenderer().render_project(project)

        query_dto = files[
            "src/main/java/com/example/school/dto/StudentQueryRequest.java"
        ]
        relation_query_dto = files[
            "src/main/java/com/example/school/dto/PageStudentWithClassQuery.java"
        ]

        self.assertIn("import javax.validation.constraints.Max;", query_dto)
        self.assertIn("import javax.validation.constraints.Min;", query_dto)
        self.assertIn("import javax.validation.constraints.Pattern;", query_dto)
        self.assertIn('@Min(value = 1, message = "page must be >= 1")', query_dto)
        self.assertIn(
            '@Pattern(regexp = "ASC|DESC|asc|desc", message = "sortDir must be ASC or DESC")',
            query_dto,
        )
        self.assertIn("private String sortBy;", query_dto)
        self.assertIn("private String sortDir;", query_dto)
        self.assertIn("private String sortBy;", relation_query_dto)
        self.assertIn("private String sortDir;", relation_query_dto)

    def test_render_init_sql_contains_explicit_and_inferred_constraints(self) -> None:
        project = parse_config(self.student_class_payload)
        files = CodeRenderer().render_project(project)

        init_sql = files["src/main/resources/init.sql"]
        self.assertIn("CREATE DATABASE IF NOT EXISTS `student_class_demo`", init_sql)
        self.assertIn("USE `student_class_demo`", init_sql)
        self.assertIn("KEY `idx_students_student_name` (`student_name`)", init_sql)
        self.assertIn("KEY `idx_students_class_id` (`class_id`)", init_sql)
        self.assertIn(
            "CONSTRAINT `fk_students_classes_student_class` FOREIGN KEY (`class_id`) REFERENCES `classes` (`id`) ON DELETE RESTRICT ON UPDATE RESTRICT",
            init_sql,
        )
        self.assertIn("INSERT INTO `students`", init_sql)
        self.assertIn("Li Lei", init_sql)

    def test_render_meta_object_handler_for_auto_fill_fields(self) -> None:
        project = parse_config(self.student_class_payload)
        files = CodeRenderer().render_project(project)

        handler = files[
            "src/main/java/com/example/school/config/MybatisMetaObjectHandler.java"
        ]

        self.assertIn("implements MetaObjectHandler", handler)
        self.assertIn('strictInsertFill(metaObject, "createdAt"', handler)
        self.assertIn('strictInsertFill(metaObject, "updatedAt"', handler)
        self.assertIn('strictUpdateFill(metaObject, "updatedAt"', handler)

    def test_render_service_and_relation_mapper_support_extended_operators_and_sorting(
        self,
    ) -> None:
        payload = json.loads(json.dumps(self.sample_payload))
        payload["tables"][1]["queryableFields"] = [
            {"name": "order_no", "operator": "LIKE"},
            {"name": "amount", "operator": "GE"},
            {"name": "user_id", "operator": "NE"},
        ]
        payload["tables"][1]["sortableFields"] = ["created_at", "amount"]
        payload["relations"][0]["filters"] = [
            {
                "table": "orders",
                "field": "order_no",
                "operator": "LIKE",
                "param": "orderNo",
            },
            {
                "table": "orders",
                "field": "amount",
                "operator": "GE",
                "param": "minAmount",
            },
            {
                "table": "users",
                "field": "username",
                "operator": "LIKE",
                "param": "username",
            },
        ]
        payload["relations"][0]["sortableFields"] = [
            {"table": "orders", "field": "created_at", "name": "createdAt"},
            {"table": "users", "field": "username", "name": "username"},
        ]

        project = parse_config(payload)
        files = CodeRenderer().render_project(project)

        service_impl = files[
            "src/main/java/com/example/demo/service/impl/OrderServiceImpl.java"
        ]
        mapper_xml = files["src/main/resources/mapper/OrderMapper.xml"]
        relation_query = files[
            "src/main/java/com/example/demo/dto/PageOrderWithUserQuery.java"
        ]

        self.assertIn("wrapper.ge(Order::getAmount, query.getAmount())", service_impl)
        self.assertIn("wrapper.ne(Order::getUserId, query.getUserId())", service_impl)
        self.assertIn("query.getSortBy()", service_impl)
        self.assertIn("orderBy", service_impl)
        self.assertIn("AND l.amount >= #{query.minAmount}", mapper_xml)
        self.assertIn("ORDER BY", mapper_xml)
        self.assertIn("l.created_at", mapper_xml)
        self.assertIn("r.username", mapper_xml)
        self.assertIn("private BigDecimal minAmount;", relation_query)
        self.assertIn("private String sortBy;", relation_query)

    def test_render_global_exception_handler_hides_internal_errors(self) -> None:
        project = parse_config(self.sample_payload)
        files = CodeRenderer().render_project(project)

        exception_handler = files[
            "src/main/java/com/example/demo/exception/GlobalExceptionHandler.java"
        ]

        self.assertIn("LoggerFactory", exception_handler)
        self.assertIn("Result.failure(ErrorCode.INTERNAL_ERROR)", exception_handler)
        self.assertNotIn(
            "ex.getMessage()", exception_handler.split("handleException")[1]
        )

    def test_render_vue2_frontend_project(self) -> None:
        payload = json.loads(json.dumps(self.sample_payload))
        payload["frontend"] = {
            "enabled": True,
            "framework": "vue2",
            "outputDir": "frontend",
            "appTitle": "Demo Admin",
            "backendUrl": "http://127.0.0.1:8080",
            "devPort": 8081,
        }
        payload["tables"][0]["frontend"] = {
            "menuTitle": "User Center",
            "menuIcon": "el-icon-user-solid",
        }
        payload["tables"][0]["fields"][1]["frontend"] = {
            "label": "Login Name",
            "component": "textarea",
            "tableVisible": False,
            "formVisible": True,
            "detailVisible": True,
            "queryVisible": True,
            "placeholder": "Type username",
        }
        payload["tables"][0]["fields"][2]["frontend"] = {
            "component": "select",
            "queryComponent": "select",
            "options": [
                {"label": "Disabled", "value": 0},
                {"label": "Enabled", "value": 1},
            ],
        }
        payload["relations"][0]["frontend"] = {
            "menuTitle": "Order User Report",
            "menuIcon": "el-icon-data-analysis",
        }

        project = parse_config(payload)
        files = CodeRenderer().render_project(project)

        package_json = files["frontend/package.json"]
        router_js = files["frontend/src/router/index.js"]
        layout_vue = files["frontend/src/layout/Layout.vue"]
        request_js = files["frontend/src/utils/request.js"]
        users_api = files["frontend/src/api/users.js"]
        orders_api = files["frontend/src/api/orders.js"]
        users_view = files["frontend/src/views/users/index.vue"]
        relation_view = files["frontend/src/views/relations/order-user/index.vue"]

        self.assertIn('"vue": "^2.7.16"', package_json)
        self.assertIn('"element-ui": "^2.15.14"', package_json)
        self.assertIn("/users", router_js)
        self.assertIn("/relations/order-user", router_js)
        self.assertIn("User Center", layout_vue)
        self.assertIn("el-icon-user-solid", layout_vue)
        self.assertIn("Order User Report", layout_vue)
        self.assertIn("response.data.code !== 0", request_js)
        self.assertIn("/api/users", users_api)
        self.assertIn("fetchUsersPage", users_api)
        self.assertIn("createUser", users_api)
        self.assertIn("fetchPageOrderWithUser", orders_api)
        self.assertIn("el-table", users_view)
        self.assertIn("sortBy", users_view)
        self.assertIn("el-dialog", users_view)
        self.assertNotIn('prop="username"', users_view)
        self.assertIn("Login Name", users_view)
        self.assertIn("Type username", users_view)
        self.assertIn('label="Enabled"', users_view)
        self.assertIn('label="Disabled"', users_view)
        self.assertIn("textarea", users_view)
        self.assertIn("fetchPageOrderWithUser", relation_view)


if __name__ == "__main__":
    unittest.main()
