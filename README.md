# Seller Copilot Agent

一个以 mock-first 为核心的多模态电商智能体演示项目，用于商品主图诊断、规则检索、工具调用，以及可追踪结果输出。

## 架构

```
用户查询 + 图片
        |
        v
     CLI 演示
        |
        v
      Planner
   /     |      \
  v      v       v
 RAG   Prompt   模型（mock/swift）
  |                 |
  v                 v
检索到的规则      JSON 工具调用
        \         /
         v       v
         工具执行器
               |
               v
          FastAPI 工具服务
               |
               v
             最终响应
               |
               v
           runs/* 轨迹记录
```

## 功能特性

- 基于 FastAPI 的 mock 工具服务，支持商品信息查询、库存查询、整改任务创建和广告文案生成
- 基于 `data/kb` 的本地确定性 Markdown 检索
- 输出严格 JSON 的 mock 运行时模型
- 具备模块化终端输出的 CLI 演示
- 在 `runs/` 目录下持久化保存运行轨迹

## 安装

```bash
pip install -r requirements.txt
```

## 启动工具服务

```bash
uvicorn tools.app:app --reload --port 8000
```

## 运行 CLI 演示

```bash
python -m demo.cli_demo \
  --image data/images/sku_001_main.jpg \
  --product-id SKU_001 \
  --query "请分析这张商品主图是否适合美国站投放，如不适合请直接创建整改任务并生成两条广告文案。"
```

## 训练脚本

参见 `train/README.md`。

## 评估

评估脚本计划在下一轮迭代中补充。

## 项目亮点

- 默认采用 mock 模式，因此即使没有 GPU 也可以直接运行演示
- 工具 schema 统一集中在 `agent/tool_registry.py`
- 训练协议与运行时协议被有意解耦，便于维护与扩展