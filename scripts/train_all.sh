#!/bin/bash
set -e

# Activate environment if not already (assuming running from a shell that might need it, 
# though usually we run python directly from full path in this environment)
# source activate qlib 

PYTHON_EXEC="/home/watson/miniconda3/envs/qlib/bin/python"
SCRIPT_PATH="scripts/train_multiscale.py"

echo "Starting Multi-Scale Training..."

echo "----------------------------------------------------------------"
echo "Training 240min Model..."
$PYTHON_EXEC $SCRIPT_PATH --timeframe 240min

echo "----------------------------------------------------------------"
echo "Training 60min Model..."
$PYTHON_EXEC $SCRIPT_PATH --timeframe 60min

echo "----------------------------------------------------------------"
echo "Training 15min Model..."
$PYTHON_EXEC $SCRIPT_PATH --timeframe 15min

echo "----------------------------------------------------------------"
echo "All models trained successfully."
