import re
import os
import sys
import grpc
import ecdsa
import asyncio
import private_set_intersection.python as psi
import restaurant_pb2
from google.protobuf.json_format import MessageToJson

psi_server = None
customer_ids = ["0x04c57743b8b39210913de928ae0b8e760d8e220c5539b069527b62f1aa3a49c47ec03188ff32f13916cf28673082a25afdd924d26d768e58e872f3f794365769d4",
				"0x04c57743b8b39210913de928ae0b8e760d8e220c5539b069527b62f1aa3a49c47ec03188ff32f13916cf28673082a25afdd924d26d768e58e872f3f794365769d2"]

#restaurant_key = """🚕🔈🧩👩🏽‍🤝‍👩🏾🏌️‍♂️👆🏾👩‍👧‍👧🐀😴🧑🏼‍💻🤒💇🏼‍♂️🥞🕵️‍♀️"""
private_key = os.urandom(32)
signing_key = ecdsa.SigningKey.from_string(private_key, curve=ecdsa.SECP256k1)
restaurant_key = '0x' + signing_key.get_verifying_key().to_string("compressed").hex()
#signing_key = '0x' + signing_key.to_string().hex()
signing_key = '0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef'

def restaurant_setup():
	global psi_server

	server_key = bytes(range(1, 33))
	psi_server = psi.server.CreateFromKey(server_key, False)

class RestaurantNeighbor():
    async def Setup(self, request: restaurant_pb2.SetupRequest):
        global psi_server
        global customer_ids
        global restaurantKey
        fpr = 0.01

        setup_request = f"Setup (num_customers: {request.num_customers})"
        setup = psi.ServerSetup()
        setup.ParseFromString(psi_server.CreateSetupMessage(
            fpr, 1, customer_ids, psi.DataStructure.BLOOM_FILTER).SerializeToString())
        ret = restaurant_pb2.SetupReply(setup=setup, restaurantKey=restaurant_key).SerializeToString()
        return ret

    async def Fetch(self, request: restaurant_pb2.CustomerRequest):
    	global psi_server

    	customer_request = f"Fetch (request: {request})"
    	response = psi.Response()
    	response.ParseFromString(psi_server.ProcessRequest(
    						request.request).SerializeToString())
    	return restaurant_pb2.CustomerReply(response=response)

if __name__ == '__main__':
    pass
    #asyncio.run(RestaurantNeighbor())