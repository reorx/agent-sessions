# Agent Guide

## 项目定位

这个仓库是一个 Agent Session 的 Static Site Generator，将各种 Coding Agent 生成的原始 Transcript 转换成可浏览的网页，并发布到 GitHub Pages。

主流程（三阶段 pipeline）：

1. 将原始对话记录放入对应 agent 目录的 `raw/` 子目录
2. 运行该 agent 对应的 parser 脚本，将原始文件转化为标准 JSONL 中间格式
3. 运行统一的 HTML 渲染脚本，将 JSONL 生成 HTML 页面
4. 生成目录索引页
5. Push 到 `master` 后由 GitHub Actions 自动构建并部署 `dist/`

## 目录说明

- `claude-code/`
  - Claude Code agent 目录
  - `raw/` 子目录存放原始 `.txt` 导出文件
  - 根目录下生成标准 `.jsonl` 中间文件
- `codex/`
  - Codex agent 目录
  - `raw/` 子目录存放原始 `.jsonl` 导出文件
  - 根目录下生成标准 `.jsonl` 中间文件
- `models.py`
  - Pydantic 模型定义，所有脚本共用
  - 定义 `SessionMeta` 和 `Message` 两个模型
- `parse-claude-code.py`
  - Claude Code 专用 parser
  - 读取 `claude-code/raw/*.txt`，输出 `claude-code/*.jsonl`
- `render-html.py`
  - 统一 HTML 渲染器
  - 读取任意标准 JSONL，输出对应 HTML
- `generate-index.py`
  - 为目录生成 `index.html`
  - 用于 `dist/` 根目录和各 agent 子目录
- `static/conversation.css`
  - 会话页面样式
- `static/conversation.js`
  - 会话页面交互逻辑
  - 包括 `j/k` 导航、焦点切换、长写文件消息折叠
- `build.sh`
  - 本地和 CI 共用的构建入口
  - 串联 parse → render → index 三个阶段
- `dev.sh`
  - 本地预览入口
  - 会先构建 `dist/`，再启动静态服务器并用 `watchexec` 监听变更
- `.github/workflows/deploy.yml`
  - GitHub Pages 部署工作流
- `dist/`
  - 构建产物目录
  - 应视为可再生文件，不应手工维护

## 标准 JSONL 中间格式

所有 agent parser 输出统一的 JSONL 格式，由 `models.py` 中的 Pydantic 模型定义：

- 第一行：`SessionMeta` — 包含 `title`、`description`、`agent`（agent 类型）、`source`（原始文件名）
- 后续每行：`Message` — 包含 `role`（user/assistant/system/header）、`content`（去掉原始前缀标记的纯文本）、`is_navigable`、`is_write_file`

## 构建与预览

常用命令：

- `./build.sh`
  - 清理并重建 `dist/`
- `./dev.sh`
  - 本地预览 `dist/`
- `uv run parse-claude-code.py claude-code/raw/INPUT.txt`
  - 单文件 parse
- `uv run render-html.py INPUT.jsonl -o OUTPUT.html --css ../static/conversation.css --js ../static/conversation.js`
  - 单文件 render

依赖约束：

- `build.sh` 依赖 `uv`
- `dev.sh` 依赖 `watchexec`
- 索引页生成使用系统 `python`
- `models.py` 依赖 `pydantic`

## 发布流程

- 触发条件：push 到 `master` 或手动触发 workflow
- CI 步骤：
  1. Checkout 仓库
  2. 安装 `uv`
  3. 执行 `./build.sh`
  4. 上传 `dist/`
  5. 发布到 GitHub Pages

如果本地改动会影响生成结果，提交前至少执行一次 `./build.sh`。

## 修改约定

- 优先修改源文件，不要手改 `dist/`
- 新增 Transcript 时，放入对应 agent 目录的 `raw/` 子目录，然后重新构建
- 修改页面表现时，优先检查这些位置是否都需要同步：
  - `render-html.py`
  - `static/conversation.css`
  - `static/conversation.js`
- 新增 agent 支持时，需要：
  1. 编写 `parse-<agent>.py`，读取 `<agent>/raw/*`，输出 `<agent>/*.jsonl`
  2. 在 `build.sh` 的 parse 阶段添加调用
  3. 渲染和索引阶段自动覆盖，无需改动

## 已知实现特征

- 页面宽度会按内容最长行动态计算
- "写文件"类助手消息会被识别并折叠
- 索引页是极简静态目录，不依赖前端框架
- 整个项目是脚本驱动，而不是包化应用

## 对后续 Agent 的建议

- 大多数改动围绕"输入格式、解析逻辑、中间格式、展示样式、发布流程"五类问题展开
- 做任何结构性改动前，先确认 GitHub Pages 产物是否仍然完全位于 `dist/`
- 完成改动后，至少验证一次构建是否成功；如果改了交互或样式，再本地打开 `dist/` 检查页面
- 不要在 `render-html.py` 里写 agent 特定的解析逻辑，那是各 parser 的职责
