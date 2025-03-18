import torch
import numpy as np
import os
import os.path as osp

# Generate random assignments of 0, 1, or 2 for 114 positions
assignment = torch.randint(0, 3, (114,))

# Create a dictionary with the tensors
data_splits = {
    "train_idx": (assignment == 0).numpy(),  # True where assignment is 0
    "val_idx": (assignment == 1).numpy(),    # True where assignment is 1
    "test_idx": (assignment == 2).numpy()    # True where assignment is 2
}

print(f"train_val_test:\n{data_splits}")

#data_splits_np = data_splits.numpy()
np.savez_compressed('train_val_test_idx.npz', **data_splits)
path = osp.join(osp.dirname(osp.realpath(__file__)), f'train_val_test_idx.npz')
print(f"path:{path}")
test = np.load(path)
print(f"test:\n{test}")
