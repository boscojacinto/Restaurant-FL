import logging
from typing import Any
from collections import OrderedDict

logger = logging.getLogger(__name__)

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
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../ml'))
from swg_db_local import SWGDatasetLocal
from swg_ml_local import SWG, create_loader, train_local, test_local
import torch.nn.functional as F
import numpy as np

disable_progress_bar()
#fds = None

def load_data(partition_id: int, num_partitions: int, model_name: str) -> tuple[DataLoader[Any], DataLoader[Any]]:

	path = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../')
	dataset = SWGDatasetLocal(path, partition_id, force_reload=True)
	fds = dataset.data 

	transform = RandomLinkSplit(
		num_val=0.1,
		num_test=0.2,
		neg_sampling_ratio=0.0,
		edge_types=[('restaurant', 'to', 'area'),
					('restaurant', 'to', 'customer'),
					],
		rev_edge_types=[('area', 'to', 'restaurant'),
					('customer', 'to', 'restaurant'),
					],
	)

	train_data, val_data, test_data = transform(fds)
	train_loader, val_loader, test_loader = create_loader(train_data, val_data, test_data)

	return fds, train_loader, val_loader,test_loader

def get_model(model_name, data):
	return SWG(hidden_channels=64, num_heads=2, num_layers=2,
                node_types=['restaurant', 'area', 'customer'],
                mlp_hidden_layers=[128, 64, 32, 1], mlp_dropout=0.4,
                data=data)

def get_params(model):
	return [val.cpu().numpy() for _, val in model.state_dict().items()]

def set_params(model, parameters) -> None:
	params_dict = zip(model.state_dict().keys(), parameters)
	state_dict = OrderedDict({k: torch.Tensor(v) for k, v in params_dict})
	model.load_state_dict(state_dict, strict=True)

def train(net, train_loader, epochs, device) -> None:
	for epoch in range(1, epochs):
		train_local(net, train_loader, epoch)

def test(net, test_loader, epochs, device) -> tuple[Any | float, Any]:
	for epoch in range(1, epochs):
		metric = test_local(net, test_loader, epoch)
	return metric['loss'], metric['acc']