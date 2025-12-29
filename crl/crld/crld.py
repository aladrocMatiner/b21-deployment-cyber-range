import asyncio
import functools
import json
import logging
import sys
from enum import Enum
from functools import partial
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, Iterable, NoReturn, Optional, Tuple, TypeAlias

from aiohttp import web
from python_on_whales import docker

from crl.crl import cmd_create, cmd_delete, cmd_start, cmd_stop, list_events, list_worlds
from crl.helpers import validate_name
from crl.world import inspect

log = logging.getLogger(__name__)  # pylint: disable=locally-disabled, invalid-name

WorldState = Enum("WorldState", ["notfound", "checking", "creating", "stopped", "starting", "running", "stopping"])
WorldSignal = Enum("WorldSignal", ["create", "start", "stop", "fail", "check", "up", "down"])
WorldHealth = Enum("WorldHealth", ["up", "degraded", "down"])
WorldStatus: TypeAlias = Dict[Tuple[str, str], WorldState]

running_configdir: str = ""
create_queue: asyncio.Queue[Tuple[Tuple[str, str], asyncio.Event]] = asyncio.Queue()
stop_queue: asyncio.Queue[Tuple[Tuple[str, str], asyncio.Event]] = asyncio.Queue()
world_state: WorldStatus = {}

routes = web.RouteTableDef()


#                               state diagram of world:
#                       |
#                       v           check
#             /-> [[ notfound ]] --------------\
#             |         |      ^                |
#        fail |  create |  fail \               v
#             |         v        ========= [ checking ] -----------\
#             \--- [ creating ] /               ^                  |
#                       |      /       check    |     check        |
#                  down |     / down   --------/ \-------------    | up
#                       |    /       /                         \   |
#                       v   v       /                   up      \  v
#                  [ stopped ] =====--> [ starting ] -------> [ running ]
#                       ^ ^                   |                    |
#                       |  \---------------- /                     |
#                       |       fail                               |
#                        \------------- [ stopping ] <-------------/
#                           down / fail                   stop
#
async def user_fsm(event: str, user: str, signal: WorldSignal) -> None:
    """The finite state machine (FSM) that takes care of all logic when it comes to handling state and signals."""
    _state: Callable[[WorldState], None] = lambda s: set_fsm_state(event, user, s, signal)
    match get_fsm_state(event, user), signal:
        case WorldState.notfound, WorldSignal.create:
            # We only do one create at a time so that portd safetly can figure out what ports should be used.
            _state(WorldState.creating)
            created_event = asyncio.Event()
            create_queue.put_nowait(((event, user), created_event))
            await created_event.wait()
        case WorldState.notfound, WorldSignal.check:
            _state(WorldState.checking)
            await checking_state(event, user)
        case WorldState.creating, WorldSignal.down:
            _state(WorldState.stopped)
        case WorldState.creating, WorldSignal.fail:
            # delete lingering files.
            await call_fsm_blocking(event, user, cmd_delete)
            _state(WorldState.notfound)

        case WorldState.checking, WorldSignal.up:
            _state(WorldState.running)
        case WorldState.checking, WorldSignal.down:
            _state(WorldState.stopped)
        case WorldState.checking, WorldSignal.fail:
            _state(WorldState.notfound)

        case WorldState.stopped, WorldSignal.check:
            _state(WorldState.checking)
            await checking_state(event, user)
        case WorldState.stopped, WorldSignal.start:
            _state(WorldState.starting)
            await call_fsm_blocking(event, user, cmd_start, WorldSignal.up, WorldSignal.fail)

        case WorldState.starting, WorldSignal.up:
            _state(WorldState.running)
        case WorldState.starting, WorldSignal.fail:
            _state(WorldState.stopped)

        case WorldState.running, WorldSignal.check:
            _state(WorldState.checking)
            await checking_state(event, user)
        case WorldState.running, WorldSignal.stop:
            _state(WorldState.stopping)
            stop_event = asyncio.Event()
            stop_queue.put_nowait(((event, user), stop_event))
            await stop_event.wait()

        case WorldState.stopping, WorldSignal.down:
            _state(WorldState.stopped)
        case WorldState.stopping, WorldSignal.fail:
            _state(WorldState.stopped)

        case current_state, _:
            # nothing happens, just set the same state to get the nice printout.
            _state(current_state)


def get_fsm_state(event: str, user: str) -> WorldState:
    """Get the state of a world."""
    return world_state.setdefault((event, user), WorldState.notfound)


def set_fsm_state(event: str, user: str, new_state: WorldState, signal: WorldSignal) -> None:
    """Set a new state of a world."""
    old_state = get_fsm_state(event, user)
    world_state[(event, user)] = new_state
    log.info(f"{event=} {user=} {old_state.name} -> {new_state.name} ({signal.name})")


async def check_fsm_integrity(event: str, user: str) -> None:
    """Check the integrity of the FSM by checking the existence of configuration files, docker stack status."""
    curr_state = get_fsm_state(event, user)
    curr_config = get_config_path(event, user).exists()
    log.debug(f"{event=} {user=} {curr_state.name=} {curr_config=}")
    if curr_config and curr_state == WorldState.notfound:
        await user_fsm(event, user, WorldSignal.check)
    elif not curr_config and curr_state != WorldState.notfound:
        log.warning(f"{event=} {user=} no configuration file found but und")
        await user_fsm(event, user, WorldSignal.check)


async def checking_state(event: str, user: str) -> None:
    """When in checking state send appropriate signal based on health status of world."""
    health = await get_health(event, user)
    if health == WorldHealth.down:
        await user_fsm(event, user, WorldSignal.down)
    elif health:
        await user_fsm(event, user, WorldSignal.up)
    else:
        await user_fsm(event, user, WorldSignal.fail)


async def call_fsm_blocking(
    event: str, user: str, op: Any, ok: Optional[WorldSignal] = None, fail: Optional[WorldSignal] = None
) -> None:
    """Call a blocking non-async function in a background thread and send signal to fsm based on return value.

    Arguments:
        op: The blocking function that should be run in the background thread.
        ok: The signal sent to the FSM when successfully executing op.
        fail: The signal sent to the FSM when it fails to execute op.
    """
    loop = asyncio.get_running_loop()
    _func = partial(op, event=event, worlds=[user], config_dir=running_configdir)
    try:
        res = await loop.run_in_executor(None, _func)
        if res:
            if ok:
                await user_fsm(event, user, ok)
        else:
            if fail:
                await user_fsm(event, user, fail)
    except Exception as e:
        log.exception(f"exception caught: {e}")
        if fail:
            await user_fsm(event, user, fail)


def get_worlds() -> Iterable[Tuple[str, str]]:
    """List all worlds that are found in config dir."""
    for e in list_events(running_configdir):
        for w in list_worlds(running_configdir, e):
            yield e, w


def get_config_path(event: str, user: str) -> Path:
    """Return the path to users wireguard config."""
    return get_world_path(event, user) / "peer" / f"peer_{user}.conf"


def get_world_path(event: str, user: str) -> Path:
    """Return the path to users world."""
    return Path(running_configdir) / "Events" / event / user


def get_user_config(event: str, user: str) -> Optional[str]:
    """Return the content of a users wireguard config."""
    try:
        config = get_config_path(event, user)
        log.debug(f"{config=}")
        with open(config) as f:
            config_content = f.read()
        return config_content
    except FileNotFoundError:
        return None


async def get_wireguard_network(event: str, user: str) -> Optional[Dict[str, str]]:
    """Return current network settings for wireguard service for a world."""

    def _internal_get_wireguard_vip(event: str, user: str) -> Optional[Dict[str, str]]:
        SERVICE_PREFIX = f"crl-{event}-{user}"
        wireguard_name = f"{SERVICE_PREFIX}_wireguard"
        wireguard_networks = {}
        services = docker.service.list(filters={"name": wireguard_name})

        if len(services) == 1:
            wireguard_service = services[0]
        else:
            return None

        if wireguard_service.endpoint.virtual_ips:
            for vip in wireguard_service.endpoint.virtual_ips:
                if not vip.network_id or not vip.addr:
                    continue
                full_name = docker.network.inspect(vip.network_id).name
                network_name = full_name.removeprefix(f"{SERVICE_PREFIX}_")
                if full_name != "ingress":
                    ip, _ = vip.addr.split("/")
                    wireguard_networks[network_name] = ip
        return wireguard_networks

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(_internal_get_wireguard_vip, event=event, user=user))


async def world_status_response(event: str, user: str) -> web.Response:
    """Get the state and status of a world and return it as a web response."""
    s = get_fsm_state(event, user)
    resp_obj = {"state": str(s.name)}
    if s == WorldState.running:
        health = await get_health(event, user)
        if health:
            resp_obj["health"] = health.name
    return web.Response(text=json.dumps(resp_obj))


async def get_health(event: str, user: str) -> Optional[WorldHealth]:
    """Get health status of a world by inspecting the docker stack of that world."""

    def determine_world_health(event: str, user: str) -> Optional[WorldHealth]:
        """Inspect a world and determine the health status."""
        world_info = inspect(world=get_world_path(event, user), world_name=f"crl-{event}-{user}", netinfo=False)
        services_status = [
            service.get("up", False) for hostname, service in world_info.items() if hostname != "wireguard"
        ]
        log.debug(f"{event=} {user=} {services_status=}")

        if not services_status:  # no services at all
            return WorldHealth.down
        elif all(services_status):  # all services ok.
            return WorldHealth.up
        elif any(services_status):  # some service ok.
            return WorldHealth.degraded
        elif not any(services_status):  # all services down
            return WorldHealth.down
        return None

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(determine_world_health, event=event, user=user))


def validate_world_args(
    func: Callable[[str, str], Awaitable[web.Response]],
) -> Callable[[web.Request], Awaitable[web.Response]]:
    """Decorator to validate event and user names and pass it on to the function."""

    @functools.wraps(func)
    async def wrapper_validate(req: web.Request) -> web.Response:
        try:
            event = validate_name(req.match_info["event"])
            user = validate_name(req.match_info["user"])
        except ValueError:
            return web.Response(status=415)
        return await func(event, user)

    return wrapper_validate


# --------------------------------------------------------------------------------
# REST API endpoints:
# --------------------------------------------------------------------------------


@routes.post("/{event}/create/{user}")
@validate_world_args
async def world_create(event: str, user: str) -> web.Response:
    await check_fsm_integrity(event, user)

    if get_fsm_state(event, user) == WorldState.notfound:
        await user_fsm(event, user, WorldSignal.create)

    if get_fsm_state(event, user) == WorldState.stopped:
        await user_fsm(event, user, WorldSignal.start)

    if c := get_user_config(event, user):
        return web.Response(text=c)
    else:
        return web.Response(status=404)


@routes.post("/{event}/reset/{user}")
@validate_world_args
async def world_reset(event: str, user: str) -> web.Response:
    await check_fsm_integrity(event, user)

    if get_fsm_state(event, user) == WorldState.running:
        await user_fsm(event, user, WorldSignal.stop)

    if get_fsm_state(event, user) == WorldState.stopped:
        await user_fsm(event, user, WorldSignal.start)

    return await world_status_response(event, user)


@routes.get("/{event}/status/{user}")
@validate_world_args
async def world_status(event: str, user: str) -> web.Response:
    await check_fsm_integrity(event, user)
    return await world_status_response(event, user)


@routes.get("/{event}/config/{user}")
@routes.get("/{event}/wireguard/{user}/config")
@validate_world_args
async def world_config(event: str, user: str) -> web.Response:
    await check_fsm_integrity(event, user)

    if c := get_user_config(event, user):
        return web.Response(text=c)
    else:
        return web.Response(status=404)


@routes.get("/{event}/wireguard/{user}/network")
@validate_world_args
async def wireguard_network(event: str, user: str) -> web.Response:
    await check_fsm_integrity(event, user)

    wg_network = await get_wireguard_network(event, user)

    if wg_network:
        return web.Response(text=json.dumps(wg_network))
    else:
        return web.Response(status=404)


# --------------------------------------------------------------------------------
# Backgrounds tasks:
# --------------------------------------------------------------------------------


async def worker_create() -> NoReturn:
    """Worker in charge of creating worlds in a FIFO order."""
    log.info("[worker_create] waiting for work...")

    while True:
        # fetch from the queue this semaphore-ish thing that is created_event.
        (event, user), created_event = await create_queue.get()
        log.info(f"[worker_create] starting processing {event=} {user=}")
        await call_fsm_blocking(event, user, cmd_create, WorldSignal.down, WorldSignal.fail)
        create_queue.task_done()
        # indicate to the awaiting coro's that the created_event is done.
        created_event.set()
        log.info(f"[worker_create] done processing {event=} {user=}")


async def worker_stop() -> NoReturn:
    """Worker in charge of stopping worlds in a FIFO order."""
    log.info("[worker_stop] waiting for work...")

    while True:
        # fetch from the queue this semaphore-ish thing that is created_event.
        (event, user), stop_event = await stop_queue.get()
        log.info(f"[worker_stop] starting processing {event=} {user=}")
        await call_fsm_blocking(event, user, cmd_stop, WorldSignal.down, WorldSignal.fail)
        stop_queue.task_done()
        # indicate to the awaiting coro's that the stop_event is done.
        stop_event.set()
        log.info(f"[worker_stop] done processing {event=} {user=}")


async def init_fsm() -> None:
    """Initialize fsm by checking integrity of all worlds founds."""
    worlds = [check_fsm_integrity(e, w) for e, w in get_worlds()]
    await asyncio.gather(*worlds)


async def start_background_tasks(app: web.Application) -> None:
    app["init_fsm"] = asyncio.create_task(init_fsm())
    app["worker_create"] = asyncio.create_task(worker_create())
    app["worker_stop"] = asyncio.create_task(worker_stop())


# --------------------------------------------------------------------------------
# Server setup:
# --------------------------------------------------------------------------------


def init_app() -> web.Application:
    app = web.Application()
    app.on_startup.append(start_background_tasks)
    app.add_routes(routes)
    return app


def main(listen_addr: str, port: int, configdir: str, log_level: str = "INFO") -> None:
    global running_configdir
    log_format = "%(asctime)s [%(levelname)s:%(module)s:%(funcName)s] %(message)s"
    alf = """%a "%r" %s %b "%{User-Agent}i" """
    logging.basicConfig(format=log_format, handlers=[logging.StreamHandler(sys.stdout)])
    logging.getLogger("crld").setLevel(log_level)
    logging.getLogger("crl").setLevel(log_level)
    logging.getLogger("aiohttp.access").setLevel("INFO")

    log.info(f"starting crld at http://{listen_addr}:{port}, {configdir=}")
    running_configdir = configdir
    web.run_app(init_app(), host=listen_addr, port=port, access_log_format=alf, print=None)
