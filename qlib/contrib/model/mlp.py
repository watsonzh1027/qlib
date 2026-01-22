# Simple MLP model for debugging neural network training
# Much simpler than LSTM - easier to identify NaN issues

import numpy as np
import pandas as pd
from typing import Text, Union
import copy
from qlib.utils import get_or_create_path
from qlib.log import get_module_logger

import torch
import torch.nn as nn
import torch.optim as optim

from qlib.model.base import Model
from qlib.data.dataset import DatasetH
from qlib.data.dataset.handler import DataHandlerLP


class MLP(Model):
    """Simple Multi-Layer Perceptron for debugging"""
    
    def __init__(
        self,
        d_feat=162,
        hidden_size=64,
        num_layers=2,
        dropout=0.0,
        n_epochs=100,
        lr=0.00001,  # Very low learning rate to prevent explosion
        metric="",
        batch_size=512,  # Smaller batch size
        early_stop=20,
        loss="mse",
        optimizer="adam",
        GPU=0,
        seed=None,
        **kwargs,
    ):
        self.logger = get_module_logger("MLP")
        self.logger.info("MLP pytorch version...")
        
        self.d_feat = d_feat
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.dropout = dropout
        self.n_epochs = n_epochs
        self.lr = lr
        self.metric = metric
        self.batch_size = batch_size
        self.early_stop = early_stop
        self.optimizer = optimizer.lower()
        self.loss = loss
        self.device = torch.device("cuda:%d" % (GPU) if torch.cuda.is_available() and GPU >= 0 else "cpu")
        self.seed = seed
        
        self.logger.info(f"MLP params: d_feat={d_feat}, hidden={hidden_size}, layers={num_layers}, lr={lr}, batch={batch_size}")
        
        if self.seed is not None:
            np.random.seed(self.seed)
            torch.manual_seed(self.seed)
        
        # Create simple MLP
        self.mlp_model = MLPModel(
            d_feat=self.d_feat,
            hidden_size=self.hidden_size,
            num_layers=self.num_layers,
            dropout=self.dropout,
        )
        
        if optimizer.lower() == "adam":
            self.train_optimizer = optim.Adam(self.mlp_model.parameters(), lr=self.lr)
        elif optimizer.lower() == "gd":
            self.train_optimizer = optim.SGD(self.mlp_model.parameters(), lr=self.lr)
        else:
            raise NotImplementedError(f"optimizer {optimizer} is not supported!")
        
        self.fitted = False
        self.mlp_model.to(self.device)
    
    @property
    def use_gpu(self):
        return self.device != torch.device("cpu")
    
    def mse(self, pred, label):
        loss = (pred - label) ** 2
        return torch.mean(loss)
    
    def loss_fn(self, pred, label):
        mask = ~torch.isnan(label)
        if self.loss == "mse":
            return self.mse(pred[mask], label[mask])
        raise ValueError(f"unknown loss `{self.loss}`")
    
    def metric_fn(self, pred, label):
        mask = torch.isfinite(label)
        if self.metric in ("", "loss"):
            return -self.loss_fn(pred[mask], label[mask])
        raise ValueError(f"unknown metric `{self.metric}`")
    
    def train_epoch(self, x_train, y_train):
        x_train_values = x_train.values
        y_train_values = np.squeeze(y_train.values)
        
        self.mlp_model.train()
        indices = np.arange(len(x_train_values))
        np.random.shuffle(indices)
        
        for i in range(len(indices))[::self.batch_size]:
            if len(indices) - i < self.batch_size:
                break
            
            feature = torch.from_numpy(x_train_values[indices[i:i+self.batch_size]]).float().to(self.device)
            label = torch.from_numpy(y_train_values[indices[i:i+self.batch_size]]).float().to(self.device)
            
            # Check for NaN/Inf in input
            if torch.isnan(feature).any() or torch.isinf(feature).any():
                self.logger.warning(f"NaN/Inf detected in features at batch {i}")
                continue
            
            pred = self.mlp_model(feature)
            loss = self.loss_fn(pred, label)
            
            # Check for NaN in loss
            if torch.isnan(loss):
                self.logger.warning(f"NaN loss at batch {i}")
                continue
            
            self.train_optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.mlp_model.parameters(), 0.5)  # Strong gradient clipping
            self.train_optimizer.step()
    
    def test_epoch(self, data_x, data_y):
        x_values = data_x.values
        y_values = np.squeeze(data_y.values)
        
        self.mlp_model.eval()
        scores = []
        losses = []
        indices = np.arange(len(x_values))
        
        for i in range(len(indices))[::self.batch_size]:
            if len(indices) - i < self.batch_size:
                break
            
            feature = torch.from_numpy(x_values[indices[i:i+self.batch_size]]).float().to(self.device)
            label = torch.from_numpy(y_values[indices[i:i+self.batch_size]]).float().to(self.device)
            
            with torch.no_grad():
                pred = self.mlp_model(feature)
                loss = self.loss_fn(pred, label)
                if not torch.isnan(loss):
                    losses.append(loss.item())
                    score = self.metric_fn(pred, label)
                    if not torch.isnan(score):
                        scores.append(score.item())
        
        if len(scores) == 0:
            return float('nan'), float('nan')
        return np.mean(losses), np.mean(scores)
    
    def fit(self, dataset: DatasetH, evals_result=dict(), save_path=None):
        df_train, df_valid, df_test = dataset.prepare(
            ["train", "valid", "test"],
            col_set=["feature", "label"],
            data_key=DataHandlerLP.DK_L,
        )
        if df_train.empty or df_valid.empty:
            raise ValueError("Empty data from dataset, please check your dataset config.")
        
        x_train, y_train = df_train["feature"], df_train["label"]
        x_valid, y_valid = df_valid["feature"], df_valid["label"]
        
        # Replace NaN/Inf in features with 0
        x_train = x_train.replace([np.inf, -np.inf], np.nan).fillna(0)
        x_valid = x_valid.replace([np.inf, -np.inf], np.nan).fillna(0)
        
        self.logger.info(f"Train shape: {x_train.shape}, Valid shape: {x_valid.shape}")
        self.logger.info(f"Train NaN count: {x_train.isna().sum().sum()}, Inf count: {np.isinf(x_train.values).sum()}")
        self.logger.info(f"Valid NaN count: {x_valid.isna().sum().sum()}, Inf count: {np.isinf(x_valid.values).sum()}")
        
        save_path = get_or_create_path(save_path)
        stop_steps = 0
        best_score = -np.inf
        best_epoch = 0
        best_param = copy.deepcopy(self.mlp_model.state_dict())
        evals_result["train"] = []
        evals_result["valid"] = []
        
        self.logger.info("training...")
        self.fitted = True
        
        for step in range(self.n_epochs):
            self.logger.info(f"Epoch{step}:")
            self.train_epoch(x_train, y_train)
            train_loss, train_score = self.test_epoch(x_train, y_train)
            val_loss, val_score = self.test_epoch(x_valid, y_valid)
            self.logger.info(f"train {train_score:.6f}, valid {val_score:.6f}")
            evals_result["train"].append(train_score)
            evals_result["valid"].append(val_score)
            
            if not np.isnan(val_score) and val_score > best_score:
                best_score = val_score
                stop_steps = 0
                best_epoch = step
                best_param = copy.deepcopy(self.mlp_model.state_dict())
            else:
                stop_steps += 1
                if stop_steps >= self.early_stop:
                    self.logger.info("early stop")
                    break
        
        self.logger.info(f"best score: {best_score:.6f} @ {best_epoch}")
        self.mlp_model.load_state_dict(best_param)
        torch.save(best_param, save_path)
        
        if self.use_gpu:
            torch.cuda.empty_cache()
    
    def predict(self, dataset: DatasetH, segment: Union[Text, slice] = "test"):
        if not self.fitted:
            raise ValueError("model is not fitted yet!")
        
        x_test = dataset.prepare(segment, col_set="feature", data_key=DataHandlerLP.DK_I)
        index = x_test.index
        self.mlp_model.eval()
        x_values = x_test.values
        sample_num = x_values.shape[0]
        preds = []
        
        for begin in range(sample_num)[::self.batch_size]:
            end = min(sample_num, begin + self.batch_size)
            x_batch = torch.from_numpy(x_values[begin:end]).float().to(self.device)
            with torch.no_grad():
                pred = self.mlp_model(x_batch).detach().cpu().numpy()
            preds.append(pred)
        
        return pd.Series(np.concatenate(preds), index=index)


class MLPModel(nn.Module):
    """Simple MLP architecture"""
    def __init__(self, d_feat=162, hidden_size=64, num_layers=2, dropout=0.0):
        super().__init__()
        
        layers = []
        input_size = d_feat
        
        for i in range(num_layers):
            layers.append(nn.Linear(input_size, hidden_size))
            layers.append(nn.ReLU())
            if dropout > 0:
                layers.append(nn.Dropout(dropout))
            input_size = hidden_size
        
        layers.append(nn.Linear(hidden_size, 1))
        
        self.mlp = nn.Sequential(*layers)
    
    def forward(self, x):
        return self.mlp(x).squeeze()
