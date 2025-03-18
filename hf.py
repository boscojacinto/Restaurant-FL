import torch
#import pandas as pd
#import networkx as nx
#import matplotlib.pyplot as plt

from datasets import load_dataset

ds = load_dataset("VincentPai/for-graphormer-v6")

#splits = {'train': 'train.jsonl', 'validation': 'validation.jsonl', 'test': 'test.jsonl'}
#df = pd.read_json("hf://datasets/VincentPai/for-graphormer-v6/" + splits["train"])

#print(df.shape())

#numpy_array = df.to_numpy()

#tensor = torch.tensor(numpy_array)

#print(tensor)
#G = nx.Graph()