import os
import os.path as osp
import numpy as np
import torch
from itertools import product
from typing import Callable, List, Optional
import networkx as nx
import matplotlib.pyplot as plt
import torch_geometric.transforms as T
from torch_geometric.utils import to_networkx
from torch_geometric.transforms import RandomLinkSplit, ToUndirected

from torch_geometric.data import (
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
        if partition_id == 0:
            self.url = 'https://www.dropbox.com/scl/fi/yunjx1gqni33lonymnk1u/SWGD_mumbai-powai.zip?rlkey=m7oa6092f4cpfo8rmwb1vdg0o&st=zopltm43&dl=1'
        elif partition_id == 1:
            self.url = 'https://www.dropbox.com/scl/fi/pi0u8bd94upmxn4qhnty8/SWGD_mumbai-santacruz-east.zip?rlkey=5e8ostffn0s8ve3rqqag1irw4&st=4aj7c48z&dl=1'
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

        # split = np.load(osp.join(self.raw_dir, 'train_val_test_idx.npz'))
        # for name in ['train', 'val', 'test']:
        #     idx = split[f'{name}_idx']
        #     idx = torch.from_numpy(idx).to(torch.long)
        #     mask = torch.zeros(data['restaurant'].num_nodes, dtype=torch.bool)
        #     mask[idx] = True
        #     data['restaurant'][f'{name}_mask'] = mask

        s = {}
        N_r = data['restaurant'].num_nodes
        N_a = data['area'].num_nodes
        N_c = data['customer'].num_nodes
        print(f"Nr:{N_r} Na:{N_a} Nc:{N_c}")

        s['restaurant'] = (0, N_r)
        s['area'] = (N_r, N_r + N_a)
        s['customer'] = (N_r + N_a, N_r + N_a + N_c)

        A = np.load(osp.join(self.raw_dir, 'adjM.npy'))
        #print(f"A.shape:{A.shape}")
        i = 0
        for src, dst in product(node_types, node_types):
            A_sub = sp.coo_matrix(A[s[src][0]:s[src][1], s[dst][0]:s[dst][1]])
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


def main():
    path = osp.join(osp.dirname(osp.realpath(__file__)), '')

    # Create dataset instance
    dataset = SWGDataset(path, 1)
    print(f"dataset.data['restaurant', 'area']:{dataset.data['restaurant', 'area'].num_edge_features}")
    print(f"dataset.data['area', 'restaurant']:{dataset.data['area', 'restaurant'].num_edge_features}")
    print(f"dataset.data = {dataset.data}")

    transform = RandomLinkSplit(
        num_val=0.05,
        num_test=0.1,
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
    print(f"test_datalen:{len(test_data['restaurant'].y)}")

    # Create a simple graph  
    # G = to_networkx(dataset.data, node_attrs=['x'])
    # print(f"Number of nodes: {G.number_of_nodes()}")
    # print(f"Number of edges: {G.number_of_edges()}")

    # pos = nx.spring_layout(G)  # Layout for visualization
    # nx.draw(G, pos, with_labels=False, node_color='lightblue', node_size=500, font_size=10)
    # plt.show()
    
if __name__ == "__main__":
    main()