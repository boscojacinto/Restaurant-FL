import torch
import os.path as osp
from typing import List, Tuple, Union, Optional, Dict, Callable
from flwr.server import ServerApp, ServerAppComponents, ServerConfig
from flwr.server.strategy import FedAvg
from flwr.server.client_proxy import ClientProxy 
from flwr.common import (
	Context,
    EvaluateIns,
    EvaluateRes,
    FitIns,
    FitRes,
    MetricsAggregationFn,
    NDArrays,
    Parameters,
    Scalar,
    ndarrays_to_parameters,
    parameters_to_ndarrays,
)
from flwr.common.logger import log
from restaurant_fl.task import get_params, get_model
from swigg_db import SWGDataset

global_metadata = (['restaurant', 'area', 'customer'],
				   [('restaurant', 'to', 'restaurant'),
				    ('restaurant', 'to', 'area'),
				    ('restaurant', 'to', 'customer'),
				    ('area', 'to', 'restaurant'),
				    ('area', 'to', 'area'),
				    ('area', 'to', 'customer'),
				    ('customer', 'to', 'restaurant'),
				    ('customer', 'to', 'area'),
				    ('customer', 'to', 'customer')
				   ])

def get_global_model(model_name, metadata):
    path = osp.join(osp.dirname(osp.realpath(__file__)), '')
    dataset = SWGDataset(path, 0, force_reload=True)
    model = get_model(model_name, dataset.data)
    model.load_state_dict(torch.load('./restaurant_fl/swg_state_global.pth'))
    return model

def server_fn(context: Context) -> ServerAppComponents:
	num_rounds = context.run_config["num-server-rounds"]
	config = ServerConfig(num_rounds=num_rounds)

	model_name = context.run_config["model-name"]
	ndarrays = get_params(get_global_model(model_name, metadata=global_metadata))
	global_model_init = ndarrays_to_parameters(ndarrays)

	fraction_fit = context.run_config["fraction-fit"]
	fraction_evaluate = context.run_config["fraction-evaluate"]
	strategy = FedAvg(
		fraction_fit=fraction_fit,
		fraction_evaluate=fraction_evaluate,
		initial_parameters=global_model_init,
	)

	return ServerAppComponents(config=config, strategy=strategy)

app = ServerApp(server_fn=server_fn)