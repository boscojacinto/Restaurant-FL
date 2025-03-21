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

disable_progress_bar()
fds = None

def load_data(partition_id: int, num_partitions: int, model_name: str) -> tuple[DataLoader[Any], DataLoader[Any]]:
	
	global fds
	if fds is None:
		partitioner = IidPartitioner(num_partitions=num_partitions)
		fds = FederatedDataset(
			dataset="DynaOuchebara/devign_for_graphormer", partitioners={"train": partitioner}
		)

	partition = fds.load_partition(partition_id)	
	print(f"\n\npartition_id partition_id: {partition_id}\n")
	print(partition.features['node_feat'])
	def replace_label(example):
		if example["y"] == "true":
			example["label"] = 1
		else:
			example["label"] = 0
		return example

	partition = partition.map(replace_label)
	partition_train_test = partition.train_test_split(test_size=0.2, seed=42)

	tokenizer = AutoTokenizer.from_pretrained(model_name, model_max_length=512)

	def tokenize_function(examples):
		return tokenizer(examples["text"], truncation=True, add_special_tokens=True, padding=True)

	#partition_train_test = partition_train_test.remove_columns("span")
	#partition_train_test = partition_train_test.remove_columns("ordinal")
	#partition_train_test = partition_train_test.map(tokenize_function, batched=True)
	#partition_train_test = partition_train_test.remove_columns("text")
	#partition_train_test = partition_train_test.rename_column("label", "labels")

	#data_collator = DataCollatorWithPadding(tokenizer=tokenizer)
	print(f"partition_train_test['train']:{partition_train_test['train'].__class__}")
	trainloader = DataLoader(
		partition_train_test["train"],
		shuffle=True,
		batch_size=32,
		#collate_fn=data_collator,
	)

	testloader = DataLoader(
		partition_train_test["test"],
		batch_size=32,
		#collate_fn=data_collator
	)

	return trainloader, testloader

def get_model(model_name):
	return AutoModelForSequenceClassification.from_pretrained(model_name, num_labels=2)

def get_params(model):
    return [val.cpu().numpy() for _, val in model.state_dict().items()]

def set_params(model, parameters) -> None:
    params_dict = zip(model.state_dict().keys(), parameters)
    state_dict = OrderedDict({k: torch.Tensor(v) for k, v in params_dict})
    model.load_state_dict(state_dict, strict=True)

def train(net, trainloader, epochs, device) -> None:
	optimizer = AdamW(net.parameters(), lr=5e-5)
	net.train()
	# for _ in range(epochs):
	# 	for batch in trainloader:
	# 		batch = {k: v.to(device) for k, v in batch.items()}
	# 		outputs = net(**batch)
	# 		loss = outputs.loss
	# 		loss.backward()
	# 		optimizer.step()
	# 		optimizer.zero_grad()

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
