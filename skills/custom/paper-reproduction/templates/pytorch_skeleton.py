#!/usr/bin/env python3
"""pytorch_skeleton.py -- Tier 3 fallback when neither cache nor github clone provide code.

Routes by SCIDEER_DATASET env var:
  Cora/Citeseer/Pubmed -> run_gcn()        (requires torch_geometric)
  MNIST/FashionMNIST   -> run_cnn()        (requires torchvision)
  other                -> graceful exit with sentinel error metric

Reads:
  SCIDEER_EPOCHS, SCIDEER_LR, SCIDEER_HIDDEN, SCIDEER_DROPOUT, SCIDEER_DATASET, SCIDEER_SUBSET

Emits sentinel lines parsed by run_experiment.py:
  SKELETON_EPOCH <n> train_loss=<v> val_acc=<v>
  SKELETON_METRIC test_accuracy=<v>
  SKELETON_METRIC train_loss_final=<v>
  SKELETON_METRIC epochs_actually_run=<v>
"""
from __future__ import annotations

import os
import sys

EPOCHS = int(os.environ.get("SCIDEER_EPOCHS", "100"))
LR = float(os.environ.get("SCIDEER_LR", "0.01"))
HIDDEN = int(os.environ.get("SCIDEER_HIDDEN", "16"))
DROPOUT = float(os.environ.get("SCIDEER_DROPOUT", "0.5"))
DATASET = os.environ.get("SCIDEER_DATASET", "Cora")
SUBSET = int(os.environ.get("SCIDEER_SUBSET", "0")) or None


def emit_metric(key: str, value) -> None:
    print(f"SKELETON_METRIC {key}={value}", flush=True)


def emit_epoch(epoch: int, train_loss: float, val_acc: float) -> None:
    print(f"SKELETON_EPOCH {epoch} train_loss={train_loss:.4f} val_acc={val_acc:.4f}",
          flush=True)


def run_gcn() -> int:
    try:
        import torch
        import torch.nn.functional as F
        from torch_geometric.datasets import Planetoid
        from torch_geometric.nn import GCNConv
    except ImportError as e:
        print(f"SKELETON_ERROR dep_missing: {e}", file=sys.stderr, flush=True)
        return 1

    cache_dir = os.path.expanduser("~/.scideer/cache/torch_geometric")
    os.makedirs(cache_dir, exist_ok=True)
    dataset = Planetoid(root=cache_dir, name=DATASET)
    data = dataset[0]
    num_features = dataset.num_features
    num_classes = dataset.num_classes

    class GCN(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.conv1 = GCNConv(num_features, HIDDEN)
            self.conv2 = GCNConv(HIDDEN, num_classes)

        def forward(self, data):
            x, edge_index = data.x, data.edge_index
            x = F.relu(self.conv1(x, edge_index))
            x = F.dropout(x, p=DROPOUT, training=self.training)
            x = self.conv2(x, edge_index)
            return F.log_softmax(x, dim=1)

    model = GCN()
    optim = torch.optim.Adam(model.parameters(), lr=LR, weight_decay=5e-4)
    final_loss = 0.0
    final_acc = 0.0
    for epoch in range(1, EPOCHS + 1):
        model.train()
        optim.zero_grad()
        out = model(data)
        loss = F.nll_loss(out[data.train_mask], data.y[data.train_mask])
        loss.backward()
        optim.step()

        model.eval()
        with torch.no_grad():
            out = model(data)
            pred = out.argmax(dim=1)
            val_acc = (pred[data.val_mask] == data.y[data.val_mask]).float().mean().item()
            test_acc = (pred[data.test_mask] == data.y[data.test_mask]).float().mean().item()
        emit_epoch(epoch, loss.item(), val_acc)
        final_loss = loss.item()
        final_acc = test_acc

    emit_metric("test_accuracy", final_acc)
    emit_metric("train_loss_final", final_loss)
    emit_metric("epochs_actually_run", EPOCHS)
    return 0


def run_cnn() -> int:
    try:
        import torch
        import torch.nn as nn
        import torch.nn.functional as F
        from torch.utils.data import DataLoader, Subset
        from torchvision import datasets, transforms
    except ImportError as e:
        print(f"SKELETON_ERROR dep_missing: {e}", file=sys.stderr, flush=True)
        return 1

    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.1307,), (0.3081,)),
    ])
    cache_dir = os.path.expanduser("~/.scideer/cache/torchvision")
    os.makedirs(cache_dir, exist_ok=True)
    train_set = datasets.MNIST(cache_dir, train=True, download=True, transform=transform)
    test_set = datasets.MNIST(cache_dir, train=False, download=True, transform=transform)
    if SUBSET:
        train_set = Subset(train_set, list(range(min(SUBSET, len(train_set)))))
    train_loader = DataLoader(train_set, batch_size=128, shuffle=True)
    test_loader = DataLoader(test_set, batch_size=512)

    class SimpleCNN(nn.Module):
        def __init__(self):
            super().__init__()
            self.conv1 = nn.Conv2d(1, 32, 3, padding=1)
            self.conv2 = nn.Conv2d(32, 64, 3, padding=1)
            self.fc1 = nn.Linear(64 * 7 * 7, 128)
            self.fc2 = nn.Linear(128, 10)

        def forward(self, x):
            x = F.relu(self.conv1(x)); x = F.max_pool2d(x, 2)
            x = F.relu(self.conv2(x)); x = F.max_pool2d(x, 2)
            x = x.view(x.size(0), -1)
            x = F.relu(self.fc1(x)); x = F.dropout(x, p=DROPOUT, training=self.training)
            return self.fc2(x)

    model = SimpleCNN()
    optim = torch.optim.Adam(model.parameters(), lr=LR)
    final_loss = 0.0
    final_acc = 0.0
    for epoch in range(1, EPOCHS + 1):
        model.train()
        running = 0.0
        for x, y in train_loader:
            optim.zero_grad()
            out = model(x)
            loss = F.cross_entropy(out, y)
            loss.backward()
            optim.step()
            running += loss.item()
        final_loss = running / max(len(train_loader), 1)

        model.eval()
        correct = 0
        total = 0
        with torch.no_grad():
            for x, y in test_loader:
                pred = model(x).argmax(dim=1)
                correct += (pred == y).sum().item()
                total += y.size(0)
        final_acc = correct / total if total else 0.0
        emit_epoch(epoch, final_loss, final_acc)

    emit_metric("test_accuracy", final_acc)
    emit_metric("train_loss_final", final_loss)
    emit_metric("epochs_actually_run", EPOCHS)
    return 0


def main() -> int:
    if DATASET in {"Cora", "Citeseer", "Pubmed"}:
        return run_gcn()
    if DATASET in {"MNIST", "FashionMNIST"}:
        return run_cnn()
    # Graceful exit for unsupported datasets
    print(f"SKELETON_ERROR unsupported_dataset: '{DATASET}' not in "
          f"{{Cora,Citeseer,Pubmed,MNIST,FashionMNIST}}",
          file=sys.stderr, flush=True)
    emit_metric("test_accuracy", "null")
    return 2


if __name__ == "__main__":
    sys.exit(main())
