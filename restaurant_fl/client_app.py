import warnings

import torch
from flwr.client import Client, ClientApp, NumPyClient
from flwr.common import Context
from transformers import logging
from restaurant_fl.task import (
	train,
	test,
	load_data,
	get_model,
	get_params,
	set_params,
)

warnings.filterwarnings("ignore", category=FutureWarning)

logging.set_verbosity_error()

class RestaurantClient(NumPyClient):
	def __init__(self, model_name, data, train_loader, val_loader, test_loader) -> None:
		self.device = torch.device("cpu")
		self.train_loader = train_loader
		self.val_loader = val_loader
		self.test_loader = test_loader
		self.net = get_model(model_name, data)
		self.net.to(self.device)

	def fit(self, parameters, config) -> tuple[list, int, dict]:
		set_params(self.net, parameters)
		train(self.net, self.train_loader, epochs=30, device=self.device)
		return get_params(self.net), len(self.train_loader), {}

	def evaluate(self, parameters, config) -> tuple[float, int, dict[str, float]]:
		set_params(self.net, parameters)
		loss, accuracy = test(self.net, self.test_loader, epochs=30, device=self.device)
		print(f"loss:{loss} accuracy:{accuracy}")
		return float(loss), len(self.test_loader), {"accuracy": float(accuracy)}


def client_fn(context: Context) -> Client:
	partition_id = context.node_config["partition-id"]
	num_partitions = context.node_config["num-partitions"]

	model_name = context.run_config["model-name"]
	print(f"CLIENT:{partition_id}")
	data, train_loader, val_loader, test_loader = load_data(
				partition_id, num_partitions, model_name)
	return RestaurantClient(
		model_name, data,
		train_loader,
		val_loader,
		test_loader).to_client()

app = ClientApp(client_fn=client_fn)