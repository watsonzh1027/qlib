#!/bin/bash
# Project-specific terminal initialization for qlib
# This file is only sourced by VS Code terminals in this workspace

# First, source user's bashrc to load their configurations
if [ -f ~/.bashrc ]; then
    source ~/.bashrc
fi

# Then initialize conda and activate qlib (this will set the prompt correctly)
if [ -f ~/miniconda3/etc/profile.d/conda.sh ]; then
    # Initialize conda
    source ~/miniconda3/etc/profile.d/conda.sh
    
    # Activate qlib environment (suppress error messages if already activated)
    if [ "$CONDA_DEFAULT_ENV" != "qlib" ]; then
        conda activate qlib 2>/dev/null
        if [ $? -eq 0 ]; then
            echo "✓ qlib environment activated"
        fi
    fi
fi
