# Libra — 科研智能体

> 一个面向科研全生命周期的 AI 智能体：文献调研、论文复现、实验设计、学术写作。

## 功能

- **系统性文献综述** —— 集成 arXiv 搜索，输出 APA / IEEE / BibTeX 引用格式
- **论文复现** —— 自动缩放规模并在隔离沙箱中执行实验代码
- **实验设计与数据分析** —— 生成出版级可视化图表
- **LaTeX 论文生成** —— 支持 NeurIPS / ICML / ACL 模板，自动编译 PDF
- **跨数据库引文图谱分析** —— 通过 Semantic Scholar 扩展 arXiv 之外的引文数据
- **科研生命周期编排** —— 由 `sci-pi` 子智能体串联完整流程

## 快速开始

```bash
# 1. 安装依赖
make config
make install

# 2. 在 .env 配置你的 LLM API key
echo "DEEPSEEK_API_KEY=sk-..." >> .env

# 3. 启动
make dev
```

浏览器打开 `http://localhost:2026`。

## 架构设计

详见 [`docs/plans/2026-05-03-scideer-design.md`](docs/plans/2026-05-03-scideer-design.md)。

核心组件：

- **Skills** (`skills/public/`, `skills/custom/`) —— Markdown 定义的科研工作流
- **Subagents** (`agents/`) —— 专用智能体，如负责编排的 `sci-pi`
- **MCP 集成** (`extensions_config.json`) —— Semantic Scholar 等外部工具
- **Sandbox** (`docker/scideer-sandbox/`) —— 论文复现实验用的隔离容器
- **评测层** (`benchmarks/sci_eval/`) —— 用于衡量科研任务能力的 mini sci-bench

## 致谢

Libra 基于 [DeerFlow 2.0](https://github.com/bytedance/deer-flow)（字节跳动开源）扩展而来，新增了：

- 两个新 skill：`paper-reproduction`（论文复现）和 `scientific-writing`（学术写作）
- 一个自定义编排子智能体：`sci-pi`
- Semantic Scholar MCP 集成（引文图谱分析）
- 一套 mini sci-bench 评测层

DeerFlow 提供了 harness 底层基础设施（LangGraph 编排、skill 加载、subagent 调度、sandbox 提供者、MCP 客户端）。Libra 在此基础上增加了科研领域专属能力。

## 许可证

保留原 DeerFlow MIT 许可证，详见 [`LICENSE`](LICENSE)。
