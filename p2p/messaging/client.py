import os
import time
import json
import pytz
import ctypes
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from dataclasses import dataclass
from dataclasses_json import dataclass_json

WAKU_GO_LIB = "p2p/libs/libgowaku.so.0"

DISC_URL = "enrtree://AKP74RJLRUIRLPUD3KHFKX23B5LKQYSTWE4KPXZUMJQZSLG4LYMY2@nodes.restaurants.com"
DISC_NAMESERVER = "nodes.restaurants.com"
DISC_ENABLE = True

ENABLE_STORE = True
STORE_TIME = (5*60) # 5 minutes
CLUSTER_ID = 89
SHARD_ID = 0
STORE_DB = "sqlite3://%s/store.db"

PUBLISH_TIMEOUT = (30)

TASTEBOT_PUBSUB_TOPIC_1 = '/waku/2/rs/88/0'
PUBSUB_IDLE_TOPIC = '/waku/2/rs/89/0'
PUBSUB_BUSY_TOPIC = '/waku/2/rs/90/0'

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

WakuCallBack = ctypes.CFUNCTYPE(None, ctypes.c_int,
				ctypes.c_char_p, ctypes.c_void_p)

cur_topic_id = None

class MessagingClient:
    
    def __init__(self, root_dir, node_key, host, port,
    			discv5_port, bootstrap_enr):
    	
    	self.m_lib = None
    	self.m_root_dir = root_dir
    	self.m_data_dir = Path(self.m_root_dir) / "data"
    	self.m_data_dir.mkdir(exist_ok=True)    	
    	self.m_port = port
    	self.m_discv5_port = discv5_port
    	self.m_bootstrap_enr = bootstrap_enr
    	self.m_node_key = node_key
    	self.m_host = host
    	self.m_ctx = None
    	self.m_peer_id = None
    	
    	self.m_init_lib()

    def m_init_lib(self):

    	self.m_lib = ctypes.CDLL(WAKU_GO_LIB)
    	self.m_lib.waku_new.argtypes = [ctypes.c_char_p, WakuCallBack, ctypes.c_void_p]
    	self.m_lib.waku_new.restype = ctypes.c_void_p
    	self.m_lib.waku_start.argtypes = [ctypes.c_void_p, WakuCallBack, ctypes.c_void_p]
    	self.m_lib.waku_start.restype = ctypes.c_int
    	self.m_lib.waku_peerid.argtypes = [ctypes.c_void_p, WakuCallBack, ctypes.c_void_p]
    	self.m_lib.waku_peerid.restype = ctypes.c_int
    	self.m_lib.waku_listen_addresses.argtypes = [ctypes.c_void_p, WakuCallBack, ctypes.c_void_p]
    	self.m_lib.waku_listen_addresses.restype = ctypes.c_int
    	self.m_lib.waku_content_topic.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p,
    											ctypes.c_char_p, WakuCallBack, ctypes.c_void_p]
    	self.m_lib.waku_content_topic.restype = ctypes.c_int
    	self.m_lib.waku_default_pubsub_topic.argtypes = [WakuCallBack, ctypes.c_void_p]
    	self.m_lib.waku_default_pubsub_topic.restype = ctypes.c_int
    	self.m_lib.waku_dns_discovery.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p,
    											ctypes.c_int, WakuCallBack, ctypes.c_void_p]
    	self.m_lib.waku_dns_discovery.restype = ctypes.c_int
    	self.m_lib.waku_connect.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int, WakuCallBack, ctypes.c_void_p]
    	self.m_lib.waku_connect.restype = ctypes.c_int
    	self.m_lib.waku_peers.argtypes = [ctypes.c_void_p, WakuCallBack, ctypes.c_void_p]
    	self.m_lib.waku_peers.restype = ctypes.c_int
    	self.m_lib.waku_peer_cnt.argtypes = [ctypes.c_void_p, WakuCallBack, ctypes.c_void_p]
    	self.m_lib.waku_peer_cnt.restype = ctypes.c_int
    	self.m_lib.waku_relay_subscribe.argtypes = [ctypes.c_void_p, ctypes.c_char_p, WakuCallBack, ctypes.c_void_p]
    	self.m_lib.waku_relay_subscribe.restype = ctypes.c_int
    	self.m_lib.waku_relay_unsubscribe.argtypes = [ctypes.c_void_p, ctypes.c_char_p, WakuCallBack, ctypes.c_void_p]
    	self.m_lib.waku_relay_unsubscribe.restype = ctypes.c_int
    	self.m_lib.waku_set_event_callback.argtypes = [ctypes.c_void_p, WakuCallBack]
    	self.m_lib.waku_relay_topics.argtypes = [ctypes.c_void_p, WakuCallBack, ctypes.c_void_p]
    	self.m_lib.waku_relay_topics.restype = ctypes.c_int
    	self.m_lib.waku_store_local_query.argtypes = [ctypes.c_void_p, ctypes.c_char_p, WakuCallBack, ctypes.c_void_p]
    	self.m_lib.waku_store_local_query.restype = ctypes.c_int
    	self.m_lib.waku_get_enr.argtypes = [ctypes.c_void_p, WakuCallBack, ctypes.c_void_p]
    	self.m_lib.waku_get_enr.restype = ctypes.c_int
    	self.m_lib.waku_relay_publish.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int, WakuCallBack, ctypes.c_void_p]
    	self.m_lib.waku_relay_publish.restype = ctypes.c_int
    	# self.m_lib.waku_pex_from_peerid.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int, ctypes.c_int, WakuCallBack, ctypes.c_void_p]
    	# self.m_lib.waku_pex_from_peerid.restype = ctypes.c_int
    	# self.m_lib.waku_pex_from_peerlist.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int, ctypes.c_int, WakuCallBack, ctypes.c_void_p]
    	# self.m_lib.waku_pex_from_peerlist.restype = ctypes.c_int

    def init(self):
    	url = STORE_DB % self.m_data_dir
    	node_config = "{ \"host\": \"%s\", \"port\": %d, \
    					\"nodeKey\": \"%s\", \"store\": %s, \
    					\"clusterID\": %d, \"shards\": [%d], \
    					\"databaseURL\": \"%s\", \"discV5\": %s, \
    					\"discV5UDPPort\": %d, \"discV5BootstrapNodes\": [\"%s\"]}" \
    					% (self.m_host, int(self.m_port), self.m_node_key, \
    					"true" if ENABLE_STORE else "false", int(CLUSTER_ID), \
    					SHARD_ID, STORE_DB % self.m_root_dir, "true" if DISC_ENABLE else "false", \
    					int(self.m_discv5_port), self.m_bootstrap_enr)

    	node_config = node_config.encode('ascii')

    	self.m_ctx = self.m_lib.waku_new(node_config, waku_callback, None)

    	ret = self.m_lib.waku_set_event_callback(self.m_ctx, event_callback)

    def start(self):

    	ret = self.m_lib.waku_start(self.m_ctx, waku_callback, None)

    	peer_id = ctypes.c_char_p(None)
    	ret = self.m_lib.waku_peerid(self.m_ctx, waku_callback, ctypes.byref(peer_id))
    	self.m_peer_id = peer_id.value.decode('utf-8')

    	address = ctypes.c_char_p(None)
    	ret = self.m_lib.waku_listen_addresses(self.m_ctx, waku_callback, ctypes.byref(address))
    	self.m_address = address.value.decode('utf-8')

    	self.m_connected = True
    	print(f"Started p2p messaging node: {self.m_peer_id}, {self.m_address}")

    def stop(self):
    	pass

    def publish(self, msg):
    	global cur_topic_id

    	topic = self.get_content_topic(cur_topic_id)
    	
    	current_time = int(datetime.now().timestamp())
    	
    	message = "{ \"payload\": \"%s\", \"contentTopic\":\"%s\", \
    				\"timestamp\":%d}" % (msg, topic.decode('utf-8'), \
    				current_time)
    	message = message.encode('ascii')    	
    	
    	self.m_lib.waku_relay_publish(self.m_ctx, message, topic,
    			PUBLISH_TIMEOUT, waku_callback, None)

    def get_content_topic(self, i):
    	
    	app_name = ctypes.c_char_p("tastebot".encode('utf-8'))
    	app_version = ctypes.c_char_p("1".encode('utf-8'))
    	topic_name = ctypes.c_char_p(f"msg-{i}".encode('utf-8'))
    	encoding = ctypes.c_char_p('proto'.encode('utf-8'))

    	content_topic = ctypes.c_char_p(None)
    	ret = self.m_lib.waku_content_topic(app_name, app_version,
    							topic_name, encoding, waku_callback,
    							ctypes.byref(content_topic))
    	
    	return content_topic.value

    async def request_idle_peer(self, peer_list):
    	
    	# ret = self.m_lib.waku_pex_from_peerlist(self.m_ctx, peer_list,
    	# 								89, 0, waku_callback, None)
    	# time.sleep(3)
    	
    	return self.filter_idle_peers()

    def update_content_topic(self, state):
    	
    	if state == "idle":
    		topic = PUBSUB_BUSY_TOPIC
    	elif state == "busy":
    		topic = PUBSUB_IDLE_TOPIC

    	topics_list = ctypes.c_char_p(None)
    	
    	self.m_lib.waku_relay_topics(self.m_ctx, waku_callback,
    							ctypes.byref(topics_list))
    	topics = topics_list.value.decode('utf-8')

    	if is_topic_subscribed(topics, topic) == True:
    		sub = "{ \"pubsubTopic\": \"%s\"}" % topic.decode('utf-8')
    		sub = sub.encode('ascii')
    		ret = self.m_lib.waku_relay_unsubscribe(self.m_ctx, sub, waku_callback, None)

    	if state == "idle":
    		topic = PUBSUB_IDLE_TOPIC
    	elif state == "busy":
    		topic = PUBSUB_BUSY_TOPIC
    	
    	sub = "{ \"pubsubTopic\": \"%s\"}" % topic.decode('utf-8')
    	sub = sub.encode('ascii')
    	ret = self.m_lib.waku_relay_subscribe(self.m_ctx, sub, waku_callback, None)

    def is_topic_subscribed(self, topics_list, topic):
    	if topics_list == 'null':
    		return False

    	topics = json.loads(topics_list)

    	for i in range(len(topics)):
    		if topic == topics[i]:
    			return True

    	return False

    def get_peers(self):

    	peers_list = ctypes.c_char_p(None)
    	self.m_lib.waku_peers(self.m_ctx, waku_callback,
    		ctypes.byref(peers_list))

    	return peers_list.value

    def connect_to_peer(self, peerId):
    	
    	peer = ctypes.c_char_p(peerId.encode('utf-8'))
    	connected = self.m_lib.waku_connect(self.m_ctx, peer, 20000,
    		waku_callback, None)

    def get_enr(self):

    	enr = ctypes.c_char_p(None)
    	self.m_lib.waku_get_enr(self.m_ctx, waku_callback,
    		ctypes.byref(enr))

    	return enr.value

    def filter_idle_peers(self):

    	plist = self.get_peers()
    	peers_string = plist.decode('utf-8')
    	peers = Peer.schema().loads(peers_string, many=True)

    	idle_filter = lambda p: p.peerID != self.peer_id and \
    					PUBSUB_IDLE_TOPIC in p.pubsubTopics
    	pl = iter(peers)
    	plist = list(filter(idle_filter, pl))

    	for peer in plist:
    		peer.timestamp = datetime.now(pytz.timezone("Asia/Kolkata")).isoformat()

    	return plist

@WakuCallBack
def waku_callback(ret_code, msg: str, user_data):
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

@WakuCallBack
def event_callback(ret_code, msg: str, user_data):
	global cur_topic_id
	
	print(f"EVENT ret: {ret_code}, msg: {msg}, user_data:{user_data}")
	if ret_code != 0:
		return

	event_str = msg.decode('utf-8')
	event = json.loads(event_str)
	if event['type'] == "message":
		msg_id = event['event']['messageId']
		pubsub_topic = event['event']['pubsubTopic']
		waku_message = event['event']['wakuMessage']
		print(f"messageId:{msg_id}")
		if pubsub_topic == TASTEBOT_PUBSUB_TOPIC_2:
			content_topic = waku_message['contentTopic']
			payload_b64 = waku_message['payload']
			if content_topic == f"/tastebot/1/msg-{cur_topic_id}/proto":
				print(f"Setup (server) -- instore")
			else:
				print(f"Other")

def main():
	
	host = "192.168.1.26"
	node_key = 'a67f37280a69830a40083a2fa2b599250c872713ec090ecf0924c8a7075b064e'#'4ddecde332eff9353c8a7df4b429299af13bbfe2f5baa7f4474c93faf2fea0b5'
	port = 60021
	discv5_port = 9921
	bootstrap_enr = "enr:-KG4QJ60C0bldIz1merR78DRaJWdhSyDGImFc7n42mHqgGadXRyzOG6LOuZPyEEshitBybFvqgFw039VmOmdTFPtgg-GAZb7zkrAgmlkgnY0gmlwhMCoARqCcnOFAFkBAACJc2VjcDI1NmsxoQNLmJB1Pj72eUSZQnMof-AJdmltBsVrqCSzGa_k_YI8UIN0Y3CC6nSDdWRwgibAhXdha3UyAw"

	client = P2PClient(node_key, host, port, discv5_port, bootstrap_enr)
	
	client.start()
	
	while True:
		time.sleep(0.2)

if __name__ == "__main__":
	main()
