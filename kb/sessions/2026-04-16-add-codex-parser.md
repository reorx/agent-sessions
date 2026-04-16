---
created: 2026-04-16
tags:
  - codex
  - parser
  - pipeline
  - jsonl
---

# 为 Codex agent 添加 raw JSONL 解析器

## 概要

前序 session 完成了 3 阶段 SSG pipeline（parse → JSONL → HTML）的重构，仅支持 Claude Code。本次 session 扩展 pipeline，新增 `parse-codex.py` 以支持 Codex CLI 导出的 rollout JSONL 文件。工作流程为：先用 `/plan` 模式分析 Codex raw 格式（一行一个结构化 JSON，共约 15 种 `type`/`payload.type` 组合），决定哪些条目映射到标准 `Message`、哪些跳过；然后实现 parser；最后更新 `build.sh` 串入 Codex parse 阶段并完成端到端构建验证。实现过程中出现一次意外：单文件模式下默认输出路径 `input_path.with_suffix('.jsonl')` 对已经是 `.jsonl` 后缀的输入返回相同路径，导致原始 raw 文件被解析结果覆盖。原始 Codex 导出未纳入 git 无法恢复，所幸已解析出的标准 JSONL（435 行）正确可用，已挪到 `codex/` 目录下。同时在代码中补了 `output == input` 的保护检查。

## 修改的文件

- `parse-codex.py`（新增）：Codex raw JSONL parser。核心映射：
  - `response_item/message`（role=user/assistant）→ 可导航 Message
  - `response_item/function_call` → assistant Message（格式化为 `$ cmd`）
  - `response_item/function_call_output` → system Message
  - `response_item/custom_tool_call`（apply_patch）→ assistant Message，`is_write_file=True`
  - `response_item/custom_tool_call_output` → system Message
  - `response_item/web_search_call` → assistant Message
  - 跳过：`reasoning`（加密）、所有 `event_msg` 类型、`developer` 角色消息、`turn_context`、`compacted`
- `build.sh`：parse 阶段新增 `uv run parse-codex.py codex/raw/`；两个 parse 调用都加了 raw 目录非空的前置判断（避免空目录时 set -e 中止）
- `codex/rollout-2026-04-01T09-29-40-019d46a9-1a24-7fd1-86ad-32001fbd8d08.jsonl`（新增）：Codex session 解析产物（435 行标准 JSONL，含 1 session_meta + 249 assistant + 16 user + 169 system 消息）
- `dist/codex/`：构建产物，包含 Codex session HTML 和 `index.html`

## Git 提交记录

本次 session 无 git 提交。

## 注意事项

- **parser 的 output 路径陷阱**：当输入文件后缀与输出后缀相同时（比如 Codex raw 和标准 JSONL 都是 `.jsonl`），`Path.with_suffix('.jsonl')` 会返回相同路径，直接写入会覆盖原始文件。新增的两层保护：
  1. 单文件模式下默认把输出放到 `input.parent.parent`（如果 input 在 `raw/` 下）
  2. 显式比较 `output_path.resolve() == input_path.resolve()`，相等则报错退出
- **Codex raw 格式要点**：每行是 `{timestamp, type, payload}`；`type` 只有 4 类（`session_meta`、`event_msg`、`response_item`、`turn_context`、`compacted`），真正承载对话内容的只有 `response_item`；`reasoning` 的 `encrypted_content` 无法解密，必须跳过；`event_msg/agent_message` 与 `response_item/message`（assistant）是同一内容的重复，不能都输出
- **function_call 的 arguments**：是 JSON 字符串而非对象，需要 `json.loads` 解析后再取 `cmd`、`workdir` 等字段。若解析失败应降级为原样输出而非崩溃
- **apply_patch 的标记**：通过 `payload.name == 'apply_patch'` 判断，而不是内容匹配。这个标记驱动 HTML 渲染的折叠行为（`is_write_file=True`）
- **title/description 抽取策略**：Codex 的 `session_meta` 不含人类可读标题，得从第一条 user message 取标题（截断 80 字），从第一条 assistant `phase=final_answer` 取 description（截断 200 字）。如果没有 final_answer（对话被打断），fallback 到任意 assistant 消息
- **raw 文件未入版本控制**：`codex/raw/` 下的原始导出不在 git 中，一旦被覆盖无法恢复。后续新增 agent 时要特别小心类似的 in-place 覆盖风险
- **build.sh 的 raw 目录判空**：改为 `[ "$(ls dir/*.ext 2>/dev/null)" ] && uv run parser.py dir/` 模式，允许 raw 目录为空时跳过 parse 而不中止流水线
