# 项目总览

## 仓库定位

`springboot2-crud-codegen` 是一个 Python CLI。它把 JSON 配置转换成可运行的 Spring Boot 2 + MyBatis-Plus CRUD 工程，并生成 `init.sql`；启用 `frontend` 后，还能生成独立的 Vue2 + Element UI 管理前端。

## 核心流程

仓库主流程固定为：`load -> validate -> parse -> render -> write`。

- `codegen/cli.py`：解析命令行参数、处理退出码、调用主流程。
- `codegen/schema.py`：定义 JSON Schema，并把 schema 报错格式化成 `tables[0].field` 风格路径。
- `codegen/parser.py`：做语义校验并把配置转换成内部 IR；这里有大量真实业务规则。
- `codegen/ir.py`：定义 `ProjectIR`、`TableIR`、`RelationIR` 等数据结构。
- `codegen/render.py`：把 IR 渲染为内存中文件映射；负责后端、SQL、联表查询、可选前端。
- `codegen/writer.py`：把文件映射写到磁盘。
- `codegen/templates/`：Jinja 模板，覆盖 Java、XML、YAML、Maven、Vue2 页面。

## 重要输入与输出

- 典型输入：`examples/*.json`
- 典型输出：`<output>/<artifactId>/backend/...`
- 前端输出：`<output>/<artifactId>/frontend/...`，仅当顶层 `frontend.enabled = true`

常见输出文件：

- `backend/pom.xml`
- `backend/src/main/resources/application.yml`
- `backend/src/main/resources/init.sql`
- `backend/src/main/resources/mapper/*.xml`
- `backend/src/main/java/<basePackage>/...`
- `frontend/src/views/<table>/index.vue`
- `frontend/src/views/relations/<relation>/index.vue`

## 关键命令

- 安装：`python -m pip install -e .`
- 运行示例：`python -m codegen -c examples/sample.json -o /tmp/codegen-out`
- 控制台命令：`codegen -c examples/sample.json -o /tmp/codegen-out`
- 全量测试：`python -m unittest discover -s tests -v`
- 单测子串过滤：`python -m unittest discover -s tests -k test_parse_and_render_sample -v`
- 语法检查：`python -m compileall codegen tests`

## 项目边界

- 仅支持 Java 8。
- 仅支持 Spring Boot 2.x。
- SQL 和 datasource 以 MySQL 为主。
- 前端仅支持 Vue2 + Element UI。
- Python 测试框架是 `unittest`，不是 pytest。
- `python -m unittest -v` 在这里会跑出 `Ran 0 tests`，不要用这种形式。

## 修改时的仓库约束

- 不要无声改变 schema 语义。
- 改解析或渲染逻辑时，同时看模板和测试。
- 不要引入无关的全仓格式化改动。
- 改生成结构时，确保导入、路径、命名保持稳定且可重复生成。
