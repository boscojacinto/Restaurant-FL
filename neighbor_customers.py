import os
import torch
import asyncio
import os.path as osp
import numpy as np
import scipy as sp
import pandas as pd
from scipy.sparse import coo_matrix, issparse, load_npz
import torch_geometric.transforms as T
from torch_geometric.utils import to_networkx
from torch_geometric.loader import HGTLoader
from restaurant_ai.restaurant_model import AIModel
import networkx as nx
import matplotlib.pyplot as plt
from torch_geometric.data import (
    HeteroData,
    InMemoryDataset,
    download_url,
    extract_zip,
)
from swigg_db import SWGDataset

MAX_CUSTOMERS = 10000
CUSTOMER_FEATURES_NUM = 1024

@torch.no_grad()
def init_params(loader):
    batch = next(iter(loader))
    print(f"batch:{batch}")
    display_graph(batch)

def display_graph(data):
    # Create a simple graph
    #print(f"data.node_offsets:{data.node_stores}")  
    G = to_networkx(data, node_attrs=['x'], remove_self_loops=True)
    #print(f"Nodes:{len(G)}")

    #[print(f"node:{node} G.nodes[node]['type']:{G.nodes[node]['type']}") for node in range(0, G.number_of_nodes())]
    color_map = {'restaurant': 'red', 'customer': 'lightblue', 'area': 'yellow'}
    node_colors = [color_map[G.nodes[node]['type']] for node in range(0, G.number_of_nodes())]

    labels = {}
    for node in range(0, G.number_of_nodes()):
        node_type = G.nodes[node]['type']
        label = f"{node_type[0]}{node}"
        labels[node] = label

    pos = nx.spring_layout(G)
    nx.draw(G, pos, with_labels=True, labels=labels,
    	edge_color='gray', node_color=node_colors,
        node_size=600, font_size=6)

    for node_type, color in color_map.items():
        plt.scatter([], [], c=color, label=node_type, s=100)
    plt.legend(title="Node Types")

    plt.show()

async def main():
    path = osp.join(osp.dirname(osp.realpath(__file__)), '')

    dataset = SWGDataset(path, 0, force_reload=True)

    async def create_new_cust_embeds(file):
        df = pd.read_csv(file)
        old_cust = df.sample(frac=0.5, random_state=42)
        new_cust = df.drop(old_cust.index)
        #print(f"old_cust indexs:{old_cust.index}")
        #print(f"new_cust indexs:{new_cust.index}")
        bot = AIModel()

        async def cust_embed(x):
            return await bot.embed(x)

        async def process_embed(values):
            tasks = [cust_embed(x) for x in values]
            return await asyncio.gather(*tasks) 

        new_cust["Customer's Description"] = await process_embed(new_cust["Customer's Description"])

        embeds = torch.tensor(
            new_cust["Customer's Description"].tolist()
        )
        #print(f"embeds:{embeds}")
        restaurant_customers_ids = torch.load('restaurant_customer_ids.pt')
        all_customer = torch.arange(MAX_CUSTOMERS)
        restof_customers_ids = all_customer[~torch.isin(all_customer, restaurant_customers_ids)]
        random_new_customer_ids = torch.randperm(restof_customers_ids.size(0))[:25]
        #print(f"random_new_customer_ids:{random_new_customer_ids.shape}")
        customer_embeds = torch.zeros((MAX_CUSTOMERS, CUSTOMER_FEATURES_NUM),
                                 dtype=torch.float)
        customer_embeds[random_new_customer_ids] = embeds
        return customer_embeds, random_new_customer_ids

    new_customers, customer_indices = await create_new_cust_embeds('./restaurant_interactions.csv')
    #print(f"new_customers:{new_customers}")
    #print(f"customer_indices:{customer_indices}")

    p_id = 1
    r_indices = torch.full((len(customer_indices), ), p_id, dtype=torch.int)
    c_indices = customer_indices.flatten()
    #print(f"c_indices:{c_indices}")
    r_to_c_indices = torch.stack([r_indices, c_indices], dim=0)
    #print(f"r_to_c_indices:{r_to_c_indices}")
    c_to_r_indices = torch.stack([c_indices, r_indices], dim=0)

    customer_graph = HeteroData({
        'customer': {'x': new_customers },
        ('restaurant', 'to', 'customer'): { 'edge_index': r_to_c_indices },
        ('customer', 'to', 'restaurant'): { 'edge_index': c_to_r_indices }
    }) 
    local_graph = dataset.data.update(customer_graph)
    print(f"local_graph = {local_graph}")

    mask = torch.zeros(10000, dtype=torch.bool)
    mask[customer_indices] =  True
    rmask = torch.zeros((1277,), dtype=torch.bool)
    rmask[p_id] = True

    kwargs = {'batch_size': 10}
    test_loader = HGTLoader(
        local_graph,
        num_samples={key: [5] * 2 for key in local_graph.node_types},
        shuffle=True,
        input_nodes=('customer', mask),
        **kwargs 
    )
    init_params(test_loader)
    
if __name__ == "__main__":
    asyncio.run(main())