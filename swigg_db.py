import os
import torch
import asyncio
import os.path as osp
import numpy as np
import pandas as pd
from itertools import product
from scipy.sparse import coo_matrix, issparse, load_npz
import scipy as sp
from typing import Callable, List, Optional
import networkx as nx
import matplotlib.pyplot as plt
import torch_geometric.transforms as T
from torch_geometric.utils import to_networkx
from torch_geometric.transforms import RandomLinkSplit, ToUndirected

from torch_geometric.data import (
    Data,
    HeteroData,
    InMemoryDataset,
    download_url,
    extract_zip,
)

class SWGDataset(InMemoryDataset): 

    def __init__(
        self,
        root: str,
        partition_id:int,
        transform: Optional[Callable] = None,
        pre_transform: Optional[Callable] = None,
        force_reload: bool = False,
    ) -> None:
        self.url = 'https://www.dropbox.com/scl/fi/oscg6t3utw6z0o6no662q/SWGD_mumbai.zip?rlkey=4cr0v3npt5mjvxysdskjt7p80&st=uiyzr3v8&dl=1'

        super().__init__(root, transform, pre_transform,
                         force_reload=force_reload)
        self.load(self.processed_paths[0], data_cls=HeteroData)

    @property
    def raw_file_names(self) -> List[str]:
        return [
            'adjM.npz', 'features_0.npz', 'features_1.npz', 'features_2.npz',
            'edge_attrs_1.npz', 'edge_attrs_3.npz', 'labels.npy'
        ]

    @property
    def processed_file_names(self) -> str:
        return 'data.pt'

    def download(self) -> None:
        path = download_url(self.url, self.raw_dir)
        extract_zip(path, self.raw_dir)
        os.remove(path)
    
    def process(self) -> None:
        import scipy.sparse as sp
      
        data = HeteroData()
        node_types = ['restaurant', 'area', 'customer']

        for i, node_type in enumerate(node_types):
            x = sp.load_npz(osp.join(self.raw_dir, f'features_{i}.npz'))
            data[node_type].x = torch.from_numpy(x.todense()).to(torch.float)

        y = np.load(osp.join(self.raw_dir, 'labels.npy'))
        data['restaurant'].y = torch.from_numpy(y).to(torch.long)

        s = {}
        N_r = data['restaurant'].num_nodes
        N_a = data['area'].num_nodes
        N_c = data['customer'].num_nodes
        print(f"Nr:{N_r} Na:{N_a} Nc:{N_c}")

        s['restaurant'] = (0, N_r)
        s['area'] = (N_r, N_r + N_a)
        s['customer'] = (N_r + N_a, N_r + N_a + N_c)

        A = np.load(osp.join(self.raw_dir, 'adjM.npy'))
        i = 0
        for src, dst in product(node_types, node_types):
            A_sub = sp.coo_matrix(A[s[src][0]:s[src][1], s[dst][0]:s[dst][1]])
            data[src, dst].edge_index = torch.empty(2, 0, dtype=torch.int64)
            if A_sub.nnz > 0:
                row = torch.from_numpy(A_sub.row).to(torch.long)
                col = torch.from_numpy(A_sub.col).to(torch.long)
                data[src, dst].edge_index = torch.stack([row, col], dim=0)
                if osp.isfile(osp.join(self.raw_dir, f'edge_attrs_{i}.npy')):
                    data[src, dst].edge_attr = torch.from_numpy(
                        np.load(osp.join(self.raw_dir, f'edge_attrs_{i}.npy'))).to(torch.float)
            i = i + 1

        if self.pre_transform is not None:
            data = self.pre_transform(data)

        self.save([data], self.processed_paths[0])

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}()'

async def main():
    path = osp.join(osp.dirname(osp.realpath(__file__)), '')

    # Create dataset instance
    dataset = SWGDataset(path, 0, force_reload=True)
    print(f"dataset.data = {dataset.data}")

    # transform = RandomLinkSplit(
    #     num_val=0.05,
    #     num_test=0.1,
    #     neg_sampling_ratio=0.0,
    #     edge_types=[('restaurant', 'to', 'area'),
    #                 ],
    #     rev_edge_types=[('area', 'to', 'restaurant'),
    #                 ],
    # )
    # train_data, val_data, test_data = transform(dataset.data)

    
if __name__ == "__main__":
    asyncio.run(main())