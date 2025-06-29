import asyncio
import threading
from .restaurant_model import AIModel as bot
from .restaurant_model import CUSTOM_MODEL, INITIAL_PROMPT

AI_MODEL = "swigg1.0-gemma3:4b"

class AIClient:
	def __init__(self):
		self.thread = None
		self.initial_prompt = INITIAL_PROMPT
		self.prompt = None
		self.customer_id = None
		self.started = False
		self.cb = None
		self.bots = {}
		self.lock = threading.Lock()
		print(f"========= Launching AI model {CUSTOM_MODEL} ========")

	def run(self):

		while True:
			with self.lock:
				if self.prompt is not None \
				and self.customer_id is not None \
				and self.bots[self.customer_id] is not None:
					bot = self.bots[self.customer_id]
					print(f"New prompt: {self.prompt}, from customer: {self.customer_id}")

					response = asyncio.run(bot.generate(self.prompt))
					print(f"Sending Bot's response:{response}")
					asyncio.run(self.cb("chat", self.customer_id, response, None))

					if bot.summary is not None:
						embeds = asyncio.run(bot.embed(bot.summary))
						asyncio.run(self.cb("feedback", self.customer_id, bot.feedback_prompt, embeds))
						bot.summary = None

					elif bot.feedback is not None:
						embeds = asyncio.run(bot.embed(bot.feedback))
						asyncio.run(self.cb("end", self.customer_id, '', embeds))
						bot.feedback = None
						self.bots[self.customer_id] = None

					self.prompt = None
					self.customer_id = None

	def start(self, cb):
		self.cb = cb
		self.thread = threading.Thread(target=self.run)
		self.started = True 		
		self.thread.start()
		return self.thread

	def sendMessage(self, customer_id, message):
		with self.lock:
			try:
				self.bots[customer_id]
				self.prompt = message
				self.customer_id = customer_id
			except KeyError:
				print("Cannot send message to Bot, User Session closed.")

	async def greet(self, customer_id, restaurant_key):
		c_id = customer_id['publicKey']
		try:
			self.bots[c_id]
		except KeyError:			
			self.bots[c_id] = bot(customer_id, restaurant_key)

		_generate = self.bots[c_id].generate

		response = await _generate(self.initial_prompt)
		print(f"Greeting:{response}")
		await self.cb("start", self.customer_id, response, None)

	def stop(self):
		self.started = False
