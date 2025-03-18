import torch
import numpy as np
import scipy as sp

# Set random seed for reproducibility
torch.manual_seed(42)

# Total nodes and dimensions
num_restaurants = 114
num_customers = 10000
total_nodes = num_restaurants + num_customers  # 10114

# Initialize the superset adjacency matrix with zeros
adj_matrix = torch.zeros((total_nodes, total_nodes), dtype=torch.float32)

# 1. Restaurant-Restaurant block (114, 114)
# Random 1's, symmetric, no diagonal 1's
rr_block = torch.zeros((num_restaurants, num_restaurants))
# Generate random 1's in the upper triangle (excluding diagonal)
for i in range(num_restaurants):
    for j in range(i + 1, num_restaurants):  # Start from i+1 to skip diagonal
        if torch.rand(1).item() < 0.1:  # 10% probability of a 1 (adjustable sparsity)
            rr_block[i, j] = 1
            rr_block[j, i] = 1  # Ensure symmetry
# Place into the superset matrix (top-left: rows 0:114, cols 0:114)
adj_matrix[0:num_restaurants, 0:num_restaurants] = rr_block

# 2. Restaurant-Customer block (114, 10000)
# Random 1's
rc_block = torch.zeros((num_restaurants, num_customers))
# Fill with random 1's (e.g., 1% probability for sparsity)
rc_block = (torch.rand((num_restaurants, num_customers)) < 0.01).float()
# Place into the superset matrix (top-right: rows 0:114, cols 114:10114)
adj_matrix[0:num_restaurants, num_restaurants:total_nodes] = rc_block

# 3. Customer-Restaurant block (10000, 114)
# Transpose of Restaurant-Customer block
cr_block = rc_block.t()  # Transpose
# Place into the superset matrix (bottom-left: rows 114:10114, cols 0:114)
adj_matrix[num_restaurants:total_nodes, 0:num_restaurants] = cr_block

# 4. Customer-Customer block (10000, 10000)
# All zeros, already handled by the initial zero tensor
# (bottom-right: rows 114:10114, cols 114:10114)

# Verify the shape
print("Shape of the superset adjacency matrix:", adj_matrix.shape)

torch.set_printoptions(threshold=20_000)

# Optional: Print a small portion to inspect
print("\nSmall portion of the Restaurant-Restaurant block (top-left 5x5):")
print(adj_matrix[0:5, 0:5])

print("\nSmall portion of the Restaurant-Customer block (first 5 rows, first 5 cols):")
print(adj_matrix[0:5, num_restaurants:num_restaurants+5])

print("\nSmall portion of the Customer-Restaurant block (first 5 rows, first 5 cols):")
print(adj_matrix[num_restaurants:num_restaurants+5, 0:5])

print("\nSmall portion of the Customer-Customer block (first 5x5):")
print(adj_matrix[num_restaurants:num_restaurants+5, num_restaurants:num_restaurants+5])

# Convert the PyTorch tensor to a NumPy array
adj_matrix_np = adj_matrix.numpy()
rows, cols = np.nonzero(adj_matrix_np)
values = adj_matrix_np[rows, cols]
adj_matrix_coo = sp.sparse.coo_matrix((values, (rows, cols)), shape=adj_matrix_np.shape)

# Save the matrix in compressed NumPy format
sp.sparse.save_npz('adjM.npz', adj_matrix_coo)
print(f"{sp.sparse.issparse(adj_matrix_coo)}")

print("Superset adjacency matrix saved as 'adjM.npz' in compressed format.")