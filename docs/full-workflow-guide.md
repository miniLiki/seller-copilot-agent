# Seller Copilot Agent 完整流程功能文档

## 1. 文档目的

本文档基于当前仓库的实际项目结构与代码实现整理，说明 `seller-copilot-agent` 的功能边界、模块职责、端到端调用流程、运行模式、Trace 机制、测试评测方式，以及在面试或演示场景下应该如何讲解整个系统。

本文档对应的核心代码目录：

- `tools/`: 本地 FastAPI 工具服务
- `rag/`: 本地规则库检索
- `agent/`: 编排、Prompt、模型适配、解析、工具执行
- `demo/`: CLI 演示入口
- `data/`: 知识库、图片、训练样本
- `train/`: ms-swift 训练 / 推理 / merge 脚本
- `eval/`: 最小评测脚本
- `tests/`: 单元测试与契约测试
- `runs/`: 每次运行的 Trace 结果

---

## 2. 项目定位

该项目是一个面向跨境电商运营场景的 mock-first Agent Demo，目标不是生产级系统，而是展示一个完整、清晰、可解释的 Agent 闭环：

1. 用户输入商品主图、商品 ID 和自然语言任务。
2. 系统检索本地业务规则与 SOP。
3. 系统构造 Prompt，并调用 mock 或 swift 模型。
4. 模型输出统一 JSON 协议。
5. 系统解析模型输出并执行工具调用。
6. 系统返回最终结果，并保存完整 Trace。

当前 MVP 主要聚焦“商品主图诊断与执行”这个闭环场景。

---

## 3. 系统总览

### 3.1 端到端数据流

```text
用户输入 image + product_id + query
                |
                v
         demo/cli_demo.py
                |
                v
         agent/planner.py
      /           |            \
     v            v             v
  rag/retrieve   prompt      model_adapter
     |                            |
     v                            v
 Top-K 规则片段               runtime JSON 输出
      \            |            /
       \           v           /
        \      parser.py      /
         \         |         /
          \        v        /
           ---- executor.py ----
                    |
                    v
               tools/app.py
                    |
                    v
            Tool Results + Final Response
                    |
                    v
                 runs/<case>/
```

### 3.2 设计原则

当前实现遵循以下几个核心原则：

- mock-first：默认保证无 GPU、无真实模型也能跑通演示。
- schema 单一来源：工具 schema 集中在 `agent/tool_registry.py`。
- 训练协议与运行协议分离：训练样本与运行时 JSON 输出不是一套协议。
- 可追踪：检索、Prompt、模型输出、工具结果、最终回复都能落盘。
- 渐进扩展：mock 模式先保演示稳定，再通过 `swift` 模式扩展到真实推理。

---

## 4. 目录与模块职责

## 4.1 `tools/` 工具服务模块

关键文件：

- `tools/app.py`
- `tools/schemas.py`
- `tools/mock_db.py`

职责：

- 提供本地 FastAPI 模拟工具服务。
- 模拟商品信息、库存信息、整改任务创建、广告文案生成。
- 为 Agent 提供 HTTP 可调用的“外部工具”。

当前已实现接口：

- `GET /health`
- `GET /product/{product_id}`
- `GET /inventory/{product_id}`
- `POST /task/create`
- `POST /copy/generate`

实现特点：

- 使用 Pydantic 定义稳定请求/响应结构。
- 使用内存字典作为 mock 数据源。
- 当商品不存在时返回 `404`。

---

## 4.2 `rag/` 检索模块

关键文件：

- `rag/kb_loader.py`
- `rag/chunking.py`
- `rag/retrieve.py`
- `rag/build_index.py`

职责：

- 从 `data/kb/` 加载 markdown 格式知识库。
- 将知识库按稳定段落切分。
- 按简单关键词重叠打分进行检索。
- 返回 Top-K 规则片段，供 Prompt 和 Trace 使用。

当前实现特点：

- `chunk_id` 稳定，格式为 `文件名:序号`。
- 检索结果字段固定为：
  - `source`
  - `chunk_id`
  - `content`
  - `score`
- 默认 deterministic 排序，按：
  - `score` 降序
  - `source` 升序
  - `chunk_id` 升序
- 可将检索结果落盘到 `retrieval.json`。

---

## 4.3 `agent/` 核心编排模块

关键文件：

- `agent/models.py`
- `agent/prompt.py`
- `agent/parser.py`
- `agent/tool_registry.py`
- `agent/executor.py`
- `agent/model_adapter.py`
- `agent/planner.py`

职责分工如下：

### `models.py`

定义运行时公共数据结构：

- `ToolCall`
- `ModelRuntimeOutput`
- `ToolExecutionRecord`
- `RunTrace`

这些结构是 planner、parser、executor 之间的统一契约。

### `prompt.py`

负责组装 Prompt，当前实现的重点是：

- 角色定义
- 输出 JSON 要求
- 可用工具 schema
- 检索到的规则片段
- 用户任务
- `<image>` 占位支持

当前主要使用：

- `runtime_json_prompt()`

### `parser.py`

负责把模型输出解析成统一 JSON 协议：

- 先尝试提取 JSON 主体
- 再执行 `json.loads`
- 再执行 Pydantic 校验

异常场景会返回标准错误结构，例如：

- `MODEL_OUTPUT_PARSE_ERROR`
- `MODEL_OUTPUT_SCHEMA_ERROR`

### `tool_registry.py`

这是整个系统的工具 schema 单一来源。

当前提供：

- `get_tool_schemas_for_prompt()`
- `get_tool_schemas_for_training()`
- `get_tool_definition_map()`
- `get_tool_executor_map()`

作用：

- 给 Prompt 提供可用工具定义。
- 给训练样本生成脚本复用同一份工具定义。
- 给执行器生成 HTTP 调用映射。

### `executor.py`

负责顺序执行模型输出中的 `tool_calls`：

- 查找工具名对应的 executor
- 发起 HTTP 请求
- 收集执行输入、输出、状态码、错误信息
- 单个工具失败时不中断整个流程

### `model_adapter.py`

负责区分不同模型运行模式。

当前实现两条分支：

- `mock_model()`
- `swift_model_adapter()`

其中：

- `mock_model()` 根据 query 关键词生成稳定 JSON。
- `swift_model_adapter()` 会：
  - 生成单条 `swift_request.jsonl`
  - 调用 `train/infer.sh`
  - 保存 `swift_stdout.log` / `swift_stderr.log`
  - 读取 `swift_result.jsonl`
  - 提取 assistant 输出文本

### `planner.py`

是系统总 orchestrator，负责串起完整链路：

1. 校验输入图片是否存在
2. 加载并归一化运行配置
3. 固定随机种子
4. 创建运行目录 `runs/<timestamp>_<product_id>/`
5. 执行 RAG 检索
6. 构造 Prompt
7. 调用模型适配层
8. 解析模型输出
9. 执行工具调用
10. 汇总最终响应
11. 保存完整 Trace
12. 返回 `RunTrace` 对象

---

## 4.4 `demo/` 演示入口模块

关键文件：

- `demo/cli_demo.py`

职责：

- 提供命令行演示入口。
- 打印适合面试展示的模块化输出。

当前终端输出顺序：

- `Runtime Config`
- `User Query`
- `Retrieved Rules`
- `Model Output`
- `Tool Calls`
- `Tool Results`
- `Final Response`
- `Errors`（如存在）

---

## 4.5 `data/` 数据模块

当前包含：

- `data/kb/*.md`: 本地规则库
- `data/images/*`: 演示图片占位文件
- `data/train.jsonl`
- `data/val.jsonl`

用途：

- 支撑 RAG 检索
- 支撑 CLI 演示
- 支撑训练脚本与数据校验脚本

---

## 4.6 `train/` 训练与推理脚本模块

关键文件：

- `train/common.sh`
- `train/sft_lora.sh`
- `train/infer.sh`
- `train/merge_lora.sh`
- `train/README.md`

作用：

- 对齐运行时与训练时的关键参数。
- 为未来接入真实 ms-swift 推理提供统一入口。

当前脚本对齐的关键参数包括：

- `MODEL_NAME`
- `ADAPTER_PATH`
- `AGENT_TEMPLATE`
- `TOOLS_PROMPT`
- `SEED`
- `LOAD_ARGS`

---

## 4.7 `tests/` 与 `eval/`

### `tests/`

当前测试覆盖：

- 工具服务测试
- 检索模块测试
- 解析模块测试
- 契约一致性测试
- swift adapter 命令拼装测试
- runtime config 归一化测试

### `eval/`

当前最小评测脚本：

- `eval_tool_call.py`
- `eval_diag.py`
- `eval_e2e.py`

作用：

- 快速衡量工具调用准确率
- 评估诊断输出质量
- 评估端到端链路是否可用

---

## 5. 端到端功能流程

## 5.1 输入阶段

CLI 用户输入以下参数：

- `--image`: 商品主图路径
- `--product-id`: 商品 ID
- `--query`: 用户任务描述
- `--config`: 运行配置文件路径
- `--save-trace / --no-save-trace`: 是否保存 Trace

输入示例：

```bash
python -m demo.cli_demo \
  --image data/images/sku_001_main.jpg \
  --product-id SKU_001 \
  --query "请分析这张商品主图是否适合美国站投放，如不适合请直接创建整改任务并生成两条广告文案。"
```

---

## 5.2 配置加载阶段

`planner.load_runtime_config()` 会合并三层配置来源：

1. `DEFAULT_CONFIG`
2. `configs/runtime.yaml`
3. 环境变量覆盖

之后会做配置归一化：

- 将 `seed` 转成 `int`
- 将 `temperature` 转成 `float`
- 将布尔字段转成 `bool`
- 将路径字段转成绝对路径

因此最终运行链路里使用的是“归一化后的配置”。

---

## 5.3 检索阶段

`retrieve_rules()` 的处理流程：

1. 从 `data/kb/` 读取 markdown 文件。
2. 按双换行切分为稳定段落。
3. 将 query、market、category 合并为一个检索查询串。
4. 用正则 tokenizer 切词。
5. 按 query-token 和 chunk-token 的交集数量打分。
6. 若 chunk 中包含 market 关键词，增加额外分数。
7. 返回 Top-3 结果。

输出结构示例：

```json
{
  "source": "sop_ad_creative.md",
  "chunk_id": "sop_ad_creative.md:002",
  "content": "The hero image must make the product the strongest visual focus in the first second.",
  "score": 0.5
}
```

---

## 5.4 Prompt 构造阶段

`runtime_json_prompt()` 会把以下内容组装到一个字符串 Prompt 中：

- 系统角色
- 严格 JSON 输出要求
- 运行时 JSON schema 样例
- 当前可用工具 schema
- 检索得到的规则片段
- 用户任务文本
- `<image>` 占位符

这样做的目的：

- 保证输出结构稳定
- 把工具能力显式暴露给模型
- 将规则依据注入推理上下文

---

## 5.5 模型调用阶段

### mock 路径

当 `model_mode=mock` 时：

- 进入 `mock_model()`
- 根据 query 中是否出现“创建整改任务”“广告文案”等关键词生成固定格式 JSON
- 直接返回字符串形式的运行时 JSON

当前 mock 路径的特点：

- 适合无模型环境快速演示
- 可稳定复现结果
- 不依赖 GPU 或 checkpoint

### swift 路径

当 `model_mode=swift` 时：

- 进入 `swift_model_adapter()`
- 在当前运行目录下生成：
  - `swift_request.jsonl`
  - `swift_stdout.log`
  - `swift_stderr.log`
  - `swift_result.jsonl`（若命令成功）
- 调用 `train/infer.sh`
- 从结果文件中提取 assistant 输出文本

当前状态：

- 适配层已打通
- 但是否真正推理成功取决于当前环境里是否安装了 `swift` 命令、是否有可用模型和 adapter

---

## 5.6 解析阶段

`parse_model_output()` 会尝试把模型输出变成 `ModelRuntimeOutput`：

1. 从原始文本中抽取 JSON 对象
2. 解析 JSON
3. 用 Pydantic 校验字段类型与结构

成功后得到：

- `task_understanding`
- `evidence`
- `need_rag`
- `need_tool_call`
- `tool_calls`
- `final_response`

失败时：

- 返回标准错误对象
- planner 会把错误写进 Trace

---

## 5.7 工具执行阶段

`execute_tool_calls()` 会依次处理模型生成的 `tool_calls`：

1. 根据工具名在 `tool_registry.py` 查找 executor
2. 根据工具定义拼接 HTTP 请求
3. 调用本地 FastAPI 服务
4. 收集：
   - `name`
   - `arguments`
   - `success`
   - `status_code`
   - `response`
   - `error`

当前支持的典型工具调用：

- `create_opt_task`
- `generate_ad_copy`

若本地工具服务没有启动：

- 请求会失败
- 但主流程不会崩
- 最终响应会追加失败提示

---

## 5.8 最终响应阶段

planner 会根据模型解析结果与工具执行结果生成最终响应：

- 模型调用失败：返回简洁失败提示，并把详细错误放进 Trace
- 模型输出解析失败：返回 parse error 提示
- 工具执行成功：返回模型生成的最终回复
- 工具部分失败：在最终回复后追加失败说明

因此最终对用户可见的是一个相对稳定的文本结果，而更细节的问题排查信息保留在 Trace 文件中。

---

## 6. Trace 机制说明

每次运行默认都会创建目录：

```text
runs/<timestamp>_<product_id>/
```

例如：

```text
runs/20260404_152308_sku_001/
```

当前会落盘的核心文件包括：

- `input.json`: 原始输入
- `retrieval.json`: 检索结果
- `prompt.txt`: 最终 Prompt
- `raw_model_output.txt`: 模型原始输出
- `parsed_output.json`: 解析后的结构化输出
- `tool_results.json`: 工具调用结果
- `final_response.txt`: 最终返回文本
- `config.json`: 本次运行的配置快照

swift 模式下还可能额外出现：

- `swift_request.jsonl`
- `swift_result.jsonl`
- `swift_stdout.log`
- `swift_stderr.log`

Trace 的价值：

- 方便定位是检索问题、Prompt 问题、模型问题还是工具问题
- 非常适合面试演示时解释 Agent 的可观测性
- 后续也可作为评测或回归分析的依据

---

## 7. mock 与 swift 两条运行路径

## 7.1 mock 路径

适用场景：

- 本地没有 GPU
- 没有真实模型
- 希望快速展示项目结构和 Agent 链路

运行方式：

1. 启动本地工具服务
2. 保持 `model_mode: mock`
3. 执行 CLI demo

特点：

- 稳定
- 快速
- 无外部模型依赖
- 最适合面试现场演示

## 7.2 swift 路径

适用场景：

- 已安装 `swift`
- 已准备好基础模型与 adapter
- 希望把 mock 模式替换为真实推理

运行方式：

1. 配置 `configs/runtime.yaml` 或环境变量：
   - `MODEL_MODE=swift`
   - `MODEL_NAME`
   - `ADAPTER_PATH`
   - `AGENT_TEMPLATE`
   - `TOOLS_PROMPT`
2. 执行 CLI demo
3. 查看 `runs/<case>/swift_*` 文件

特点：

- 已打通适配层
- 可与训练脚本使用相同关键参数
- 真正能否成功依赖本地 swift 环境和模型资源

---

## 8. 功能点清单

当前项目已具备的功能：

- 本地工具服务启动与工具调用
- 商品信息和库存信息查询
- 整改任务创建
- 广告文案生成
- 本地 markdown 规则检索
- runtime Prompt 构造
- mock 模型 JSON 输出
- swift 推理适配层
- 模型输出解析与字段校验
- 工具执行结果收集
- 完整 Trace 落盘
- CLI 面试演示入口
- 训练脚本和推理脚本
- 数据生成脚本与数据校验脚本
- 单元测试、契约测试、最小评测脚本

---

## 9. 典型演示流程

在面试或汇报场景下，可以按下面顺序演示：

### 第一步：启动工具服务

```bash
uvicorn tools.app:app --reload --port 8000
```

### 第二步：运行 CLI demo

```bash
python -m demo.cli_demo \
  --image data/images/sku_001_main.jpg \
  --product-id SKU_001 \
  --query "请分析这张商品主图是否适合美国站投放，如不适合请直接创建整改任务并生成两条广告文案。"
```

### 第三步：展示 CLI 输出中的 6 个重点

- Runtime Config
- Retrieved Rules
- Model Output
- Tool Calls
- Tool Results
- Final Response

### 第四步：打开 `runs/` 目录展示可追踪性

重点展示：

- `prompt.txt`
- `raw_model_output.txt`
- `tool_results.json`
- `final_response.txt`

### 第五步：补充说明 mock 与 swift 的切换

可以说明：

- mock 模式用于演示稳定链路
- swift 模式通过 `agent/model_adapter.py` 和 `train/infer.sh` 接入真实推理
- 训练与推理参数已对齐，便于后续替换模型

---

## 10. 测试与评测说明

### 测试

运行方式：

```bash
pytest -q
```

当前重点测试内容：

- Tool API 是否返回稳定结构
- Retriever 是否正常加载和排序
- Parser 是否正确处理合法 / 非法 JSON
- Tool schema 是否与 Prompt / 训练数据一致
- swift adapter 命令拼装是否正确
- runtime config 是否正确归一化

### 评测

运行方式：

```bash
python eval/eval_tool_call.py
python eval/eval_diag.py
python eval/eval_e2e.py
```

当前评测目标：

- tool name accuracy
- argument exact match
- evidence item hit rate
- final action correctness
- end-to-end success rate

---

## 11. 当前实现边界

当前项目是可演示、可扩展的 Agent Demo，但仍有明确边界：

- 没有前端 UI
- 没有数据库持久化
- 没有用户系统和权限系统
- 工具服务是 mock，不是真实 ERP / CRM
- 检索是轻量规则检索，不是向量检索
- swift 模式适配层已实现，但真实效果依赖本地模型环境

---

## 12. 后续可扩展方向

基于当前结构，后续比较自然的扩展包括：

- 将 `mock_db.py` 替换为真实业务接口
- 增加更多工具，如 `submit_ab_test`
- 用更强的检索方法替换当前关键词检索
- 将 runtime JSON 输出与评测集进一步对齐
- 增加 Web Demo 或 Streamlit Demo
- 增加更多训练样本模板和复杂场景

---

## 13. 总结

从当前代码实现来看，`seller-copilot-agent` 已经具备一个完整 Agent 系统最关键的闭环能力：

- 有输入
- 有检索
- 有 Prompt
- 有模型输出协议
- 有工具执行
- 有结果汇总
- 有 Trace
- 有测试和评测

它的最大特点不是功能复杂，而是结构清晰、链路完整、可解释、可扩展，非常适合用于：

- 面试项目展示
- Agent 系统骨架示例
- 后续继续演化成真实业务 Demo 的起点
