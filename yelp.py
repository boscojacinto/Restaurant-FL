import networkx as nx
import pandas as pd
import matplotlib.pyplot as plt

nodes_df = pd.read_csv("~/Downloads/toronto_data_filtered.csv")

G = nx.Graph()

for i, row in nodes_df.iterrows():
	G.add_node(row['node_id'], size=10,
		reviews=row['review_count'],
		stars=row['stars'],
		is_open=row['is_open'],
		pos_reviews=row['pos_reviews'])
	if i == 2000:
		break

print("Nodes and atrtributes:", G.nodes(data=True))

pos = nx.spring_layout(G)

nx.draw(G, pos, node_size=30, with_labels=True, font_size=6)
plt.show()
