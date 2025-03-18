import networkx as nx
import matplotlib.pyplot as plt

# Step 1: Create the graph
G = nx.Graph()

# Add nodes (restaurants) with attributes
G.add_node("A_Thai", success=True, pref="spicy", location="downtown")
G.add_node("B_Italian", success=True, pref="family", location="downtown")
G.add_node("C_Burger", success=False, pref="fast", location="outskirts")
G.add_node("D_Taco", success=None, pref="spicy", location="downtown")  # New restaurant

# Add edges based on preference similarity or proximity
G.add_edge("A_Thai", "B_Italian")  # Downtown proximity
G.add_edge("A_Thai", "D_Taco")     # Spicy preference + downtown
G.add_edge("B_Italian", "D_Taco")  # Downtown proximity
# C_Burger is isolated (outskirts, different customer base)

# Step 2: Compute simple structural identity (degree and neighbors)
def get_structural_identity(graph):
    identity = {}
    for node in graph.nodes:
        degree = graph.degree[node]
        neighbors = sorted([n for n in graph.neighbors(node)])  # Neighbor list
        identity[node] = {"degree": degree, "neighbors": neighbors}
    return identity

structural_identity = get_structural_identity(G)

# Step 3: Display structural identity and predict success
print("Structural Identity of Restaurants:")
for node, info in structural_identity.items():
    success = G.nodes[node]["success"]
    print(f"{node}: Degree={info['degree']}, Neighbors={info['neighbors']}, Success={success}")

# Prediction logic: Compare D_Taco to successful restaurants
def predict_success(graph, new_node, structural_identity):
    new_identity = structural_identity[new_node]
    for node in graph.nodes:
        if node != new_node and graph.nodes[node]["success"] == True:
            if new_identity["degree"] == structural_identity[node]["degree"]:
                print(f"\nPrediction: {new_node} matches {node}'s degree ({new_identity['degree']}).")
                print(f"Since {node} is successful, {new_node} is likely to succeed!")
                return
    print(f"\nPrediction: No strong match for {new_node}. Success uncertain.")

predict_success(G, "D_Taco", structural_identity)

# Step 4: Visualize the graph
pos = nx.spring_layout(G)
colors = ["green" if G.nodes[n]["success"] else "red" if G.nodes[n]["success"] == False else "blue" for n in G.nodes]
nx.draw(G, pos, with_labels=True, node_color=None, node_size=2000, font_size=8, font_weight="bold")
plt.title("Restaurant Network (Green=Success, Red=Failure, Blue=New)")
plt.show()

sparse_matrix = nx.to_scipy_sparse_array(G)

print(sparse_matrix)