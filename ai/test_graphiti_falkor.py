import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from logging import INFO

from dotenv import load_dotenv

from graphiti_core import Graphiti
from graphiti_core.driver.falkordb_driver import FalkorDriver

graphiti = None

logging.basicConfig(
    level=INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger(__name__)

load_dotenv()

falkor_host = 'localhost'
falkor_port = '6379'
falkor_username = None
falkor_password = None

async def start():
	global graphiti

	falkor_driver = FalkorDriver(host=falkor_host, port=falkor_port,
		username=falkor_username, password=falkor_password)
	print(f"Init falkor driver")

	graphiti = Graphiti(graph_driver=falkor_driver)
	print(f"Init graphiti")

	await graphiti.build_indices_and_constraints()
	print(f"Done initializing")

async def main():
	global graphiti

	await start()

if __name__ == '__main__':
    asyncio.run(main())

