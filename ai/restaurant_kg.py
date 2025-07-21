import time
from subprocess import Popen 
from config import ConfigOptions
from graphiti_core import Graphiti
from graphiti_core.driver.falkordb_driver import FalkorDriver

REDIS_BACKEND_BIN = "ai/libs/redis-server"
REDIS_CONFIG = "ai/libs/redis.conf"

class KGClient():
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        self.config = ConfigOptions().get_kg_config()
        self.graphiti = None
        self.redis_backend = None 
        try:
            self.redis_backend = Popen([REDIS_BACKEND_BIN, REDIS_CONFIG])
            print(f"Started redis backend:{self.redis_backend}")
        except OSError as e:
            print(f"Error: redis backend failed to start:{e}.")
            raise e

        print(f"Starting KGClient")

        time.sleep(2)

        falkor_driver = FalkorDriver(host=self.config.db_host,
                port=self.config.db_port,
                username=None,
                password=None)
        self.graphiti = Graphiti(graph_driver=falkor_driver)
        print("Init Graphiti..")
    
    async def start(self):
        try:
            # Initialize the graph database with graphiti's indices. This only needs to be done once.
            await self.graphiti.build_indices_and_constraints()
        except Error as e:
            print(f"Error: Failed to initialize graphiti")

        print("Done Starting Graphiti..")
    
    def stop(self):
        print(f"Stopping KGClient")
        #self.graphiti.close()

