import importlib.resources
import logging
import os
import sys
import sysconfig
import subprocess
from pathlib import Path
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

def build_consensus(io: IO) -> int:
    consensus_dir = Path("p2p/consensus").resolve(strict=True)
    io.write_line(f"<info>Building consensus in: {consensus_dir}</>")

    try:
        result = subprocess.run(["go", "build", "-o", "lib/libconsensus.so.0",
        "-buildmode=c-shared", "-ldflags", 
        f"-extldflags '-Wl,-soname,libconsensus.so.0'", consensus_dir],
        cwd=consensus_dir, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        io.write_line(f"<error>Error compiling libconsensus:{e}</>")
        return 1

def build_waku(io: IO) -> int:
    waku_dir = Path("p2p/waku").resolve(strict=True)
    io.write_line(f"<info>Building waku in: {waku_dir}</>")

    try:
        result = subprocess.run(["go", "build", "-o", "lib/libgowaku.so.0",
        "-buildmode=c-shared", "--tags", "gowaku_no_rln", "-ldflags", 
        f"-extldflags '-Wl,-soname,libgowaku.so.0'", "./library/c/"],
        cwd=waku_dir, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        io.write_line(f"<error>Error compiling libwaku:{e}</>")
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
        io.write_line("<info>Applying status-go patches..</>")
        result = subprocess.run(["git", "apply", "../patches/0001-status-go-api-ext.patch"],
        cwd=statusgo_dir, check=True, capture_output=True, text=True)
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

def build_redis(io: IO) -> int:
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
        return 1

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

def run_build(io: IO, venv_path: Path) -> int:

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

    build_proto(io, venv_path)
    build_consensus(io)
    build_waku(io)
    build_statusgo(io)
    build_falkorDB(io)
    build_redis(io)

    return 0

class BuildLibs(EnvCommand):
    name = "build-libs"
    description = "Compiles libraries for consensus, waku"

    def __init__(self, config: Dict[str, str]) -> None:
        super().__init__()

    def handle(self) -> int:
        return run_build(self.io, self.env.path)

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

        config = tool_data.get("poetry-tastebot-plugin")
        if config is None:
            return None
        return config

    def run_build(
        self, event: Event, event_name: str, dispatcher: EventDispatcher
    ) -> None:
        if (
            not isinstance(event, ConsoleCommandEvent)
            or not isinstance(event.command, BuildCommand)
            or not self.application
        ):
            return
        # config = self.load_config()

        # if config is None:
        #     event.io.write_line(
        #         "<debug>Skipped update, [tool.poetry-grpc-plugin] or pyproject.toml missing.</>",
        #         Verbosity.DEBUG,
        #     )
        #     return

        if run_build(event.io, event.command.env.path) != 0:
            raise Exception("Error: {} failed".format(event.command))

