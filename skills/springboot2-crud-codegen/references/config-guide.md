# 配置文档

## 目录

- [文档定位](#文档定位)
- [先记住这 8 条](#先记住这-8-条)
- [顶层结构](#顶层结构)
- [顶层节点详解](#顶层节点详解)
- [`tables[]` 完整说明](#tables-完整说明)
- [`relations[]` 完整说明](#relations-完整说明)
- [前端配置完整说明](#前端配置完整说明)
- [不同场景配置示例](#不同场景配置示例)
- [常见校验错误与修复](#常见校验错误与修复)
- [推荐起步方式](#推荐起步方式)

## 文档定位

这份文档是本 skill 里最关键的参考文件，目标不是简单复述 README，而是把 `codegen/schema.py`、`codegen/parser.py`、`codegen/render.py` 里的真实配置规则整理成可直接照着写的说明。

阅读时请优先相信代码行为，尤其是：

- `codegen/schema.py`：决定哪些键必填、哪些值合法、是否允许额外字段。
- `codegen/parser.py`：决定哪些组合虽然“长得像对”，但实际会报语义错误。
- `codegen/render.py`：决定配置最终会生成什么代码、SQL 和前端页面。

## 先记住这 8 条

1. 几乎所有对象都不允许出现未声明字段；多写一个键也会报错，因为 schema 大量使用了 `additionalProperties: false`。
2. 顶层必须有 `project`、`datasource`、`tables`、`relations`、`global`；`backend`、`frontend` 可选。
3. `comment` 在表和字段层面都必须存在；可以写空字符串，但键本身不能省。
4. `queryableFields` 在每张表里也是必填；如果不需要查询条件，写空数组 `[]`。
5. `relations` 顶层也是必填；如果没有联表关系，写空数组 `[]`。
6. `bootVersion` 必须以 `2.` 开头，`javaVersion` 当前只能是 `8`。
7. 单表和联表排序都必须显式走白名单，不能自由传任意字段名。
8. 生成前端时，数据库字段名可以继续保留英文，界面文案优先走 `frontend.label`，其次走字段 `comment`。

## 顶层结构

最小合法骨架建议写成这样：

```json
{
  "project": {},
  "datasource": {},
  "backend": {},
  "frontend": {},
  "tables": [],
  "relations": [],
  "global": {}
}
```

其中：

- `backend`、`frontend` 可以不写。
- `relations` 可以是空数组。
- `tables` 至少要有一张表。
- 文档里的“可选”通常指“键可不写”；如果 schema 把某个键列为 required，那就必须出现。

## 顶层节点详解

### `project`

必填字段：

- `groupId`
- `artifactId`
- `name`
- `basePackage`
- `bootVersion`
- `javaVersion`

说明：

- `groupId`：Maven `groupId`。
- `artifactId`：Maven `artifactId`，也决定最终输出目录名 `<output>/<artifactId>/`。
- `name`：Spring 应用名；同时作为一部分显示名来源。
- `basePackage`：Java 根包名，必须是合法 Java package。
- `bootVersion`：必须以 `2.` 开头。
- `javaVersion`：当前固定只能是 `8`。

补充：

- `ProjectIR.application_class_name` 会基于 `artifactId` 推导主启动类名。
- 虽然 parser 内部对 `entityName` 有回退逻辑，但 schema 当前仍要求显式填写；写配置时以 schema 为准，不要依赖隐藏回退。

### `datasource`

必填字段：

- `url`
- `username`
- `password`
- `driverClassName`

可选字段：

- `databaseName`

说明：

- `databaseName` 强烈建议显式填写；`init.sql` 会优先使用它创建并切换数据库。
- 如果没写 `databaseName`，parser 会尝试从 JDBC URL 推断。
- 生成的 `application.yml` 不会直接写死数据库配置，而是转成环境变量占位：`DB_URL`、`DB_USERNAME`、`DB_PASSWORD`、`DB_DRIVER_CLASS_NAME`。

例如：

```yaml
spring:
  datasource:
    url: ${DB_URL:jdbc:mysql://127.0.0.1:3306/demo?...}
    username: ${DB_USERNAME:root}
    password: ${DB_PASSWORD:123456}
```

### `backend`

可选字段：

- `outputDir`

默认值：

- `backend`

说明：

- 只影响生成目录，不影响 Java 包名。
- 常见生成结果会位于 `<artifactId>/<backend.outputDir>/...`。

### `frontend`

可选字段：

- `enabled`
- `framework`
- `locale`
- `outputDir`
- `appTitle`
- `backendUrl`
- `devPort`

默认值：

- `enabled: false`
- `framework: "vue2"`
- `locale: "zh-CN"`
- `outputDir: "frontend"`
- `backendUrl: "http://127.0.0.1:8080"`
- `devPort: 8081`

限制：

- `framework` 当前只能是 `vue2`。
- `locale` 当前只能是 `zh-CN` 或 `en-US`。

说明：

- 只有 `enabled: true` 时，才会生成独立前端工程。
- `appTitle` 不写时回退到 `project.name`。

### `global`

必填字段：

- `apiPrefix`
- `author`
- `dateTimeFormat`
- `enableSwagger`

说明：

- `apiPrefix` 必须以 `/` 开头。
- `dateTimeFormat` 会进入生成的时间格式配置与模板上下文。
- `enableSwagger` 控制 Swagger 相关输出逻辑。

## `tables[]` 完整说明

每个元素代表一张基础 CRUD 表。

### 表级字段

必填字段：

- `name`
- `comment`
- `entityName`
- `fields`
- `primaryKey`
- `queryableFields`

可选字段：

- `frontend`
- `sortableFields`
- `indexes`
- `foreignKeys`
- `inferIndexes`
- `inferForeignKeys`
- `seedData`

关键规则：

- `name` 不能和其他表重名。
- `primaryKey` 必须能在 `fields[].name` 中找到。
- 同一张表内字段名不能重复。
- 每张表最多只能有一个 `logicDelete: true` 字段。
- `queryableFields` 虽然必填，但可以写成空数组。
- URL 资源名最终使用 `table.name.lower()`；为了路径稳定，建议表名直接使用小写下划线风格。

### 表级 `frontend`

可选字段：

- `menuTitle`
- `menuIcon`
- `menuVisible`

默认值：

- `menuIcon: "el-icon-document"`
- `menuVisible: true`

说明：

- `menuTitle` 不写时，会按 `table.frontend.menuTitle -> table.comment -> entityName` 的顺序回退。
- 该配置会影响前端左侧菜单、页面标题和路由展示文案。

### `fields[]`

必填字段：

- `name`
- `type`
- `nullable`
- `comment`

可选字段：

- `unique`
- `logicDelete`
- `frontend`
- `autoFill`
- `idType`

说明：

- `name`：数据库列名。
- `type`：数据库列类型，既影响 DDL，也影响 Java 类型映射。
- `nullable`：同时影响建表 SQL 和 DTO 校验策略。
- `comment`：用于 SQL 注释，也常作为前端默认标签文案。
- `unique`：会参与 `init.sql` 中的唯一键生成。
- `logicDelete`：标记逻辑删除字段。
- `autoFill`：支持 `INSERT`、`UPDATE`、`INSERT_UPDATE`。
- `idType`：支持 `AUTO`、`ASSIGN_ID`、`INPUT`。

字段名转换规则：

- 列名 `student_name` 会被转成 Java 属性 `studentName`。
- 这个 camelCase 名会影响 DTO 字段名、排序参数名、前端字段名、联表默认 alias 等多个地方。

### 数据库类型到 Java 类型映射

当前映射规则如下：

- `bigint` -> `Long`
- `int` / `integer` / `tinyint` / `smallint` / `mediumint` -> `Integer`
- `varchar` / `char` / `text` / `longtext` / `json` -> `String`
- `datetime` / `timestamp` -> `LocalDateTime`
- `date` -> `LocalDate`
- `decimal` / `numeric` -> `BigDecimal`
- `double` / `float` -> `Double`
- `bit` / `boolean` -> `Boolean`
- 其他未知类型 -> `String`

建议：

- 如果你依赖数值、时间、布尔组件或 DTO 校验的精确生成，尽量使用映射表中的标准类型。
- 自定义数据库类型若无法正确归类，渲染层会退回 `String`。

### DTO 与校验注解生成规则

create/update DTO 生成时：

- 主键字段不会进入 create/update DTO。
- `logicDelete` 字段不会进入 create/update DTO。
- `autoFill` 字段不会进入 create/update DTO。

create DTO 校验：

- 非空字符串 -> `@NotBlank`
- 非空非字符串 -> `@NotNull`
- `varchar(n)`、`char(n)` 等可提取长度的字符串 -> `@Size(max = n)`

query DTO 固定字段：

- `page`，默认 `1L`
- `size`，默认 `20L`
- 如果配置了排序，还会生成 `sortBy` 和 `sortDir`

`sortDir` 额外校验：

- 允许 `ASC`
- 允许 `DESC`
- 同时接受小写 `asc` / `desc`

### `autoFill` 的真实生效范围

`autoFill` 在 schema 层允许：

- `INSERT`
- `UPDATE`
- `INSERT_UPDATE`

但当前渲染层自动填充值只内建支持：

- `LocalDateTime` -> `LocalDateTime.now()`
- `LocalDate` -> `LocalDate.now()`

这意味着：

- 你可以给别的类型写 `autoFill`，schema 和 parser 不会立刻报错。
- 但 `MybatisMetaObjectHandler` 实际不会为所有类型自动赋值。
- 最稳妥的用法仍然是 `created_at` / `updated_at` 这类日期时间字段。

### `queryableFields[]`

支持两种写法：

```json
["student_name"]
```

等价于：

```json
[{"name": "student_name", "operator": "EQ"}]
```

完整写法：

```json
{"name": "amount", "operator": "GE"}
```

支持操作符：

- `EQ`
- `NE`
- `LIKE`
- `GT`
- `GE`
- `LT`
- `LE`

语义限制：

- `LIKE` 只能用于 `String`
- `GT` / `GE` / `LT` / `LE` 只能用于数值或日期时间类型

### `sortableFields`

写法：

```json
"sortableFields": ["created_at", "amount"]
```

规则：

- 每个字段必须真实存在于当前表的 `fields[]`。
- 最终对外暴露的排序参数名不是数据库列名，而是 camelCase 属性名。
- 如果两个数据库字段转换后得到相同 camelCase 名，会触发重复报错。

作用：

- 控制 Query DTO 是否生成 `sortBy` / `sortDir`
- 控制 Mapper SQL 中允许进入 `ORDER BY` 的白名单

### `indexes[]`

写法：

```json
{
  "name": "idx_orders_user_created",
  "columns": ["user_id", "created_at"],
  "unique": false
}
```

规则：

- `columns` 至少一个元素。
- 每一列都必须是当前表真实字段。
- `name` 不写时，会自动生成：普通索引前缀 `idx_`，唯一索引前缀 `uk_`。
- 同一张表内索引名不能重复。

补充：

- 字段级 `unique: true` 也会在 `init.sql` 里生成单列唯一键。
- render 层会对显式索引、推断索引、字段唯一键做一定程度去重。

### `foreignKeys[]`

写法：

```json
{
  "name": "fk_orders_users_user_id",
  "columns": ["user_id"],
  "refTable": "users",
  "refColumns": ["id"],
  "onDelete": "RESTRICT",
  "onUpdate": "RESTRICT"
}
```

支持动作：

- `RESTRICT`
- `CASCADE`
- `SET NULL`
- `NO ACTION`

规则：

- `columns` 和 `refColumns` 长度必须一致。
- `columns` 必须是当前表真实字段。
- `refTable` 必须存在于 `tables[]`。
- `refColumns` 必须真实存在于被引用表中。
- 同一张表内外键名不能重复。

### `inferIndexes` 与 `inferForeignKeys`

默认值：

- `inferIndexes: true`
- `inferForeignKeys: true`

推断逻辑非常值得知道：

- 自动索引会从单表 `queryableFields` 推断。
- 自动索引也会从 relation 的 `on` 字段和 `filters` 字段推断。
- 自动外键只会基于 relation 的 `on` 条件推断，而且方向是“左表引用右表”。

建议：

- 演示或快速原型可以依赖推断。
- 生产风格 DDL 更推荐显式写 `indexes` 和 `foreignKeys`。

### `seedData[]`

写法：

```json
"seedData": [
  {"id": 1, "student_name": "Alice"},
  {"id": 2, "student_name": "Bob"}
]
```

规则：

- 每个键都必须能在当前表字段中找到。
- 允许的值类型：字符串、数字、整数、布尔、`null`。

效果：

- 会被写入 `init.sql` 的 `INSERT INTO ... VALUES ...;`
- 很适合演示环境、本地初始化、冒烟测试。

## `relations[]` 完整说明

每个元素代表一个联表分页查询能力，不会生成完整的联表 CRUD，只会生成只读查询接口、DTO 和 Mapper SQL。

### relation 级字段

必填字段：

- `name`
- `leftTable`
- `rightTable`
- `joinType`
- `dtoName`
- `methodName`
- `on`
- `select`
- `filters`

可选字段：

- `sortableFields`
- `frontend`

说明：

- `joinType` 当前只能是 `LEFT` 或 `INNER`。
- `filters` 虽然必填，但可以写空数组 `[]`。
- relation 的接口会挂在左表控制器下，路径形如：`GET /api/<left-resource>/relations/<relation-name>`。

### `on`

写法：

```json
{"leftField": "class_id", "rightField": "id"}
```

规则：

- `leftField` 必须存在于 `leftTable`。
- `rightField` 必须存在于 `rightTable`。
- 至少要有一个有效 ON 条件；全部无效时 relation 整体报错。

### `select`

写法：

```json
{"table": "students", "field": "student_name", "alias": "studentName"}
```

`table` 可接受的值：

- `left`
- `right`
- 左表真实表名
- 右表真实表名

说明：

- parser 对 `table` 是大小写不敏感匹配。
- `alias` 可选；不写时默认取源字段的 camelCase 属性名。
- 至少要有一个有效 `select` 项。

### `filters`

写法：

```json
{"table": "classes", "field": "class_name", "operator": "LIKE", "param": "className"}
```

规则：

- 操作符规则和单表 `queryableFields` 完全一致。
- `param` 最终会被规范化成 camelCase。
- 规范化后的参数名不能重复；比如 `class_name` 和 `className` 会视为同一个参数。

### `sortableFields`

写法：

```json
{"table": "classes", "field": "class_name", "name": "className"}
```

说明：

- `name` 可选；不写时默认使用源字段的 camelCase 属性名。
- 最终对外暴露的也是 camelCase 排序参数名。
- 同一 relation 内排序名不能重复。

### `dtoName`、`methodName` 与命名冲突

规则：

- `methodName` 必须是合法 Java 方法名。
- `dtoName` 必须是合法 Java 类名。
- 系统会自动生成 query 类型名：`<MethodName首字母大写>Query`。
- `name`、`dtoName`、自动生成的 query 类名都不能和其他 relation 冲突。
- 同一个左表下，`methodName` 不能重复，因为它会进入左表 Mapper。

### relation 级 `frontend`

可选字段：

- `menuTitle`
- `menuIcon`
- `menuVisible`

默认值：

- `menuIcon: "el-icon-connection"`
- `menuVisible: true`

说明：

- 仅在生成前端时生效。
- 用于左侧菜单、联表页面标题、路由展示。

## 前端配置完整说明

前端由顶层 `frontend` 决定是否生成；表、字段、relation 上的 `frontend` 只是进一步控制页面表现。

### 字段级 `frontend`

可选字段：

- `label`
- `component`
- `queryComponent`
- `tableVisible`
- `formVisible`
- `detailVisible`
- `queryVisible`
- `placeholder`
- `options`

`component` / `queryComponent` 可选值：

- `text`
- `textarea`
- `number`
- `switch`
- `date`
- `datetime`
- `select`

`options` 每项结构：

```json
{"label": "启用", "value": 1}
```

### 不写组件时的自动推断

render 层会根据字段类型和配置自动选择前端组件：

- `String`：默认 `text`；长文本或大长度字符串可能推成 `textarea`
- `Long` / `Integer`：`number`
- `Double` / `BigDecimal`：`number`，步长 `0.01`
- `LocalDateTime`：`datetime`
- `LocalDate`：`date`
- `Boolean`：表单中默认 `switch`；查询中会走布尔选择逻辑
- 只要配置了 `options`，即使没写 `component`，通常也会优先按 `select` 处理

### 文案回退规则

字段显示名回退顺序：

- `frontend.label`
- 字段 `comment`
- 根据属性名自动拆词生成标题

表页面标题回退顺序：

- 表级 `frontend.menuTitle`
- 表 `comment`
- `entityName`

relation 页面标题回退顺序：

- relation 级 `frontend.menuTitle`
- 根据 relation `name` 或 `dtoName` 自动推导

### placeholder 行为

- 如果你已经写了 `请输入状态`、`请选择状态`、`Enter status` 这种完整文案，渲染层会直接使用。
- 如果只是写了字段标签，渲染层会根据组件类型自动补成“请输入...”或“请选择...”。

## 不同场景配置示例

### 场景 1：最小单表 CRUD

适合快速起一个最小可用后端。

```json
{
  "project": {
    "groupId": "com.example",
    "artifactId": "student-management",
    "name": "student-management",
    "basePackage": "com.example.student",
    "bootVersion": "2.7.18",
    "javaVersion": 8
  },
  "datasource": {
    "url": "jdbc:mysql://127.0.0.1:3306/student_management?useSSL=false&serverTimezone=UTC&characterEncoding=UTF-8",
    "databaseName": "student_management",
    "username": "root",
    "password": "123456",
    "driverClassName": "com.mysql.cj.jdbc.Driver"
  },
  "tables": [
    {
      "name": "students",
      "comment": "学生表",
      "entityName": "Student",
      "primaryKey": "id",
      "queryableFields": [
        {"name": "student_name", "operator": "LIKE"}
      ],
      "fields": [
        {"name": "id", "type": "bigint", "nullable": false, "comment": "主键", "idType": "AUTO"},
        {"name": "student_name", "type": "varchar(64)", "nullable": false, "comment": "学生姓名"},
        {"name": "created_at", "type": "datetime", "nullable": false, "comment": "创建时间", "autoFill": "INSERT"},
        {"name": "updated_at", "type": "datetime", "nullable": false, "comment": "更新时间", "autoFill": "INSERT_UPDATE"}
      ]
    }
  ],
  "relations": [],
  "global": {
    "apiPrefix": "/api",
    "author": "codegen",
    "dateTimeFormat": "yyyy-MM-dd HH:mm:ss",
    "enableSwagger": false
  }
}
```

### 场景 2：带排序、索引、外键和种子数据的业务表

适合更接近真实业务表结构。

```json
{
  "name": "orders",
  "comment": "订单表",
  "entityName": "Order",
  "primaryKey": "id",
  "queryableFields": [
    {"name": "order_no", "operator": "LIKE"},
    {"name": "user_id", "operator": "EQ"},
    {"name": "amount", "operator": "GE"}
  ],
  "sortableFields": ["id", "created_at", "amount"],
  "indexes": [
    {"name": "idx_orders_user_created", "columns": ["user_id", "created_at"]}
  ],
  "foreignKeys": [
    {
      "name": "fk_orders_users_user_id",
      "columns": ["user_id"],
      "refTable": "users",
      "refColumns": ["id"],
      "onDelete": "RESTRICT",
      "onUpdate": "RESTRICT"
    }
  ],
  "seedData": [
    {"id": 1, "order_no": "ORD-001", "user_id": 10, "amount": 99.50}
  ],
  "fields": [
    {"name": "id", "type": "bigint", "nullable": false, "comment": "主键", "idType": "AUTO"},
    {"name": "order_no", "type": "varchar(64)", "nullable": false, "comment": "订单号", "unique": true},
    {"name": "user_id", "type": "bigint", "nullable": false, "comment": "用户ID"},
    {"name": "amount", "type": "decimal(10,2)", "nullable": false, "comment": "订单金额"},
    {"name": "created_at", "type": "datetime", "nullable": false, "comment": "创建时间", "autoFill": "INSERT"}
  ]
}
```

### 场景 3：联表分页查询

适合生成 `LEFT JOIN` / `INNER JOIN` 查询接口。

```json
{
  "name": "order-user",
  "leftTable": "orders",
  "rightTable": "users",
  "joinType": "LEFT",
  "dtoName": "OrderUserDTO",
  "methodName": "pageOrderWithUser",
  "on": [
    {"leftField": "user_id", "rightField": "id"}
  ],
  "select": [
    {"table": "orders", "field": "id", "alias": "orderId"},
    {"table": "orders", "field": "order_no", "alias": "orderNo"},
    {"table": "users", "field": "username", "alias": "username"},
    {"table": "orders", "field": "amount", "alias": "amount"}
  ],
  "filters": [
    {"table": "orders", "field": "order_no", "operator": "LIKE", "param": "orderNo"},
    {"table": "users", "field": "username", "operator": "LIKE", "param": "username"}
  ],
  "sortableFields": [
    {"table": "orders", "field": "created_at", "name": "createdAt"},
    {"table": "users", "field": "username", "name": "username"}
  ]
}
```

### 场景 4：生成前后端一体项目

适合演示项目、课程项目、快速交付一个可浏览页面的后台。

```json
{
  "frontend": {
    "enabled": true,
    "framework": "vue2",
    "locale": "zh-CN",
    "outputDir": "frontend",
    "appTitle": "Demo Admin",
    "backendUrl": "http://127.0.0.1:8080",
    "devPort": 8081
  }
}
```

### 场景 5：字段级前端配置

适合英文字段名数据库配中文界面，或者需要精细控制页面显隐与组件类型。

```json
{
  "name": "status",
  "type": "int",
  "nullable": false,
  "comment": "状态",
  "frontend": {
    "label": "状态",
    "component": "select",
    "queryComponent": "select",
    "tableVisible": true,
    "formVisible": true,
    "detailVisible": true,
    "queryVisible": true,
    "placeholder": "请选择状态",
    "options": [
      {"label": "启用", "value": 1},
      {"label": "禁用", "value": 0}
    ]
  }
}
```

### 场景 6：关闭推断，完全显式控制 DDL

适合对 DDL 稳定性要求更高的项目。

```json
{
  "name": "students",
  "comment": "学生表",
  "entityName": "Student",
  "primaryKey": "id",
  "queryableFields": [],
  "inferIndexes": false,
  "inferForeignKeys": false,
  "indexes": [
    {"name": "idx_students_class_id", "columns": ["class_id"]}
  ],
  "foreignKeys": [
    {
      "name": "fk_students_classes_class_id",
      "columns": ["class_id"],
      "refTable": "classes",
      "refColumns": ["id"]
    }
  ],
  "fields": [
    {"name": "id", "type": "bigint", "nullable": false, "comment": "主键", "idType": "AUTO"},
    {"name": "class_id", "type": "bigint", "nullable": false, "comment": "班级ID"}
  ]
}
```

## 常见校验错误与修复

### 1. 多写了一个自定义键

常见报错：

- `Additional properties are not allowed`

原因：

- schema 对大多数对象都启用了 `additionalProperties: false`。

修复：

- 删除未声明字段，或把信息迁移到已有字段中。

### 2. `comment` 被省略

常见报错位置：

- `tables[0]`
- `tables[0].fields[0]`

原因：

- 表和字段的 `comment` 当前都被 schema 设为必填。

修复：

- 至少补空字符串 `"comment": ""`；更推荐写真实注释。

### 3. `primaryKey` 指向了不存在字段

常见报错：

- `primary key 'id' does not exist in fields`

修复：

- 检查 `primaryKey` 是否与 `fields[].name` 完全一致。

### 4. 给非字符串字段用了 `LIKE`

常见报错：

- `LIKE operator only supports String fields`

修复：

- 把字段类型改成字符串查询，或把操作符改成 `EQ` / `GE` / `LE` 等合适形式。

### 5. 范围操作符用于不支持类型

常见报错：

- `GE operator only supports numeric or date/time fields`

修复：

- 只在数字、日期、时间字段上使用 `GT` / `GE` / `LT` / `LE`。

### 6. relation 的 `table` 写错

常见报错：

- `must be one of: left, right, orders, users`

修复：

- 把 `select[].table`、`filters[].table`、`sortableFields[].table` 改为 `left` / `right` 或真实表名。

### 7. relation 参数名看起来不同，实际上冲突

示例：

- `class_name`
- `className`

原因：

- parser 会先把 `param` 归一化成 camelCase，再判断重复。

修复：

- 保证归一化后的参数名唯一。

### 8. 开放了排序但没配置白名单

现象：

- 前端想传排序字段，但生成后的 DTO/SQL 不支持。

修复：

- 单表补 `sortableFields`。
- 联表补 relation `sortableFields`。

### 9. 以为 `autoFill` 任意类型都能自动赋值

现象：

- 字段配置了 `autoFill`，但运行时没自动填值。

修复：

- 优先用于 `LocalDateTime` / `LocalDate` 类型字段。

推荐验证命令：

```bash
python -m codegen -c examples/sample.json -o /tmp/codegen-out
python -m unittest discover -s tests -v
python -m compileall codegen tests
```
