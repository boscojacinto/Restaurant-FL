import os
import os.path as osp
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

    def create_labels(self):

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

    def create_restaurants(self):
        self.x = torch.tensor(self.data.values, dtype=torch.float)
        self.y = torch.tensor(self.data.iloc[:,-1].values, dtype=torch.float)

def main():
    csv_path = './restaurant.csv'
    
    dataset = SWGDataset(csv_path)
    dataset.create_labels()
    dataset.create_restaurants()

    tensor = dataset.x.numpy()
    rows, cols = np.nonzero(tensor)
    values = tensor[rows, cols]
    features_0 = coo_matrix((values, (rows, cols)), shape=tensor.shape)
    sp.sparse.save_npz('features_0.npz', features_0)

    labels_np = dataset.y.numpy()
    np.save('labels.npy', labels_np, allow_pickle=False) 

if __name__ == "__main__":
    main()


        # # Label output as success or fail randomly
        # self.y = torch.tensor(
        #     [1, 0, 0, 0, 0, 0, 1, 0, 0, 0,
        #     0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0,
        #     0, 0, 0, 1, 0, 0, 1, 1, 0, 0,
        #     0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        #     1, 0, 0, 0, 0, 1, 0, 0, 1, 0,
        #     0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 1,
        #     0, 0, 0, 0, 0, 0, 1, 0, 0,
        #     0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        #     0, 0, 1, 0, 0, 1, 0, 0, 0,
        #     1, 0, 0, 0, 1, 0, 0, 0, 0, 0,
        #     0, 0, 0, 0, 0, 0, 0, 0, -1, 0,
        #     0, 0, 0, 0], dtype=torch.long)
        # #print(f"self.y {self.y}")
