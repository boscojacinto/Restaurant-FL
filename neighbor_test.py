import torch
import torch_geometric.transforms as T
from torch_geometric.utils import to_networkx
from torch_geometric.transforms import RandomLinkSplit, ToUndirected
from torch_geometric.loader import HGTLoader
import networkx as nx
import matplotlib.pyplot as plt
from torch_geometric.data import (
    HeteroData,
    InMemoryDataset,
    download_url,
    extract_zip,
)

def main():
	data = HeteroData()
	data['restaurant'].x = torch.normal(mean=0.5, std=0.1, size=(40, 1024))	
	data['customer'].x = torch.normal(mean=0.1, std=0.2, size=(100, 1024))
	data['area'].x = torch.normal(mean=0.3, std=0.1, size=(4, 1024))

	def create_edges(r, c, n):
		row = torch.randint(low=0, high=r, size=(n,))
		col = torch.randint(low=0, high=c, size=(n,))
		edge = torch.stack([row, col], dim=0)
		mask = edge[0] != edge[1]
		#print(f"mask.shape:{mask.shape}")
		edge = edge[:, mask]
		#print(f"edge.shape:{edge.shape}")

		edge_t = edge.t()
		unique_indices, counts = torch.unique(edge_t, dim=0, return_counts=True, return_inverse=False)
		#print(f"counts:{counts}")
		unique_indices = unique_indices.t()
		#print(f"unique_indices.shape:{unique_indices.shape}")
		# columns = [tuple(edge[:, i].tolist()) for i in range(edge.shape[1])]
		# seen = set()
		# unique_indices = [i for i, col in enumerate(columns) if not (col in seen or seen.add(col))]
		# print(f"unique_indices:{unique_indices}")
		# edge = edge[:, unique_indices]
		return unique_indices

	data['restaurant', 'to', 'customer'].edge_index = create_edges(40, 100, 200)
	data['restaurant', 'to', 'area'].edge_index = create_edges(40, 4, 100)
	data['customer', 'to', 'area'].edge_index = create_edges(100, 4, 100)

	d = data.to_namedtuple()
	print(f"d.restaurant__to__customer:{d.restaurant__to__customer}")
	print(f"d.restaurant__to__area:{d.restaurant__to__area}")
	print(f"d.customer__to__area:{d.restaurant__to__area}")

	display_graph(data)

	# sample_loader = HGTLoader(
	# 	data,
	# 	num_samples={'restaurant': [2], 'customer': [50], 'area': [2]},
	# 	batch_size=10,
	# 	input_nodes=['restaurant', 'customer', 'area']
	# )
	# print(f"sample_loader:{sample_loader}")


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

if __name__ == "__main__":
	main()