import os
import os.path as osp
import zipfile
import torch
import pandas as pd
import numpy as np
import scipy as sp
from torch.utils.data import Dataset, DataLoader
from torch_geometric.data import Data
from scipy.sparse import coo_matrix, issparse, load_npz

# 1. First, create a custom Dataset class
class SWGDataset(Dataset):
    def __init__(self, csv_file):

        df = pd.read_csv(csv_file)

        self.data = df.loc[(df['City'].str.contains('Mumbai', case=False)) & 
            df['Area'].str.contains('Powai', case=False)
        ]
        self.data = self.data.drop(['ID', 'Price', 'Total ratings', 'Restaurant', 'Avg ratings', 'Avg ratings', 'Address', 'Delivery time'], axis=1)

    def __len__(self):
        return len(self.data)
    
    def __getitem__(self, idx):
        sample = self.data.iloc[idx, 3]
        return sample

    def create_features(self):

        self.city_labels = { 'mumbai': 1.0 }
        self.area_labels = { 'powai': 1.0 }
        self.food_labels = { 'mughlai': 1.0 }        

        self.data['City'] = self.data['City'].str.lower().apply(
            lambda x: next((v for k, v in self.city_labels.items() if k in x.split(',')), 1.0)           
        ).astype(float)

        self.data['Area'] = self.data['Area'].str.lower().apply(
            lambda x: next((v for k, v in self.area_labels.items() if k in x.split(',')), 1.0)
        ).astype(float)        

        self.data['Food type'] = self.data['Food type'].str.lower().apply(
            lambda x: next((v for k, v in self.food_labels.items() if k in x.split(',')), 0)
        ).astype(float)

        self.x = torch.tensor(self.data.values, dtype=torch.float)
        self.y = torch.tensor(self.data.iloc[:,-1].values, dtype=torch.float)

        x = self.x.numpy()
        # np.savetxt('restaurant_matrix.csv', x,
        #             delimiter=",", fmt="%.2f",
        #             header='Area,City,Food type')
        rows, cols = np.nonzero(x)
        values = x[rows, cols]
        self.features_0 = coo_matrix((values, (rows, cols)), shape=x.shape)
        sp.sparse.save_npz('features_0.npz', self.features_0)

        self.c = torch.ones(10000, 3, dtype=torch.float)
        mask = torch.rand(10000) < 0.1

        self.c[:, 2] = 0.0
        self.c[mask, 2] = 1.0

        self.features_1 =coo_matrix(self.c)
        sp.sparse.save_npz('features_1.npz', self.features_1)

        self.labels = self.y.numpy()
        np.save('labels.npy', self.labels, allow_pickle=False) 

    def create_adjacency(self):
        x_n = self.x.shape[0]
        x_col_2 = self.x[:, 2]

        r_to_r_adj = (x_col_2[:, None] == x_col_2[None, :]).int()
        r_to_r_adj = r_to_r_adj - torch.eye(x_n, dtype=torch.float)

        c_to_c_adj = torch.zeros((self.c.shape[0], self.c.shape[0]))

        c_n = self.c.shape[0]
        c_col_2 = self.c[:, 2]
        torch.manual_seed(323)
        r_to_c_adj = torch.randint(0, 2, (x_n, c_n), dtype=torch.float)
        r_to_c_adj = r_to_c_adj * c_col_2.t()

        c_to_r_adj = r_to_c_adj.t()

        total_n = x_n + c_n  # 10114

        adj_matrix = torch.zeros((total_n, total_n), dtype=torch.float)
        adj_matrix[0:x_n, 0:x_n] = r_to_r_adj
        adj_matrix[0:x_n, x_n:total_n] = r_to_c_adj
        adj_matrix[x_n:total_n, 0:x_n] = c_to_r_adj
        adj_matrix[x_n:total_n, x_n:total_n] = c_to_c_adj

        adj_matrix_np = adj_matrix.numpy()
        rows, cols = np.nonzero(adj_matrix_np)
        values = adj_matrix_np[rows, cols]
        self.adjM = sp.sparse.coo_matrix((values, (rows, cols)), shape=adj_matrix_np.shape)
        sp.sparse.save_npz('adjM.npz', self.adjM)

    def create_train_val_test_split(self):
        assignment = torch.randint(0, 3, (114,))

        data_splits = {
            "train_idx": (assignment == 0).numpy(),  # True where assignment is 0
            "val_idx": (assignment == 1).numpy(),    # True where assignment is 1
            "test_idx": (assignment == 2).numpy()    # True where assignment is 2
        }

        np.savez_compressed('train_val_test_idx.npz', **data_splits)

    def create_zip(self):
        with zipfile.ZipFile('SWGD_processed.zip', 'w', compression=zipfile.ZIP_DEFLATED) as zipf:
            zipf.write('adjM.npz')
            zipf.write('features_0.npz')
            zipf.write('features_1.npz')
            zipf.write('labels.npy')
            zipf.write('train_val_test_idx.npz')

        os.remove('adjM.npz')
        os.remove('features_0.npz')
        os.remove('features_1.npz')
        os.remove('labels.npy')
        os.remove('train_val_test_idx.npz')

def main():
    csv_path = './restaurant.csv'
    
    dataset = SWGDataset(csv_path)
    dataset.create_features()
    dataset.create_adjacency()
    dataset.create_train_val_test_split()
    dataset.create_zip()

if __name__ == "__main__":
    main()