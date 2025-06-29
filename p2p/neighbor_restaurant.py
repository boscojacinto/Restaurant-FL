import re
import os
import sys
import grpc
import asyncio
import private_set_intersection.python as psi
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../'))
import p2p.restaurant_pb2 as r_pb2
import p2p.restaurant_pb2_grpc as r_pb2_gprc

psi_server = None
customer_ids = ["0x04c57743b8b39210913de928ae0b8e760d8e220c5539b069527b62f1aa3a49c47ec03188ff32f13916cf28673082a25afdd924d26d768e58e872f3f794365769d4",
				"0x04c57743b8b39210913de928ae0b8e760d8e220c5539b069527b62f1aa3a49c47ec03188ff32f13916cf28673082a25afdd924d26d768e58e872f3f794365769d2"]
restaurantKey = """🚕🔈🧩👩🏽‍🤝‍👩🏾🏌️‍♂️👆🏾👩‍👧‍👧🐀😴🧑🏼‍💻🤒💇🏼‍♂️🥞🕵️‍♀️"""

def restaurant_setup():
	global psi_server

	server_key = bytes(range(1, 33))
	psi_server = psi.server.CreateFromKey(server_key, False)

class RestaurantNeighbor(r_pb2_gprc.RestaurantNeighborServicer):
    async def Setup(self, request: r_pb2.SetupRequest,
    				context: grpc.aio.ServicerContext):
        global psi_server
        global customer_ids
        global restaurantKey
        fpr = 0.01

        setup_request = f"Setup (num_customers: {request.num_customers})"
        setup = psi.ServerSetup()
        setup.ParseFromString(psi_server.CreateSetupMessage(
            fpr, 1, customer_ids, psi.DataStructure.RAW).SerializeToString())
        return r_pb2.SetupReply(setup=setup, restaurantKey=restaurantKey)

    async def Fetch(self, request: r_pb2.CustomerRequest,
    				context: grpc.aio.ServicerContext):
    	global psi_server

    	customer_request = f"Fetch (request: {request})"
    	response = psi.Response()
    	response.ParseFromString(psi_server.ProcessRequest(
    						request.request).SerializeToString())
    	return r_pb2.CustomerReply(response=response)

async def serve():
    restaurant_setup()

    server = grpc.aio.server()

    r_pb2_gprc.add_RestaurantNeighborServicer_to_server(
    					RestaurantNeighbor(), server)
    server.add_insecure_port('[::]:50051')
    
    await server.start()
    print("Server started on port 50051")
    await server.wait_for_termination()

def main():
    asyncio.run(serve())

if __name__ == '__main__':
    asyncio.run(serve())