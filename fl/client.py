import threading
from flwr.client.supernode.app import run_supernode

class FLClient:
	def __init__(self, i):
		self.started = False
		self.thread = None
		self.id = i
		print(f"\n========= Initializing Flower Client {i} ========\n")

	def run(self, i):
		run_supernode(i)

	def start(self):
		self.thread = threading.Thread(target=self.run, args=(self.id,))
		self.started = True
		self.thread.start()
		return self.thread

	def stop(self):
		self.started = False
