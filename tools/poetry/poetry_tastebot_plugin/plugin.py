import os
import sys
import logging
import sysconfig
import subprocess
import importlib.resources
from pathlib import Path
from dotenv import load_dotenv
from typing import Any, Dict, List, Optional
from grpc_tools import protoc

from cleo.events.console_command_event import ConsoleCommandEvent
from cleo.events.console_events import COMMAND
from cleo.events.event import Event
from cleo.events.event_dispatcher import EventDispatcher
from cleo.helpers import option
from cleo.io.io import IO
from cleo.io.outputs.output import Verbosity
from poetry.console.application import Application
from poetry.console.commands.env_command import EnvCommand
from poetry.console.commands.update import UpdateCommand
from poetry.console.commands.build import BuildCommand
from poetry.console.commands.install import InstallCommand
from poetry.core.utils.helpers import module_name
from poetry.plugins.application_plugin import ApplicationPlugin

def well_known_protos_path() -> str:
    if sys.version_info >= (3, 9):
        with importlib.resources.as_file(
            importlib.resources.files("grpc_tools") / "_proto"
        ) as path:
            return str(path)
    else:
        import pkg_resources

        return pkg_resources.resource_filename("grpc_tools", "_proto")

def build_proto(io: IO, venv_path: Path) -> int:
    p2p_dir = Path("p2p").resolve(strict=True)
    proto_files = ["psi.proto", "restaurant.proto"]
    args = [
        f"--{key}={value}"
        for key, value in [
            ("proto_path", str(p2p_dir)),
            ("python_out", str(p2p_dir)),
            ("grpc_python_out", str(p2p_dir)),
        ]
    ]

    venv_sitepackages_path = 'lib/python3.12/site-packages'
    venv_proto_path = 'private_set_intersection/proto/psi_python_proto_pb/private_set_intersection/proto'
    venv_proto_path = Path(venv_path, venv_sitepackages_path, venv_proto_path)
    args.append(
        f"--proto_path={venv_proto_path}"
    )
    
    command = (
        ["grpc_tools.protoc", f"--proto_path={well_known_protos_path()}"]
        + args
        + proto_files
    )
    protoc_result = protoc.main(command)
    if protoc_result == 0:
        io.write_line(
            f"<info>Successfully generated proto files in '{p2p_dir}'</>"
        )
        subprocess.run(["cp", f"{p2p_dir}/psi_pb2.py", f"{venv_proto_path}"])
        subprocess.run(["sed", "-i", "s/import psi_pb2 as psi__pb2/import p2p.psi_pb2 as psi__pb2/", f"{p2p_dir}/restaurant_pb2.py"])
        subprocess.run(["sed", "-i", "s/import restaurant_pb2 as restaurant__pb2/import p2p.restaurant_pb2 as restaurant__pb2/", f"{p2p_dir}/restaurant_pb2_grpc.py"])

    return protoc_result

def build_consensus(io: IO, env, args) -> int:
    p2p_dir = Path("p2p").resolve(strict=True)
    consensus_dir = Path("p2p/consensus").resolve(strict=True)
    tendermint_dir = Path("p2p/tendermint").resolve(strict=True)
    io.write_line(f"<info>Building consensus in: {consensus_dir}</>")

    try:
        io.write_line("<info>Checking out tendermint (tag v0.34.24)</>")
        result = subprocess.run(["git", "checkout", "-f", "v0.34.24"],
        cwd=tendermint_dir, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        io.write_line(f"<error>Error checking out tag:{e}</>")
        return 1

    try:
        result = subprocess.run(["git", "apply", "--check", "../patches/0001-tendermint-init-cmd.patch"],
        cwd=tendermint_dir, capture_output=True, text=True)

        if result.returncode == 0:
            try:
                io.write_line("<info>Applying tendermint patches..</>")
                result = subprocess.run(["git", "apply", "../patches/0001-tendermint-init-cmd.patch"],
                cwd=tendermint_dir, check=True, capture_output=True, text=True)
            except subprocess.CalledProcessError as e:
                io.write_line(f"<error>Error applying patches to tendermint:{e}</>")
                return 1
    except subprocess.CalledProcessError as e:
        io.write_line(f"<error>Error applying patches to tendermint:{e}</>")
        return 1

    try:
        result = subprocess.run(["make", "build"],
        cwd=tendermint_dir, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        io.write_line(f"<error>Error building tendermint:{e}</>")
        return 1

    try:
        result = subprocess.run(["rm", "-rf", f"{env['TMHOME']}/config", f"{env['TMHOME']}/data"],
        cwd=p2p_dir, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        io.write_line(f"<error>Error deleting tenderming config:{e}</>")
        return 1    

    try:
        result = subprocess.run(["build/tendermint", "init", "validator"],
        cwd=tendermint_dir, env=env, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        io.write_line(f"<error>Error configuring tendermint:{e}</>")
        return 1

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
        print(f"Error configuring tendermint:{e}")
        return 1

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
                print(f"Error configuring tendermint:{e}")
                return 1
    except subprocess.CalledProcessError as e:
        print(f"Error configuring tendermint:{e}")
        return 1

    env["CGO_LDFLAGS"] = "-Wl,-soname,libgowaku.so.0"

    try:
        result = subprocess.run(["go", "build", "-o", "build/lib/libconsensus.so",
        "-buildmode=c-shared", consensus_dir],
        cwd=consensus_dir, env=env, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        io.write_line(f"<error>Error compiling libconsensus:{e}</>")
        return 1

    try:
        result = subprocess.run(["sed", "-i", "s/#include <cgo_utils.h>//gi",
                                f"{consensus_dir}/build/lib/libconsensus.h"],
        cwd=consensus_dir, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        io.write_line(f"<error>Error compiling libconsensus:{e}</>")
        return 1

    try:
        result = subprocess.run(["mv", "consensus/build/lib/libconsensus.so", "libs/libconsensus.so.0"],
        cwd=p2p_dir, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        io.write_line(f"<error>Error copying consensus libs:{e}</>")
        return 1    

    try:
        result = subprocess.run(["cp", "consensus/build/lib/libconsensus.h", "libs"],
        cwd=p2p_dir, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        io.write_line(f"<error>Error copying consensus libs:{e}</>")
        return 1

def build_waku(io: IO) -> int:
    p2p_dir = Path("p2p").resolve(strict=True)
    waku_dir = Path("p2p/waku").resolve(strict=True)
    io.write_line(f"<info>Building waku in: {waku_dir}</>")

    try:
        result = subprocess.run(["git", "apply", "--check", "../patches/0001-waku-api-ext.patch"],
        cwd=waku_dir, capture_output=True, text=True)

        if result.returncode == 0:
            try:
                io.write_line("<info>Applying waku patches..</>")
                result = subprocess.run(["git", "apply", "../patches/0001-waku-api-ext.patch"],
                cwd=waku_dir, check=True, capture_output=True, text=True)
            except subprocess.CalledProcessError as e:
                io.write_line(f"<error>Error applying patches to waku:{e}</>")
                return 1
    except subprocess.CalledProcessError as e:
        io.write_line(f"<error>Error applying patches to waku:{e}</>")
        return 1

    try:
        result = subprocess.run(["go", "build", "-o", "lib/libgowaku.so.0",
        "-buildmode=c-shared", "--tags", "gowaku_no_rln", "-ldflags", 
        f"-extldflags '-Wl,-soname,libgowaku.so.0'", "./library/c/"],
        cwd=waku_dir, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        io.write_line(f"<error>Error compiling libwaku:{e}</>")
        return 1

    try:
        result = subprocess.run(["cp", "waku/lib/libgowaku.so.0", "libs"],
        cwd=p2p_dir, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        io.write_line(f"<error>Error copying waku libs:{e}</>")
        return 1    

def build_statusgo(io: IO) -> int:
    im_dir = Path("im").resolve(strict=True)
    statusgo_dir = Path("im/status-go").resolve(strict=True)
    io.write_line(f"<info>Building statusgo in: {statusgo_dir}</>")

    try:
        io.write_line("<info>Checking out Status-go(tag v10.4.0)</>")
        result = subprocess.run(["git", "checkout", "-f", "v10.4.0"],
        cwd=statusgo_dir, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        io.write_line(f"<error>Error checking out tag:{e}</>")
        return 1

    try:
        result = subprocess.run(["git", "apply", "--check", "../patches/0001-status-go-api-ext.patch"],
        cwd=statusgo_dir, capture_output=True, text=True)

        if result.returncode == 0:
            try:
                io.write_line("<info>Applying status-go patches..</>")
                result = subprocess.run(["git", "apply", "../patches/0001-status-go-api-ext.patch"],
                cwd=statusgo_dir, check=True, capture_output=True, text=True)
            except subprocess.CalledProcessError as e:
                io.write_line(f"<error>Error applying patches to status-go:{e}</>")
                return 1
    except subprocess.CalledProcessError as e:
        io.write_line(f"<error>Error applying patches to status-go:{e}</>")
        return 1

    try:
        result = subprocess.run(["make", "status-go-deps"],
        cwd=statusgo_dir, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        io.write_line(f"<error>Error downloading status-go deps:{e}</>")
        return 1

    try:
        result = subprocess.run(["make", "status-backend"],
        cwd=statusgo_dir, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        io.write_line(f"<error>Error compiling status-backend:{e}</>")
        return 1

    try:
        result = subprocess.run(["make", "statusgo-shared-library"],
        cwd=statusgo_dir, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        io.write_line(f"<error>Error compiling status-go shared library:{e}</>")
        return 1

    try:
        result = subprocess.run(["cp", "status-go/build/bin/status-backend", "libs"],
        cwd=im_dir, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        io.write_line(f"<error>Error copying im libs:{e}</>")
        return 1

    try:
        result = subprocess.run(["cp", "status-go/build/bin/libstatus.so.0", "libs"],
        cwd=im_dir, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        io.write_line(f"<error>Error copying im libs:{e}</>")
        return 1

def build_falkorDB(io: IO) -> int:
    ai_dir = Path("ai").resolve(strict=True)
    falkorDB_dir = Path("ai/FalkorDB").resolve(strict=True)
    io.write_line(f"<info>Building FalkorDB in: {falkorDB_dir}</>")

    try:
        result = subprocess.run(["wget", "-P", "libs", "https://github.com/FalkorDB/FalkorDB/releases/download/v4.10.3/falkordb-x64.so"],
        cwd=ai_dir, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        io.write_line(f"<error>Error downloading falkordb:{e}</>")
        return 1

    try:
        result = subprocess.run(["chmod", "+x", "libs/falkordb-x64.so"],
        cwd=ai_dir, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        io.write_line(f"<error>Error setting permission for FalkorDB lib:{e}</>")
        return 1

    # try:
    #     io.write_line("<info>Checking out FalkorDB(tag v4.10.3)</>")
    #     result = subprocess.run(["git", "checkout", "v4.10.3"],
    #     cwd=falkorDB_dir, check=True, capture_output=True, text=True)
    # except subprocess.CalledProcessError as e:
    #     io.write_line(f"<error>Error checking out tag:{e}</>")
    #     return 1

    # try:
    #     io.write_line("<info>Updating submodules of FalkorDB</>")
    #     result = subprocess.run(["git", "submodule", "update", "--init"],
    #     cwd=falkorDB_dir, check=True, capture_output=True, text=True)
    # except subprocess.CalledProcessError as e:
    #     io.write_line(f"<error>Error checking out tag:{e}</>")
    #     return 1

    # try:
    #     result = subprocess.run(["make"],
    #     cwd=falkorDB_dir, check=True, capture_output=True, text=True)
    #     io.write_line(f"<info>Build logs:{result.stdout}</>")
    # except subprocess.CalledProcessError as e:
    #     io.write_line(f"<error>Error compiling FalkorDB:{e}</>")
    #     return 1

    # try:
    #     result = subprocess.run(["cp", "bin/linux-x64-release/src/falkordb.so", "../libs"],
    #     cwd=falkorDB_dir, check=True, capture_output=True, text=True)
    # except subprocess.CalledProcessError as e:
    #     io.write_line(f"<error>Error copying FalkorDB libs:{e}</>")
    #     return 1

def build_redis(io: IO, env, args) -> int:
    ai_dir = Path("ai").resolve(strict=True)
    libs_dir = Path("ai/libs").resolve(strict=True)
    redis_dir = Path("ai/redis").resolve(strict=True)
    io.write_line(f"<info>Building Redis in: {redis_dir}</>")

    try:
        result = subprocess.run(["wget", "https://download.redis.io/releases/redis-7.4.0.tar.gz"],
        cwd=redis_dir, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        io.write_line(f"<error>Error downloading redis:{e}</>")
        return 1

    try:
        result = subprocess.run(["tar", "-xzvf", "redis-7.4.0.tar.gz", "--strip-components=1"],
        cwd=redis_dir, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        io.write_line(f"<error>Error downloading redis:{e}</>")
        return 1

    try:
        result = subprocess.run(["make", "all"],
        cwd=redis_dir, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        io.write_line(f"<error>Error compiling redis:{e}</>")
        return 1

    try:
        result = subprocess.run(["cp", "src/redis-server", "../libs"],
        cwd=redis_dir, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        io.write_line(f"<error>Error copying redis server:{e}</>")
        return 0

    try:
        result = subprocess.run(["cp", "redis.conf", "../libs"],
        cwd=redis_dir, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        io.write_line(f"<error>Error copying redis conf:{e}</>")
        return 1

    try:
        result = subprocess.run("echo loadmodule ai/libs/falkordb-x64.so >> redis.conf",
        shell=True, cwd=libs_dir, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        io.write_line(f"<error>Error updating redis conf:{e}</>")
        return 1

def run_build(io: IO, venv_path: Path, config_args) -> int:

    venv_bin_dir = sysconfig.get_path("scripts")
    io.write_line(
        f"<debug>Adding virtual environment bin dir '{venv_bin_dir}' to PATH</>",
        Verbosity.DEBUG,
    )
    path = os.getenv("PATH", "")
    if path and venv_bin_dir not in path:
        os.environ["PATH"] = f"{path}:{venv_bin_dir}"
    io.write_line(
        f"<debug>Modified PATH='{os.environ['PATH']}'</>",
        Verbosity.DEBUG,
    )

    env = []
    try:
        env_path = Path.cwd() / '.env'
        load_dotenv(dotenv_path=env_path)
        env = os.environ.copy()
    except FileNotFoundError:
        print("Error: .env file not found, Create .env")

    build_proto(io, venv_path)
    build_consensus(io, env, config_args['p2p'])
    build_waku(io)
    build_statusgo(io)
    build_falkorDB(io)
    build_redis(io, env, config_args['kg'])

    return 0

class BuildLibs(EnvCommand):
    name = "build-libs"
    description = "Compiles libraries for consensus, waku"

    options = [
        option(
            "c_moniker",
            description="A custom human readable name for the consensus node.",
            value_required=True,
            flag=False,
            default="Restaurant",
        ),
        option(
            "c_persistent_peers",
            description="List of nodes to keep persistent connections to.",
            value_required=True,
            flag=False,
            default="04c6ff08d435e1b3f7fde44bdab924a166071bbb@192.168.1.26:26658",
        ),        
        option(
            "c_addr_book_strict",
            description="Strict address routability rules, Set false for private or local networks",
            value_required=True,
            flag=False,
            default="false",
        ),
        option(
            "c_allow_duplicate_ip",
            description="Toggle to disable guard against peers connecting from the same ip.",
            value_required=True,
            flag=False,
            default="true",
        ),
        option(
            "c_wal_dir",
            description="WAL directory.",
            value_required=True,
            flag=False,
            default="p2p/consensus",
        ),
        option(
            "c_timeout_commit",
            description="How long we wait after committing a block, before starting on the new height.",
            value_required=True,
            flag=False,
            default="10s",
        ),
        option(
            "c_create_empty_blocks",
            description="EmptyBlocks mode and possible interval between empty blocks.",
            value_required=True,
            flag=False,
            default="false",
        ),
        option(
            "c_index_tags",
            description="What transactions to index.",
            value_required=True,
            flag=False,
            default="order_tx_check,order_tx_deliver",
        ),        
    ]

    def __init__(self, config: Dict[str, str]) -> None:
        super().__init__()
        self.config = config
        for o in self.options:
            if o.name in config:
                o.set_default(config[o.name])

    def handle(self) -> int:
        args = {o.name: self.option(o.name) for o in self.options}
        args = {name: value for name, value in args.items() if value is not None}
        return run_build(self.io, self.env.path, args)

class TasteBotPlugin(ApplicationPlugin):
    _application: Application

    @property
    def application(self) -> Optional[Application]:
        return self._application

    @application.setter
    def application(self, value: Application) -> None:
        self._application = value

    def activate(self, application: Application) -> None:
        self.application = application
        application.command_loader.register_factory(
            "build-libs", lambda: BuildLibs(self.load_config() or {})
        )

        application.event_dispatcher.add_listener(COMMAND, self.run_build)

        #run_build(application._io, application._env.path)

    def load_config(self) -> Optional[Dict[str, str]]:
        poetry = self._application.poetry
        tool_data: Dict[str, Any] = poetry.pyproject.data.get("tool", {})
        tastebot_data: Dict[str, Any] = tool_data.get("tastebot", {})
        app_data = tastebot_data.get("app", {})

        return app_data

    def run_build(
        self, event: Event, event_name: str, dispatcher: EventDispatcher
    ) -> None:
        if (
            not isinstance(event, ConsoleCommandEvent)
            or not isinstance(event.command, BuildCommand)
            or not self.application
        ):
            return
        config = self.load_config()

        if config is None:
            event.io.write_line(
                "<debug>Skipped update, [tool.poetry-tastebot-plugin] or pyproject.toml missing.</>",
                Verbosity.DEBUG,
            )
            return

        if run_build(event.io, event.command.env.path, config) != 0:
            raise Exception("Error: {} failed".format(event.command))

