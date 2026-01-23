#!/bin/bash
# Quick fix script for VS Code terminal conda activation

echo "=== VS Code Terminal Conda Activation Fix ==="
echo ""

# 1. Check if conda is available
echo "1. Checking conda installation..."
if [ -f ~/miniconda3/etc/profile.d/conda.sh ]; then
    echo "   ✓ conda.sh found"
    source ~/miniconda3/etc/profile.d/conda.sh
else
    echo "   ✗ conda.sh not found at ~/miniconda3/etc/profile.d/conda.sh"
    exit 1
fi

# 2. Check if qlib environment exists
echo ""
echo "2. Checking qlib environment..."
if conda env list | grep -q "^qlib "; then
    echo "   ✓ qlib environment exists"
else
    echo "   ✗ qlib environment not found"
    exit 1
fi

# 3. Try to activate qlib
echo ""
echo "3. Activating qlib environment..."
conda activate qlib
if [ $? -eq 0 ]; then
    echo "   ✓ qlib activated successfully"
else
    echo "   ✗ Failed to activate qlib"
    exit 1
fi

# 4. Verify Python
echo ""
echo "4. Verifying Python..."
echo "   Python: $(which python)"
echo "   Version: $(python --version)"
echo "   Conda ENV: $CONDA_DEFAULT_ENV"

# 5. Add to .bashrc if needed
echo ""
echo "5. Checking ~/.bashrc configuration..."
if grep -q "# Auto-activate qlib for VS Code" ~/.bashrc; then
    echo "   ✓ Auto-activation already configured in ~/.bashrc"
else
    echo "   Adding auto-activation to ~/.bashrc..."
    cat >> ~/.bashrc << 'EOF'

# Auto-activate qlib for VS Code (added by fix script)
if [[ "$TERM_PROGRAM" == "vscode" ]] && [[ -z "$CONDA_DEFAULT_ENV" ]]; then
    if [ -f ~/miniconda3/etc/profile.d/conda.sh ]; then
        source ~/miniconda3/etc/profile.d/conda.sh
        conda activate qlib 2>/dev/null
    fi
fi
EOF
    echo "   ✓ Auto-activation added to ~/.bashrc"
fi

echo ""
echo "=== Fix Complete ==="
echo ""
echo "Next steps:"
echo "1. Close ALL VS Code terminals (click the trash icon on each)"
echo "2. Open a new terminal: Ctrl+Shift+\`"
echo "3. You should see: (qlib) watson@u24:~/work/qlib$"
echo ""
echo "If it still doesn't work, completely close and reopen VS Code."
