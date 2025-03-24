import os.path as osp

import torch
import torch.nn.functional as F
import torch_geometric
import torch_geometric.transforms as T
from torch_geometric.nn import HGTConv, Linear
from torch_geometric.utils import to_networkx
from torch_geometric.transforms import RandomLinkSplit, ToUndirected
import networkx as nx
import matplotlib.pyplot as plt

from swigg_db import SWGDataset

class SWG(torch.nn.Module):
    def __init__(self, hidden_channels, out_channels, num_heads, num_layers, node_types, metadata):
        super().__init__()

        self.lin_dict = torch.nn.ModuleDict()
        for node_type in node_types:
            self.lin_dict[node_type] = Linear(-1, hidden_channels)

        self.convs = torch.nn.ModuleList()
        for _ in range(num_layers):
            conv = HGTConv(hidden_channels, hidden_channels, metadata,
                           num_heads)
            self.convs.append(conv)

        self.lin = Linear(hidden_channels, out_channels)

    def forward(self, x_dict, edge_index_dict):
        x_dict = {
            node_type: self.lin_dict[node_type](x).relu_()
            for node_type, x in x_dict.items()
        }
        for conv in self.convs:
            x_dict = conv(x_dict, edge_index_dict)

        return self.lin(x_dict['restaurant'])

def main():
    path = osp.join(osp.dirname(osp.realpath(__file__)), '')
    # We initialize conference node features with a single one-vector as feature:
    dataset = SWGDataset(path, 0)
    #data = dataset[0]
    transform = RandomLinkSplit(
        num_val=0.1,
        num_test=0.2,
        neg_sampling_ratio=0.0,
        edge_types=[('restaurant', 'to', 'restaurant'),
                    ('restaurant', 'to', 'area'),
                    ('restaurant', 'to', 'customer'),
                    ('area', 'to', 'restaurant'),
                    ('area', 'to', 'customer'),
                    ('customer', 'to', 'restaurant'),
                    ('customer', 'to', 'area')]
    )

    train_data, val_data, test_data = transform(dataset.data)

    print(f"\n\ndataset.data.metadata():\n{dataset.data.metadata()}")
    model = SWG(hidden_channels=64, out_channels=2, num_heads=2, num_layers=1,
                node_types=['restaurant', 'area', 'customer'], metadata=dataset.data.metadata())

    device = torch.device('cpu')
    train_data = train_data.to(device)
    val_data = val_data.to(device)
    test_data = test_data.to(device)
    model = model.to(device)

    with torch.no_grad():  # Initialize lazy modules.
        out = model(train_data.x_dict, train_data.edge_index_dict)

    optimizer = torch.optim.Adam(model.parameters(), lr=0.005, weight_decay=0.001)

    def train():
        results = [val.cpu().numpy() for _, val in model.state_dict().items()]
        #print(f"\nresults:\n{results}")    
        
        model.train()
        optimizer.zero_grad()
        out = model(train_data.x_dict, train_data.edge_index_dict)
        loss = F.cross_entropy(out, train_data['restaurant'].y)
        loss.backward()
        optimizer.step()
        return float(loss)

    @torch.no_grad()
    def test():
        model.eval()
        out = model(test_data.x_dict, test_data.edge_index_dict)
        pred = out.argmax(dim=-1)
        acc = []

        acc1 = (pred == train_data['restaurant'].y).sum() / len(train_data['restaurant'].y)
        acc.append(float(acc1))
        acc2 = (pred == val_data['restaurant'].y).sum() / len(val_data['restaurant'].y)
        acc.append(float(acc2))
        acc3 = (pred == test_data['restaurant'].y).sum() / len(test_data['restaurant'].y)
        acc.append(float(acc3))  

        loss = F.cross_entropy(out, train_data['restaurant'].y)
        return acc, loss

    for epoch in range(1, 30):
        train()
        acc, loss = test()
        print(f'Epoch: {epoch:03d}, Loss: {loss:.4f}, Acc(train): {acc[0]:.4f}, \n'
                f'Acc(val): {acc[1]:.4f}, Acc(test): {acc[2]:.4f}')

if __name__ == "__main__":
    main()