import os
import ctypes
import multiprocessing
from ctypes import CDLL
from ollama import chat
from ollama import ChatResponse
from flwr.client.supernode.app import run_supernode


def main():	
	lib = CDLL("./restaurant_status/libstatus.so.0")

	mp_spawn_context = multiprocessing.get_context("spawn")

	print("\n\n========= Trying to run supernode in a new process ========\n\n")

	proc = mp_spawn_context.Process(
	    target=run_supernode,
	    daemon=True,
	)

	print("\n\n========= Trying to Login in ========\n\n")

	# lib.GetAccounts.argtypes = [ctypes.c_char_p]
	# lib.GetAccounts.restype = ctypes.c_char_p

	result = lib.Login()

	print("\n\n========= Trying to launch model ========\n\n")

	response: ChatResponse = chat(model='swigg-gemma3:1b', messages=[
		{
			'role': 'user',
			'content': 'Hello',
		}
	])

	print(response['message']['content'])

	proc.start()
	proc.join()


if __name__ == '__main__':
	main()