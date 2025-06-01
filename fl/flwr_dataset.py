from flwr_datasets import FederatedDataset
from torch.utils.data import DataLoader

fds = FederatedDataset(dataset="DynaOuchebara/devign_graphs", partitioners={"train": 10})
print(f"fds:{fds}")

partition = fds.load_partition(0, "train")
print(f"partition:{partition.features}")

print(f"{partition.set_format("torch")}")

#DataLoader()

print("Done")