import os
import tomli
from pathlib import Path
from pydantic import BaseModel
from dataclasses import dataclass, fields
from typing import IO, Any, Optional, TypeVar, Union, cast, get_args

PROJECT_CONFIG_FILE = "pyproject.toml"

@dataclass
class Config():
	root_dir: Union[str, Path]

@dataclass
class RestaurantConfig():
	uuid: str
	name: str
	device: str
	password: str

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

	def __new__(cls):
		if cls._instance is None:
			cls._instance = super().__new__(cls)
			cls._root_dir, cls._app_config = init()
		return cls._instance

	def get_embeddings_config(self) -> EmbeddingsConfig:
		field_names = {f.name for f in fields(EmbeddingsConfig)}
		config = self._app_config['embeddings']
		filtered_config = {k: v for k, v in config.items() if k in field_names}
		return EmbeddingsConfig(**filtered_config)

	def get_restaurant_config(self) -> RestaurantConfig:
		field_names = {f.name for f in fields(RestaurantConfig)}
		config = self._app_config['restaurant']
		filtered_config = {k: v for k, v in config.items() if k in field_names}
		return RestaurantConfig(**filtered_config)

def init():
	root_dir: Union[str, Path]

	if os.getenv("TASTEBOT_ROOTDIR") is not None:
		root_dir = os.environ.get('TASTEBOT_ROOTDIR')
	else:
		home_dir = Path.home()
		root_dir = home_dir / ".cache" / "tastebot"
		root_dir.mkdir(exist_ok=True)

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
