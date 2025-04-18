import os
import os.path as osp
import numpy as np
import torch
import scipy.sparse as sp
from itertools import product
from typing import Callable, List, Optional
import networkx as nx
import matplotlib.pyplot as plt
import torch_geometric.transforms as T
from torch_geometric.utils import to_networkx
from torch_geometric.transforms import RandomLinkSplit, ToUndirected
from client import CUSTOMER_FEATURES_FILE 
from client import RESTAURANT_FEATURES_FILE 

from torch_geometric.data import (
    HeteroData,
    InMemoryDataset,
    download_url,
    extract_zip,
)

class SWGDatasetLocal(InMemoryDataset): 
    
    url = 'https://www.dropbox.com/scl/fi/2jgvl6ns32rjx7cbaxpdl/data.pt?rlkey=o483u2pb2rely4qd2tq26f1xo&st=skgaxcnj&dl=1'
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
        return ['localdata.pt']

    def download(self) -> None:
        path = download_url(self.url, self.raw_dir)
    
    def process(self) -> None:
            
        self.load(os.path.join(self.raw_dir, 'data.pt'), data_cls=HeteroData)

        print(f"self.data:{self.data}")
        print(f"node_items:{self.data.node_items()[0]}")
        r_to_a_edge = self.data.edge_items()[1]
        edge = r_to_a_edge[1]
        local_restaurant = edge['edge_index'][0][self.partition_id]
        local_restaurant = torch.Tensor([local_restaurant]).type(torch.int64)
        local_area = edge['edge_index'][1][self.partition_id]
        local_area = torch.Tensor([local_area]).type(torch.int64)
        local_area_attr = edge['edge_attr'][self.partition_id]
        area_attrs = edge['edge_attr']
        restaurants = edge['edge_index']

        #mask = torch.abs(area_attrs - local_area_attr) < 0.01
        mask = (restaurants[1] == restaurants[1][self.partition_id]) 
        local_area_attrs = area_attrs[mask]
        edge_mask = torch.stack([mask, mask], dim=0)
        local_restaurants = restaurants[edge_mask].reshape(2, -1)
        r_to_a_indices = torch.where(mask)[0].to(dtype=torch.int64)
        a_to_r_indices = r_to_a_indices

        r_to_r_edge = self.data.edge_items()[0]
        r_to_r_edge = r_to_r_edge[1]['edge_index']

        mask = torch.isin(r_to_r_edge, local_restaurants[0])
        r_to_r_indices = torch.where(mask)[0].to(dtype=torch.int64)

        edge_dict = {
            ('restaurant', 'to', 'area'): r_to_a_indices,
            ('area', 'to', 'restaurant'): a_to_r_indices,
            ('restaurant', 'to', 'restaurant'): r_to_r_indices,
        }

        local_graph = self.data.edge_subgraph(edge_dict)

        x = sp.load_npz(osp.join('/home/boscojacinto/projects/Restaurant-SetFit-FedLearning/', CUSTOMER_FEATURES_FILE))
        customers_nodes = torch.from_numpy(x.todense()).to(torch.float)
        print(f"cust:\n{customers_nodes}")

        # Customer features
        edge_customer = customers_nodes[:, -1]
        edge_customer = torch.nonzero(edge_customer, as_tuple=False).squeeze()
        edge_restaurants = torch.full(edge_customer.shape, edge['edge_index'][0][self.partition_id], dtype=torch.int64)
        r_to_c_edge_index = torch.stack([edge_restaurants, edge_customer], dim=0)
        c_to_r_edge_index = torch.stack([edge_customer, edge_restaurants], dim=0)

        print(f"partition_id:{self.partition_id}")
        print(f"edge_customer:{edge_customer}")
        print(f"edge_restaurants:{edge_restaurants}")

        #Restaurant features
        x = sp.load_npz(osp.join('/home/boscojacinto/projects/Restaurant-SetFit-FedLearning/', RESTAURANT_FEATURES_FILE))
        restaurant_nodes = torch.from_numpy(x.todense()).to(torch.float)
        print(f"rest:\n{restaurant_nodes}")
        edge_restaurant = restaurant_nodes[:, -1]
        edge_restaurant = torch.nonzero(edge_restaurant, as_tuple=False)
        edge_restaurant = edge_restaurant[:, -1]

        if edge['edge_index'][0][edge_restaurant[0]]:
            edge_customers = torch.full(edge_restaurant.shape, edge_customer[0], dtype=torch.int64)
            new_edge = torch.stack([torch.tensor([edge_restaurant[0]]),
                torch.tensor([edge_customer[0]])], dim=0)
            print(f"new_edge:{new_edge}")

            r_to_c_edge_index = torch.hstack((r_to_c_edge_index, new_edge))
            print(f"r_to_c_edge_index:{r_to_c_edge_index}")
            new_edge = torch.stack([torch.tensor([edge_customer[0]]),
                torch.tensor([edge_restaurant[0]])], dim=0)
            print(f"new_edge:{new_edge}")
            c_to_r_edge_index = torch.hstack((c_to_r_edge_index, new_edge))
            print(f"c_to_r_edge_index:{c_to_r_edge_index}")
        
        list_restaurants = self.data.node_items()[0]
        print(f"list_restaurants0:{list_restaurants}")

        list_restaurants = list_restaurants[1]['x']
        print(f"list_restaurants1:{list_restaurants}")
        print(f"edge_restaurant[0]:{edge_restaurant[0]}")
        print(f"restaurant_nodes[0, -1]:{restaurant_nodes[edge_restaurant[0], -1]}")

        list_restaurants[edge_restaurant[0], -1 ] = torch.Tensor([restaurant_nodes[edge_restaurant[0], -1]]).type(torch.float)
        print(f"list_restaurants2:{list_restaurants}")

        customer_graph = HeteroData({
            'restaurant': {'x': list_restaurants},
            'customer': {'x': customers_nodes},
            ('restaurant', 'to', 'customer'): { 'edge_index': r_to_c_edge_index },
            ('customer', 'to', 'restaurant'): { 'edge_index': c_to_r_edge_index }
        })        
        print(f"customer_graph:{customer_graph}")

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
    dataset = SWGDatasetLocal(path, 1, force_reload=True)
    print(f"\ndataset.data:{dataset.data}")

    # transform = RandomLinkSplit(
    #     num_val=0.1,
    #     num_test=0.2,
    #     neg_sampling_ratio=0.0,
    #     edge_types=[('restaurant', 'to', 'restaurant'),
    #                 ('restaurant', 'to', 'area'),
    #                 ('restaurant', 'to', 'customer'),
    #                 ('customer', 'to', 'restaurant')
    #                 ]
    # )

    # train_data, val_data, test_data = transform(dataset.data)
    # print(f"\ntrain_data:{train_data}")
    # print(f"\nval_data:{val_data}")
    # print(f"\ntest_data:{test_data}")


    # # Create a simple graph  
    # G = to_networkx(dataset.data, node_attrs=['x'])
    # print(f"Number of nodes: {G.number_of_nodes()}")
    # print(f"Number of edges: {G.number_of_edges()}")

    # pos = nx.spring_layout(G)  # Layout for visualization
    # nx.draw(G, pos, with_labels=False, node_color='grey', node_size=500, font_size=10)
    # plt.show()
    
    
if __name__ == "__main__":
    main()