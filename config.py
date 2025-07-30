import os
import sys
import json
import tomli
import base64
import hashlib
import subprocess
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel
from dataclasses import dataclass, fields
from typing import IO, Any, Optional, TypeVar, Union, cast, get_args

PROJECT_CONFIG_FILE = "pyproject.toml"

@dataclass
class Config():
	root_dir: Union[str, Path]

@dataclass
class RestaurantConfig():
	name: str
	device: str
	password: Optional[str] = None

@dataclass
class KGConfig():
	db_host: str
	db_username: str
	db_port: str
	db_password: Optional[str] = None

@dataclass
class IMConfig():
	status_host: str
	status_port: str

@dataclass
class P2PConfig():
	m_host: str
	m_port: str
	m_discv5_port: str
	m_bootstrap_enr: Optional[str] = None
	node_key: Optional[str] = None

@dataclass
class EmbeddingsConfig():
	max_customers: int
	max_restaurants: int
	customer_features_num: int
	restaurant_features_num: int

def validate_config(config_dict: dict[str, Any]) -> None:
    for key, value in config_dict.items():
        if not isinstance(value, get_args(Union[bool, float, int, str])):
            raise ValueError(
                f"The value for key {key} needs to be of type `int`, `float`, "
                "`bool, `str`, or  a `dict` of those.",
            )

class ConfigOptions:
	_instance = None
	_app_config = None
	_root_dir = None
	_env_file = None 

	def __new__(cls, env_file='.env', check=True):
		if cls._instance is None:
			cls._instance = super().__new__(cls)
			cls._env_file = env_file
			cls._instance.__init__(env_file, check)
		return cls._instance

	def __init__(self, env_file='.env', check=True):
		self._root_dir, self._app_config = init(env_file=self._env_file, check=check)		

	def get_embeddings_config(self) -> EmbeddingsConfig:
		field_names = {f.name for f in fields(EmbeddingsConfig)}
		config = self._app_config['embeddings']
		filtered_config = {k: v for k, v in config.items() if k in field_names}
		return EmbeddingsConfig(**filtered_config)

	def get_restaurant_config(self) -> RestaurantConfig:
		field_names = {f.name for f in fields(RestaurantConfig)}
		config = self._app_config['restaurant']
		filtered_config = {k: v for k, v in config.items() if k in field_names}
		restaurant_config = RestaurantConfig(**filtered_config)
		try:
			load_dotenv(dotenv_path=self._env_file)
			password = os.getenv("RESTAURANT_PASSWORD")
			if password is None:
				raise ValueError("Env vairable 'RESTAURANT_PASSWORD' not found")
			restaurant_config.password = password 
		except FileNotFoundError:
			print("Error: .env file not found, Create .env")

		return restaurant_config

	def get_kg_config(self) -> KGConfig:
		field_names = {f.name for f in fields(KGConfig)}
		config = self._app_config['kg']
		filtered_config = {k: v for k, v in config.items() if k in field_names}
		kg_config = KGConfig(**filtered_config)
		try:
			load_dotenv(dotenv_path=self._env_file)
			password = os.getenv("KG_DB_PASSWORD")
			if password is None:
				raise ValueError("Env vairable 'KG_DB_PASSWORD' not found")
			else:
				kg_config.db_password = password 

		except FileNotFoundError:
			print("Error: .env file not found, Create .env")

		return kg_config

	def get_im_config(self) -> IMConfig:
		field_names = {f.name for f in fields(IMConfig)}
		config = self._app_config['im']
		filtered_config = {k: v for k, v in config.items() if k in field_names}
		im_config = IMConfig(**filtered_config)

		return im_config

	def get_p2p_config(self) -> P2PConfig:
		field_names = {f.name for f in fields(P2PConfig)}
		config = self._app_config['p2p']
		filtered_config = {k: v for k, v in config.items() if k in field_names}
		p2p_config = P2PConfig(**filtered_config)
		try:
			load_dotenv(dotenv_path=self._env_file)
			tm_home = os.getenv("TMHOME")
			if tm_home is None:
				raise ValueError("Env vairable 'TMHOME' not found")
			else:
				path = Path(tm_home) / 'config' / 'node_key.json'

				with open(path, 'r') as file:
					data = json.load(file)
					try:
						node_key = data['priv_key']['value']
						p2p_config.node_key = base64.b64decode(node_key).hex()
					except KeyError:
						raise ValueError("ValueError: node key invalid")

		except FileNotFoundError:
			print("Error: .env file not found 1, Create .env")

		return p2p_config

def init(env_file, check):
	root_dir: Union[str, Path] = ""

	env_path = Path.cwd() / env_file

	load_dotenv(dotenv_path=env_path)

	if check == True:
		if os.getenv("TASTEBOT_ROOTDIR") is not None:
			root_dir = os.environ.get('TASTEBOT_ROOTDIR')
		else:
			raise OSError(
				f"Taste bot working directory not configured."
			)

		if os.path.isdir(root_dir) is None:
			raise FileNotFoundError(
				f"Root directory '{root_dir}' not present."
			)

	project_dir = os.path.dirname(os.path.realpath(__file__))
	toml_path = Path(project_dir) / PROJECT_CONFIG_FILE

	if not toml_path.is_file():
		raise FileNotFoundError(
			f"Cannot find {PROJECT_CONFIG_FILE} in {project_dir}"
		)

	with toml_path.open(encoding="utf-8") as toml_file:
		config = tomli.loads(toml_file.read())

	errors = []
	warnings = []

	if ("tool" not in config
		or "tastebot" not in config["tool"]
		or "app" not in config["tool"]["tastebot"]
	):
		errors.append("Missing [tool.tastebot.app] section")

	else:
		if "restaurant" in config["tool"]["tastebot"]["app"]:
			validate_config(config["tool"]["tastebot"]["app"]["restaurant"])		
		elif "config" in config["tool"]["tastebot"]["app"]:
			validate_config(config["tool"]["tastebot"]["app"]["config"])
		else:
			errors.append("Missing [tool.tastebot.app.config] section")

	if not len(errors) == 0:
		error_msg = "\n".join([f"  - {error}" for error in errors])
		raise ValueError(f"Invalid {PROJECT_CONFIG_FILE}:\n{error_msg}")

	app_config = config['tool']['tastebot']['app']
	return root_dir, app_config

def configure(root_dir, config):

	env = {}
	p2p_dir = Path("p2p").resolve(strict=True)
	tendermint_dir = Path("p2p/tendermint").resolve(strict=True)
	
	env['TMHOME'] =  str(root_dir / 'p2p' / 'consensus')

	try:
		result = subprocess.run(["build/tendermint", "init", "validator", "--log_level", "error"],
		cwd=tendermint_dir, env=env)
	except subprocess.CalledProcessError as e:
		print(f"Error configuring tendermint1:{e}")
		return False

	args = config['p2p']

	try:
		result = subprocess.run(["sed", "-i", "-e", f's/moniker = "[^"]*"/moniker = "{args["c_moniker"]}"/',
			"-e", f's/persistent_peers = "[^"]*"/persistent_peers = "{args["c_persistent_peers"]}"/',
			"-e", rf's/addr_book_strict = \(true\|false\)/addr_book_strict = {args["c_addr_book_strict"]}/',
			"-e", rf's/allow_duplicate_ip = \(true\|false\)/allow_duplicate_ip = {args["c_allow_duplicate_ip"]}/',
			"-e", f's/wal_dir = "[^"]*"/wal_dir = "{args["c_wal_dir"].replace('/', r'\/')}"/',
			"-e", f's/timeout_commit = "[^"]*"/timeout_commit = "{args["c_timeout_commit"]}"/',
			"-e", rf's/create_empty_blocks = \(true\|false\)/create_empty_blocks = {args["c_create_empty_blocks"]}/',
			f"{env['TMHOME']}/config/config.toml"],
		cwd=p2p_dir, env=env, check=True, capture_output=True, text=True)
	except subprocess.CalledProcessError as e:
		print(f"Error configuring tendermint2:{e}")
		return False

	try:
		result = subprocess.run(["sed", "-n", 
			f'/index_tags = "[^"]*"/p',
			f"{env['TMHOME']}/config/config.toml"],
		cwd=p2p_dir, env=env, check=True, capture_output=True, text=True)

		if not result.stdout:
			try:
				result = subprocess.run(["sed", "-i", 
					"-e", rf's/indexer = \("null"\|"kv"\|"psql"\)/indexer = "kv"\nindex_tags = "{args["c_index_tags"]}"/',
					f"{env['TMHOME']}/config/config.toml"],
					cwd=p2p_dir, env=env, check=True, capture_output=True, text=True)
			except subprocess.CalledProcessError as e:
				print(f"Error configuring tendermint3:{e}")
				return False
	except subprocess.CalledProcessError as e:
		print(f"Error configuring tendermint4:{e}")
		return False

	return True

def main():
	if len(sys.argv) != 2:
		print(f"Error: Enter a single .env file:{len(sys.argv)}")
		return

	env_file = sys.argv[1]
	sha256_hash = hashlib.sha256()

	env_file_path = Path(env_file).resolve(strict=True)

	with open(env_file_path, "r") as file:
		lines = file.readlines()

	lines = [line for line in lines if "TASTEBOT_ROOTDIR=" not in line and "TMHOME=" not in line]

	with open(env_file_path, 'w') as file:
		file.writelines(lines)

	with open(env_file_path, "rb") as file:
		for chunk in iter(lambda: file.read(4096), b""):
			sha256_hash.update(chunk)

	hash_id = sha256_hash.hexdigest()
	home_dir = Path.home()
	root_dir = home_dir / ".cache" / f"tastebot-{hash_id}" 
	root_dir.mkdir(mode=0o755, exist_ok=True)

	config = ConfigOptions(env_file=env_file, check=False)

	env = os.environ.copy()

	ret = configure(root_dir, config._app_config)

	if ret == True:
		print(f"Root directory(host):{root_dir}")
		host_volume = root_dir

		home_dir = Path("/root")
		root_dir = home_dir / ".cache" / f"tastebot"
		tmhome_dir = root_dir / "p2p" / "consensus"

		with open(env_file_path, 'w') as file:
			file.writelines(lines)
			file.writelines(
				[f"TASTEBOT_ROOTDIR={root_dir}\n",
				 f"TMHOME={tmhome_dir}\n"]
			)

		print(f"Root directory(docker):{root_dir}")
		image_volume = root_dir

		print(f"\nShared volume for docker container:\n{host_volume}:{image_volume}")

	return ret


