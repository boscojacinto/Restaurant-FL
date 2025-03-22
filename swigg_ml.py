import os.path as osp

import torch
import torch.nn.functional as F

import torch_geometric
import torch_geometric.transforms as T
from swigg_db import SWGDataset
from torch_geometric.nn import HGTConv, Linear
from torch_geometric.utils import to_networkx
import networkx as nx
import matplotlib.pyplot as plt

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
    dataset = SWGDataset(path)
    data = dataset[0]

    model = SWG(hidden_channels=64, out_channels=2, num_heads=2, num_layers=1,
                node_types=['restaurant', 'area', 'customer'], metadata=data.metadata())
    if torch.cuda.is_available():
        device = torch.device('cuda')
    elif torch_geometric.is_xpu_available():
        device = torch.device('xpu')
    else:
        device = torch.device('cpu')
    data, model = data.to(device), model.to(device)

    with torch.no_grad():  # Initialize lazy modules.
        out = model(data.x_dict, data.edge_index_dict)

    optimizer = torch.optim.Adam(model.parameters(), lr=0.005, weight_decay=0.001)

    def train():
        results = [val.cpu().numpy() for _, val in model.state_dict().items()]
        print(f"\nresults:\n{results}")    
        
        model.train()
        optimizer.zero_grad()
        out = model(data.x_dict, data.edge_index_dict)
        mask = data['restaurant'].train_mask
        loss = F.cross_entropy(out[mask], data['restaurant'].y[mask])
        loss.backward()
        optimizer.step()
        return float(loss)

    @torch.no_grad()
    def test():
        model.eval()
        pred = model(data.x_dict, data.edge_index_dict).argmax(dim=-1)

        accs = []
        for split in ['train_mask', 'val_mask', 'test_mask']:
            mask = data['restaurant'][split]
            acc = (pred[mask] == data['restaurant'].y[mask]).sum() / mask.sum()
            accs.append(float(acc))
        return accs

    for epoch in range(1, 2):
        loss = train()
        train_acc, val_acc, test_acc = test()
        print(f'Epoch: {epoch:03d}, Loss: {loss:.4f}, Train: {train_acc:.4f}, '
              f'Val: {val_acc:.4f}, Test: {test_acc:.4f}')


if __name__ == "__main__":
    main()