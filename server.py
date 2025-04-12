import os
import time
import json
import requests
import threading
from flwr.server.app import run_superlink
from flwr.cli.run import run

from types import SimpleNamespace
import flwr
from pathlib import Path

class FLServer:
	def __init__(self):
		self.started = False
		self.thread = None

	def run(self):
		run_superlink()

	def start(self):
		self.thread = threading.Thread(target=self.run)
		self.started = True
		self.thread.start()

	def federate(self):
		print("Started Federated Learning")
		run(federation="local-deployment")

def main():
	print(flwr.__file__)

	fl_server = FLServer()
	time.sleep(1)
	fl_server.start()
	# time.sleep(10)
	# fl_server.federate()

	try:
		while True:
			time.sleep(1)
	except KeyboardInterrupt:
		pass

if __name__ == '__main__':
	main()