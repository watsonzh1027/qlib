# 项目级别 VS Code 终端自动激活 qlib 环境

## ✅ 解决方案

**仅在本项目中自动激活 qlib 环境，不影响其他项目或全局终端配置。**

## 📁 相关文件

- `.vscode/settings.json` - VS Code 工作区设置（仅本项目生效）
- `.vscode/terminal-init.sh` - 项目级别的终端初始化脚本
- `.vscode/test_terminal.sh` - 测试脚本

## 🔧 工作原理

1. **VS Code 设置** (`.vscode/settings.json`)：
   ```json
   "terminal.integrated.profiles.linux": {
       "bash": {
           "path": "bash",
           "args": ["--init-file", "${workspaceFolder}/.vscode/terminal-init.sh"]
       }
   }
   ```
   - 使用 `--init-file` 参数指定项目专属的初始化脚本
   - `${workspaceFolder}` 确保脚本路径相对于当前项目

2. **初始化脚本** (`.vscode/terminal-init.sh`)：
   - 只在 VS Code 终端中运行
   - 初始化 conda 并激活 qlib 环境
   - 然后加载用户的 `~/.bashrc` 以保留其他配置
   - **不修改任何全局配置文件**

## 📋 使用步骤

### 1. 重新加载 VS Code 窗口
- 按 `Ctrl+Shift+P`
- 输入 "Reload Window"
- 回车

### 2. 关闭所有旧终端
- 点击每个终端标签的 🗑️ 图标
- 或右键选择 "Kill All Terminals"

### 3. 打开新终端
- 按 `Ctrl+Shift+\``
- 或点击：Terminal → New Terminal

### 4. 验证环境
应该看到：
```bash
✓ qlib environment activated (project-specific)
(qlib) watson@u24:~/work/qlib$
```

## 🧪 测试配置

运行测试脚本：
```bash
./.vscode/test_terminal.sh
```

**预期输出：**
```
=== Testing Project-Specific Terminal Environment ===

1. Current working directory:
   PWD = /home/watson/work/qlib

2. Checking if in qlib project:
   ✓ In qlib project directory

3. Checking CONDA_DEFAULT_ENV:
   CONDA_DEFAULT_ENV = qlib

4. Checking active conda environment:
* qlib          /home/watson/miniconda3/envs/qlib

5. Python location:
   /home/watson/miniconda3/envs/qlib/bin/python

6. Python version:
   Python 3.12.7

7. Verifying qlib environment:
   ✓ qlib environment is active

8. Checking VS Code workspace:
   ✓ Running in VS Code terminal

9. Checking init script:
   ✓ Project init script exists
```

## 🎯 优势

### ✅ 仅项目级别
- **不修改** `~/.bashrc` 或 `~/.bash_profile`
- **不影响**其他项目的 VS Code 终端
- **不影响**系统终端或其他应用

### ✅ 灵活性
- 在本项目中：自动激活 qlib
- 在其他项目中：使用默认配置
- 在系统终端中：不受影响

### ✅ 可维护性
- 所有配置都在 `.vscode/` 目录中
- 可以随项目一起版本控制
- 团队成员克隆项目后也能自动工作

## 🔍 验证项目隔离

### 测试 1: 本项目中的终端
```bash
# 在 qlib 项目的 VS Code 中打开终端
echo $CONDA_DEFAULT_ENV
# 应输出: qlib
```

### 测试 2: 其他项目中的终端
```bash
# 在其他项目的 VS Code 中打开终端
echo $CONDA_DEFAULT_ENV
# 应输出: (空) 或其他环境
```

### 测试 3: 系统终端
```bash
# 打开系统终端 (Ctrl+Alt+T)
echo $CONDA_DEFAULT_ENV
# 应输出: (空) - 不受影响
```

## ⚙️ 自定义配置

### 修改环境名称
如果需要激活不同的 conda 环境，编辑 `.vscode/terminal-init.sh`：

```bash
# 将 "qlib" 改为你的环境名
conda activate your_env_name 2>/dev/null
```

### 添加额外的初始化命令
在 `.vscode/terminal-init.sh` 中添加：

```bash
# 例如：设置环境变量
export MY_VAR="value"

# 例如：切换到特定目录
cd scripts/
```

## 🐛 故障排查

### 问题 1: 新终端没有激活 qlib

**检查步骤：**
```bash
# 1. 确认初始化脚本存在且可执行
ls -la .vscode/terminal-init.sh
# 应该显示: -rwxr-xr-x ... terminal-init.sh

# 2. 手动测试脚本
bash --init-file .vscode/terminal-init.sh

# 3. 检查 VS Code 设置
cat .vscode/settings.json | grep -A5 "terminal.integrated.profiles"
```

**解决方案：**
1. 确保已重新加载 VS Code 窗口
2. 关闭所有旧终端后再打开新的
3. 完全退出并重启 VS Code

### 问题 2: 出现 "command not found: conda"

**原因：** conda 未正确安装或路径不对

**检查：**
```bash
ls -la ~/miniconda3/etc/profile.d/conda.sh
```

**修复：** 如果路径不同，编辑 `.vscode/terminal-init.sh` 修改 conda.sh 路径

### 问题 3: 环境激活但提示消失

**原因：** 可能是 PS1 提示符被覆盖

**检查 `.bashrc`：**
```bash
grep "PS1=" ~/.bashrc
```

**解决：** 确保 `.bashrc` 中的 PS1 设置在最后

## 📝 注意事项

1. **不要提交敏感信息**
   - `.vscode/terminal-init.sh` 可以提交到版本控制
   - 不要在其中包含密码或密钥

2. **团队协作**
   - 团队成员需要有相同的 conda 环境
   - 可以在项目 README 中说明环境名称

3. **性能影响**
   - 首次打开终端可能需要 1-2 秒初始化
   - 这是正常的 conda 环境激活时间

## 🆚 与全局配置的对比

| 特性 | 项目级配置 | 全局配置 |
|------|-----------|---------|
| 影响范围 | 仅本项目 | 所有终端 |
| 配置位置 | `.vscode/` | `~/.bashrc` |
| 版本控制 | 可提交 | 不应提交 |
| 团队共享 | 容易 | 困难 |
| 冲突风险 | 低 | 高 |
| 灵活性 | 高 | 低 |

## ✨ 最佳实践

1. **保持脚本简洁**
   - 只包含必要的环境激活
   - 避免复杂的逻辑

2. **添加错误处理**
   - 使用 `2>/dev/null` 抑制错误
   - 检查命令执行状态

3. **文档化配置**
   - 在项目 README 中说明
   - 注释脚本中的关键部分

4. **定期测试**
   - 使用提供的测试脚本
   - 确保新成员能正常使用
