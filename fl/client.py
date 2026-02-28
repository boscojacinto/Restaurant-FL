import logging
import threading
from pathlib import Path
from config import ConfigOptions
from flwr.client.supernode.app import run_supernode

logger = logging.getLogger(__name__)

class FLClient:
	def __init__(self):
		self.flwr_dir = None
		self.started = False
		self.thread = None
		self.config = ConfigOptions().get_fl_config()
		logger.info("========= Initializing Flower Client ========")

	def run(self):
		self.flwr_dir = Path(ConfigOptions()._root_dir) / "fl"
		self.flwr_dir.mkdir(exist_ok=True)
		run_supernode(flwr_dir=str(self.flwr_dir),
			insecure=self.config.flwr_insecure,
			node_config=f"partition-id={self.config.flwr_partition_id} num-partitions=2",
			clientappio_api_address=self.config.flwr_clientappio_api_address)

	def start(self):
		self.thread = threading.Thread(target=self.run)
		self.started = True
		self.thread.start()
		return self.thread

	def stop(self):
		self.started = False
