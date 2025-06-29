import os
import time
import asyncio
import threading
import flwr

class FLServer:
	def __init__(self):
		self.started = False
		self.thread = None
		self.thread_neighbor = None

	def run(self):
		flwr.server.app.run_superlink()

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