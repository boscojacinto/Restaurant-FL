import numpy as np
import scipy as sp
from scipy.sparse import coo_matrix

# Create tensor of shape (10000, 3)
tensor = np.ones((10000, 3), dtype=float)  # Fill all with 1.0
tensor[:, 2] = np.random.choice([0.0, 1.0], size=10000)  # Last column with random 0.0 or 1.0

# Example of first few rows to verify
print(tensor[:5])

features_1 =coo_matrix(tensor)
sp.sparse.save_npz('features_1.npz', features_1)