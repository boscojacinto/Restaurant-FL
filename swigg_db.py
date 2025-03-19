import os
import os.path as osp
from itertools import product
from typing import Callable, List, Optional
import torch_geometric.transforms as T
from torch_geometric.utils import to_networkx
import networkx as nx
import matplotlib.pyplot as plt

import numpy as np
import torch

from torch_geometric.data import (
    HeteroData,
    InMemoryDataset,
    download_url,
    extract_zip,
)

class SWGDataset(InMemoryDataset):
    
    url = 'https://www.dropbox.com/scl/fi/mxpq52u98qfo7ajkdv37h/SWGD_processed.zip?rlkey=j8t29lb7ipwvah0hszs6pgzll&st=6u2j3nbe&dl=1'

    def __init__(
        self,
        root: str,
        transform: Optional[Callable] = None,
        pre_transform: Optional[Callable] = None,
        force_reload: bool = False,
    ) -> None:
        super().__init__(root, transform, pre_transform,
                         force_reload=force_reload)
        print(f"self.processed_paths[0]:{self.processed_paths[0]}")
        self.load(self.processed_paths[0], data_cls=HeteroData)

    @property
    def raw_file_names(self) -> List[str]:
        return [
            'adjM.npz', 'features_0.npz', 'features_1.npz',
            'labels.npy', 'train_val_test_idx.npz'
        ]

    @property
    def processed_file_names(self) -> str:
        return 'data.pt'

    def download(self) -> None:
        print(f"self.raw_dir:{self.raw_dir}")
        path = download_url(self.url, self.raw_dir)
        extract_zip(path, self.raw_dir)
        os.remove(path)
    
    def process(self) -> None:
        import scipy.sparse as sp
      
        data = HeteroData()
        node_types = ['restaurant', 'customer']

        for i, node_type in enumerate(node_types):
            x = sp.load_npz(osp.join(self.raw_dir, f'features_{i}.npz'))
            data[node_type].x = torch.from_numpy(x.todense()).to(torch.float)

        y = np.load(osp.join(self.raw_dir, 'labels.npy'))
        data['restaurant'].y = torch.from_numpy(y).to(torch.long)
        print(f"y:\n{y}")

        split = np.load(osp.join(self.raw_dir, 'train_val_test_idx.npz'))
        print(f"\n\n\nsplit:\n{split}")
        for name in ['train', 'val', 'test']:
            idx = split[f'{name}_idx']
            idx = torch.from_numpy(idx).to(torch.long)
            mask = torch.zeros(data['restaurant'].num_nodes, dtype=torch.bool)
            mask[idx] = True
            data['restaurant'][f'{name}_mask'] = mask

        s = {}
        N_r = data['restaurant'].num_nodes
        N_c = data['customer'].num_nodes
        print(f"N_r:{N_r}")
        print(f"N_c:{N_c}")

        s['restaurant'] = (0, N_r)
        s['customer'] = (N_r, N_r + N_c)
        print(f"s:{s}")

        A = sp.load_npz(osp.join(self.raw_dir, 'adjM.npz')).tocsr()
        print(f"A shape {A.shape}")
        print(f"A issparse:{sp.issparse(A)}")
        for src, dst in product(node_types, node_types):
            print(f"src:{src} dst:{dst}")
            print(f"s[{src}][0]: {s[src][0]} s[{src}][1]: {s[src][1]}")
            print(f"s[{dst}][0]: {s[dst][0]} s[{dst}][0]: {s[dst][1]}")
            A_sub = A[s[src][0]:s[src][1], s[dst][0]:s[dst][1]].tocoo()
            print(f"A_sub shape: {A_sub.shape}")
            if A_sub.nnz > 0:
                row = torch.from_numpy(A_sub.row).to(torch.long)
                col = torch.from_numpy(A_sub.col).to(torch.long)
                data[src, dst].edge_index = torch.stack([row, col], dim=0)

        if self.pre_transform is not None:
            data = self.pre_transform(data)

        self.save([data], self.processed_paths[0])

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}()'


def main():
    path = osp.join(osp.dirname(osp.realpath(__file__)), '')

    # Create dataset instance
    dataset = SWGDataset(path)
    dataset.process();

    # Create a simple graph  
    G = to_networkx(dataset.data, node_attrs=['x'])
    print(f"Number of nodes: {G.number_of_nodes()}")
    print(f"Number of edges: {G.number_of_edges()}")

    pos = nx.spring_layout(G)  # Layout for visualization
    nx.draw(G, pos, with_labels=False, node_color='lightblue', node_size=500, font_size=10)
    plt.show()
    
if __name__ == "__main__":
    main()