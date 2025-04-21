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
    def __init__(self, csv_file, city):

        df = pd.read_csv(csv_file)

        self.data = df.loc[(df['City'].str.contains(city, case=False))]
        self.data = self.data.drop(['ID', 'City', 'Restaurant', 'Price', 'Avg ratings', 'Total ratings', 'Delivery time'], axis=1)
        self.city = city

    def __len__(self):
        return len(self.data)
    
    def __getitem__(self, idx):
        sample = self.data.iloc[idx, 3]
        return sample

    def create_features(self):

        self.food_labels = { 'mughlai': 1.0 }

        keys = np.unique(self.data['Area'].astype(str).str.lower())
        vals = torch.rand((keys.size, 1), dtype=torch.float).tolist()
        self.area_labels = dict(zip(keys, vals))

        i = 0
        areas_df = {}
        self.address_labels = {}

        for area in self.area_labels:
            areas_df[area] = self.data[self.data['Area'].str.lower() == area]
            torch.manual_seed(42+i)
            keys = np.unique(areas_df[area]['Address'].astype(str).str.lower())
            vals = torch.rand((keys.size, 1), dtype=torch.float).tolist()
            self.address_labels[area] = dict(zip(keys, vals))
            i = i + 1

        self.data['Address'] = self.data.apply(
            lambda x: next((val[0] for addr, val in self.address_labels[x['Area'].lower()].items() if addr == x['Address'].lower()), 0.0),
            axis=1
        ).astype(float)
        #print(f"self.data['Address']:{self.data['Address']}")

        self.data['Area'] = self.data['Area'].str.lower().apply(
            lambda x: next((v[0] for k, v in self.area_labels.items() if k == x), 0.0)
        ).astype(float)        

        self.data['Food type'] = self.data['Food type'].str.lower().apply(
            lambda x: next((v for k, v in self.food_labels.items() if k in x.split(',')), 0.0)
        ).astype(float)

        filter_cols = [col for col in self.data.columns if ((col != 'Address') & (col != 'Area'))]
        self.f_r = torch.tensor(self.data[filter_cols].values, dtype=torch.float)
        filter_cols = [col for col in self.data.columns if ((col != 'Address') & (col != 'Food type'))]
        self.f_a = torch.tensor(self.data[filter_cols].values, dtype=torch.float)
        self.y = torch.tensor(self.data[filter_cols].iloc[:,-1].values, dtype=torch.float)
        self.a = torch.tensor(list(self.area_labels.values()), dtype=torch.float)

        # Restaurant features
        x = self.f_r.numpy()
        rows, cols = np.nonzero(x)
        values = x[rows, cols]
        self.features_0 = coo_matrix((values, (rows, cols)), shape=x.shape)
        sp.sparse.save_npz('features_0.npz', self.features_0)

        # Area features
        x = self.a.numpy()
        rows, cols = np.nonzero(x)
        values = x[rows, cols]
        self.features_1 = coo_matrix((values, (rows, cols)), shape=x.shape)
        sp.sparse.save_npz('features_1.npz', self.features_1)
        self.edge_attrs_1 = self.data.apply(
            lambda x: (x['Address'] if x['Food type'] == 1.0 else 0.0),
            axis=1
        ).to_numpy(dtype=float)
        self.edge_attrs_1 = np.compress(self.edge_attrs_1 != 0, self.edge_attrs_1)
        self.edge_attrs_1 = torch.tensor(self.edge_attrs_1, dtype=torch.float).numpy()
        np.save('edge_attrs_1.npy', self.edge_attrs_1, allow_pickle=False) 

        self.edge_attrs_3 = np.array(self.edge_attrs_1, copy=True)
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
        r_n = self.f_r.shape[0]
        c_n = self.c.shape[0]
        a_n = len(self.area_labels) #self.f_a.shape[0]

        # Restaurant to Restaurant
        # x_col_2 = self.f_r[:, -1]
        # r_to_r_adj = (x_col_2[:, None] == x_col_2[None, :]).int()
        # print(f"r_to_r_adj.shape={r_to_r_adj.shape}")
        # r_to_r_adj = r_to_r_adj - torch.eye(r_n, dtype=torch.float)
        r_to_r_adj = torch.zeros((r_n, r_n), dtype=torch.float)

        # Area to Area
        a_to_a_adj = torch.zeros((a_n, a_n))

        # Customer to Customer
        c_to_c_adj = torch.zeros((c_n, c_n))

        # Restuarant to Area
        r_col = self.f_r[:, -1]
        a_col = self.f_a[:, -1]

        rows = []
        cols = []
        values = []
        for r, r_v in enumerate(r_col):
            if r_v:
                a_v = a_col[r]
                if a_v:
                    for i, v in enumerate(self.a):
                        if a_v == v[0]:
                            rows.append(r)
                            cols.append(i)
                            print(f"r:{r}, a:{i}, v:{v[0]}")
                            values.append(v[0])
                            break

        print(f"len(values):{len(values)}")
        r_to_a_adj = sp.sparse.coo_matrix((values, (rows, cols)), shape=(r_n, a_n), copy=True)    
        r_to_a_adj = torch.tensor(r_to_a_adj.todense(), dtype=torch.float)
        # Area to Restaurant
        a_to_r_adj = r_to_a_adj.t()

        # Restaurant to Customer
        r_to_c_adj = torch.zeros((r_n, c_n))
        # Customer to Restaurant
        c_to_r_adj = r_to_c_adj.t()

        # Area to Customer
        a_to_c_adj = torch.zeros((a_n, c_n))
        # Cutomer to Area
        c_to_a_adj = a_to_c_adj.t()

        # Total
        total_n = r_n + c_n + a_n # 10115

        adj_matrix = torch.zeros((total_n, total_n), dtype=torch.float)
        # First layer
        adj_matrix[0:r_n, 0:r_n] = r_to_r_adj
        adj_matrix[0:r_n, r_n:r_n+a_n] = r_to_a_adj
        adj_matrix[0:r_n, r_n+a_n:total_n] = r_to_c_adj

        # Second layer
        adj_matrix[r_n:r_n+a_n, 0:r_n] = a_to_r_adj
        adj_matrix[r_n:r_n+a_n, r_n:r_n+a_n] = a_to_a_adj
        adj_matrix[r_n:r_n+a_n, r_n+a_n:total_n] = a_to_c_adj

        # Third layer
        adj_matrix[r_n+a_n:total_n, 0:r_n] = c_to_r_adj
        adj_matrix[r_n+a_n:total_n, r_n:r_n+a_n] = c_to_a_adj
        adj_matrix[r_n+a_n:total_n, r_n+a_n:total_n] = c_to_c_adj

        adj_matrix_np = adj_matrix.numpy()
        self.adjM = adj_matrix_np

        # rows, cols = np.nonzero(adj_matrix_np)
        # values = adj_matrix_np[rows, cols]
        # self.adjM = sp.sparse.coo_matrix((values, (rows, cols)), shape=adj_matrix_np.shape, copy=True)
        # sp.sparse.save_npz('adjM.npz', self.adjM)
        np.save('adjM.npy', self.adjM, allow_pickle=False) 

    def create_zip(self):
        with zipfile.ZipFile(f'SWGD_{self.city.replace(" ","-")}.zip',
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

    dataset = SWGDataset(csv_path, city)
    dataset.create_features()
    dataset.create_adjacency()
    dataset.create_zip()

if __name__ == "__main__":
    main()