# 项目概览
- **目标**：利用大模型从化学论文中抽取含氟材料的合成方法、物化性质与应用信息。
- **最小样例**：`draft/main.ipynb` 已跑通一个端到端流程（读取原始数据、调用模型、校验输出）。
- **运行环境**：统一使用 [pixi](https://pixi.sh/latest/) 管理依赖；Notebook 需要 `notebook` 虚拟环境。
- **核心代码**：均位于 `src/extract4chem_fluorine` 下，`entities/抽取.py` 定义了抽取结果的数据模型，`tool.py` 提供任务调度逻辑。

# 目录速览
```
.
├── data
│   ├── raw/                 # 原始样例与需求描述（请勿直接改动）
│   └── out/                 # 运行产出的结构化结果示例
├── draft/main.ipynb         # 最小可运行样例（重点）
├── prompts/                 # LLM 提示词，抽取指令存放于 `抽取.txt`
├── src/extract4chem_fluorine    # 核心代码，后续跑脚本扩展
│   ├── entities/抽取.py     # Pydantic 数据模型
│   └── tool.py              # 主要业务逻辑
├── pixi.lock                # 锁定依赖
└── pyproject.toml           # 项目配置
```

# 准备工作
1. **安装 pixi（一次性）**
   
2. **克隆仓库并同步依赖**
   ```bash
   git clone <repo_url>
   cd extract4chem_fluorine
   pixi install
   pixi install --environment notebook
   ```
   默认会生成名为 `extract4chem_fluorine-<版本>` 的环境。

# 运行最小样例（推荐使用 VS Code）
3. **用 VS Code 打开仓库**
   - 安装 VS Code 扩展：Python、Jupyter。
   - 在 VS Code 中打开 `draft/main.ipynb`，选择右上角内核为 `Python: notebook`。
4. **运行 Notebook**
   - 按顺序执行每个单元，即可查看从原始文本到结构化 JSON 的完整流程。

# 数据与配置
- `data/raw/full.md`：示例论文片段原文。
- `data/raw/data_sample.jsonc`：结构化抽取的目标格式与字段约束（含注释）。
- `prompts/抽取.txt`：给大模型的提示词模版，可根据业务需要调整。
- `data/out/extraction_results.json`：Notebook 运行后的示例输出，可用于比对。


# 后续拓展建议
- 结合实际论文扩展 `data/raw` 样本，并在 `draft/main.ipynb` 复制新的工作表。
- 根据 ` entities/抽取.py` 的数据模型添加字段或校验逻辑，确保输出质量。
- 将 Notebook 中的流程拆分为可复用的模块，并在 `src/extract4chem_fluorine` 中沉淀脚本或命令。

如遇环境或数据问题，先确认 pixi 环境是否安装成功，再比对 Notebook 中的运行日志。