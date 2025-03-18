import networkx as nx
import matplotlib.pyplot as plt

# Step 1: Create the graph
G = nx.Graph()

# Add nodes
G.add_nodes_from([(1, {"f1": 61, "f2": 1, "f3": 33}),
                 (2, {"f1": 61, "f2": 1, "f3": 33}),
(3, {"f1": 61, "f2": 1, "f3": 53}),
(4, {"f1": 61, "f2": 1, "f3": 53}),
(5, {"f1": 61, "f2": 1, "f3": 33}),
(6, {"f1": 61, "f2": 3, "f3": 33}),
(7, {"f1": 61, "f2": 3, "f3": 47}),
(8, {"f1": 61, "f2": 3, "f3": 47}),
(9, {"f1": 61, "f2": 3, "f3": 47}),
(10, {"f1": 61, "f2": 5, "f3": 1}),
(11, {"f1": 61, "f2": 7, "f3": 30}),
(12, {"f1": 61, "f2": 7, "f3": 37}),
(13, {"f1": 61, "f2": 7, "f3": 32}),
(14, {"f1": 61, "f2": 7, "f3": 23}),
(15, {"f1": 61, "f2": 7, "f3": 45}),
(16, {"f1": 61, "f2": 9, "f3": 36}),
(17, {"f1": 61, "f2": 9, "f3": 23}),
(18, {"f1": 61, "f2": 9, "f3": 39}),
(19, {"f1": 61, "f2": 9, "f3": 77}),
(20, {"f1": 61, "f2": 9, "f3": 31})
                 ])

print(G.nodes())
# # Add some edges
G.add_edges_from([(1, 19), (13, 9), (19, 9), (10, 13), (11, 10), (11, 13), (11, 10),
(12, 11), (12, 13), (12, 11), (14, 12), (13, 9), (13, 14), (10, 13), (11, 13), (12, 13),
(14, 13), (15, 13), (14, 12), (14, 14), (13, 19), (15, 13), (15, 15), (16, 19), (16, 15),
(17, 16), (17, 19), (17, 16), (18, 17), (18, 19), (18, 17), (19, 18), (19, 9), (19, 18),
(15, 19), (16, 19), (17, 19), (18, 19), (19, 1) ])


# # Extract node attributes for visualization
node_f1 = [G.nodes[node]['f1'] * 10 for node in G.nodes()]  # Scale size for visibility
# node_f2 = nx.get_node_attributes(G, 'f2')
node_labels = {node: f"{node}\n({G.nodes[node]['f1']}, {G.nodes[node]['f2']}, {G.nodes[node]['f3']})" for node in G.nodes()}

# # Draw the graph
plt.figure(figsize=(50, 80))
pos = nx.spring_layout(G)  # Layout for positioning nodes
nx.draw(G, pos, 
        node_size=node_f1,        # Size based on 'size' attribute
        with_labels=True,            # Show labels
        labels=node_labels,          # Custom labels with attributes
        font_size=10,                # Font size for labels
        font_weight='bold',          # Bold text
        edge_color='gray')           # Edge color

# # Add a title
plt.title("NetworkX Graph with Node Attributes")
plt.show()
# # Add edges based on preference similarity or proximity

# # # Step 4: Visualize the graph
# # pos = nx.spring_layout(G)
# # #colors = ["green" if G.nodes[n]["success"] else "red" if G.nodes[n]["success"] == False else "blue" for n in G.nodes]
# # nx.draw(G, pos, with_labels=True, node_color=None, node_size=2000, font_size=8, font_weight="bold")
# # plt.title("Restaurant Network (Green=Success, Red=Failure, Blue=New)")
# # plt.show()

# # sparse_matrix = nx.to_scipy_sparse_array(G)

# # print(sparse_matrix)