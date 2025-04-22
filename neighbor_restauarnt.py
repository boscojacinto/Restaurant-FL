import re
import sys
import grpc
import asyncio
import private_set_intersection.python as psi
import restaurant_pb2
import restaurant_pb2_grpc

psi_server = None
customer_ids = ["0x04c57743b8b39210913de928ae0b8e760d8e220c5539b069527b62f1aa3a49c47ec03188ff32f13916cf28673082a25afdd924d26d768e58e872f3f794365769d4",
				"0x04c57743b8b39210913de928ae0b8e760d8e220c5539b069527b62f1aa3a49c47ec03188ff32f13916cf28673082a25afdd924d26d768e58e872f3f794365769d2"]
restaurantKey = """🚕🔈🧩👩🏽‍🤝‍👩🏾🏌️‍♂️👆🏾👩‍👧‍👧🐀😴🧑🏼‍💻🤒💇🏼‍♂️🥞🕵️‍♀️"""

def restaurant_setup():
	global psi_server

	server_key = bytes(range(1, 33))
	psi_server = psi.server.CreateFromKey(server_key, False)

class RestaurantNeighbor(restaurant_pb2_grpc.RestaurantNeighborServicer):
    async def Setup(self, request: restaurant_pb2.SetupRequest,
    				context: grpc.aio.ServicerContext):
        global psi_server
        global customer_ids
        global restaurantKey
        fpr = 0.01

        setup_request = f"Setup (num_customers: {request.num_customers})"
        setup = psi.ServerSetup()
        setup.ParseFromString(psi_server.CreateSetupMessage(
            fpr, 1, customer_ids, psi.DataStructure.RAW).SerializeToString())
        return restaurant_pb2.SetupReply(setup=setup, restaurantKey=restaurantKey)

    async def Fetch(self, request: restaurant_pb2.CustomerRequest,
    				context: grpc.aio.ServicerContext):
    	global psi_server

    	customer_request = f"Fetch (request: {request})"
    	response = psi.Response()
    	response.ParseFromString(psi_server.ProcessRequest(
    						request.request).SerializeToString())
    	return restaurant_pb2.CustomerReply(response=response)

async def serve():
    restaurant_setup()

    server = grpc.aio.server()

    restaurant_pb2_grpc.add_RestaurantNeighborServicer_to_server(
    					RestaurantNeighbor(), server)
    server.add_insecure_port('[::]:50051')
    
    await server.start()
    print("Server started on port 50051")
    await server.wait_for_termination()

if __name__ == '__main__':
    asyncio.run(serve())