import os
import sys
import time
import json
import pytz
import ctypes
import base64
import threading
from ctypes import CDLL
from typing import List, Optional
from datetime import datetime
from dataclasses import dataclass
from dataclasses_json import dataclass_json, Undefined
#import restaurant_pb2

DISC_URL = "enrtree://AKP74RJLRUIRLPUD3KHFKX23B5LKQYSTWE4KPXZUMJQZSLG4LYMY2@nodes.restaurants.com"
DISC_NAMESERVER = "nodes.restaurants.com"
DISC_ENABLE = True

SETUP_STORE = True
SETUP_STORE_TIME = (30*24*60*60) # 30 days
SETUP_CLUSTER_ID = 88
SETUP_SHARD_ID = 0

MSG_STORE = True
MSG_STORE_TIME = (5*60) # 5 minutes
MSG_CLUSTER_ID = 89
MSG_SHARD_ID = 0

MSG_PUBLISH_TIMEOUT = (30)

TASTEBOT_PUBSUB_TOPIC_1 = '/waku/2/rs/88/0'
PUBSUB_IDLE_TOPIC = '/waku/2/rs/89/0'
PUBSUB_BUSY_TOPIC = '/waku/2/rs/90/0'

WakuCallBack = ctypes.CFUNCTYPE(
	None,
	ctypes.c_int,
	ctypes.c_char_p,
	ctypes.c_void_p
)

waku_go = None
cur_msg_topic_id = None

@dataclass_json
@dataclass
class Peer:
    peerID: str
    protocols: List[str]
    addrs: List[str]
    connected: bool
    pubsubTopics: List[str]
    timestamp: Optional[str] = ""
    signature: Optional[str] = "123abc"

class P2PClient:
    def __init__(self, client_id, node_key, host, setup_port, setup_discv5_port, setup_bs_enr, msg_port, msg_discv5_port, msg_bs_enr):
    	self.client_id = client_id
    	self.setup_port = setup_port
    	self.setup_discv5_port = setup_discv5_port
    	self.setup_bs_enr = setup_bs_enr
    	
    	self.msg_port = msg_port
    	self.msg_discv5_port = msg_discv5_port
    	self.msg_bs_enr = msg_bs_enr
    	self.node_key = node_key
    	self.host = host
    	self.setup_ctx = None
    	self.msg_ctx = None
    	self.setup_peer_id = None
    	self.msg_peer_id = None
    	self.setup_store_db = f"sqlite3://data/setup_store_{self.client_id}.db"
    	self.msg_store_db = f"sqlite3://data/msg_store_{self.client_id}.db"
    	waku_lib_init()

    def start(self):
    	
    	# (self.setup_ctx, setup_connected, self.setup_peer_id,
    	# 	setup_address) = self.init_setup_node()
    	# print(f"Started Setup node: {self.setup_peer_id}, {setup_address}")

    	(self.msg_ctx, msg_connected, self.msg_peer_id,
    		msg_address) = self.init_msg_node()
    	print(f"Started MSG node: {self.msg_peer_id}, {msg_address}")

    def init_setup_node(self):
    	node_config = "{ \"host\": \"%s\", \"port\": %d, \"nodeKey\": \"%s\", \"store\": %s, \"clusterID\": %d, \"shards\": [%d], \"databaseURL\": \"%s\", \"discV5\": %s, \"discV5UDPPort\": %d, \"discV5BootstrapNodes\": [\"%s\"]}" \
    					% (self.host, int(self.setup_port), self.node_key, "true" if SETUP_STORE else "false", int(SETUP_CLUSTER_ID), SETUP_SHARD_ID, self.setup_store_db, "true" if DISC_ENABLE else "false", int(self.setup_discv5_port), self.setup_bs_enr)
    	node_config = node_config.encode('ascii')

    	ctx = waku_go.waku_new(node_config, wakuCallBack, None)
    	print(f"ctx:{ctx}")

    	ret = waku_go.waku_set_event_callback(ctx, setupEventCallBack)

    	ret = waku_go.waku_start(ctx, wakuCallBack, None)

    	peer_id = ctypes.c_char_p(None)
    	ret = waku_go.waku_peerid(ctx, wakuCallBack, ctypes.byref(peer_id))
    	peer_id = peer_id.value.decode('utf-8')

    	address = ctypes.c_char_p(None)
    	ret = waku_go.waku_listen_addresses(ctx, wakuCallBack, ctypes.byref(address))
    	address = address.value.decode('utf-8')

    	connected = True

    	return ctx, connected, peer_id, address

    def init_msg_node(self):
    	node_config = "{ \"host\": \"%s\", \"port\": %d, \"nodeKey\": \"%s\", \"store\": %s, \"clusterID\": %d, \"shards\": [%d], \"databaseURL\": \"%s\", \"discV5\": %s, \"discV5UDPPort\": %d, \"discV5BootstrapNodes\": [\"%s\"]}" \
    					% (self.host, int(self.msg_port), self.node_key, "true" if MSG_STORE else "false", int(MSG_CLUSTER_ID), MSG_SHARD_ID, self.msg_store_db, "true" if DISC_ENABLE else "false", int(self.msg_discv5_port), self.msg_bs_enr)

    	node_config = node_config.encode('ascii')

    	ctx = waku_go.waku_new(node_config, wakuCallBack, None)

    	ret = waku_go.waku_set_event_callback(ctx, msgEventCallBack)

    	ret = waku_go.waku_start(ctx, wakuCallBack, None)

    	peer_id = ctypes.c_char_p(None)
    	ret = waku_go.waku_peerid(ctx, wakuCallBack, ctypes.byref(peer_id))
    	peer_id = peer_id.value.decode('utf-8')

    	address = ctypes.c_char_p(None)
    	ret = waku_go.waku_listen_addresses(ctx, wakuCallBack, ctypes.byref(address))
    	address = address.value.decode('utf-8')

    	connected = True

    	return ctx, connected, peer_id, address 

    # def get_setup_content_topic(self):
    # 	app_name = ctypes.c_char_p("tastebot".encode('utf-8'))
    # 	app_version = ctypes.c_char_p("1".encode('utf-8'))
    # 	topic_name = ctypes.c_char_p("setup".encode('utf-8'))
    # 	encoding = ctypes.c_char_p('proto'.encode('utf-8'))

    # 	content_topic = ctypes.c_char_p(None)
    # 	ret = waku_go.waku_content_topic(app_name, app_version, topic_name,
    # 		encoding, wakuCallBack, ctypes.byref(content_topic))
    # 	return content_topic.value

    def get_msg_content_topic(self, i):
    	app_name = ctypes.c_char_p("tastebot".encode('utf-8'))
    	app_version = ctypes.c_char_p("1".encode('utf-8'))
    	topic_name = ctypes.c_char_p(f"msg-{i}".encode('utf-8'))
    	encoding = ctypes.c_char_p('proto'.encode('utf-8'))

    	content_topic = ctypes.c_char_p(None)
    	ret = waku_go.waku_content_topic(app_name, app_version, topic_name,
    		encoding, wakuCallBack, ctypes.byref(content_topic))
    	return content_topic.value

    async def req_msg_idle_peer(self, peer_list):
    	ret = waku_go.waku_pex_from_peerlist(self.msg_ctx, peer_list, 89, 0, wakuCallBack, None)
    	time.sleep(3)
    	return filter_idle_peers(self)

    def update_msg_topics(self, state):
    	if state == "idle":
    		topic = PUBSUB_BUSY_TOPIC
    	elif state == "busy":
    		topic = PUBSUB_IDLE_TOPIC

    	topics_list = ctypes.c_char_p(None)
    	waku_go.waku_relay_topics(self.msg_ctx, wakuCallBack, ctypes.byref(topics_list))
    	subs = topics_list.value.decode('utf-8')

    	if isTopicSubscribed(subs, topic) == True:
    		sub = "{ \"pubsubTopic\": \"%s\"}" % topic.decode('utf-8')
    		sub = sub.encode('ascii')
    		ret = waku_go.waku_relay_unsubscribe(self.msg_ctx, sub, wakuCallBack, None)

    	if state == "idle":
    		topic = PUBSUB_IDLE_TOPIC
    	elif state == "busy":
    		topic = PUBSUB_BUSY_TOPIC
    	
    	sub = "{ \"pubsubTopic\": \"%s\"}" % topic.decode('utf-8')
    	sub = sub.encode('ascii')
    	ret = waku_go.waku_relay_subscribe(self.msg_ctx, sub, wakuCallBack, None)

    def publish_msg(self, msg):
    	topic = self.get_msg_content_topic(self.msg_topic_id)
    	current_time = int(datetime.now().timestamp())
    	message = "{ \"payload\": \"%s\", \"contentTopic\":\"%s\", \"timestamp\":%d}" % (msg, topic.decode('utf-8'), current_time)
    	message = message.encode('ascii')    	
    	waku_go.waku_relay_publish(ctx, message, topic, MSG_PUBLISH_TIMEOUT, wakuCallBack, None)

    # def get_setup_peers(self):
    # 	peers_list = ctypes.c_char_p(None)
    # 	waku_go.waku_peers(self.setup_ctx, wakuCallBack, ctypes.byref(peers_list))
    # 	return peers_list.value

    def get_msg_peers(self):
    	peers_list = ctypes.c_char_p(None)
    	waku_go.waku_peers(self.msg_ctx, wakuCallBack, ctypes.byref(peers_list))
    	return peers_list.value

    # def connect_setup_to_peer(self, peerId):
    # 	peer = ctypes.c_char_p(peerId.encode('utf-8'))
    # 	connected = waku_go.waku_connect(self.setup_ctx, peer, 20000, wakuCallBack, None)

    def connect_msg_to_peer(self, peerId):
    	peer = ctypes.c_char_p(peerId.encode('utf-8'))
    	connected = waku_go.waku_connect(self.msg_ctx, peer, 20000, wakuCallBack, None)

    # def get_setup_enr(self):
    # 	enr = ctypes.c_char_p(None)
    # 	waku_go.waku_get_enr(self.setup_ctx, wakuCallBack, ctypes.byref(enr))
    # 	return enr.value

    def get_msg_enr(self):
    	enr = ctypes.c_char_p(None)
    	waku_go.waku_get_enr(self.msg_ctx, wakuCallBack, ctypes.byref(enr))
    	return enr.value

def filter_idle_peers(client):
	plist = client.get_msg_peers()
	peers_string = plist.decode('utf-8')
	peers = Peer.schema().loads(peers_string, many=True)
	
	idle_filter = lambda p: p.peerID != client.msg_peer_id and PUBSUB_IDLE_TOPIC in p.pubsubTopics
	pl = iter(peers)
	plist = list(filter(idle_filter, pl))
	for peer in plist:
		print(f"Peer ID: {peer.peerID}")
		print(f"Protocols: {peer.protocols}")
		print(f"Addresses: {peer.addrs}")
		print(f"Connected: {peer.connected}")
		print(f"Pubsub Topics: {peer.pubsubTopics}")
		peer.timestamp = datetime.now(pytz.timezone("Asia/Kolkata")).isoformat()
		print(f"Timestamp: {peer.timestamp}")
		print(f"Signature: {peer.signature}")
			
	return plist

def isTopicSubscribed(subscription_list, topic):
	print(f"subscription_list:{subscription_list}")
	if subscription_list == 'null':
		return False

	subs = json.loads(subscription_list)
	num_subs = len(subs)
	for i in range(num_subs):
		print(f"subs[i]:{subs[i]}")
		if topic == subs[i]:
			return True

	return False


@WakuCallBack
def wakuCallBack(ret_code, msg: str, user_data):
	if ret_code != 0:
		print(f"Error: {ret_code}, msg:{msg}")

	if not user_data:
		return

	data_ref = ctypes.cast(user_data, ctypes.POINTER(ctypes.c_char_p))
	data_ptr = data_ref[0]

	if data_ref.contents:
		data_ref.contents = None

	if msg:
		msg_ptr = ctypes.create_string_buffer(msg)

		if not msg_ptr:
			return

		data_ref[0] = ctypes.cast(msg_ptr, ctypes.c_char_p)
		data_ptr = data_ref[0]

# @WakuCallBack
# def setupEventCallBack(ret_code, msg: str, user_data):
# 	print(f"EVENT ret: {ret_code}, msg: {msg}, user_data:{user_data}")
# 	if ret_code != 0:
# 		return

# 	event_str = msg.decode('utf-8')
# 	event = json.loads(event_str)
# 	if event['type'] == "message":
# 		msgId = event['event']['messageId']
# 		pubsub_topic = event['event']['pubsubTopic']
# 		waku_message = event['event']['wakuMessage']
# 		print(f"messageId:{msgId}")
# 		if pubsub_topic == TASTEBOT_PUBSUB_TOPIC_1:
# 			content_topic = waku_message['contentTopic']
# 			payload_b64 = waku_message['payload']
# 			if content_topic == "/tastebot/1/customer-list/proto":
# 				print(f"Setup (server) -- instore")
# 			else:
# 				print(f"Other")

@WakuCallBack
def msgEventCallBack(ret_code, msg: str, user_data):
	print(f"EVENT ret: {ret_code}, msg: {msg}, user_data:{user_data}")
	if ret_code != 0:
		return

	event_str = msg.decode('utf-8')
	event = json.loads(event_str)
	if event['type'] == "message":
		msgId = event['event']['messageId']
		pubsub_topic = event['event']['pubsubTopic']
		waku_message = event['event']['wakuMessage']
		print(f"messageId:{msgId}")
		if pubsub_topic == TASTEBOT_PUBSUB_TOPIC_2:
			content_topic = waku_message['contentTopic']
			payload_b64 = waku_message['payload']
			if content_topic == f"/tastebot/1/msg-{cur_msg_topic_id}/proto":
				print(f"Setup (server) -- instore")
			else:
				print(f"Other")

def waku_lib_init():
	global waku_go

	path = os.path.dirname(__file__)
	lib_path = os.path.join(path, "libgowaku.so.0")
	waku_go = CDLL(lib_path)
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
	waku_go.waku_peers.argtypes = [ctypes.c_void_p, WakuCallBack, ctypes.c_void_p]
	waku_go.waku_peers.restype = ctypes.c_int
	waku_go.waku_peer_cnt.argtypes = [ctypes.c_void_p, WakuCallBack, ctypes.c_void_p]
	waku_go.waku_peer_cnt.restype = ctypes.c_int
	waku_go.waku_relay_subscribe.argtypes = [ctypes.c_void_p, ctypes.c_char_p, WakuCallBack, ctypes.c_void_p]
	waku_go.waku_relay_subscribe.restype = ctypes.c_int
	waku_go.waku_relay_unsubscribe.argtypes = [ctypes.c_void_p, ctypes.c_char_p, WakuCallBack, ctypes.c_void_p]
	waku_go.waku_relay_unsubscribe.restype = ctypes.c_int
	waku_go.waku_set_event_callback.argtypes = [ctypes.c_void_p, WakuCallBack]
	waku_go.waku_relay_topics.argtypes = [ctypes.c_void_p, WakuCallBack, ctypes.c_void_p]
	waku_go.waku_relay_topics.restype = ctypes.c_int
	waku_go.waku_store_local_query.argtypes = [ctypes.c_void_p, ctypes.c_char_p, WakuCallBack, ctypes.c_void_p]
	waku_go.waku_store_local_query.restype = ctypes.c_int
	waku_go.waku_get_enr.argtypes = [ctypes.c_void_p, WakuCallBack, ctypes.c_void_p]
	waku_go.waku_get_enr.restype = ctypes.c_int
	waku_go.waku_relay_publish.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int, WakuCallBack, ctypes.c_void_p]
	waku_go.waku_relay_publish.restype = ctypes.c_int
	waku_go.waku_pex_from_peerid.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int, ctypes.c_int, WakuCallBack, ctypes.c_void_p]
	waku_go.waku_pex_from_peerid.restype = ctypes.c_int
	waku_go.waku_pex_from_peerlist.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int, ctypes.c_int, WakuCallBack, ctypes.c_void_p]
	waku_go.waku_pex_from_peerlist.restype = ctypes.c_int


if __name__ == "__main__":
	host = "192.168.1.26"
	node_key = 'a67f37280a69830a40083a2fa2b599250c872713ec090ecf0924c8a7075b064e'#'4ddecde332eff9353c8a7df4b429299af13bbfe2f5baa7f4474c93faf2fea0b5'

	setup_port = 60011
	setup_discv5_port = 9911
	setup_bs_enr = "enr:-KG4QB3eb3HfEYfkM3qJ4PbnxrjM_KK4BIsYh0hh1NNFWYi0UhgbINGm38YoNDgiRSFJBLJT2aRj2qifsWTlZ886GV6GAZb7zkKYgmlkgnY0gmlwhMCoARqCcnOFAFgBAACJc2VjcDI1NmsxoQNLmJB1Pj72eUSZQnMof-AJdmltBsVrqCSzGa_k_YI8UIN0Y3CC6mqDdWRwgia2hXdha3UyAw"

	msg_port = 60021
	msg_discv5_port = 9921
	msg_bs_enr = "enr:-KG4QJ60C0bldIz1merR78DRaJWdhSyDGImFc7n42mHqgGadXRyzOG6LOuZPyEEshitBybFvqgFw039VmOmdTFPtgg-GAZb7zkrAgmlkgnY0gmlwhMCoARqCcnOFAFkBAACJc2VjcDI1NmsxoQNLmJB1Pj72eUSZQnMof-AJdmltBsVrqCSzGa_k_YI8UIN0Y3CC6nSDdWRwgibAhXdha3UyAw"

	client = P2PClient(1, node_key, host, setup_port, setup_discv5_port, setup_bs_enr, msg_port, msg_discv5_port, msg_bs_enr)
	client.start()
	while True:
		time.sleep(0.2)
