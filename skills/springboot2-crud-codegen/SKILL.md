---
name: springboot2-crud-codegen
description: Work with the `springboot2-crud-codegen` repository to understand docs, edit JSON configs, generate Spring Boot 2 + MyBatis-Plus CRUD backends with `init.sql`, optionally generate Vue 2 admin frontends, diagnose schema/parser/render issues, or extend this generator. Use when users ask in English or Chinese to understand this repo, modify `examples/*.json`, run `codegen`, inspect generated Java/Maven/Vue output, or fix/extend parser, templates, and rendering behavior.
---

# springboot2-crud-codegen

## 快速执行

- 先区分任务类型：编写配置、排查配置报错、生成项目、检查生成结果、修改生成器实现。
- 先读 `references/project-guide.md` 了解仓库结构、命令和边界。
- 编辑 JSON 配置前，读 `references/config-guide.md`；里面已经包含规则说明和不同场景示例。
- 始终遵守主流程：`load -> validate -> parse -> render -> write`。
- 始终记住项目边界：仅 Java 8、仅 Spring Boot 2.x、SQL 偏 MySQL、前端仅 Vue2 + Element UI。

## 工作流

### 1. 选择最近的起点

- 单表最小 CRUD：从 `examples/student_management.json` 或 `examples/student_single_table.json` 开始。
- 双表 + 联表查询：从 `examples/sample.json` 或 `examples/student_class_management.json` 开始。
- 后端 + 前端：从 `examples/fullstack_sample.json` 或 `examples/student_class_management_fullstack.json` 开始。

### 2. 编写或修改配置

- 保持顶层必填键：`project`、`datasource`、`tables`、`relations`、`global`。
- 优先保持数据库字段英文命名；需要中文界面时，用字段 `comment` 或 `frontend.label` 提供中文显示名。
- 暴露排序时补 `sortableFields`，避免生成不安全的排序 SQL。
- 联表查询时同时检查 `on`、`select`、`filters`，必要时补 `sortableFields`。
- 需要更贴近生产的 DDL 时，优先写显式 `indexes` 和 `foreignKeys`，不要只依赖推断。

### 3. 运行生成器

- 安装：`python -m pip install -e .`
- 生成示例：`python -m codegen -c examples/sample.json -o /tmp/codegen-out`
- 控制台脚本等价命令：`codegen -c examples/sample.json -o /tmp/codegen-out`
- 输出根目录固定为 `<output>/<artifactId>/`。

### 4. 验证结果

- 语法检查：`python -m compileall codegen tests`
- 单元测试：`python -m unittest discover -s tests -v`
- 只测一个方法时，用 `-k` 子串匹配；不要用 pytest node id，也不要用 `python -m unittest -v`。
- 需要人工验收时，至少检查 `backend/pom.xml`、`backend/src/main/resources/application.yml`、`backend/src/main/resources/init.sql` 与核心 Java/Mapper 文件。
- 只有在任务明确需要时，再继续构建生成后的 Maven 或前端项目。

### 5. 修改生成器实现

- 改 schema 语义时，同时更新 `codegen/schema.py`、`codegen/parser.py`、相关模板、示例或测试。
- 改生成结构时，同时检查 `codegen/render.py` 和 `codegen/templates/`，确保路径、导入和命名仍一致。
- 保持解析和渲染尽量纯净；文件系统写入留在 `codegen/writer.py` 和 CLI 边界。
- 行为变化后补测试，优先断言具体生成路径或片段内容。

## 排障重点

- 结构错误先看 `codegen/schema.py`；它负责 JSON Schema 级别的必填项、枚举、额外字段限制。
- 语义错误再看 `codegen/parser.py`；它负责主键存在性、操作符类型兼容、重名冲突、联表字段存在性等校验。
- 渲染结果不对时看 `codegen/render.py`，尤其是 DTO 字段推导、自动索引/外键推断、前端组件映射、联表 SQL 片段生成。
- 文件没落盘或覆盖行为异常时看 `codegen/writer.py` 与 CLI 的 `--force/--no-force`。

## 读取参考资料

- 仓库结构、命令、限制：读 `references/project-guide.md`
- 配置规则、校验点、常见坑、场景示例：读 `references/config-guide.md`
