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
from client import NEIGHBOR_REST_CUST_FILE
from scipy.sparse import coo_matrix
from torch_geometric.loader import HGTLoader


from torch_geometric.data import (
    HeteroData,
    InMemoryDataset,
    download_url,
    extract_zip,
)

class SWGDatasetLocal(InMemoryDataset): 
    
    url = 'https://www.dropbox.com/scl/fi/k8wk3x6ev5fx5mlvbjhn3/data.pt?rlkey=x8rhi4deb6ryijiu1brczbyh5&st=1xzptsjh&dl=1'
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

        d = self._data.to_namedtuple()
        p_id = self.partition_id

        r_to_a = d.restaurant__to__area
        r_to_r = d.restaurant__to__restaurant

        restaurants = r_to_a.edge_index[0]
        areas = r_to_a.edge_index[1]
        area_attrs = r_to_a.edge_attr

        r_id = restaurants[p_id]
        a_id = areas[p_id]
        aa_id = area_attrs[p_id]

        r_filter = (areas == a_id)
        #print(f"r_filter:{r_filter.shape}")
        r_to_a_mask = torch.stack([r_filter, r_filter], dim=0)
        r_to_a_indices = torch.where(r_filter)[0].to(dtype=torch.int64)
        a_to_r_indices = r_to_a_indices

        local_restaurants = r_to_a.edge_index[r_to_a_mask].reshape(2, -1)[0]
        local_area_attrs = r_to_a.edge_attr[r_filter]

        r_filter_0 = torch.isin(r_to_r.edge_index[0], local_restaurants)
        r_filter_1 = torch.isin(r_to_r.edge_index[1], local_restaurants)
        r_to_r_mask = torch.stack([r_filter_0, r_filter_1], dim=0)
        r_to_r_mask = torch.any(r_to_r_mask, dim=0)
        r_to_r_mask = r_to_r_mask.unsqueeze(0).expand(2, -1)
        r_to_r_indices = r_to_r.edge_index[r_to_r_mask].reshape(2, -1)

        # print(f"local_restaurants:{local_restaurants}")
        # print(f"r_to_a_indices:{r_to_a_indices}")
        # print(f"a_to_r_indices:{a_to_r_indices}")

        subgraph_filter = {
            ('restaurant', 'to', 'area'): r_to_a_indices,
            ('area', 'to', 'restaurant'): a_to_r_indices,
        }
        local_graph = self._data.edge_subgraph(subgraph_filter)
        
        # print(f"local_graph:{local_graph}")
        # print(f"{local_graph.to_namedtuple().restaurant.x}")

        # Customer features
        x = sp.load_npz(osp.join('/home/boscojacinto/projects/Restaurant-FL/', CUSTOMER_FEATURES_FILE))
        customer_attrs = torch.from_numpy(x.todense()).to(torch.float)
        #print(f"customer_attrs.shape:{customer_attrs.shape}")
        customers = torch.nonzero(customer_attrs.any(dim=1)).squeeze()
        #print(f"customers:{customers}")
        #customers = torch.tensor([customers])
        num_customers = customers.shape[0]
        #print(f"num_customers:{num_customers}")

        r_indices = torch.full((num_customers, ), p_id, dtype=torch.int)
        c_indices = customers.flatten()
        r_to_c_indices = torch.stack([r_indices, c_indices], dim=0)
        c_to_r_indices = torch.stack([c_indices, r_indices], dim=0)

        lg = local_graph.to_namedtuple()

        # Restaurant features
        x = sp.load_npz(osp.join('/home/boscojacinto/projects/Restaurant-FL/', RESTAURANT_FEATURES_FILE))
        restaurant_attrs = torch.from_numpy(x.todense()).to(torch.float)
        #print(f"restaurant_attrs:{restaurant_attrs}")
        neighbor_restaurants = torch.nonzero(restaurant_attrs.any(dim=1)).squeeze()
        neighbor_restaurants = torch.tensor([neighbor_restaurants.item()])
        #print(f"neighbor_restaurants:{neighbor_restaurants.flatten()}")

        x = np.load(osp.join('/home/boscojacinto/projects/Restaurant-FL/', NEIGHBOR_REST_CUST_FILE))
        r_c_adj = sp.coo_matrix(x).toarray()
        for idx in neighbor_restaurants.flatten():
            idx = idx.item()
            #print(f"idx:{idx}")
            lg.restaurant.x[idx] = restaurant_attrs[idx]
            #print(f"lg.restaurant.x[idx]: {lg.restaurant.x[idx]}")
            c_row = torch.tensor(r_c_adj[idx:])[0]
            #print(f"c_row:{c_row}")
            c_row = torch.nonzero(c_row)[0]
            num_c_row = c_row.shape[0]
            #print(f"num_c_row:{num_c_row}")
            n_r_indices = torch.full((num_c_row, ), torch.tensor(idx), dtype=torch.int)
            #print(f"n_r_indices:{n_r_indices}")
            n_c_indices = c_row
            #print(f"n_c_indices:{n_c_indices}")
            n_r_to_c_indices = torch.stack([n_r_indices, n_c_indices], dim=0)
            n_c_to_r_indices = torch.stack([n_c_indices, n_r_indices], dim=0)
            r_to_c_indices = torch.hstack((r_to_c_indices, n_r_to_c_indices))
            c_to_r_indices = torch.hstack((c_to_r_indices, n_c_to_r_indices))
            #print(f"r_to_c_indices:{r_to_c_indices}")

        r_to_a_self = torch.stack([torch.tensor([p_id]), torch.tensor([p_id])], dim=0)
        r_to_a_indices = torch.hstack((lg.restaurant__to__area.edge_index, r_to_a_self))

        customer_graph = HeteroData({
            'customer': {'x': customer_attrs },
            ('restaurant', 'to', 'area'): { 'edge_index': r_to_a_indices },
            ('restaurant', 'to', 'customer'): { 'edge_index': r_to_c_indices },
            ('customer', 'to', 'restaurant'): { 'edge_index': c_to_r_indices }
        })        

        local_graph = local_graph.update(customer_graph)        
        #print(f"new local_graph:{local_graph}")
        ll = local_graph.to_namedtuple()

        self.data = local_graph

        if self.pre_transform is not None:
            self.data = self.pre_transform(self.data)

        self.save([self.data], self.processed_paths[0])

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}()'

def display_graph(data):
    # Create a simple graph  
    G = to_networkx(data, node_attrs=['x'])
    color_map = {'restaurant': 'red', 'customer': 'lightblue', 'area': 'yellow'}
    nodes_to_remove = [
        node for node, degree in G.degree()
        if degree == 0# and G.nodes[node]['type'] == 'customer'
    ]
    G.remove_nodes_from(nodes_to_remove)
    node_colors = [color_map[G.nodes[node]['type']] for node in G.nodes]

    labels = {}
    for node in G.nodes:
        node_type = G.nodes[node]['type']
        label = f"{node_type[0]}{node}"
        labels[node] = label

    pos = nx.spring_layout(G)
    nx.draw(G, pos, with_labels=True, labels=labels,
        node_color=node_colors, edge_color='gray',
        node_size=600, font_size=6)

    for node_type, color in color_map.items():
        plt.scatter([], [], c=color, label=node_type, s=100)
    plt.legend(title="Node Types")

    plt.show()

def create_dummy_customers():
    customer_embeds = torch.rand(10000, 1024)
    torch.save(customer_embeds, 'customer_embeddings.pt')    
    customer_embeds[1] = torch.tensor(torch.rand(1024), dtype=torch.float)
    #print(f"customer_embeds:{customer_embeds[1]}")
    torch.save(customer_embeds, 'customer_embeddings.pt')
    customer_feats = coo_matrix(customer_embeds)
    #print(f"customer_feats:{customer_feats}")
    sp.save_npz(CUSTOMER_FEATURES_FILE, customer_feats)

def main():
    path = osp.join(osp.dirname(osp.realpath(__file__)), '')

    create_dummy_customers()

    # Create dataset instance
    dataset = SWGDatasetLocal(path, 0, force_reload=True)

    # transform = RandomLinkSplit(
    #     num_val=0.1,
    #     num_test=0.2,
    #     neg_sampling_ratio=0.0,
    #     edge_types=[('restaurant', 'to', 'area'),
    #                 ('restaurant', 'to', 'customer'),
    #                 ],
    #     rev_edge_types=[('area', 'to', 'restaurant'),
    #                 ('customer', 'to', 'restaurant'),
    #                 ],
    # )

    # train_data, val_data, test_data = transform(dataset.data)
    #display_graph(batch)
        
if __name__ == "__main__":
    main()