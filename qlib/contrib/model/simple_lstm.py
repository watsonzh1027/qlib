# Simple LSTM wrapper that works with Alpha158 features
# by treating each feature as a separate "timestep"

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


class SimpleLSTM(Model):
    """
    Simplified LSTM that works with Alpha158 features.
    Treats features as a sequence by reshaping [batch, features] to [batch, seq_len, features_per_step]
    """
    
    def __init__(
        self,
        d_feat=162,
        hidden_size=64,
        num_layers=2,
        dropout=0.0,
        n_epochs=100,
        lr=0.001,
        metric="",
        batch_size=2000,
        early_stop=20,
        loss="mse",
        optimizer="adam",
        GPU=0,
        seed=None,
        **kwargs,
    ):
        self.logger = get_module_logger("SimpleLSTM")
        self.logger.info("SimpleLSTM pytorch version...")
        
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
        
        if self.seed is not None:
            np.random.seed(self.seed)
            torch.manual_seed(self.seed)
        
        # Create model - treat each feature as one timestep
        self.lstm_model = SimpleLSTMModel(
            d_feat=self.d_feat,
            hidden_size=self.hidden_size,
            num_layers=self.num_layers,
            dropout=self.dropout,
        )
        
        if optimizer.lower() == "adam":
            self.train_optimizer = optim.Adam(self.lstm_model.parameters(), lr=self.lr)
        elif optimizer.lower() == "gd":
            self.train_optimizer = optim.SGD(self.lstm_model.parameters(), lr=self.lr)
        else:
            raise NotImplementedError(f"optimizer {optimizer} is not supported!")
        
        self.fitted = False
        self.lstm_model.to(self.device)
    
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
        
        self.lstm_model.train()
        indices = np.arange(len(x_train_values))
        np.random.shuffle(indices)
        
        for i in range(len(indices))[::self.batch_size]:
            if len(indices) - i < self.batch_size:
                break
            
            feature = torch.from_numpy(x_train_values[indices[i:i+self.batch_size]]).float().to(self.device)
            label = torch.from_numpy(y_train_values[indices[i:i+self.batch_size]]).float().to(self.device)
            
            pred = self.lstm_model(feature)
            loss = self.loss_fn(pred, label)
            
            self.train_optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_value_(self.lstm_model.parameters(), 3.0)
            self.train_optimizer.step()
    
    def test_epoch(self, data_x, data_y):
        x_values = data_x.values
        y_values = np.squeeze(data_y.values)
        
        self.lstm_model.eval()
        scores = []
        losses = []
        indices = np.arange(len(x_values))
        
        for i in range(len(indices))[::self.batch_size]:
            if len(indices) - i < self.batch_size:
                break
            
            feature = torch.from_numpy(x_values[indices[i:i+self.batch_size]]).float().to(self.device)
            label = torch.from_numpy(y_values[indices[i:i+self.batch_size]]).float().to(self.device)
            
            with torch.no_grad():
                pred = self.lstm_model(feature)
                loss = self.loss_fn(pred, label)
                losses.append(loss.item())
                score = self.metric_fn(pred, label)
                scores.append(score.item())
        
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
        
        save_path = get_or_create_path(save_path)
        stop_steps = 0
        best_score = -np.inf
        best_epoch = 0
        best_param = copy.deepcopy(self.lstm_model.state_dict())
        evals_result["train"] = []
        evals_result["valid"] = []
        
        self.logger.info("training...")
        self.fitted = True
        
        for step in range(self.n_epochs):
            self.logger.info(f"Epoch{step}:")
            self.logger.info("training...")
            self.train_epoch(x_train, y_train)
            self.logger.info("evaluating...")
            train_loss, train_score = self.test_epoch(x_train, y_train)
            val_loss, val_score = self.test_epoch(x_valid, y_valid)
            self.logger.info(f"train {train_score:.6f}, valid {val_score:.6f}")
            evals_result["train"].append(train_score)
            evals_result["valid"].append(val_score)
            
            if val_score > best_score:
                best_score = val_score
                stop_steps = 0
                best_epoch = step
                best_param = copy.deepcopy(self.lstm_model.state_dict())
            else:
                stop_steps += 1
                if stop_steps >= self.early_stop:
                    self.logger.info("early stop")
                    break
        
        self.logger.info(f"best score: {best_score:.6lf} @ {best_epoch}")
        self.lstm_model.load_state_dict(best_param)
        torch.save(best_param, save_path)
        
        if self.use_gpu:
            torch.cuda.empty_cache()
    
    def predict(self, dataset: DatasetH, segment: Union[Text, slice] = "test"):
        if not self.fitted:
            raise ValueError("model is not fitted yet!")
        
        x_test = dataset.prepare(segment, col_set="feature", data_key=DataHandlerLP.DK_I)
        index = x_test.index
        self.lstm_model.eval()
        x_values = x_test.values
        sample_num = x_values.shape[0]
        preds = []
        
        for begin in range(sample_num)[::self.batch_size]:
            end = min(sample_num, begin + self.batch_size)
            x_batch = torch.from_numpy(x_values[begin:end]).float().to(self.device)
            with torch.no_grad():
                pred = self.lstm_model(x_batch).detach().cpu().numpy()
            preds.append(pred)
        
        return pd.Series(np.concatenate(preds), index=index)


class SimpleLSTMModel(nn.Module):
    """LSTM model that treats each feature as a timestep"""
    def __init__(self, d_feat=162, hidden_size=64, num_layers=2, dropout=0.0):
        super().__init__()
        self.d_feat = d_feat
        
        # Treat each feature as one timestep, with 1 feature per step
        self.rnn = nn.LSTM(
            input_size=1,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout,
        )
        self.fc_out = nn.Linear(hidden_size, 1)
    
    def forward(self, x):
        # x: [batch, d_feat]
        # Reshape to [batch, d_feat, 1] to treat each feature as a timestep
        x = x.unsqueeze(-1)  # [batch, d_feat, 1]
        out, _ = self.rnn(x)  # [batch, d_feat, hidden_size]
        # Use the last timestep's output
        return self.fc_out(out[:, -1, :]).squeeze()
