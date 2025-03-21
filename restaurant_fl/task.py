from typing import Any
from collections import OrderedDict

import torch
from torch.optim import AdamW
from torch.utils.data import DataLoader
from transformers import (
	AutoModelForSequenceClassification,
	AutoTokenizer,
	DataCollatorWithPadding,
)
from evaluate import load as load_metric
from datasets.utils.logging import disable_progress_bar
from flwr_datasets import FederatedDataset
from flwr_datasets.partitioner import IidPartitioner

import os
import sys
from torch_geometric.transforms import RandomLinkSplit, ToUndirected
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../'))
from swigg_db import SWGDataset
from swigg_ml import SWG
import torch.nn.functional as F
import numpy as np

disable_progress_bar()
fds = None

def load_data(partition_id: int, num_partitions: int, model_name: str) -> tuple[DataLoader[Any], DataLoader[Any]]:
	
	global fds
	if fds is None:
		path = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../')
		dataset = SWGDataset(path)
		fds = dataset[0] 

	trainloader = fds
	testloader = {}

	return trainloader, testloader

def get_model(model_name, metadata):
	return SWG(hidden_channels=64, out_channels=2, num_heads=2, num_layers=1,
			node_types=['restaurant', 'area', 'customer'], metadata=metadata)

def get_params(model):
	return [val.cpu().numpy() for _, val in model.state_dict().items()]

def set_params(model, parameters) -> None:
	print('set_params')
	# params_dict = zip(model.state_dict().keys(), parameters)
	# state_dict = OrderedDict({k: torch.Tensor(v) for k, v in params_dict})
	# model.load_state_dict(state_dict, strict=True)

def train(net, trainloader, epochs, device) -> None:
	optimizer = torch.optim.Adam(net.parameters(), lr=0.005, weight_decay=0.001)		
	net.train()
	optimizer.zero_grad()
	out = net(trainloader.x_dict, trainloader.edge_index_dict)
	mask = trainloader['restaurant'].train_mask
	loss = F.cross_entropy(out[mask], trainloader['restaurant'].y[mask])
	loss.backward()
	optimizer.step()

def test(net, trainloader, testloader, device) -> tuple[Any | float, Any]:
	metric = load_metric("accuracy")
	loss = 0
	net.eval()
	with torch.no_grad():
		outputs = net(trainloader.x_dict, trainloader.edge_index_dict).argmax(dim=-1)

	mask = trainloader['restaurant']['test_mask']
	accuracy = (outputs[mask] == trainloader['restaurant'].y[mask]).sum() / mask.sum()
	loss = 1 - accuracy
	return loss, accuracy
