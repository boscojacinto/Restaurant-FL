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
		#print(f"SWGD:{fds.data}")
		#print(f"data.node_types:{fds.data.node_types}")

		# partitioner = IidPartitioner(num_partitions=num_partitions)
		# fds = FederatedDataset(
		# 	dataset="DynaOuchebara/devign_for_graphormer", partitioners={"train": partitioner}
		# )

	trainloader = fds
	print(f"trainloader:{trainloader}")
	testloader = {}
	# partition = fds.load_partition(partition_id)	
	# print(f"\n\npartition_id partition_id: {partition_id}\n")
	# print(partition.features['node_feat'])
	# def replace_label(example):
	# 	if example["y"] == "true":
	# 		example["label"] = 1
	# 	else:
	# 		example["label"] = 0
	# 	return example

	# partition = partition.map(replace_label)
	# partition_train_test = partition.train_test_split(test_size=0.2, seed=42)

	# tokenizer = AutoTokenizer.from_pretrained(model_name, model_max_length=512)

	# def tokenize_function(examples):
	# 	return tokenizer(examples["text"], truncation=True, add_special_tokens=True, padding=True)

	# #partition_train_test = partition_train_test.remove_columns("span")
	# #partition_train_test = partition_train_test.remove_columns("ordinal")
	# #partition_train_test = partition_train_test.map(tokenize_function, batched=True)
	# #partition_train_test = partition_train_test.remove_columns("text")
	# #partition_train_test = partition_train_test.rename_column("label", "labels")

	# #data_collator = DataCollatorWithPadding(tokenizer=tokenizer)
	# print(f"partition_train_test['train']:{partition_train_test['train'].__class__}")
	# trainloader = DataLoader(
	# 	partition_train_test["train"],
	# 	shuffle=True,
	# 	batch_size=32,
	# 	#collate_fn=data_collator,
	# )

	# testloader = DataLoader(
	# 	partition_train_test["test"],
	# 	batch_size=32,
	# 	#collate_fn=data_collator
	# )

	return trainloader, testloader

def get_model(model_name, metadata):
	if model_name == 'swigg/hgt-small-v1.0-restaurants-pred':		
		return SWG(hidden_channels=64, out_channels=2, num_heads=2, num_layers=1,
				node_types=['restaurant', 'area', 'customer'], metadata=metadata)
	else:
		return AutoModelForSequenceClassification.from_pretrained(model_name, num_labels=2)

def get_params(model):
	#return [[], 1, {}]
    return [np.empty((1, 2))]

def set_params(model, parameters) -> None:
	print('set_params')
	# if model != "swigg/hgt-small-v1.0-restaurants-pred":
	# 	params_dict = zip(model.state_dict().keys(), parameters)
	# 	state_dict = OrderedDict({k: torch.Tensor(v) for k, v in params_dict})
	# 	model.load_state_dict(state_dict, strict=True)

def train(net, trainloader, epochs, device) -> None:
	print(f"\n\nnet.__class__:{net.__class__}")	
	# with torch.no_grad():  # Initialize lazy modules.
	# 	net(trainloader.x_dict, trainloader.edge_index_dict)				
	optimizer = torch.optim.Adam(net.parameters(), lr=0.005, weight_decay=0.001)		
	net.train()
	optimizer.zero_grad()
	out = net(trainloader.x_dict, trainloader.edge_index_dict)
	mask = trainloader['restaurant'].train_mask
	loss = F.cross_entropy(out[mask], trainloader['restaurant'].y[mask])
	loss.backward()
	optimizer.step()
	print(f"\n\n\nTRAINN DONE\n\n\n\n")

def test(net, testloader, device) -> tuple[Any | float, Any]:
	metric = load_metric("accuracy")
	loss = 0
	# net.eval()
	# for batch in testloader:
	# 	batch = {k: v.to(device) for k, v in batch.items()}
	# 	with torch.no_grad():
	# 		outputs = net(**batch)
	# 	logits = outputs.logits
	# 	loss += outputs.loss.item()
	# 	predictions = torch.argmax(logits, dim=-1)
	# 	metric.add_batch(predictions=predictions, references=batch["labels"])

	#loss /= len(testloader.dataset)
	accuracy = 0
	#accuracy = metric.compute()["accuracy"]
	return loss, accuracy
