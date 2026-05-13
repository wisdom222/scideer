"""Minimal fake pygcn train script for unit tests.

Reads scaled epochs via env var SCIDEER_EPOCHS, prints sentinel metrics.
"""
import os
import time

epochs = int(os.environ.get("SCIDEER_EPOCHS", "100"))
for ep in range(1, epochs + 1):
    loss = 1.94 * (0.95 ** ep)
    acc = 0.30 + (0.50 * (1 - 0.95 ** ep))
    print(f"SKELETON_EPOCH {ep} train_loss={loss:.4f} val_acc={acc:.4f}", flush=True)
    time.sleep(0.001)

final_acc = 0.8023
print(f"SKELETON_METRIC test_accuracy={final_acc}", flush=True)
print(f"SKELETON_METRIC train_loss_final=0.234", flush=True)
print(f"SKELETON_METRIC epochs_actually_run={epochs}", flush=True)
