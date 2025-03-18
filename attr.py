import networkx as nx
import matplotlib.pyplot as plt

# Create a simple graph
G = nx.Graph()

# Add nodes with attributes (e.g., 'size' and 'type')
G.add_node(1, size=10, type='A')
G.add_node(2, size=20, type='B')
G.add_node(3, size=15, type='A')
G.add_node(4, size=25, type='B')

# Add some edges
G.add_edges_from([(1, 2), (2, 3), (3, 4), (4, 1)])

# Extract node attributes for visualization
node_sizes = [G.nodes[node]['size'] * 100 for node in G.nodes()]  # Scale size for visibility
node_types = nx.get_node_attributes(G, 'type')
node_colors = ['skyblue' if node_types[node] == 'A' else 'salmon' for node in G.nodes()]
node_labels = {node: f"{node}\n({G.nodes[node]['type']}, {G.nodes[node]['size']})" for node in G.nodes()}

# Draw the graph
plt.figure(figsize=(8, 6))
pos = nx.spring_layout(G)  # Layout for positioning nodes
nx.draw(G, pos, 
        node_size=node_sizes,        # Size based on 'size' attribute
        node_color=node_colors,      # Color based on 'type' attribute
        with_labels=True,            # Show labels
        labels=node_labels,          # Custom labels with attributes
        font_size=10,                # Font size for labels
        font_weight='bold',          # Bold text
        edge_color='gray')           # Edge color

# Add a title
plt.title("NetworkX Graph with Node Attributes")
plt.show()