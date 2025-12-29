import json
import logging
import random
import re
import string
import subprocess
from pathlib import Path
from time import sleep
from typing import Any, Dict, Set

import httpx
import yaml

from crl.config import USER_ALLOWED_REGEX, USER_CASE_SENSITIVE, USER_MAX_LEN, USER_MIN_LEN

log = logging.getLogger(__name__)  # pylint: disable=locally-disabled, invalid-name


class quoted(str):
    pass


def quoted_presenter(dumper: yaml.Dumper, data: Any) -> yaml.ScalarNode:
    """
    A function to represent a scalar with single quotes.
    """
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="'")


yaml.add_representer(quoted, quoted_presenter)


class Dumper(yaml.Dumper):
    def increase_indent(self, flow=False, *args, **kwargs):  # type: ignore # noqa
        """
        Increase the indentation level of the YAML document.

        Args:
            flow (bool, optional): Whether to use flow style for the indentation. Defaults to False.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.
        Returns:
            None
        """
        return super().increase_indent(flow=flow, indentless=False)


def get_services(name: str, inspect_service: bool = False) -> Dict[str, Any]:
    """
    Gets the status information for all services in the stack
    Args:
        name (str): The world( stack) name
        get_task (bool): Retrive information on running tasks(containers), slow
    Returns:
        Dict[str, Any]: information on all running services or empty Dict
    """
    command = ["docker", "stack", "ps", "--format=json", "--filter", "desired-state=running", name]
    services = {}
    try:
        # Run the command
        result = subprocess.run(command, capture_output=True, text=True, check=True)

        # Loop over each line in the output
        for line in result.stdout.splitlines():
            try:
                # Parse each line as JSON
                service = json.loads(line)
                servicename = service["Name"].removeprefix(f"{name}_").rsplit(".", 1)[0]
                service["up"] = (
                    not service["Error"]
                    and service["DesiredState"] == "Running"
                    and service["CurrentState"].startswith("Running")
                )
                if inspect_service:
                    if info := get_inspect_info(service["ID"]):
                        if "Hostname" in info["Spec"]["ContainerSpec"]:
                            service["hostname"] = info["Spec"]["ContainerSpec"]["Hostname"]
                        service["nets"] = {}
                        service["ServiceID"] = info["ServiceID"]
                        for net in info["NetworksAttachments"]:
                            netname = net["Network"]["Spec"]["Name"]
                            addr = net["Addresses"]
                            short_name = netname.removeprefix(f"{name}_")
                            service["nets"][short_name] = (
                                addr[0].split("/")[0] if len(addr) == 1 else addr.split("/")[0]
                            )
                services[servicename] = service
            except json.JSONDecodeError as e:
                print(f"Failed to parse line as JSON: {line}, {e}")
                return {}

    except subprocess.CalledProcessError as e:
        print(f"Command failed with error: {e}")
        return {}

    return services


def get_service_vips(id: str) -> Dict[str, Any]:
    service = get_inspect_info(id)
    world_name = service.get("Spec", {}).get("Labels", {}).get("com.docker.stack.namespace", "")
    vips = {}
    for vip in service.get("Endpoint", {}).get("VirtualIPs", {}):
        if not vip.get("NetworkID") or not vip.get("Addr"):
            continue
        full_name = get_inspect_info(vip["NetworkID"])["Name"]
        if world_name:
            network_name = full_name.removeprefix(f"{world_name}_")
        else:
            network_name = full_name
        vips[network_name] = vip["Addr"].split("/")[0]
    return vips


def get_endpoint_mode(service_definition: Dict[str, Any]) -> str:
    """
    Takes a service defnition as specified in a docker compose file
    and return what the endpoint_mode is.
    """
    # By default the endpoint_mode is VirtualIP (vip)
    if "deploy" not in service_definition:
        return "vip"

    if "endpoint_mode" not in service_definition["deploy"]:
        return "vip"

    return str(service_definition["deploy"]["endpoint_mode"])


def get_inspect_info(id: str) -> Dict[str, Any]:
    """
    Gets the inspect status information for a specific entity in docker swarm
    Args:
        id (str): The id or name of the service/task
    Returns:
        Dict[str, Any]: Service/Task information or empty Dict
    """
    command = ["docker", "inspect", "--format=json", id]
    info = {}
    try:
        # Run the command
        result = subprocess.run(command, capture_output=True, text=True, check=True)

        # Loop over each line in the output
        lines = result.stdout.splitlines()
        if len(lines) > 0:
            try:
                # Parse first line as JSON
                line_json = json.loads(lines[0])
                if len(line_json) > 0:
                    info = line_json[0]
            except json.JSONDecodeError as e:
                print(f"Failed to parse line as JSON: {lines[0]}, {e}")
                return {}
        return info
    except subprocess.CalledProcessError as e:
        print(f"Command failed with error: {e}")
        return {}

    except subprocess.CalledProcessError as e:
        print(f"Command failed with error: {e}")
        return {}


def validate_name(name: str) -> str:
    """
    Checks if the string contains only lowercase letters, numbers and '-'.
    throw an error if name contain invalid charcters or are above 32 characters
    """
    allowed_chars = re.compile(USER_ALLOWED_REGEX)
    if not allowed_chars.match(name) or len(name) > USER_MAX_LEN or len(name) < USER_MIN_LEN:
        raise ValueError(f"{name} not betweeen {USER_MIN_LEN} and {USER_MAX_LEN} or contains illegal characters")
    return name if USER_CASE_SENSITIVE else name.lower()


def check_url(url: str) -> bool:
    """
    Check the URL connectivity by attempting to connect to it for 60 seconds.

    Args:
        url (str): The URL to check the connectivity.

    Returns:
        bool: True if the URL is reachable, False otherwise.
    """
    log.info(f"Waiting for {url} to be available")
    for x in range(60):
        try:
            httpx.get(url, timeout=1)
            log.info(f"Done, {url} took {x} seconds to connect")
            return True
        except Exception:
            sleep(1)

    log.error(f"Gave up on {url}")
    return False


def strip_docker_compose_options(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove invalid and empty options from the "services" section of a Docker Compose configuration.

    Args:
        config (Dict[str, Dict[str, Dict[str, str]]]): The Docker Compose configuration as a dictionary.

    Returns:
        Dict[str, Any]: The modified Docker Compose configuration without the "build" and "include" options.

    Note:
        - This function modifies the input dictionary in-place.
        - The "services" section of the configuration is expected to be a dictionary of service names and their options.
        - Invalid keys can be added to the code by uncommenting the TODO comment and providing additional keys.
    """
    for name in list(config.get("services", {})):
        service = config["services"][name]
        service.pop("build", None)
        service.pop("include", None)
        service.pop("env_file", None)
        service.pop("restart", None)
        service.pop("depends_on", None)
        service.pop("links", None)
        # TODO Add more invalid keys here
        # Delete all empty keys
        for k in list(service):
            if not service[k]:
                service.pop(k, None)
        # Delete all empty services
        if not service:
            config["services"].pop(name, None)

    return config


def deep_update(destination: Dict[str, Any], u: Dict[str, Any]) -> Dict[str, Any]:
    """
    A recursive function that updates a dictionary with the values from another dictionary.

    Args:
    - destination: A dictionary to be updated with values from u.
    - u: A dictionary with values to update destination.

    Returns:
    - A dictionary with updated values.
    """
    for key, val in u.items():
        if isinstance(val, dict):
            destination[key] = deep_update(destination.get(key, {}), val) if val else {}
        elif isinstance(val, list):
            destination[key] = list(set((destination.get(key, []) + val))) if val else []  # remove duplicates
        else:
            destination[key] = u[key]
    return destination


def read_yaml(file: Path) -> Dict[str, Any] | None:
    """
    Read YAML file and parse its content into a Python dictionary.

    Args:
        file (Path): Path to the YAML file.

    Returns:
        Dict[str, Any] | None: Parsed YAML content as a dictionary or None if file doesn't exist or cannot be parsed.
    """
    if not file.is_file():
        log.debug(f"{file=} does not exist")
        return None
    # Basic verification, is it proper yaml
    try:
        with file.open() as ymlfile:
            return dict(yaml.load(ymlfile, Loader=yaml.SafeLoader))
    except Exception as e:
        log.error(f"Failed to open {file}, {e}")
        return None


def write_yaml(file: Path, config: Dict[str, Any]) -> None:
    """
    Write Python dictionary to a YAML file.

    Args:
        file (Path): Path to the YAML file.
        config (Dict[str, Any]): Dictionary to be written to the YAML file.
    """
    log.debug(f"Will dump this {config=}")
    with file.open(mode="w") as newconf:
        yaml.dump(config, newconf, default_flow_style=False, sort_keys=False, Dumper=Dumper)


def random_string(length: int) -> str:
    """
    Generate a random string of specified length.

    Args:
        length (int): Length of the random string to generate.

    Returns:
        str: Random string of specified length.
    """
    source = string.ascii_letters + string.digits
    result_str = "".join((random.choice(source) for i in range(length)))
    return result_str


def find_free_port(blacklist: Set[int] = set()) -> int:
    """
    Find a free port on the local machine.

    Args:
        blacklist (Set[int], optional): Set of ports to exclude from consideration.

    Returns:
        int: A free port number.
    """
    unix_socket_path = "/var/run/portd/portd.sock"

    client = httpx.Client(transport=httpx.HTTPTransport(uds=unix_socket_path))
    r = client.get("http://portd/", params={"blacklist": list(blacklist)})
    try:
        port = int(r.text)
    except Exception as e:
        log.error(f"Could not convert port to number: {r.text}")
        raise Exception(f"Could not convert port to number: {r.text}, {e}")
    return port


def read_random_line(file_path: Path) -> str:
    with open(file_path, "r") as file:
        lines = file.readlines()
        return str(random.choice(lines)).strip()
