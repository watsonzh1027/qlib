# VS Code Terminal Auto-Activate qlib Environment

## 问题
VS Code 终端打开时没有自动激活 qlib conda 环境。

## 解决方案

已更新 `.vscode/settings.json` 添加以下配置：

### 1. 基础 Python 设置
```json
"python.terminal.activateEnvironment": true,
"python.defaultInterpreterPath": "~/miniconda3/envs/qlib/bin/python",
"python.terminal.activateEnvInCurrentTerminal": true
```

### 2. 终端环境变量
```json
"terminal.integrated.env.linux": {
    "CONDA_DEFAULT_ENV": "qlib"
}
```

### 3. 自定义终端配置文件（最重要）
```json
"terminal.integrated.profiles.linux": {
    "qlib-conda": {
        "path": "bash",
        "args": ["-c", "source ~/miniconda3/etc/profile.d/conda.sh && conda activate qlib && exec bash"]
    }
},
"terminal.integrated.defaultProfile.linux": "qlib-conda"
```

## 使用方法

### 应用新配置

1. **重新加载 VS Code 窗口**
   - 按 `Ctrl+Shift+P`
   - 输入 "Reload Window"
   - 回车

   或者

2. **关闭并重新打开 VS Code**
   - 完全退出 VS Code
   - 重新打开项目

### 打开新终端

1. 使用快捷键：`Ctrl+Shift+\`` 或 `Ctrl+\``
2. 或点击菜单：Terminal → New Terminal
3. 新终端应该自动显示 `(qlib)` 前缀

### 测试终端环境

在新终端中运行测试脚本：
```bash
./.vscode/test_terminal.sh
```

**预期输出：**
```
=== Testing Terminal Environment ===

1. Checking CONDA_DEFAULT_ENV:
   CONDA_DEFAULT_ENV = qlib

2. Checking active conda environment:
* qlib          /home/watson/miniconda3/envs/qlib

3. Python location:
   /home/watson/miniconda3/envs/qlib/bin/python

4. Python version:
   Python 3.x.x

5. Verifying qlib environment:
   ✓ qlib environment is active

===================================
```

## 手动切换终端配置

如果需要使用不同的终端配置：

1. 点击终端右上角的 `+` 旁边的下拉箭头
2. 选择终端类型：
   - **qlib-conda** - 自动激活 qlib 环境（默认）
   - **bash** - 标准 bash（不自动激活）
   - 其他已安装的 shell

## 故障排查

### 问题 1: 终端仍未激活 qlib 环境

**解决方案：**
1. 确认已重新加载 VS Code 窗口
2. 关闭所有旧的终端标签页
3. 打开新的终端

### 问题 2: 出现 "conda: command not found"

**解决方案：**
检查 conda 路径是否正确：
```bash
ls -la ~/miniconda3/etc/profile.d/conda.sh
```

如果路径不同，修改 `.vscode/settings.json` 中的路径。

### 问题 3: VS Code Python 扩展不识别 qlib 环境

**解决方案：**
1. 按 `Ctrl+Shift+P`
2. 输入 "Python: Select Interpreter"
3. 选择 `~/miniconda3/envs/qlib/bin/python`

### 问题 4: 每次打开终端都很慢

**解决方案：**
这是正常的，因为需要初始化 conda 环境。通常只需 1-2 秒。

如果太慢（>5秒），可以优化 `~/.bashrc` 或 `~/.bash_profile` 中的 conda 初始化代码。

## 验证完整设置

运行以下命令验证所有组件：

```bash
# 1. 检查 VS Code 设置
cat .vscode/settings.json | grep -A5 "terminal.integrated"

# 2. 检查 Python 解释器
which python
python --version

# 3. 检查 conda 环境
conda env list

# 4. 运行测试脚本
./.vscode/test_terminal.sh
```

## 额外提示

### 为所有项目启用（可选）

如果希望所有项目都自动激活 qlib 环境：

1. 打开 VS Code 用户设置：`Ctrl+,`
2. 点击右上角的 `{}` 图标（打开 settings.json）
3. 将相同的配置添加到用户级别的 settings.json

### 使用其他 conda 环境

如果项目需要不同的环境，只需修改 `.vscode/settings.json`：

```json
"terminal.integrated.profiles.linux": {
    "my-env-conda": {
        "path": "bash",
        "args": ["-c", "source ~/miniconda3/etc/profile.d/conda.sh && conda activate my-env && exec bash"]
    }
},
"terminal.integrated.defaultProfile.linux": "my-env-conda"
```

### 性能优化

如果启动速度是问题，可以考虑：

1. 使用 mamba 代替 conda（更快）
2. 精简环境中的包
3. 使用 conda-forge 频道

## 相关文件

- `.vscode/settings.json` - VS Code 项目设置
- `.vscode/test_terminal.sh` - 终端环境测试脚本

## 参考文档

- [VS Code Terminal Profiles](https://code.visualstudio.com/docs/terminal/profiles)
- [VS Code Python Environments](https://code.visualstudio.com/docs/python/environments)
- [Conda User Guide](https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html)
