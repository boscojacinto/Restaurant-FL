import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.data import Data
from torch_geometric.nn import AGNNConv  # Attention-based GNN
from torch.nn import TransformerEncoder, TransformerEncoderLayer
from torch_geometric.utils import to_networkx
import networkx as nx
import matplotlib.pyplot as plt

# Step 1: Simulate Graph Data
# Nodes: A_Thai, B_Italian, C_Burger, D_Taco (new), P1_Spicy, P2_Family
# Features: [spicy_pref, family_pref, avg_spend, downtown=1/outskirts=0]
x = torch.tensor([
    [0.8, 0.2, 20.0, 1.0],  # A_Thai
    [0.1, 0.9, 30.0, 1.0],  # B_Italian
    [0.3, 0.3, 10.0, 0.0],  # C_Burger
    [0.7, 0.3, 15.0, 1.0],  # D_Taco (new)
    [1.0, 0.0, 0.0, 0.0],   # P1_Spicy (preference cluster)
    [0.0, 1.0, 0.0, 0.0]    # P2_Family
], dtype=torch.float)

# Edges: restaurant-restaurant and restaurant-preference
edge_index = torch.tensor([
    [0, 1, 0, 3, 1, 3, 0, 4, 1, 5, 3, 4],  # Source
    [1, 0, 3, 0, 3, 1, 4, 0, 5, 1, 4, 3]   # Target
], dtype=torch.long)

# Labels: Success (1) or Failure (0), None for new
y = torch.tensor([1, 1, 0, -1], dtype=torch.long)  # -1 for D_Taco (unknown)

# Create PyG data object
data = Data(x=x, edge_index=edge_index, y=y)

print(x)
print(edge_index)
print(y)

G = to_networkx(data, node_attrs=['x'], to_undirected=False)

print(f"Number of nodes: {G.number_of_nodes()}")
print(f"Number of edges: {G.number_of_edges()}")

for node in list(G.nodes):
    print(f"Node {node}: {G.nodes[node]['x']}")

for edge in list(G.edges):
    print(f"Edge {edge}")

print(list(G.adj[0]))

# Draw the graph
pos = nx.spring_layout(G)  # Layout for visualization
#node_labels = {node: f"{node}\n({G.nodes[node]['ID']}, {G.nodes[node]['Food type']}, {G.nodes[node]['Price']})" for node in G.nodes()}
labels = {i: str(x[i, 0].item()) for i in range(x.shape[0])}

nx.draw(G, pos, with_labels=True, labels=labels, node_color='lightblue', node_size=500, font_size=10)
plt.show()

# Step 2: Define the Model
class RestaurantGNN(nn.Module):
    def __init__(self, input_dim, hidden_dim):
        super(RestaurantGNN, self).__init__()
        self.agnn = AGNNConv(requires_grad=True)  # Attention-based GNN
        # Transformer setup
        encoder_layer = TransformerEncoderLayer(d_model=input_dim, nhead=2)
        self.transformer = TransformerEncoder(encoder_layer, num_layers=1)
        self.fc = nn.Linear(input_dim, hidden_dim)
        self.out = nn.Linear(hidden_dim, 2)  # 2 classes: success/failure

    def forward(self, data):
        x, edge_index = data.x, data.edge_index
        # AGNNConv: Attention-based propagation
        x = self.agnn(x, edge_index)
        # Transformer: Global context
        x = x.unsqueeze(1)  # Add sequence dim for transformer
        x = self.transformer(x).squeeze(1)
        # Prediction
        x = F.relu(self.fc(x))
        x = self.out(x)
        return x

# Step 3: Train and Predict
model = RestaurantGNN(input_dim=4, hidden_dim=32)
optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
criterion = nn.CrossEntropyLoss()

# Training (on known restaurants: A, B, C)
for epoch in range(100):
    model.train()
    optimizer.zero_grad()
    out = model(data)
    print(f"out shape: {out.shape}")
    print(f"out: {out[:3]}")
    print(f"y: {y[:3]}")
    loss = criterion(out[:3], y[:3])  # Only train on A, B, C
    loss.backward()
    optimizer.step()
    if epoch % 20 == 0:
        print(f"Epoch {epoch}, Loss: {loss.item():.4f}")

# Predict for D_Taco
model.eval()
with torch.no_grad():
    pred = model(data)
    taco_prob = F.softmax(pred[3], dim=0)
    print(f"\nD_Taco Success Probability: {taco_prob[1].item():.4f}")

# Step 4: Simulate New Data (e.g., new restaurant E)
# Add new node, edges, and retrain periodically...