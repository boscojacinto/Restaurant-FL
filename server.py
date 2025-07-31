import os
import time
import asyncio
import threading
from pathlib import Path
import flwr
from config import ConfigOptions

class FLServer:
	def __init__(self):
		self.started = False
		self.thread = None
		self.flwr_dir = Path(ConfigOptions()._root_dir) / "fl_server"
		self.flwr_dir.mkdir(exist_ok=True)		

	def run(self):
		flwr.server.app.run_superlink(flwr_dir=str(self.flwr_dir),
			insecure=True)
	def start(self):
		self.thread = threading.Thread(target=self.run)
		self.started = True
		self.thread.start()

	def federate(self):
		print("Started Federated Learning")
		flwr.cli.run(federation="local-deployment")

def main():

	fl_server = FLServer()
	time.sleep(1)
	fl_server.start()
	# time.sleep(10)
	# fl_server.federate()

	try:
		while True:
			time.sleep(1)
	except KeyboardInterrupt:
		fl_server.thread.join()
		
if __name__ == '__main__':
	main()