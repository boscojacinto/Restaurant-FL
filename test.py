import torch
from torch_geometric.data import HeteroData

# Create a HeteroData object
data = HeteroData()

# Define node features (not the focus, but included for completeness)
data['user'].x = torch.tensor([[1.0, 2.0], [3.0, 4.0]])  # 2 users, 2 features each
data['item'].x = torch.tensor([[5.0], [6.0], [7.0]])     # 3 items, 1 feature each

# Define edge indices (connections between nodes)
data['user', 'follows', 'user'].edge_index = torch.tensor([[0, 1], [1, 0]])  # user 0 follows user 1, and vice versa
data['user', 'rates', 'item'].edge_index = torch.tensor([[0, 1, 1], [0, 1, 2]])  # user 0 rates item 0, user 1 rates items 1 and 2

# Define edge features
data['user', 'follows', 'user'].edge_attr = torch.tensor([[1.5, 2023], [0.8, 2022]], dtype=torch.float)  # 2 features: strength, year
data['user', 'rates', 'item'].edge_attr = torch.tensor([[4.5], [3.0], [5.0]], dtype=torch.float)       # 1 feature: rating

# Access num_edge_features for each edge type
follows_edge_features = data['user', 'follows', 'user'].num_edge_features
rates_edge_features = data['user', 'rates', 'item'].num_edge_features

# Print results
print("Number of edge features for ('user', 'follows', 'user'): ", follows_edge_features)
print("Number of edge features for ('user', 'rates', 'item'): ", rates_edge_features)

# Optional: Inspect the edge attributes
print("\nEdge attributes for ('user', 'follows', 'user'):\n", data['user', 'follows', 'user'].edge_attr)
print("Edge attributes for ('user', 'rates', 'item'):\n", data['user', 'rates', 'item'].edge_attr)