import torch
import torch.nn as nn
import torch.nn.functional as F
import pandas as pd
import networkx as nx
import numpy as np
import matplotlib.pyplot as plt
from torch.utils.data import Dataset, DataLoader
from torch_geometric.data import Data
from torch_geometric.utils import to_networkx
from torch_geometric.nn import AGNNConv  # Attention-based GNN
from torch.nn import TransformerEncoder, TransformerEncoderLayer

# 1. First, create a custom Dataset class
class SWGDataset(Dataset):
    def __init__(self, csv_file):
        # Load the CSV file using pandas
        df = pd.read_csv(csv_file)
        # Filter only Mumbai restaurants
        self.data = df.loc[(df['City'].str.contains('Mumbai', case=False)) & 
            df['Area'].str.contains('Powai', case=False)
        ]
        self.data = self.data.drop(['ID', 'Price', 'Total ratings', 'Restaurant', 'Avg ratings', 'Avg ratings', 'Address', 'Delivery time'], axis=1)
        print(f"self.data:\n {self.data}")
    def __len__(self):
        # Return the total size of the dataset
        return len(self.data)
    
    def __getitem__(self, idx):
        # Get one item from the dataset
        # Convert the row to tensor
        sample = self.data.iloc[idx, 3]
        return sample

    def create_labels(self):
        torch.manual_seed(42)
        #food_rand = 0.5 + 0.5 * torch.rand(1).item()

        self.city_labels = {
            'mumbai': 1.0
        }
        self.area_labels = {
            'powai': 1.0,
        }
        self.food_labels = {
            'mughlai': 1.0,
        }        

        # Label cities
        self.data['City'] = self.data['City'].str.lower().apply(
            lambda x: next((v for k, v in self.city_labels.items() if k in x.split(',')), 1.0)           
            #lambda x: next((v for k, v in self.city_labels.items() if k in x.split(',')), -1)
        ).astype(float)

        # Label area's in Mumbai city
        self.data['Area'] = self.data['Area'].str.lower().apply(
            lambda x: next((v for k, v in self.area_labels.items() if k in x.split(',')), 1.0)
            #lambda x: (0.5 + 0.5 * torch.rand(1).item()) if any(k in x for k in self.area_labels) else -1
        ).astype(float)        

        # Label restaurant food type
        self.data['Food type'] = self.data['Food type'].str.lower().apply(
            lambda x: next((v for k, v in self.food_labels.items() if k in x.split(',')), 0)
            #lambda x: (0.5 + 0.5 * torch.rand(1).item()) if any(k in x for k in self.food_labels) else -1
        ).astype(float)

        #print(f"self.data['Food type']: {self.data['Food type']}")
        # Label output as success or fail randomly
        self.y = torch.tensor(
            [1, 0, 0, 0, 0, 0, 1, 0, 0, 0,
            0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0,
            0, 0, 0, 1, 0, 0, 1, 1, 0, 0,
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
            1, 0, 0, 0, 0, 1, 0, 0, 1, 0,
            0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 1,
            0, 0, 0, 0, 0, 0, 1, 0, 0,
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
            0, 0, 1, 0, 0, 1, 0, 0, 0,
            1, 0, 0, 0, 1, 0, 0, 0, 0, 0,
            0, 0, 0, 0, 0, 0, 0, 0, -1, 0,
            0, 0, 0, 0], dtype=torch.long)
        #print(f"self.y {self.y}")

    def create_restaurants(self):
        #print(self.data)
        self.x = torch.tensor(self.data.values, dtype=torch.float)
        print(self.x.shape[0])
        print(self.x)

    def create_links(self):
        # Food type linking
        mask = self.x[:, -1] == 1.0
        print(mask)
        indices = mask.nonzero()
        print(indices)
        pairs = torch.combinations(indices.flatten(), 2)
        print(pairs)
        # result = self.x[mask]
        # print(result)
        # n_rows = result.shape[0]
        # indices = list(range(n_rows))
        # pairs = 
        # pairs = torch.combinations(torch.flatten(result), r=)
        # print(pairs)

    def create_links1(self):
        col_idx = -1
        values = self.x[:, col_idx] # Shape: (13,)
        #print(f"values: {values}")
        # Get all possible pairs of node indices (one direction)
        pair_indices = torch.combinations(torch.arange(self.x.shape[0]), r=2)  # Shape: (78, 2)
        #print(f"pair_indices: {pair_indices}")
        #print(pair_indices)
        # Compute condition for each pair
        #mask = torch.isclose(values[pair_indices[:, 0]], values[pair_indices[:, 1]], rtol=0.10, atol=1e-1) & \

        mask = (values[pair_indices[:, 0]] == values[pair_indices[:, 1]]) & \
                (~torch.isclose(values[pair_indices[:, 0]], torch.tensor(0.0), rtol=0.0, atol=1e-1)) & \
                (~torch.isclose(values[pair_indices[:, 1]], torch.tensor(0.0), rtol=0.0, atol=1e-1))  # Shape: (78,)

        # mask = (values[pair_indices[:, 0]] == values[pair_indices[:, 1]]) & \
        #         (values[pair_indices[:, 0]] == torch.tensor(0.00e+00)) & \
        #         (values[pair_indices[:, 1]] == torch.tensor(0.00e+00))  # Shape: (78,)

        directed_edges = pair_indices[mask]  # Shape: (num_edges, 2)

        # Create undirected edges by adding reverse pairs
        reverse_edges = directed_edges.flip(1)  # Swap columns: (i, j) -> (j, i)
        self.edge_index = torch.cat([directed_edges, reverse_edges], dim=0).t()  # Shape: (2, 2*num_edges)
        self.edge_index = torch.tensor(self.edge_index, dtype=torch.long)
        self.x = torch.tensor(self.x, dtype=torch.float)
        features_0 = self.x.numpy()
        np.savez_compressed('features_0', features_0=features_0)
       # print(f"Here X: {self.x}")

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

# 2. Example usage
def main():
    # Path to your CSV file
    csv_path = './restaurant.csv'
    
    # Create dataset instance
    dataset = SWGDataset(csv_path)

    torch.set_printoptions(threshold=20_000)
    torch.set_printoptions(precision=2)

    #print(dataset.__len__())
    
    dataset.create_labels()
    #print(dataset.__getitem__(0))
    
    dataset.create_restaurants()
    dataset.create_links1()

    # Create PyG data object
    data = Data(x=dataset.x, edge_index=dataset.edge_index, y=dataset.y)

    # print(dataset.x)
    # print(dataset.edge_index)
    # print(dataset.y)

    # Create a simple graph  
    G = to_networkx(data, node_attrs=['x'], to_undirected=True)

    # print(f"Number of nodes: {G.number_of_nodes()}")
    # print(f"Number of edges: {G.number_of_edges()}")

    # for node in list(G.nodes):
    #     print(f"Node {node}: {G.nodes[node]['x']}")

    # for edge in list(G.edges):
    #     print(f"Edge {edge}")

    # print(list(G.adj[0]))

    # # Draw the graph
    # pos = nx.spring_layout(G)  # Layout for visualization
    # #node_labels = {node: f"{node}\n({G.nodes[node]['ID']}, {G.nodes[node]['Food type']}, {G.nodes[node]['Price']})" for node in G.nodes()}
    # labels = {i: str(dataset.x[i, 0].item()) for i in range(dataset.x.shape[0])}

    # nx.draw(G, pos, with_labels=True, labels=labels, node_color='lightblue', node_size=500, font_size=10)
    # plt.show()

    # Step 3: Train and Predict
    model = RestaurantGNN(input_dim=4, hidden_dim=16)
    print(model.parameters())
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
    criterion = nn.CrossEntropyLoss()

    # Training (on known restaurants: A, B, C)
    for epoch in range(200):
        model.train()
        optimizer.zero_grad()
        out = model(data)
        #print(f"out shape: {out.shape}")
        #print(f"out: {out[:3]}")
        #print(f"y: {out[:3]}")

        loss = criterion(out[:108], dataset.y[:108])  # Only train on A, B, C
        loss.backward()
        optimizer.step()
        if epoch % 20 == 0:
            print(f"Epoch {epoch}, Loss: {loss.item():.4f}")

    # Predict for D_Taco
    model.eval()
    with torch.no_grad():
        pred = model(data)
        rest_prob = F.softmax(pred[108], dim=0)
        print(f"\nID {dataset.x[108][0]} Success Probability: {rest_prob[1].item():.4f}")

    # # Create data loader
    # batch_size = 32  # Adjust as needed
    # dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
    
    # # Example: Iterate through the data
    # for batch in dataloader:
    #     print(f"Batch shape: {batch.shape}")
    #     # Your training code here
    #     break  # Remove this to process all batches

if __name__ == "__main__":
    main()


        #     r_df = pd.read_csv(osp.join(root, 'restaurant.csv'))
        # c_df = pd.read_csv(osp.join(root, 'customers.csv'))
        # l_np = np.load(osp.join(root, 'labels.npy'))

        # x = r_df.loc[(r_df['City'].str.contains('Mumbai', case=False)) & 
        #              (r_df['Area'].str.contains('Powai', case=False))]
        # x = x.drop(['ID', 'Total ratings', 'Restaurant', 'Avg ratings', 'Address', 'Delivery time'], axis=1)
        # c = c_df.drop(['ID', 'Area', 'City', 'Avg Spend', 'Food type'])

        # city_labels = { 'mumbai': 1.0 }
        # area_labels = { 'powai': 1.0 }
        # food_labels = { 'mughlai': 1.0 }        

        # x['City'] = x['City'].str.lower().apply(
        #     lambda a: next((v for k, v in city_labels.items() if k in a.split(',')), 1.0)           
        # ).astype(float)

        # x['Area'] = x['Area'].str.lower().apply(
        #     lambda a: next((v for k, v in area_labels.items() if k in a.split(',')), 1.0)
        # ).astype(float)        

        # x['Food type'] = x['Food type'].str.lower().apply(
        #     lambda x: next((v for k, v in food_labels.items() if k in a.split(',')), 0)
        # ).astype(float)

