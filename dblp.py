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


class DBLP(InMemoryDataset):
    r"""A subset of the DBLP computer science bibliography website, as
    collected in the `"MAGNN: Metapath Aggregated Graph Neural Network for
    Heterogeneous Graph Embedding" <https://arxiv.org/abs/2002.01680>`_ paper.
    DBLP is a heterogeneous graph containing four types of entities - authors
    (4,057 nodes), papers (14,328 nodes), terms (7,723 nodes), and conferences
    (20 nodes).
    The authors are divided into four research areas (database, data mining,
    artificial intelligence, information retrieval).
    Each author is described by a bag-of-words representation of their paper
    keywords.

    Args:
        root (str): Root directory where the dataset should be saved.
        transform (callable, optional): A function/transform that takes in an
            :obj:`torch_geometric.data.HeteroData` object and returns a
            transformed version. The data object will be transformed before
            every access. (default: :obj:`None`)
        pre_transform (callable, optional): A function/transform that takes in
            an :obj:`torch_geometric.data.HeteroData` object and returns a
            transformed version. The data object will be transformed before
            being saved to disk. (default: :obj:`None`)
        force_reload (bool, optional): Whether to re-process the dataset.
            (default: :obj:`False`)

    **STATS:**

    .. list-table::
        :widths: 20 10 10 10
        :header-rows: 1

        * - Node/Edge Type
          - #nodes/#edges
          - #features
          - #classes
        * - Author
          - 4,057
          - 334
          - 4
        * - Paper
          - 14,328
          - 4,231
          -
        * - Term
          - 7,723
          - 50
          -
        * - Conference
          - 20
          - 0
          -
        * - Author-Paper
          - 196,425
          -
          -
        * - Paper-Term
          - 85,810
          -
          -
        * - Conference-Paper
          - 14,328
          -
          -
    """

    url = 'https://www.dropbox.com/s/yh4grpeks87ugr2/DBLP_processed.zip?dl=1'

    def __init__(
        self,
        root: str,
        transform: Optional[Callable] = None,
        pre_transform: Optional[Callable] = None,
        force_reload: bool = False,
    ) -> None:
        super().__init__(root, transform, pre_transform,
                         force_reload=force_reload)
        self.load(self.processed_paths[0], data_cls=HeteroData)

    @property
    def raw_file_names(self) -> List[str]:
        return [
            'adjM.npz', 'features_0.npz', 'features_1.npz', 'features_2.npy',
            'labels.npy', 'node_types.npy', 'train_val_test_idx.npz'
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
        node_types = ['author', 'paper', 'term', 'conference']
        for i, node_type in enumerate(node_types[:2]):
            x = sp.load_npz(osp.join(self.raw_dir, f'features_{i}.npz'))
            print(f"x:\n{x}")
            data[node_type].x = torch.from_numpy(x.todense()).to(torch.float)

        x = np.load(osp.join(self.raw_dir, 'features_2.npy'))
        data['term'].x = torch.from_numpy(x).to(torch.float)

        node_type_idx = np.load(osp.join(self.raw_dir, 'node_types.npy'))
        node_type_idx = torch.from_numpy(node_type_idx).to(torch.long)
        data['conference'].num_nodes = int((node_type_idx == 3).sum())

        y = np.load(osp.join(self.raw_dir, 'labels.npy'))
        data['author'].y = torch.from_numpy(y).to(torch.long)
        print(f"shape of y: {data['author'].y.shape}")
        print(f"{data['author'].y}")

        split = np.load(osp.join(self.raw_dir, 'train_val_test_idx.npz'))
        print(f"split:\n{split}")
        for name in ['train', 'val', 'test']:
            idx = split[f'{name}_idx']
            idx = torch.from_numpy(idx).to(torch.long)
            mask = torch.zeros(data['author'].num_nodes, dtype=torch.bool)
            mask[idx] = True
            data['author'][f'{name}_mask'] = mask
        #print(f"test_mask:\n{data['author'][f'test_mask']}")

        s = {}
        N_a = data['author'].num_nodes
        N_p = data['paper'].num_nodes
        N_t = data['term'].num_nodes
        N_c = data['conference'].num_nodes
        s['author'] = (0, N_a)
        s['paper'] = (N_a, N_a + N_p)
        s['term'] = (N_a + N_p, N_a + N_p + N_t)
        s['conference'] = (N_a + N_p + N_t, N_a + N_p + N_t + N_c)

        A = sp.load_npz(osp.join(self.raw_dir, 'adjM.npz'))
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


path = osp.join(osp.dirname(osp.realpath(__file__)), '../../data/DBLP')

dataset = DBLP(path, transform=T.Constant(node_types='conference'))
torch.set_printoptions(threshold=900_000)
dataset.process();
data = dataset[0]
print(data)
#print(data.data.x_dict)

#G = to_networkx(data, node_attrs=['x'])

#print(f"Number of nodes: {G.number_of_nodes()}")
#print(f"Number of edges: {G.number_of_edges()}")

# for node in list(G.nodes):
#     print(f"Node {node}: {G.nodes[node]['x']}")

# for edge in list(G.edges):
#     print(f"Edge {edge}")

# print(list(G.adj[0]))

# Draw the graph
#pos = nx.spring_layout(G)  # Layout for visualization
#node_labels = {node: f"{node}\n({G.nodes[node]['ID']}, {G.nodes[node]['Food type']}, {G.nodes[node]['Price']})" for node in G.nodes()}
#labels = {i: str(data.x_dict[''][i, 0].item()) for i in range(dataset.x.shape[0])}

#nx.draw(G, pos, with_labels=False, node_color='lightblue', node_size=500, font_size=10)
#plt.show()
