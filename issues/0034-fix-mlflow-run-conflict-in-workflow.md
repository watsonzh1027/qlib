# 0034-fix-mlflow-run-conflict-in-workflow

Status: CLOSED
Created: 2025-11-08 15:00:00

## Problem Description
The crypto workflow failed with MLflow error: "Run with UUID ... is already active. To start a new run, first end the current run with mlflow.end_run()."

This occurred because `model.fit()` starts an MLflow run, and then the code attempts to start another run for backtesting without ending the first one.

## Root Cause
Qlib's model training automatically starts an MLflow run for experiment tracking. When the workflow then tries to start a new experiment run for signal generation and backtesting, MLflow detects the active run and throws an error.

## Solution
Added `mlflow.end_run()` after model training to properly close the run started by `model.fit()`, allowing the subsequent experiment run for backtesting to start cleanly.

Modified `workflow_crypto.py`:
- Imported `mlflow` module
- Added `mlflow.end_run()` after `train_crypto_model()` call

## Update Log
- 2025-11-08: Identified MLflow run conflict in workflow execution
- 2025-11-08: Added mlflow import and end_run() call after model training
- 2025-11-08: Verified workflow completes successfully with proper run management