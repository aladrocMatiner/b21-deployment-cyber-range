#!/usr/bin/env python3

import logging
import os
import sys
from argparse import ArgumentParser
from importlib.resources import files
from pathlib import Path
from shutil import rmtree
from typing import Any, Callable, Dict, List, Optional, Set

from pathvalidate.argparse import validate_filepath_arg

import crl.world as crlw
from crl.config import USER_ALLOWED_REGEX, USER_CASE_SENSITIVE, USER_MAX_LEN, USER_MIN_LEN
from crl.helpers import (
    check_url,
    deep_update,
    find_free_port,
    quoted,
    random_string,
    read_yaml,
    strip_docker_compose_options,
    validate_name,
    write_yaml,
)

log = logging.getLogger(__name__)  # pylint: disable=locally-disabled, invalid-name


def cmd_create(
    event: str,
    config_dir: str,
    worlds: List[str],
    blueprint: Optional[str] = None,
    external_url: Optional[str] = None,
    stored_event: Optional[str] = None,
    event_name: Optional[str] = None,
    **kwargs: int,
) -> bool:
    """
    Create command function.

    Parameters:
        event:
        worlds:
        blueprint:
        external_url:
        stored_event:
        event_name:
        config_dir: the base dir for configuration files (.) .
        **kwargs: additional keyword arguments are ignored.

    Returns:
    """
    config_path = Path(config_dir)
    world_basepath = config_path / "Events"
    global_config_file = world_basepath / "docker-compose.yml"
    args_blueprint = blueprint if blueprint else ""
    args_stored_event = stored_event if stored_event else ""
    blueprint_path = (
        Path(args_blueprint)
        if args_blueprint and Path(args_blueprint).is_file()
        else config_path / "blueprints" / args_blueprint
    )
    stored_event_path = (
        Path(args_stored_event)
        if args_stored_event and Path(args_stored_event).is_file()
        else config_path / "events" / args_stored_event
    )
    event_path = world_basepath / event
    event_file = event_path / "docker-compose.yml"

    # Check if event already exists
    if not worlds and read_yaml(event_file):
        log.info(f"{event=} already exists")
        return False

    # If event doesn't exist, check if necessary parameters are provided
    if not read_yaml(event_file):
        if external_url and blueprint_path.is_file() or stored_event_path.is_file():
            if stored_config := read_yaml(stored_event_path):
                event_traefik = stored_config.get("use-traefik", False)
                event_crld = stored_config.get("use-crld", False)
                if global_config := read_yaml(global_config_file):
                    global_traefik = global_config["x-crl"].get("use-traefik", False)
                    global_crld = global_config["x-crl"].get("use-crld", False)
                    if (not global_traefik and event_traefik) or (not global_crld and event_crld):
                        log.info(f"Global config is {global_traefik=}, {global_crld=}")
                        log.info(f"which differs from {event_traefik=}, {event_crld=}")
                        log.info("please reconfigure event or re-run init to enable missing service(s)")
                        return False
                elif event_traefik or event_crld:
                    log.info(f"Global config file {global_config_file} not found")
                    help_str = "please run crl init "
                    if event_traefik:
                        help_str += "--use-traefik "
                    if event_crld:
                        help_str += "--use-crld "
                    help_str += "first"
                    log.info(help_str)
                    return False
            # When we do not have a stored event, we cannot configure crld or traefik so no need to check for that

            # Create event and associated files
            event_path.mkdir(parents=True, exist_ok=True)
            used_ports = crlw.find_ports_used_in_worlds(path=world_basepath)
            create_event(
                event=event,
                used_ports=used_ports,
                stored_event_path=stored_event_path if stored_event_path.is_file() else None,
                blueprint_path=blueprint_path if blueprint_path.is_file() else None,
                config_path=config_path,
                event_file=event_file,
                external_url=external_url,
                event_name=event_name,
            )
        else:
            log.info("Need to supply a external-url and a valid blueprint or a stored event file to create an event")
            log.info(f"Blueprints in {config_dir}:")
            for path in config_path.glob("**/*blueprints*/*.y*ml"):
                log.info(f"{path.name} ({path.absolute()})")
            log.info(f"Stored events in {config_dir}:")
            for path in config_path.glob("**/*events*/*.y*ml"):
                log.info(f"{path.name} ({path.absolute()})")
            return False

    # If event exists, create worlds based on that event configuration.
    if event_config := read_yaml(event_file):
        config_ctf_url = event_config["x-event"].get("ctf-url", None)
        config_ctf_token = event_config["x-event"].get("ctf-token", None)
        config_ctf_blueprint = Path(event_config["x-event"]["blueprint"])
        config_external_url = event_config["x-event"]["external-url"]
        config_flag_format = event_config["x-event"].get("flag-format")
        if worlds:  # Ensure the event is up before I start the worlds(if any)
            crlw.start(world=event_path, world_name=f"crl-{event}")
            if config_ctf_url:
                if check_url(config_ctf_url):
                    log.info(f"External CTF for event is : {event_config['x-event']['ctf-external-url']}")
                else:
                    log.error("Could not connect to ctfd")
                    return False

        for w in worlds:
            log.info(f"- {w}")
            crlw.create(
                event=event,
                blueprint=config_ctf_blueprint,
                ctf_url=config_ctf_url,
                ctf_token=config_ctf_token,
                username=w,
                world=event_path / w,
                config_dir=config_path,
                world_basepath=world_basepath,
                flag_format_override=config_flag_format,
                external_url=config_external_url,
            )
    else:
        log.error(f"Could not read {event_file=}")
        return False
    return True


def cmd_list(event: Optional[str], worlds: List[str], config_dir: str, **kwargs: int) -> bool:
    """
    List command function.

    Parameters:
        event:
        worlds:
        config_dir: The base dir for configuration files (.) .
        **kwargs: additional keyword arguments are ignored.

    Returns:
    """
    world_basepath = Path(config_dir) / "Events"
    event_path = world_basepath / event if event else None

    # List events or worlds within an event
    if not event_path:
        log.info("These events exist:")
        for e in list_events(config_dir):
            log.info(f"- {e}")
    elif event and not worlds:
        if not event_path or not event_path.is_dir():
            log.error(f"Event {event} does not exist")
            return False
        log.info(f"These worlds exist in event {event}:")
        for w in list_worlds(config_dir, event):
            log.info(f"- {w}")
    else:
        for w in worlds:
            world_path = event_path / w
            if len(worlds) > 1:
                log.info(f"- {world_path.name}")
            if not world_path.is_dir():
                log.info("Does not exist, ignoring")
                continue

            services = crlw.inspect(world=world_path, world_name=f"crl-{event}-{w}")

            # Print service information in Markdown table format
            columns = ["UP", "NAME", "NET", "PORTS", "FLAGS"]
            data = []

            for hostname, service in services.items():
                net = ",".join(
                    [f"{name}({ip})" for name, ip in service.get("networks", {}).items() if name != "ingress"]
                )

                if service.get("vips"):
                    vips = ",".join([f"{name}({ip})" for name, ip in service["vips"].items() if name != "ingress"])
                    net += f" VIP: {vips}"
                name = f"{hostname}({service.get('ServiceID', '')})"
                ports = service.get("ports", "")
                up = "\033[92m✓\033[00m" if service.get("up") else "\033[91m–\033[00m"
                flags = service.get("flags", "")
                data.append([f" {up}", f"{name}", f"{net}", f"{ports}", f"{flags}"])

            # Calculate column widths with a fixed max for the first column
            col_widths = [
                (
                    min(max(len(str(row[i])) for row in ([columns] + data)), 2)
                    if i == 0
                    else max(len(str(row[i])) for row in ([columns] + data))
                )
                for i in range(len(columns))
            ]

            # Ensure minimum separator widths
            col_widths = [max(w, 2) for w in col_widths]  # Minimum width of 2 for all separators
            # Create format string dynamically
            md_table_format = " | ".join([f"{{:<{w}}}" for w in col_widths])

            # Create separator rows
            separator = " | ".join(
                ["-" * col_widths[0]] + [":-" + "-" * (col_widths[i] - 2) for i in range(1, len(columns))]
            )

            log.info(md_table_format.format(*columns))
            log.info(separator)
            for row in data:
                log.info(md_table_format.format(*row))

    return True


def cmd_start(event: str, worlds: List[str], config_dir: str, **kwargs: int) -> bool:
    """
    Performs the start operation on one or more worlds.
    If the world does not exist, the start operation is skipped.

    Args:
        event -
        worlds -
        config_dir - the base dir for configuration files (.) .
        **kwargs - additional keyword arguments are ignored.

    Returns:
    """
    if not worlds:
        log.info(f"Starting event: {event}")
        if event_config := event_op(event=event, command="start", config_dir=config_dir, func=crlw.start):
            log.info(f"External CTF for event is : {event_config['x-event']['ctf-external-url']}")
    else:
        world_op(event=event, worlds=worlds, command="start", config_dir=config_dir, func=crlw.start)
    return True


def cmd_stop(event: str, worlds: List[str], config_dir: str, **kwargs: int) -> bool:
    """
    Performs the stop operation on one or more worlds if they exist.
    If no world is specified, the entire event is stopped.

    Parameters:
        event:
        worlds:
        config_dir: The base dir for configuration files (.) .
        **kwargs - additional keyword arguments are ignored.

    Returns:
    """
    if not worlds:
        event_op(event=event, command="stop", config_dir=config_dir, func=crlw.stop)
    else:
        world_op(event=event, worlds=worlds, command="stop", config_dir=config_dir, func=crlw.stop)
    return True


def cmd_delete(event: str, worlds: List[str], config_dir: str, **kwargs: int) -> bool:
    """
    Performs the delete operation on a specified event, or on
    one or more worlds within a specified event.
    If no world is specified, the entire event is deleted.

    Parameters:
        event:
        worlds:
        config_dir: The base dir for configuration files (.) .
        **kwargs: Additional keyword arguments are ignored.

    Returns:
    """
    if not worlds:
        log.info(f"Removing event: {event}")
        event_op(event=event, command="stop", config_dir=config_dir, func=crlw.stop)
        event_path = Path(config_dir) / "Events" / event
        rmtree(event_path)
    else:
        world_op(event=event, worlds=worlds, command="delete", config_dir=config_dir, func=crlw.delete)

    return True


def cmd_blueprint(config_dir: str, **kwargs: int) -> bool:
    """
    Prints the names and relative paths of YAML files containing blueprints.

    Parameters:
        config_dir: The base dir for configuration files (.) .
        **kwargs: Additional keyword arguments are ignored.
    """
    config_dir_path = Path(config_dir)
    paths = config_dir_path.glob("blueprints/**/*.y*ml")
    log.info(f"Blueprints ({config_dir_path / 'blueprints' }):")
    for path in paths:
        log.info(f"- {path}")
    return True


def cmd_stored_events(config_dir: str, **kwargs: int) -> bool:
    """
    Prints the names and relative paths of YAML files containing stored events.

    Parameters:
        config_dir: The base dir for configuration files (.) .
        **kwargs: Additional keyword arguments are ignored.

    Returns:
    """
    config_dir_path = Path(config_dir)
    paths = config_dir_path.glob("stored-events/**/*.y*ml")
    log.info(f"Stored events ({config_dir_path / 'stored-events' }):")
    for path in paths:
        log.info(f"- {path}")
    return True


def cmd_init(config_dir: str, use_traefik: bool = False, use_crld: bool = False, **kwargs: int) -> bool:
    """
    A function that initializes the configuration for CRL.

    Parameters:
        config_dir: The directory path for the configuration.
        use_traefik: Whether to use Traefik.
        use_crld: Whether to use CRLD.
        **kwargs: Additional keyword arguments are ignored.

    Returns:
        None
    """
    config_path = Path(config_dir)
    global_config_dir = config_path / "Events"
    global_config_dir.mkdir(parents=True, exist_ok=True)
    global_config_file = global_config_dir / "docker-compose.yml"
    global_config: Dict[str, Any] = {"x-crl": {}}
    if old_config := read_yaml(global_config_file):
        global_traefik = old_config["x-crl"].get("use-traefik", False)
        global_crld = old_config["x-crl"].get("use-crld", False)
        if (not use_traefik and global_traefik) or (not use_crld and global_crld):
            if not use_traefik and global_traefik:
                log.info(f"Cannot disable traefik once enabled service globally {global_traefik=}")
            if not use_crld and global_crld:
                log.info(f"Cannot disable crld once enabled service globally {global_crld=}")
            return False
        if global_traefik == use_traefik and global_crld == use_crld:
            global_config = old_config.get("x-crl", {})
            log.info(f"Nothing changed {global_config=}")
            return False

    global_config["x-crl"]["use-traefik"] = use_traefik
    global_config["x-crl"]["use-crld"] = use_crld

    if portd_template := read_yaml(Path(str(files("crl.services").joinpath("portd.yml")))):
        portd_template = strip_docker_compose_options(portd_template)
        if crl_image := os.getenv("CRL_IMAGE"):
            portd_template["services"]["portd"]["image"] = crl_image
        global_config = deep_update(global_config, portd_template)
    else:
        log.error("Sorry, portd config need to exist, giving up")
        return False
    if global_config["x-crl"]["use-traefik"]:
        if traefik_template := read_yaml(Path(str(files("crl.services").joinpath("traefik.yml")))):
            traefik_template = strip_docker_compose_options(traefik_template)
            # If the mail should be configurable, remove from template and add here
            # eg. traefik_template["services"]["traefik"]["command"].append
            #     (f"-certificatesresolvers.crl-resolver.acme.email={quoted(mail)}")
            if traefik_image := os.getenv("TRAEFIK_IMAGE"):
                traefik_template["services"]["traefik"]["image"] = traefik_image
            global_config = deep_update(global_config, traefik_template)
    if global_config["x-crl"]["use-crld"]:
        if crld_template := read_yaml(Path(str(files("crl.services").joinpath("crld.yml")))):
            crld_template = strip_docker_compose_options(crld_template)
            crld_template["services"]["crld"].pop("ports", None)
            abs_config_path = str(config_path.resolve())
            crld_template["services"]["crld"]["volumes"] = [
                "/var/run/docker.sock:/var/run/docker.sock",
                "portd-run:/var/run/portd/",
                f"{abs_config_path}:{abs_config_path}",
            ]
            if docker_auth_file := os.getenv("DOCKER_AUTH_FILE"):
                crld_template["services"]["crld"]["volumes"].append(f"{docker_auth_file}:/root/.docker/config.json:ro")
            if crl_image := os.getenv("CRL_IMAGE"):
                crld_template["services"]["crld"]["image"] = crl_image
                crld_template["services"]["crld"]["environment"]["CRL_IMAGE"] = crl_image
            if traefik_image := os.getenv("TRAEFIK_IMAGE"):
                crld_template["services"]["crld"]["environment"]["TRAEFIK_IMAGE"] = traefik_image
            if wg_image := os.getenv("WG_IMAGE"):
                crld_template["services"]["crld"]["environment"]["WG_IMAGE"] = wg_image
            if ctfd_image := os.getenv("CTFD_IMAGE"):
                crld_template["services"]["crld"]["environment"]["CTFD_IMAGE"] = ctfd_image
            crld_template["services"]["crld"]["working_dir"] = abs_config_path
            global_config = deep_update(global_config, crld_template)

    write_yaml(global_config_file, global_config)
    return crlw.start(world=global_config_dir, world_name="crl")


def use_service(event_config: Dict[str, Any], service: str, global_value: bool) -> bool:
    if not global_value:  # if globally disabled then don't care about local config.
        return False
    elif service in event_config:
        return not event_config[service]
    else:
        return True


def list_events(config_dir: str) -> List[str]:
    world_basepath = Path(config_dir) / "Events"
    return [d.name for d in world_basepath.glob("[!.]*") if d.is_dir()]


def list_worlds(config_dir: str, event: str) -> List[str]:
    event_path = Path(config_dir) / "Events" / event
    return [d.name for d in event_path.glob("[!.]*") if d.is_dir()]


def event_op(func: Callable[[Path, str], bool], event: str, command: str, config_dir: str) -> Optional[Dict[str, Any]]:
    """
    Utility function to perform event operations.

    Parameters:
        func: The operation to be performed on each world.
        event: The command line arguments.
        command:
        config_dir: The base dir for configuration files (.) .

    Returns:
        The event config if event was found.
    """
    event_path = Path(config_dir) / "Events" / event
    if event_path.is_dir():
        event_file = event_path / "docker-compose.yml"
        if event_config := read_yaml(event_file):
            log.info(f"Executing {command} on event {event}")
            func(event_path, f"crl-{event}")
            return event_config
        else:
            log.error(f"Could not find {event=}")
    return None


def world_op(func: Callable[[Path, str], bool], event: str, worlds: List[str], command: str, config_dir: str) -> bool:
    """
    Utility function to perform world operations.

    Parameters:
        func: The operation to be performed on each world.
        event: The command line arguments.
        worlds:
        command:
        config_dir: The base dir for configuration files (.) .

    Returns:
    """
    event_path = Path(config_dir) / "Events" / event
    ws = worlds if worlds else list_worlds(config_dir, event)
    if ws:
        log.info(f"Will {command} these worlds in {event}: {','.join(ws)}")
    for w in ws:
        world_path = event_path / w
        if not world_path.is_dir():
            log.info(f"World {world_path.name} does not exist, ignoring")
            continue
        func(world_path, f"crl-{event}-{w}")
    return True


def create_event(
    event: str,
    used_ports: Set[int],
    event_file: Path,
    config_path: Path,
    stored_event_path: Optional[Path] = None,
    external_url: Optional[str] = None,
    blueprint_path: Optional[Path] = None,
    event_name: Optional[str] = None,
) -> None:
    global_traefik = False
    global_crld = False
    if global_config := read_yaml(config_path / "Events" / "docker-compose.yml"):
        global_traefik = global_config["x-crl"].get("use-traefik", False)
        global_crld = global_config["x-crl"].get("use-crld", False)

    # The configuration for the event
    event_config: Dict[str, Any] = {"x-event": {}}
    if stored_event_path and (stored_config := read_yaml(stored_event_path)):
        event_config["x-event"] = stored_config
    x_event = event_config["x-event"]

    if external_url:
        x_event["external-url"] = external_url

    if blueprint_path:
        x_event["blueprint"] = str(blueprint_path.absolute())

    if ctfd_extra_config := x_event.get("ctfd"):
        traefik = use_service(x_event, "disable-traefik", global_traefik)
        tls = True  # TODO: make this configurable from where?
        crld = use_service(x_event, "disable-crld", global_crld)

        # Add ctfd section
        if ctfd_template := read_yaml(Path(str(files("crl.services").joinpath("ctfd.yml")))):
            ctfd = ctfd_template["services"]["ctfd"]
            labels = ctfd["deploy"]["labels"]

            if ctfd_image := os.getenv("CTFD_IMAGE"):
                ctfd["image"] = ctfd_image

            if traefik:
                ctfd.pop("ports", None)
                x_event["ctf-external-url"] = f"http://{event}.{x_event['external-url']}"
                ctfd["environment"]["REVERSE_PROXY"] = quoted(str(True).lower())
                labels["traefik.enable"] = quoted(str(True).lower())
                labels[f"traefik.http.routers.{event}-ctfd.rule"] = quoted(f"Host(`{event}.{x_event['external-url']}`)")
                labels[f"traefik.http.routers.{event}-ctfd.entrypoints"] = quoted("web")
                labels[f"traefik.http.services.{event}-ctfd.loadbalancer.server.port"] = quoted("8000")
                if tls:
                    x_event["ctf-external-url"] = f"https://{event}.{x_event['external-url']}"  # Change to https://
                    labels[f"traefik.http.routers.{event}-ctfd.entrypoints"] = quoted(
                        "websecure"
                    )  # Change from web to websecure
                    labels[f"traefik.http.routers.{event}-ctfd.tls"] = quoted(str(True).lower())  # Enable tls
                    labels[f"traefik.http.routers.{event}-ctfd.tls.certresolver"] = quoted(
                        "crl-resolver"
                    )  # Add  acme resolver

            else:
                port = find_free_port(blacklist=used_ports)
                ctfd["ports"] = [f"{port}:8000"]
                x_event["ctf-external-url"] = f"http://{x_event['external-url']}:{port}"
                ctfd["environment"]["REVERSE_PROXY"] = quoted(str(False).lower())
                labels["traefik.enable"] = quoted(str(False).lower())

            if crld:
                ctfd["environment"]["CRL_ENABLE"] = quoted(str(True).lower())
                # Set some defaults that are OK for crl
                # Can be overridden in the event template but should not be more lenient.
                ctfd["environment"]["REGISTRATION_USERNAME_ALLOWED_REGEX"] = quoted(USER_ALLOWED_REGEX)
                ctfd["environment"]["REGISTRATION_USERNAME_MIN_LENGTH"] = quoted(USER_MIN_LEN)
                ctfd["environment"]["REGISTRATION_USERNAME_MAX_LENGTH"] = quoted(USER_MAX_LEN)
                ctfd["environment"]["REGISTRATION_USERNAME_CASE_SENSITIVE"] = quoted(str(USER_CASE_SENSITIVE).lower())
            else:
                ctfd["environment"]["CRL_ENABLE"] = quoted(str(False).lower())

            x_event["ctf-url"] = f"http://{event}-ctfd:8000"  # We always use the internal address to connect to ctfd
            ctfd["environment"]["INIT_EVENT_NAME"] = quoted(event_name) if event_name else event
            ctfd["environment"]["INIT_EVENT_SHORT_NAME"] = event
            ctfd["environment"]["INIT_ADMIN_TOKEN"] = random_string(10)
            # Read overrides from the template
            ctfd["environment"].update(ctfd_extra_config)
            if "OAUTH_CALLBACK_URL" in ctfd["environment"]:
                ctfd["environment"]["OAUTH_CALLBACK_URL"] = f"{x_event['ctf-external-url']}/redirect"
            ctfd["hostname"] = f"{event}-ctfd"
            if "networks" in ctfd:
                ctfd["networks"]["crl-public"]["aliases"] = [f"{event}-ctfd"]
            event_config = deep_update(event_config, ctfd_template)
            x_event["ctf-token"] = event_config["services"]["ctfd"]["environment"]["INIT_ADMIN_TOKEN"]
    # Cleanup the resulting event configuration
    x_event.pop("ctfd", None)
    x_event.pop("crld", None)
    x_event.pop("traefik", None)

    # Write the event configuration to the event YAML file
    write_yaml(file=event_file, config=event_config)


def main() -> None:
    """
    The main function.

    This function creates command-line arguments using the `create_args` function
    and then calls the function specified by the command-line arguments, passing in
    the arguments themselves. Finally, it exits with the return value of the called
    function.
    """
    parser = build_parser()
    args = parser.parse_args()

    if hasattr(args, "func"):
        logging.basicConfig(format="%(message)s", handlers=[logging.StreamHandler(sys.stdout)])
        logging.getLogger("crl").setLevel("DEBUG" if args.debug else "INFO")
        kwargs = vars(args)
        exit(args.func(**kwargs))
    else:
        parser.print_help()
        exit(1)


def build_parser() -> ArgumentParser:
    """
    Create command-line arguments.
    """
    parser = ArgumentParser(prog="crl", description="Cyber Range Lite")

    general_arguments = ArgumentParser(add_help=False)
    general_arguments.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug printouts",
    )
    general_arguments.add_argument(
        "--config-dir",
        default=".",
        type=validate_filepath_arg,
        help="The base path where the config (blueprints/challenges etc) are stored",
    )

    cmd_subparsers = parser.add_subparsers(dest="command", help="Command help")

    # Create the command parsers
    cmd_parser = {}
    arg_cmds = {
        "create": cmd_create,
        "list": cmd_list,
        "delete": cmd_delete,
        "start": cmd_start,
        "stop": cmd_stop,
    }

    # Common functions
    for cmd, arg_function in arg_cmds.items():
        cmd_parser[cmd] = cmd_subparsers.add_parser(cmd, help=f"{cmd} help", parents=[general_arguments])
        cmd_parser[cmd].set_defaults(func=arg_function)
        cmd_parser[cmd].add_argument(
            "event",
            nargs="?" if cmd == "list" else None,
            type=validate_name,
            help="The particular event (need to be a unique and valid directory name)",
        )
        cmd_parser[cmd].add_argument(
            # "world",
            nargs="*",
            dest="worlds",
            metavar="world",
            type=validate_name,
            help="The name of the world, eg. username (need to be unique and valid directory name)",
        )
    # Blueprint command
    cmd_parser["blueprint"] = cmd_subparsers.add_parser(
        "blueprints", help="List blueprints", parents=[general_arguments]
    )
    cmd_parser["blueprint"].set_defaults(func=cmd_blueprint)

    # Events command
    cmd_parser["events"] = cmd_subparsers.add_parser("events", help="List stored events", parents=[general_arguments])
    cmd_parser["events"].set_defaults(func=cmd_stored_events)

    # Init command
    cmd_parser["init"] = cmd_subparsers.add_parser(
        "init", help="Init system and optionally traefik and crld", parents=[general_arguments]
    )
    cmd_parser["init"].set_defaults(func=cmd_init)
    cmd_parser["init"].add_argument(
        "--use-traefik",
        action="store_true",
        help="Will we use traefik, default false",
    )
    cmd_parser["init"].add_argument(
        "--use-crld",
        action="store_true",
        help="Will we use crld, default false",
    )

    # Create command
    # crl create event --blueprint ...
    create_args = cmd_parser["create"].add_argument_group(
        "Create event/world arguments",
        "These options are required for creating a new event (optional when event exists)",
    )
    create_args.add_argument(
        "--blueprint",
        type=validate_filepath_arg,
        help="Use this as a template for creating the world",
    )
    create_args.add_argument(
        "--external-url",
        help="Address/fqdn users should connect to (for wireguard and jeopardy style)",
    )
    create_args.add_argument(
        "-e",
        "--event",
        dest="stored_event",
        type=validate_filepath_arg,
        help="Use this as a template for creating the event",
    )
    create_args.add_argument(
        "--event-name",
        help="Optional friendly name to use for the event (default eventname)",
    )

    return parser


if __name__ == "__main__":
    main()
