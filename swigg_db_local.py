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

class SWGDatasetLocal(InMemoryDataset): 
    
    url = 'https://www.dropbox.com/scl/fi/2w4rea25rs7bdl17z4tpf/data.pt?rlkey=1ziqessubooxp3w30aagzo496&st=pqslqdwq&dl=1'
    partition_id = 0

    def __init__(
        self,
        root: str,
        partition_id:int,
        transform: Optional[Callable] = None,
        pre_transform: Optional[Callable] = None,
        force_reload: bool = False,
    ) -> None:
        self.partition_id = partition_id

        super().__init__(root, transform, pre_transform,
                         force_reload=force_reload)
        self.load(self.processed_paths[0], data_cls=HeteroData)

    @property
    def raw_file_names(self) -> List[str]:
        return ['data.pt']

    @property
    def processed_file_names(self) -> str:
        return 'localdata.pt'

    def download(self) -> None:
        path = download_url(self.url, self.raw_dir)
    
    def process(self) -> None:
                 
        self.load(os.path.join(self.raw_dir, 'data.pt'), data_cls=HeteroData)

        r_to_a_edge = self.data.edge_items()[1]
        edge = r_to_a_edge[1]
        local_restaurant = edge['edge_index'][0][self.partition_id]
        local_restaurant = torch.Tensor([local_restaurant]).type(torch.int64)
        local_area = edge['edge_index'][1][self.partition_id]
        local_area = torch.Tensor([local_area]).type(torch.int64)
        local_area_attr = edge['edge_attr'][self.partition_id]
        area_attrs = edge['edge_attr']
        restaurants = edge['edge_index']

        mask = torch.abs(area_attrs - local_area_attr) < 0.01
        local_area_attrs = area_attrs[mask]
        edge_mask = torch.stack([mask, mask], dim=0)
        local_restaurants = restaurants[edge_mask].reshape(2, -1)
        r_to_a_indices = torch.where(mask)[0].to(dtype=torch.int64)
        a_to_r_indices = r_to_a_indices

        r_to_r_edge = self.data.edge_items()[0]
        r_to_r_edge = r_to_r_edge[1]['edge_index']

        mask = torch.isin(r_to_r_edge, local_restaurants[0])
        r_to_r_indices = torch.where(mask)[0].to(dtype=torch.int64)

        # Customer features
        edge_customer = torch.randperm(10000, dtype=torch.int64)[0:500].sort()[0]
        edge_restaurants = torch.full((500,), edge['edge_index'][0][46], dtype=torch.int64)
        r_to_c_edge_index = torch.stack([edge_restaurants, edge_customer], dim=0)
        c_to_r_edge_index = torch.stack([edge_customer, edge_restaurants], dim=0)

        edge_dict = {
            ('restaurant', 'to', 'area'): r_to_a_indices,
            ('area', 'to', 'restaurant'): a_to_r_indices,
            ('restaurant', 'to', 'restaurant'): r_to_r_indices,
        }

        local_graph = self.data.edge_subgraph(edge_dict)

        customer_graph = HeteroData({
            ('restaurant', 'to', 'customer'): { 'edge_index': r_to_c_edge_index },
            ('customer', 'to', 'restaurant'): { 'edge_index': c_to_r_edge_index }
        })        
        local_graph.update(customer_graph)
        
        self.data = local_graph

        if self.pre_transform is not None:
            self.data = self.pre_transform(self.data)

        self.save([self.data], self.processed_paths[0])

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}()'


def main():
    path = osp.join(osp.dirname(osp.realpath(__file__)), '')

    # Create dataset instance
    dataset = SWGDatasetLocal(path, 3)

    transform = RandomLinkSplit(
        num_val=0.05,
        num_test=0.1,
        neg_sampling_ratio=0.0,
        edge_types=[('restaurant', 'to', 'restaurant'),
                    ('restaurant', 'to', 'area'),
                    ('area', 'to', 'restaurant'),
                    ('restaurant', 'to', 'customer'),
                    ('customer', 'to', 'restaurant')]
    )

    train_data, val_data, test_data = transform(dataset.data)

    
if __name__ == "__main__":
    main()