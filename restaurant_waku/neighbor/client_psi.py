import os
import sys
import json
import ctypes
import time
import asyncio
import base64
import ecdsa
from ctypes import CDLL
import pytz
from datetime import datetime
import secrets
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../../'))
from neighbor_restauarnt import RestaurantNeighbor, restaurant_setup, restaurant_key, signing_key 
import restaurant_pb2
import message_pb2

# Use reference from go-waku https://github.com/waku-org/go-waku/blob/master/examples/c-bindings/main.c 
# Use PSI repo for reference for messages https://github.com/OpenMined/PSI
# Use neighbor_restaurant.py for PSI package api references and usuage with customer list

WAKU_GO_LIB = "../libgowaku.so.0"
HOST = "192.168.1.26"
PORT = 0
IS_STORE = True
PEER_ID = "16Uiu2HAm85Z14GrGtobwAD48wcazYXiuRMCjmjMHLFU7W6UCnfsr"
PEER_PORT = "42267"
CLUSTER_ID = 89
SHARD_ID = 1

WakuCallBack = ctypes.CFUNCTYPE(
	None,
	ctypes.c_int,
	ctypes.c_char_p,
	ctypes.c_void_p
)

def main():	
	@WakuCallBack
	def wakuCallBack(ret_code, msg: str, user_data):
		if ret_code != 0:
			print(f"Error: {ret_code}, msg:{msg}")

		if not user_data:
			print("user data is null")
			return

		if not msg:
			print(f"msg: {msg}")
			return

		data_ref = ctypes.cast(user_data, ctypes.POINTER(ctypes.c_char_p))
		data_ptr = data_ref[0]

		# if data_ref.contents:
		# 	libc.free(data_ref.contents)
		# 	data_ref.contents = None

		if msg:
			msg_str = msg.decode('utf-8')
			msg_len = len(msg_str)

			msg_ptr = ctypes.create_string_buffer(msg_len)

			if not msg_ptr:
				return

			ctypes.memmove(msg_ptr, msg_str.encode(), msg_len)

			data_ref[0] = ctypes.cast(msg_ptr, ctypes.c_char_p)
			data_ptr = data_ref[0]

	@WakuCallBack
	def eventCallBack(ret_code, msg: str, user_data):
		if ret_code != 0:
			print(f"Error: {ret_code}")
			print(f"\nEvent: {msg}")
	
	waku_go = CDLL(WAKU_GO_LIB)
	waku_go.waku_new.argtypes = [ctypes.c_char_p, WakuCallBack, ctypes.c_void_p]
	waku_go.waku_new.restype = ctypes.c_void_p
	waku_go.waku_start.argtypes = [ctypes.c_void_p, WakuCallBack, ctypes.c_void_p]
	waku_go.waku_start.restype = ctypes.c_int
	waku_go.waku_peerid.argtypes = [ctypes.c_void_p, WakuCallBack, ctypes.c_void_p]
	waku_go.waku_peerid.restype = ctypes.c_int
	waku_go.waku_listen_addresses.argtypes = [ctypes.c_void_p, WakuCallBack, ctypes.c_void_p]
	waku_go.waku_listen_addresses.restype = ctypes.c_int
	waku_go.waku_content_topic.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p,
										   ctypes.c_char_p, WakuCallBack, ctypes.c_void_p]
	waku_go.waku_content_topic.restype = ctypes.c_int
	waku_go.waku_default_pubsub_topic.argtypes = [WakuCallBack, ctypes.c_void_p]
	waku_go.waku_default_pubsub_topic.restype = ctypes.c_int
	waku_go.waku_dns_discovery.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p,
										   ctypes.c_int, WakuCallBack, ctypes.c_void_p]
	waku_go.waku_dns_discovery.restype = ctypes.c_int
	waku_go.waku_connect.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int, WakuCallBack, ctypes.c_void_p]
	waku_go.waku_connect.restype = ctypes.c_int
	waku_go.waku_peer_cnt.argtypes = [ctypes.c_void_p, WakuCallBack, ctypes.c_void_p]
	waku_go.waku_peer_cnt.restype = ctypes.c_int
	waku_go.waku_relay_subscribe.argtypes = [ctypes.c_void_p, ctypes.c_char_p, WakuCallBack, ctypes.c_void_p]
	waku_go.waku_relay_subscribe.restype = ctypes.c_int
	waku_go.waku_encode_symmetric.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, WakuCallBack, ctypes.c_void_p]
	waku_go.waku_encode_symmetric.restype = ctypes.c_int
	waku_go.waku_relay_publish.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int, WakuCallBack, ctypes.c_void_p]
	waku_go.waku_relay_publish.restype = ctypes.c_int
	waku_go.waku_relay_topics.argtypes = [ctypes.c_void_p, WakuCallBack, ctypes.c_void_p]
	waku_go.waku_relay_topics.restype = ctypes.c_int
	# waku_go.waku_set_event_callback.argtypes = [ctypes.c_void_p, WakuCallBack]
	# waku_go.waku_set_event_callback.restype = ctypes.c_void

	restaurant = RestaurantNeighbor()
	restaurant_setup()

	json_config = "{ \"host\": \"%s\", \"port\": %d, \"store\": %s, \"clusterID\": %d, \"shards\": [%d]}" % (HOST, int(PORT), "true" if IS_STORE else "false", int(CLUSTER_ID), int(SHARD_ID))
	json_config = json_config.encode('ascii')

	ctx = waku_go.waku_new(json_config, wakuCallBack, None)
	time.sleep(2)

	# ret = waku_go.waku_set_event_callback(ctx, eventCallBack)
	# print(f"setcallback:{ret}")

	ret = waku_go.waku_start(ctx, wakuCallBack, None)
	print(f"start:{ret}")
	time.sleep(2)

	peer_id = ctypes.c_char_p(None)
	ret = waku_go.waku_peerid(ctx, wakuCallBack, ctypes.byref(peer_id))
	print(f"peerid:{peer_id.value}")
	time.sleep(2)

	addresses = ctypes.c_char_p(None)
	ret = waku_go.waku_listen_addresses(ctx, wakuCallBack, ctypes.byref(addresses))
	print(f"addresses:{addresses.value}")
	time.sleep(2)

	default_pubsub_topic = ctypes.c_char_p(None)
	waku_go.waku_default_pubsub_topic(wakuCallBack, ctypes.byref(default_pubsub_topic))
	print(f"default_pubsub_topic:{default_pubsub_topic.value}")

	# pubsub_topic = '/tastbot/1/neighbor-1/proto'
	# app_name_str = "tastebot"
	# app_version_str = "1"
	# topic_name_str = "customer-list"
	# encoding_str = "proto"
	# app_name = ctypes.c_char_p(app_name_str.encode('utf-8'))
	# app_version = ctypes.c_char_p(app_version_str.encode('utf-8'))
	# topic_name = ctypes.c_char_p(topic_name_str.encode('utf-8'))
	# encoding = ctypes.c_char_p(encoding_str.encode('utf-8'))

	# content_topic = ctypes.c_char_p(None)
	# ret = waku_go.waku_content_topic(app_name, app_version, topic_name,
	# 								 encoding, wakuCallBack, ctypes.byref(content_topic))
	# print(f"content topic:{content_topic.value}")
	# time.sleep(2)

	# # url_str = "enrtree://AOGYWMBYOUIMOENHXCHILPKY3ZRFEULMFI4DOM442QSZ73TT2A7VI@test.waku.nodes.status.im"
	# url_str = "enrtree://AIRVQ5DDA4FFWLRBCHJWUWOO6X6S4ZTZ5B667LQ6AJU6PEYDLRD5O@sandbox.waku.nodes.status.im"
	# nameserver_str = ""
	# timeout = 20000
	# url = ctypes.c_char_p(url_str.encode('utf-8'))
	# nameserver = ctypes.c_char_p(nameserver_str.encode('utf-8'))

	# discovered_nodes = ctypes.c_char_p(None)
	# waku_go.waku_dns_discovery(ctx, url, nameserver, timeout, wakuCallBack, ctypes.byref(discovered_nodes))
	# print(f"discovered_nodes:{discovered_nodes.value}")
	# time.sleep(2)

	# peer_str = f"/ip4/192.168.1.26/tcp/{PEER_PORT}/p2p/{PEER_ID}"
	# peer = ctypes.c_char_p(peer_str.encode('utf-8'))
	# ret = waku_go.waku_connect(ctx, peer, 20000, wakuCallBack, None)
	# print(f"connect:{ret}")
	# time.sleep(2)

	# subscription = "{ \"pubsubTopic\": \"%s\", \"contentTopics\":[\"%s\"]}" % (pubsub_topic, content_topic.value.decode('utf-8'))
	# subscription = subscription.encode('ascii')
	# print(f"subscription:{subscription}")

	# ret = waku_go.waku_relay_subscribe(ctx, subscription, wakuCallBack, None)
	# print(f"ret:{ret}")
	# time.sleep(2)

	# stopics = ctypes.c_char_p(None)
	# waku_go.waku_relay_topics(ctx, wakuCallBack, ctypes.byref(stopics))
	# print(f"stopics:{stopics.value}")
	# time.sleep(2)

	# setup_request = restaurant_pb2.SetupRequest(num_customers=1)
	# setup_msg = asyncio.run(restaurant.Setup(setup_request))
	# print(f"\nsetup_msg:{setup_msg}")
	# setup_reply = restaurant_pb2.SetupReply()
	# setup_reply.ParseFromString(setup_msg)
	# print(f"restaurantKey:{setup_reply.restaurantKey}")
	# payload = base64.b64encode(setup_msg).decode()
	# print(f"payload:{payload}")

	# waku_msg_str = "{ \"payload\":\"%s\",\"contentTopic\":\"%s\",\"timestamp\":%d}" % (payload, content_topic.value.decode('utf-8'), int(0))
	# waku_msg_ptr = waku_msg_str.encode('ascii')
	# print(f"waku_msg_ptr:{waku_msg_ptr}")

	# pubsub_topic_ptr = ctypes.c_char_p(pubsub_topic.encode('utf-8'))
	# print(f"pubsub_topic_ptr:{pubsub_topic_ptr}")
	
	# key = ctypes.c_char_p(signing_key.encode('utf-8'))
	# print(f"key:{key})")

	# encoded_msg = ctypes.c_char_p(None)
	# ret = waku_go.waku_encode_symmetric(waku_msg_ptr, key, None, wakuCallBack, ctypes.byref(encoded_msg))
	# print(f"encoding:{ret}")
	# print(f"encoded_msg:{encoded_msg.value}")
	# print(f"encoded_msg1:{encoded_msg}")

	# message_id = ctypes.c_char_p(None)
	# ret = waku_go.waku_relay_publish(ctx, encoded_msg, pubsub_topic_ptr, 0, wakuCallBack, ctypes.byref(message_id))
	# print(f"publish:{ret}")


	# time.sleep(10)

	# store_query = '{ "pubsubTopic": "%s", "pagingOptions": {"pageSize": 40, "forward":false}}' % pubsub_topic
	# #store_query = "{ \"pubsubTopic\": \"%s\"}" % (pubsub_topic)
	# #store_query = store_query.encode('utf-8')
	# store_query_ptr = ctypes.c_char_p(store_query.encode('utf-8'))
	# print(f"\nstore_query_ptr:{store_query_ptr}")
	# local_store = ctypes.c_char_p(None)
	# print(f"ctx:{ctx}") 
	# ret = waku_go.waku_store_local_query(ctx, store_query_ptr, wakuCallBack, ctypes.byref(local_store))
	# print(f"RET:{ret}")
	# print(f"local_store:{local_store.value}")

	while True:
		time.sleep(1)

if __name__ == "__main__":
	main()