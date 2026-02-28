import time
import json
import ctypes
import threading
import asyncio
from ctypes import CDLL
from pathlib import Path
from config import ConfigOptions
from p2p.messaging.client import MessagingClient
from p2p.consensus.client import ConsensusClient

class P2PClient(MessagingClient, ConsensusClient):
    
    def __init__(self):

        _root_dir = ConfigOptions()._root_dir
        self.root_dir = Path(_root_dir) / "p2p"
        self.root_dir.mkdir(exist_ok=True)
        self.m_root_dir = Path(self.root_dir) / "messaging"
        self.m_root_dir.mkdir(exist_ok=True)
        self.m_root_dir = str(self.m_root_dir)
        self.c_root_dir = Path(self.root_dir) / "consensus"
        self.c_root_dir.mkdir(exist_ok=True)
        self.c_root_dir = str(self.c_root_dir)

        self.config = ConfigOptions().get_p2p_config()

        self.thread = None

    def init(self, on_consensus_cb):
        MessagingClient.__init__(self, self.m_root_dir,
                        self.config.node_key, self.config.m_host,
                        self.config.m_port, self.config.m_discv5_port,
                        self.config.m_bootstrap_enr)

        ConsensusClient.__init__(self, self.c_root_dir, self.config.node_key)

        MessagingClient.init(self)

        ConsensusClient.init(self, cb=on_consensus_cb)


    def start(self):

        MessagingClient.start(self)

        ConsensusClient.start(self)

        self.thread = threading.Thread(target=self.run)
        self.thread.start()
        return self.thread

    def stop(self):

    	MessagingClient.stop(self)

    	ConsensusClient.stop(self)

    	if self.thread:
    		self.thread.join()

    async def publish(self, proof):

        msg = {}
        msg['ID'] = self.m_peer_id
        msg['ENR'] = self.get_enr()
        msg['peers'] = await self.find_peers(1, None)
        msg['mode'] = 'solo'
        msg['proof'] = proof

        await ConsensusClient.publish(self, msg)

    async def find_peers(self, height, url):
    	# if height != 0:
    	# 	from_peers = self.query("peers", f"{url}-peers")
    	# else:
    	# 	from_peers = None

    	from_peers = json.dumps(['16Uiu2HAmHk5rdpnfYGDh2XchPsQxvqB3j4zb9owzfFjV7fMWbQNs']).encode('utf-8')
    	peers = await self.request_idle_peer(from_peers)

    	peer_list = []
    	for peer in peers:
    		peer_list.append(json.loads(peer.to_json()))

    	return peer_list

    def run(self):
    	while True:
    		time.sleep(0.2)


if __name__ == "__main__":
	
	client = P2PClient()
	
	client.start()

	while True:
		time.sleep(0.2)
