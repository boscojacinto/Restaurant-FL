import sys
import private_set_intersection.python as psi

# import p2p.restaurant_pb2

def main():
	server_key = bytes(range(1, 33))
	psi_server = psi.server.CreateFromKey(server_key, False)	


if __name__ == "__main__":
	main()