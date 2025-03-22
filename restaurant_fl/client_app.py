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
	def __init__(self, model_name, trainloader, testloader) -> None:
		self.device = torch.device("cpu")
		self.trainloader = trainloader
		self.testloader = testloader
		self.net = get_model(model_name, trainloader.metadata())
		self.net.to(self.device)

	def fit(self, parameters, config) -> tuple[list, int, dict]:
		set_params(self.net, parameters)
		train(self.net, self.trainloader, epochs=1, device=self.device)
		return get_params(self.net), 1, {}

	def evaluate(self, parameters, config) -> tuple[float, int, dict[str, float]]:
		set_params(self.net, parameters)
		loss, accuracy = test(self.net, self.testloader, device=self.device)
		#print(f"LOSS:{loss} ACCURACY:{accuracy}")
		return float(loss), 1, {"accuracy": float(accuracy)}


def client_fn(context: Context) -> Client:
	partition_id = context.node_config["partition-id"]
	num_partitions = context.node_config["num-partitions"]

	model_name = context.run_config["model-name"]
	trainloader, testloader = load_data(partition_id, num_partitions, model_name)

	return RestaurantClient(model_name, trainloader, testloader).to_client()

app = ClientApp(client_fn=client_fn)