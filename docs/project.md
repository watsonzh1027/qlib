### 项目总结：qlib-crypto

#### 简介
**qlib-crypto** 是基于微软开源量化投资平台 **Qlib** 的扩展项目，专注于加密货币（Cryptocurrency）领域的量化投资研究和应用。Qlib 是一个 AI 导向的量化投资平台，旨在利用人工智能技术实现量化投资的潜力，从理念探索到生产实施的全链条支持。它支持多种机器学习建模范式，包括监督学习、市场动态建模和强化学习，涵盖数据处理、模型训练、回测、投资组合优化和订单执行等完整量化投资流程。

该项目特别针对加密货币市场，集成了数据收集模块（如 OKX 交易所数据收集器），并遵循测试驱动开发（TDD）原则，确保代码质量和可靠性。项目强调模块化设计，各组件松耦合，可独立使用或组合。

#### 项目结构
项目采用模块化目录结构，便于管理和扩展。主要目录和文件如下：

- **根目录文件**：
  - `README.md`：项目介绍、安装指南和快速开始。
  - `pyproject.toml` / `setup.py` / `requirements.txt`：依赖管理和构建配置。
  - `Dockerfile` / `build_docker_image.sh`：Docker 支持，便于容器化部署。
  - `Makefile`：自动化构建和任务脚本。
  - `LICENSE` / `SECURITY.md` / `CHANGELOG.md`：许可证、安全政策和变更日志。

- **核心代码目录** (`qlib/`)：
  - `backtest/`：回测引擎，支持模拟交易和性能评估。
  - `data/`：数据层框架，包括数据加载、处理和存储。
  - `model/`：预测模型，支持多种算法（如 LightGBM、神经网络）。
  - `strategy/`：交易策略模块，包括信号生成和决策逻辑。
  - `rl/`：强化学习框架，用于连续决策建模。
  - `workflow/`：工作流管理，协调整个研究流程。
  - `utils/` / `config.py` / `constant.py`：工具函数、配置和常量。
  - `contrib/`：社区贡献模块。
  - `tests/`：单元测试和集成测试。

- **脚本和工具** (`scripts/`)：
  - 数据收集脚本，如 `okx_data_collector.py`（OKX 交易所数据收集）、`get_data.py`（通用数据获取）、`convert_to_qlib.py`（数据转换）。
  - 分析和检查脚本，如 `check_data_health.py`（数据健康检查）、`sample_backtest.py`（示例回测）。
  - 配置管理：`config_manager.py`。

- **配置和数据** (`config/` / `data/` / `cache/`)：
  - `config/`：配置文件，如 `instruments.json`（交易仪器）、`workflow.json`（工作流配置）、`top50_symbols.json`（前50加密货币符号）。
  - `data/`：存储数据集，包括 `klines/`（K线数据）和 `qlib_data/`（Qlib 格式数据）。
  - `cache/`：缓存文件，如 `coingecko_marketcap.json`（CoinGecko 市值数据）、`okx_contracts.json`（OKX 合约数据）。

- **测试和示例** (`tests/` / `examples/`)：
  - `tests/`：测试套件，包括单元测试、集成测试和端到端测试，支持覆盖率报告。
  - `examples/`：示例代码，如 `workflow_by_code.py`（代码驱动的工作流）、`run_all_model.py`（多模型运行）、`workflow_by_code.ipynb`（Jupyter Notebook 示例）。

- **文档和规范** (`docs/` / `openspec/` / `issues/`)：
  - `docs/`：Sphinx 文档，包括介绍、安装、组件说明和教程。
  - `openspec/`：OpenSpec 规范，用于规划和提案管理。
  - `issues/`：问题文档，按照 `<number>-<description>.md` 格式记录调试和解决方案。

- **其他**：
  - `htmlcov/`：测试覆盖率报告。
  - `mlruns/`：MLflow 实验跟踪日志。
  - `specs/`：规范文件。

##### 详细目录树状结构
```
qlib-crypto/
├── AGENTS.md                           # OpenSpec 指令文件，用于 AI 助手指导
├── build_docker_image.sh               # Docker 镜像构建脚本
├── CHANGELOG.md                        # 项目变更日志
├── CHANGES.rst                         # 变更记录（RST 格式）
├── Dockerfile                          # Docker 容器配置
├── LICENSE                             # MIT 许可证文件
├── Makefile                            # 自动化构建任务脚本
├── MANIFEST.in                         # Python 包清单文件
├── pyproject.toml                      # 项目配置和依赖（现代 Python 包管理）
├── README.md                           # 项目主要文档，包含介绍、安装和使用指南
├── req-update.txt                      # 依赖更新脚本或列表
├── requirements.txt                    # Python 依赖列表
├── SECURITY.md                         # 安全政策文档
├── setup.py                            # 传统 Python 包安装脚本
├── cache/                              # 缓存目录
│   ├── coingecko_marketcap.json        # CoinGecko 市值数据缓存
│   └── okx_contracts.json              # OKX 合约数据缓存 
├── config/                             # 配置文件目录
│   ├── instruments.json                # 交易仪器配置（加密货币列表）
│   ├── test_symbols.json               # 测试用符号配置
│   ├── top50_symbols.json              # 前50加密货币符号配置
│   └── workflow.json                   # 工作流配置示例
├── data/                               # 数据存储目录
│   ├── klines/                         # K线数据存储
│   └── qlib_data/                      # Qlib 格式化数据存储
├── docs/                               # 文档目录
│   ├── conf.py                         # Sphinx 文档配置
│   ├── data_feeder.md                  # 数据馈送文档
│   ├── index.rst                       # 文档首页（RST 格式）
│   ├── make.bat                        # Windows 文档构建脚本
│   ├── Makefile                        # 文档构建任务
│   ├── requirements.txt                # 文档依赖
│   ├── sync-fork-repo.md               # 仓库同步文档
│   ├── _static/                        # 静态资源
│   ├── advanced/                       # 高级主题文档
│   ├── changelog/                      # 变更日志文档
│   ├── component/                      # 组件文档
│   ├── developer/                      # 开发者指南
│   ├── FAQ/                            # 常见问题解答
│   ├── hidden/                         # 隐藏文档
│   ├── introduction/                   # 介绍文档
│   ├── reference/                      # 参考文档
│   └── start/                          # 入门文档
├── examples/                           # 示例代码目录
│   ├── data_collection_and_storage_explained.md  # 数据收集和存储说明
│   ├── README.md                       # 示例目录说明
│   ├── run_all_model.py                # 运行所有模型的脚本
│   ├── workflow_by_code.ipynb          # Jupyter Notebook 工作流示例
│   ├── workflow_by_code.py             # Python 代码工作流示例
│   ├── benchmarks/                     # 基准测试示例
│   ├── benchmarks_dynamic/             # 动态基准测试
│   ├── data_demo/                      # 数据演示
│   ├── highfreq/                       # 高频交易示例
│   ├── hyperparameter/                 # 超参数调优示例
│   ├── model_interpreter/              # 模型解释示例
│   ├── model_rolling/                  # 模型滚动示例
│   ├── nested_decision_execution/      # 嵌套决策执行示例
│   ├── online_srv/                     # 在线服务示例
│   ├── orderbook_data/                 # 订单簿数据示例
│   ├── portfolio/                      # 投资组合示例
│   ├── rl/                             # 强化学习示例
│   ├── rolling_process_data/           # 滚动数据处理示例
│   └── tutorial/                       # 教程示例 
├── htmlcov/                            # HTML 覆盖率报告
│   ├── class_index.html                # 类索引
│   ├── coverage_html_cb_6fb7b396.js    # 覆盖率 JS
│   ├── function_index.html             # 函数索引
│   ├── index.html                      # 覆盖率首页
│   ├── status.json                     # 状态文件
│   ├── style_cb_6b508a39.css           # 样式文件
│   └── z_*.html                        # 各模块覆盖率详情
├── issues/                             # 问题跟踪目录
│   ├── 0001-implement-crypto-data-feeder-phase1.md  # 问题文档示例
│   ├── 0002-complete-phase1-integration-test.md
│   ├── 0002-fix_okxdatacollector_import_error.md
│   ├── 0003-complete-phase1-final.md
│   └── 0003-fix_relative_import_error.md
├── logs/                               # 日志目录
├── mlruns/                             # MLflow 运行日志
│   ├── 0/                              # 实验 0
│   └── 319424849901669180/             # 具体实验 ID
├── openspec/                           # OpenSpec 规范目录
├── pyqlib.egg-info/                    # Python 包信息
├── qlib/                               # 核心 Qlib 代码
│   ├── __init__.py                     # 包初始化
│   ├── __pycache__/                    # Python 缓存
│   ├── backtest/                       # 回测模块
│   ├── cli/                            # 命令行接口
│   ├── config.py                       # 配置模块
│   ├── constant.py                     # 常量定义
│   ├── contrib/                        # 社区贡献
│   ├── data/                           # 数据模块
│   ├── log.py                          # 日志模块
│   ├── model/                          # 模型模块
│   ├── rl/                             # 强化学习模块
│   ├── strategy/                       # 策略模块
│   ├── tests/                          # 测试模块
│   ├── typehint.py                     # 类型提示
│   ├── utils/                          # 工具模块
│   └── workflow/                       # 工作流模块
├── scripts/                            # 脚本目录
│   ├── README.md                       # 脚本说明
│   ├── __init__.py
│   ├── __pycache__/
│   ├── check_data_health.py            # 数据健康检查脚本
│   ├── check_dump_bin.py               # 二进制转储检查
│   ├── collect_info.py                 # 信息收集脚本
│   ├── config_manager.py               # 配置管理脚本
│   ├── convert_to_qlib.py              # 数据转换脚本
│   ├── data_collector/                 # 数据收集器子目录
│   ├── dump_bin.py                     # 二进制转储脚本
│   ├── dump_pit.py                     # 点对点转储脚本
│   ├── get_data.py                     # 数据获取脚本
│   ├── get_top50.py                    # 获取前50脚本
│   ├── okx_data_collector.py           # OKX 数据收集器
│   └── sample_backtest.py              # 示例回测脚本
├── specs/                              # 规范文件目录
├── test_data/                          # 测试数据目录
└── tests/                              # 测试套件目录
```

##### 重要文件说明
- **README.md**：项目的核心文档，包含项目概述、安装步骤、快速开始指南和主要功能介绍。是新用户入门的首要参考。
- **pyproject.toml**：现代 Python 项目配置文件，定义项目元数据、依赖关系和构建配置。相比 setup.py 更推荐使用。
- **requirements.txt**：列出项目运行所需的 Python 包及其版本，确保环境一致性。
- **Dockerfile**：定义 Docker 容器镜像的构建过程，便于在不同环境中部署和运行项目。
- **Makefile**：自动化脚本集合，包含构建、测试、文档生成等常见任务的快捷命令。
- **config/workflow.json**：示例工作流配置文件，展示如何通过 JSON 配置 Qlib 的数据处理、模型训练和回测流程。
- **examples/workflow_by_code.py**：核心示例脚本，演示如何使用 Python 代码定义完整的量化投资工作流，包括数据加载、模型训练和回测。
- **scripts/okx_data_collector.py**：专门用于从 OKX 加密货币交易所收集数据的脚本，是项目加密货币功能的关键组件。
- **qlib/__init__.py**：Qlib 包的入口文件，定义包的公共接口和初始化逻辑。
- **docs/index.rst**：Sphinx 文档的首页文件，组织整个文档结构，提供导航和内容索引。
- **issues/0001-implement-crypto-data-feeder-phase1.md**：问题跟踪文档示例，记录开发过程中的具体问题、解决方案和调试步骤。

#### 技术栈
- **编程语言**：Python 3.8+（支持 3.8 到 3.12）。
- **核心依赖**（从 `pyproject.toml` 和 `requirements.txt`）：
  - 数据处理：`numpy`、`pandas`（数据操作和分析）。
  - 机器学习：`lightgbm`（梯度提升树）、`scikit-learn`（通用 ML）。
  - 强化学习：`gym`（环境模拟）。
  - 优化：`cvxpy`（凸优化，用于投资组合优化）。
  - 实验管理：`mlflow`（模型跟踪）。
  - 数据存储：`redis`、`pymongo`（缓存和数据库）。
  - 其他：`pyyaml`（配置）、`tqdm`（进度条）、`loguru`（日志）、`fire`（命令行接口）。
- **构建工具**：`setuptools`、`cython`（性能优化）、`pytest`（测试）。
- **部署**：Docker 支持，便于容器化运行。
- **开发环境**：推荐使用 Conda 管理 Python 环境，确保依赖一致性。
- **特殊技术**：
  - 支持高频交易和嵌套决策执行。
  - 集成 RD-Agent（LLM 驱动的自主代理，用于因子挖掘和模型优化）。
  - 点对点（Point-in-Time）数据库，用于历史数据回放。

#### 功能
- **数据处理**：支持多种数据源，包括加密货币交易所（如 OKX）的实时和历史数据。提供数据健康检查、转换和缓存机制。
- **模型训练和预测**：支持监督学习（如 LightGBM、神经网络）、市场动态建模（适应性概念漂移）和强化学习。内置多种 SOTA 模型（如 Transformer、RNN、Tabnet）。
- **回测和策略**：模拟交易执行，支持多种策略（如 TopkDropoutStrategy）。提供投资组合优化和风险建模。
- **分析和报告**：生成信号分析、投资组合分析和性能报告。支持在线服务和自动模型滚动更新。
- **高频和嵌套执行**：支持高频交易场景下的嵌套决策框架。
- **实验管理**：使用 Qlib Recorder 和 MLflow 跟踪实验，支持参数调优和结果可视化。
- **加密货币特定**：集成 CoinGecko 和 OKX 数据，专注于加密货币市场的 alpha 挖掘和策略优化。

#### 使用方法
1. **环境准备**：
   - 激活 qlib Conda 环境：`conda activate qlib`。
   - 安装依赖：`pip install pyqlib`（稳定版）或从源码安装（开发版）。

2. **数据准备**：
   - 下载或收集数据：使用 `scripts/get_data.py` 或 `scripts/okx_data_collector.py` 获取加密货币数据。
   - 初始化 Qlib：`qlib.init(provider_uri="~/.qlib/qlib_data", region=REG_CN)`（或对应区域）。

3. **快速开始**：
   - **命令行接口**：使用 `qrun config/workflow.json` 运行预定义工作流。
   - **代码接口**（参考 `examples/workflow_by_code.py`）：
     - 定义模型、数据集和策略。
     - 训练模型：`model.fit(dataset)`。
     - 生成信号和分析：使用 `SignalRecord` 和 `SigAnaRecord`。
     - 回测：使用 `PortAnaRecord` 配置执行器、策略和基准。
   - 示例运行：`python examples/workflow_by_code.py`（需要 16G 内存和 5G 磁盘）。

4. **测试和调试**：
   - 运行测试：`pytest tests/`（支持覆盖率：`pytest --cov=qlib tests/`）。
   - 调试：遵循 TDD 原则，先写测试。问题记录在 `issues/` 目录，格式为 `<number>-<description>.md`，包含状态、描述和更新日志。

5. **高级用法**：
   - 自定义模型：继承 Qlib 的模型类。
   - 高频交易：参考 `examples/highfreq/`。
   - 强化学习：参考 `examples/rl/`。
   - 在线服务：参考 `component/online.rst`。

6. **贡献和规范**：
   - 使用 OpenSpec（`openspec/`）规划新功能。
   - 遵循 MIT 许可证，提交 PR 前确保测试通过。

该项目适用于量化研究员、数据科学家和开发者，旨在加速加密货币量化投资的研发和部署。如需深入了解特定组件，请参考 `docs/` 或示例代码。