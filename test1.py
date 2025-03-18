import torch
import numpy as np

def create_adj_matrix(rows=114, cols=1, max_consecutive=5):
    # Initialize empty matrix
    adj_matrix = torch.zeros(rows, cols, dtype=torch.float32)
    
    for i in range(rows):
        # Keep track of consecutive ones
        consecutive_count = 0
        for j in range(cols):
            # If we've reached max consecutive ones, force a zero
            if consecutive_count >= max_consecutive:
                adj_matrix[i, j] = 0
                consecutive_count = 0
            else:
                # Randomly decide if this should be a 1
                value = torch.rand(1).item() < 0.2
                if value:
                    adj_matrix[i, j] = 1
                    consecutive_count += 1
                else:
                    adj_matrix[i, j] = 0
                    consecutive_count = 0
    
    return adj_matrix

# Create the matrix
adj_matrix = create_adj_matrix()

# Convert PyTorch tensor to NumPy array
adj_matrix_np = adj_matrix.numpy()

# Save as compressed NumPy file
np.savez_compressed('customer_adj.npz', adj_matrix=adj_matrix_np)

# Verify the save (optional)
print(f"Shape: {adj_matrix.shape}")
print(f"Sample row: {adj_matrix[0]}")

# Optional: Load and verify the saved file
loaded_data = np.load('customer_adj.npz')
loaded_matrix = loaded_data['adj_matrix']
print(f"Loaded shape: {loaded_matrix.shape}")