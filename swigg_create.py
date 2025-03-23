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
    def __init__(self, csv_file, city, area):

        df = pd.read_csv(csv_file)

        self.data = df.loc[(df['City'].str.contains(city, case=False)) & 
            df['Area'].str.contains(area, case=False)
        ]
        self.data = self.data.drop(['ID', 'Price', 'Total ratings', 'Restaurant', 'Avg ratings', 'Avg ratings', 'Delivery time'], axis=1)
        self.city = city
        self.area = area

    def __len__(self):
        return len(self.data)
    
    def __getitem__(self, idx):
        sample = self.data.iloc[idx, 3]
        return sample

    def create_features(self):

        self.city_labels = { 'mumbai': 1.0 }
        self.area_labels = { self.area: 0.3 }
        self.food_labels = { 'mughlai': 1.0 }

        keys = np.unique(self.data['Address'].astype(str).str.lower())
        vals = torch.rand((keys.size, 1), dtype=torch.float).tolist()
        self.address_labels = dict(zip(keys, vals))

        self.data['City'] = self.data['City'].str.lower().apply(
            lambda x: next((v for k, v in self.city_labels.items() if k in x.split(',')), 1.0)           
        ).astype(float)

        self.data['Area'] = self.data['Area'].str.lower().apply(
            lambda x: next((v for k, v in self.area_labels.items() if k in x.split(',')), 1.0)
        ).astype(float)        

        self.data['Food type'] = self.data['Food type'].str.lower().apply(
            lambda x: next((v for k, v in self.food_labels.items() if k in x.split(',')), 0)
        ).astype(float)

        self.data['Address'] = self.data['Address'].str.lower().apply(
            lambda x: next((v[0] for k, v in self.address_labels.items() if k == x), 0.0)
        ).astype(float)

        filter_cols = [col for col in self.data.columns if col != 'Address']
        self.x = torch.tensor(self.data[filter_cols].values, dtype=torch.float)
        self.y = torch.tensor(self.data[filter_cols].iloc[:,-1].values, dtype=torch.float)

        # Restaurant features
        x = self.x.numpy()
        # np.savetxt('restaurant_matrix.csv', x,
        #             delimiter=",", fmt="%.2f",
        #             header='Area,City,Food type')
        rows, cols = np.nonzero(x)
        values = x[rows, cols]
        self.features_0 = coo_matrix((values, (rows, cols)), shape=x.shape)
        sp.sparse.save_npz('features_0.npz', self.features_0)

        # Area features
        self.a = torch.ones(1, 2, dtype=torch.float)
        mask = torch.rand(1) < 0.1
        self.a[:, 1] = 0.0
        self.a[mask, 1] = 1.0
        self.features_1 =coo_matrix(self.a)
        sp.sparse.save_npz('features_1.npz', self.features_1)
        self.edge_attrs_1 = torch.tensor(self.data['Address'].values, dtype=torch.float).numpy()
        np.save('edge_attrs_1.npy', self.edge_attrs_1, allow_pickle=False) 
        self.edge_attrs_3 = torch.tensor(self.data['Address'].values, dtype=torch.float).numpy()
        np.save('edge_attrs_3.npy', self.edge_attrs_3, allow_pickle=False) 

        # Customer features
        self.c = torch.ones(10000, 3, dtype=torch.float)
        mask = torch.rand(10000) < 0.1
        self.c[:, 2] = 0.0
        self.c[mask, 2] = 1.0
        self.features_2 =coo_matrix(self.c)
        sp.sparse.save_npz('features_2.npz', self.features_2)

        # Labels (based on food type success)
        self.labels = self.y.numpy()
        np.save('labels.npy', self.labels, allow_pickle=False) 

    def create_adjacency(self):
        x_n = self.x.shape[0]
        c_n = self.c.shape[0]
        a_n = 1

        # Restaurant to Restaurant
        x_col_2 = self.x[:, 2]
        r_to_r_adj = (x_col_2[:, None] == x_col_2[None, :]).int()
        r_to_r_adj = r_to_r_adj - torch.eye(x_n, dtype=torch.float)

        # Area to Area
        a_to_a_adj = torch.zeros((a_n, a_n))

        # Customer to Customer
        c_to_c_adj = torch.zeros((c_n, c_n))

        # Restuarant to Area
        r_to_a_adj = torch.ones((x_n, a_n))  
        # Area to Restaurant
        a_to_r_adj = r_to_a_adj.t()

        # Restaurant to Customer
        c_col_2 = self.c[:, 2]
        torch.manual_seed(323)
        r_to_c_adj = torch.randint(0, 2, (x_n, c_n), dtype=torch.float)
        r_to_c_adj = r_to_c_adj * c_col_2.t()
        # Customer to Restaurant
        c_to_r_adj = r_to_c_adj.t()

        # Area to Customer
        a_to_c_adj = torch.ones((a_n, c_n), dtype=torch.float)
        #a_to_c_adj = torch.randint(0, 2, (a_n, c_n), dtype=torch.float)
        # Cutomer to Area
        c_to_a_adj = a_to_c_adj.t()

        # Total
        total_n = x_n + c_n + a_n # 10115

        adj_matrix = torch.zeros((total_n, total_n), dtype=torch.float)
        # First layer
        adj_matrix[0:x_n, 0:x_n] = r_to_r_adj
        adj_matrix[0:x_n, x_n:x_n+a_n] = r_to_a_adj
        adj_matrix[0:x_n, x_n+a_n:total_n] = r_to_c_adj

        # Second layer
        adj_matrix[x_n:x_n+a_n, 0:x_n] = a_to_r_adj
        adj_matrix[x_n:x_n+a_n, x_n:x_n+a_n] = a_to_a_adj
        adj_matrix[x_n:x_n+a_n, x_n+a_n:total_n] = a_to_c_adj

        # Third layer
        adj_matrix[x_n+a_n:total_n, 0:x_n] = c_to_r_adj
        adj_matrix[x_n+a_n:total_n, x_n:x_n+a_n] = c_to_a_adj
        adj_matrix[x_n+a_n:total_n, x_n+a_n:total_n] = c_to_c_adj

        adj_matrix_np = adj_matrix.numpy()
        self.adjM = adj_matrix_np

        # rows, cols = np.nonzero(adj_matrix_np)
        # values = adj_matrix_np[rows, cols]
        # self.adjM = sp.sparse.coo_matrix((values, (rows, cols)), shape=adj_matrix_np.shape, copy=True)
        # sp.sparse.save_npz('adjM.npz', self.adjM)
        np.save('adjM.npy', self.adjM, allow_pickle=False) 

    def create_zip(self):
        with zipfile.ZipFile(f'SWGD_{self.city.replace(" ","-")}-{self.area.replace(" ","-")}.zip',
                             'w', compression=zipfile.ZIP_DEFLATED) as zipf:
            zipf.write('adjM.npy')
            zipf.write('features_0.npz')
            zipf.write('features_1.npz')
            zipf.write('features_2.npz')
            zipf.write('edge_attrs_1.npy')
            zipf.write('edge_attrs_3.npy')
            zipf.write('labels.npy')

        os.remove('adjM.npy')
        os.remove('features_0.npz')
        os.remove('features_1.npz')
        os.remove('features_2.npz')
        os.remove('edge_attrs_1.npy')
        os.remove('edge_attrs_3.npy')
        os.remove('labels.npy')

def main():
    csv_path = './restaurant.csv'
    city = 'mumbai'
    area = 'powai'

    dataset = SWGDataset(csv_path, city, area)
    dataset.create_features()
    dataset.create_adjacency()
    dataset.create_zip()

if __name__ == "__main__":
    main()