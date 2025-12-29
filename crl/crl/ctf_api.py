#!/usr/bin/env python3
import argparse
import logging
from pprint import pformat
from typing import Any, Dict, List, Tuple

import requests

log = logging.getLogger(__name__)  # pylint: disable=locally-disabled, invalid-name


# Function to get the challenge ID from its name or ID
def get_chall_id(url: str, token: str, chall_name: str | int) -> int | None:
    """
    Retrieves the challenge ID from the given URL using the provided token and challenge name or ID.

    Args:
        url (str): The URL of the API.
        token (str): The authorization token.
        chall_name (str | int): The name or ID of the challenge.

    Returns:
        int | None: The ID of the challenge if found, otherwise None.
    """
    # Check if the provided challenge name is already an ID
    if isinstance(chall_name, int):
        return chall_name

    # Create a session with the provided token
    session = requests.Session()
    session.headers.update({"Authorization": f"Token {token}"})

    # Send a GET request to the challenges API endpoint to retrieve the list of challenges
    challenges = session.get(f"{url}/api/v1/challenges", headers={"Content-Type": "application/json"}).json()

    # Iterate over the challenges and check if the challenge name matches the provided name
    for chall in challenges["data"]:
        if chall["name"] == chall_name:
            return int(chall["id"])

    # Return None if no match is found
    return None


# Function to get the flag ID from its content and associated challenge ID
def get_flag_id(url: str, token: str, flag: str, chall_id: int) -> int | None:
    """
    Get the ID of a flag based on the provided URL, token, flag, and challenge ID.

    Args:
        url (str): The URL for the API.
        token (str): The authorization token.
        flag (str): The flag to search for.
        chall_id (int): The challenge ID.

    Returns:
        int | None: The ID of the flag if found, None otherwise.

    This function sends a GET request to the API to retrieve a list of flags.
    It then iterates over the flags and checks if the content of the flag
    matches the provided flag and if the challenge ID of the flag matches
    the provided challenge ID. If a match is found, the ID of the flag is
    returned. Otherwise, None is returned.
    """
    # Create a session and update the headers with the authorization token
    session = requests.Session()
    session.headers.update({"Authorization": f"Token {token}"})

    # Send a GET request to retrieve the list of flags
    flags = session.get(f"{url}/api/v1/flags", headers={"Content-Type": "application/json"}).json()

    # Iterate over the flags and check for a match
    for f in flags["data"]:
        if f["content"].startswith(flag) and f["challenge_id"] == chall_id:
            return int(f["id"])

    # Return None if no match is found
    return None


# Function to get the hint IDs associated with a challenge
def get_hint_ids(url: str, token: str, chall_id: int) -> List[int]:
    """
    Retrieves the hint IDs for a specific challenge from the given URL using the provided token.

    Args:
        url (str): The URL to send the request to.
        token (str): The authentication token.
        chall_id (int): The ID of the challenge.

    Returns:
        List[int]: A list of hint IDs for the specified challenge.
    """
    # Create a session with the provided token
    session = requests.Session()
    session.headers.update({"Authorization": f"Token {token}"})

    # Send a GET request to the hints API endpoint to retrieve the hints
    response = session.get(f"{url}/api/v1/hints", headers={"Content-Type": "application/json"})

    # Parse the response JSON
    hints = response.json()

    # Extract the hint IDs for the specified challenge
    hint_ids = [int(h["id"]) for h in hints["data"] if h["challenge_id"] == chall_id]

    return hint_ids


# Function to get the player ID from their name or ID
def get_player_id(url: str, token: str, player_name: str | int) -> int | None:
    """
    Get the player ID based on the player's name or ID by making a request to the specified URL using
    the provided token.

    Args:
        url (str): The URL for the API endpoint.
        token (str): The authentication token.
        player_name (str | int): The name of the player as a string or the player's ID as an integer.

    Returns:
        int | None: The player ID if found, or None if the player is not found.
    """
    # Send a request to the users API endpoint to get the list of players
    session = requests.Session()
    session.headers.update({"Authorization": f"Token {token}"})
    response = session.get(f"{url}/api/v1/users", headers={"Content-Type": "application/json"})

    # Parse the JSON response
    players = response.json()

    # Loop over the players and check if the name or ID matches the provided player name
    for player in players["data"]:
        if player["name"] == player_name or player["id"] == player_name:
            return int(player["id"])

    # If the provided player name is an integer, return it as the player ID
    if isinstance(player_name, int):
        return player_name

    # If the player is not found, return None
    return None


# Function to parse and format data
def parse(foo: str, bar: str) -> str:
    """
    Parse function to format the output string based on the input parameters.

    Args:
        foo (str): The first input parameter.
        bar (str): The second input parameter.

    Returns:
        str: The formatted output string.

    The function checks if the `foo` parameter is equal to "hints". If it is,
    it returns a formatted string containing `foo` and the last element of the
    split `bar` string. Otherwise, it returns a formatted string containing
    `foo` and `bar`.
    """
    # Check if the foo parameter is equal to "hints"
    if foo == "hints":
        # Split the bar string and return a formatted string
        # containing foo and the last element of the split bar string
        return f"{foo},{bar.split()[-1]}"
    # Return a formatted string containing foo and bar
    return f"{foo},{bar}"


# Function to get awards for a specific player
def get_awards(url: str, token: str, player_name: str | int | None = None) -> List[str] | None:
    """
    Retrieve awards data from the given URL using the provided token. Optionally filter the data by player name.

    Args:
        url (str): The URL to retrieve awards data from.
        token (str): The authentication token for accessing the API.
        player_name (str | int | None, optional): The name of the player to filter awards data for. Defaults to None.

    Returns:
        List[str] | None: A list of award details, or None if the player is not found.
    """
    # Get player ID if player_name is specified
    if player_name:
        pid = get_player_id(url, token, player_name)
        # If player is not found, return None
        if not pid:
            log.info(f"[GET AWARDS]: Could not find player: {player_name}.")
            return None

    # Make a request to the awards API
    session = requests.Session()
    session.headers.update({"Authorization": f"Token {token}"})
    awards = session.get(f"{url}/api/v1/awards", headers={"Content-Type": "application/json"}).json()

    # Filter awards data by player ID if player_name is specified
    if player_name:
        return [
            f"{a['date']},{pid},{parse(a['category'],a['description'])},{a['value']}"
            for a in awards["data"]
            if a["user_id"] == pid
        ]
    # Return all awards data if player_name is not specified
    return [f"{a['date']},{a['user_id']},{parse(a['category'],a['description'])},{a['value']}" for a in awards["data"]]


# Function to get submissions for a specific player
def get_submissions(url: str, token: str, player_name: str | int | None = None) -> List[str] | None:
    """
    Retrieve submissions based on the provided URL, token, and optional player name.

    Args:
        url (str): The URL for the submissions.
        token (str): The authentication token.
        player_name (str | int | None, optional): The name of the player (optional).

    Returns:
        List[str] | None: A list of submission details or None if the player is not found.
    """
    # If player name is provided, get the player ID and return None if not found
    if player_name:
        pid = get_player_id(url, token, player_name)
        if not pid:
            log.info(f"[GET SUBMISSIONS]: Could not find player: {player_name}.")
            return None

    # Set up the session with the authentication token
    session = requests.Session()
    session.headers.update({"Authorization": f"Token {token}"})

    # Get the submissions data from the API
    awards = session.get(f"{url}/api/v1/submissions", headers={"Content-Type": "application/json"}).json()

    # If player name is provided, filter the submissions by player ID
    if player_name:
        return [
            f"{a['date']},{pid},{a['type']},{a['challenge']['name']},{a['provided']}"  # Format each submission
            for a in awards["data"]  # Iterate over each submission
            if a["user_id"] == pid  # Check if the submission belongs to the player
        ]

    # If player name is not provided, return all submissions
    return [
        f"{a['date']},{a['user_id']},{a['type']},{a['challenge']['name']},{a['provided']}"  # Format each submission
        for a in awards["data"]  # Iterate over each submission
    ]


# Function to post a flag for a challenge
def post_flag(url: str, token: str, flag: str, challenge: str | int) -> None:
    """
    Posts a flag for a challenge to a CTFd server.

    Args:
        url (str): The URL of the CTFd server.
        token (str): The authentication token.
        flag (str): The flag to be posted.
        challenge (str | int): The ID or name of the challenge.

    This function first tries to retrieve the challenge ID using the get_chall_id
    function. If there is a connection error, it prints a message and returns. If
    the challenge ID is not found, it prints a message and returns. It then creates
    a session, updates the headers with the provided token, and sends a POST request
    to the URL with the flag, data, type, and challenge ID in the JSON payload. If
    DEBUG is True, it prints the JSON response.
    """

    log.debug("[POST FLAG]:")
    log.debug(pformat(f"{challenge=}, {flag=}"))

    # Retrieve the challenge ID
    try:
        cid = get_chall_id(url, token, challenge)
    except (requests.exceptions.ConnectionError, requests.exceptions.MissingSchema) as e:
        # Print error message and return if there is a connection error
        log.info(f"[POST FLAG]: {challenge=} Failed to connect to {url=}")
        log.debug(f"{e=}")
        return

    # Print error message and return if challenge ID is not found
    if not cid:
        log.info(f"[POST FLAG]: Could not find challenge: {challenge}.")
        return

    # Create session, update headers, and send POST request
    session = requests.Session()
    session.headers.update({"Authorization": f"Token {token}"})
    r = session.post(
        f"{url}/api/v1/flags",
        json={"content": flag, "data": "", "type": "static", "challenge": cid},
        headers={"Content-Type": "application/json"},
    )

    log.debug("[POST FLAG]:")
    log.debug(pformat(r.json()))


# Function to delete a flag for a challenge
def delete_flag(url: str, token: str, flag: str, challenge: str | int) -> None:
    """
    Deletes a flag associated with a challenge on the given URL using the provided token.

    Parameters:
        url (str): The URL of the server.
        token (str): The authentication token.
        flag (str): The flag to be deleted.
        challenge (str | int): The challenge ID or name.
    Returns:
        None
    """
    # Get the challenge ID
    try:
        cid = get_chall_id(url, token, challenge)
    except (requests.exceptions.ConnectionError, requests.exceptions.MissingSchema) as e:
        # Print error message if connection to the server fails
        log.info(f"[DELETE FLAG]: Failed to connect to {url}: {e}")
        return

    # If the challenge ID is not found, print an error message and return
    if not cid:
        log.info(f"[DELETE FLAG]: Could not find challenge: {challenge}.")
        return

    # Get the flag ID
    fid = get_flag_id(url, token, flag, cid)

    # If the flag ID is not found, print an error message and return
    if not fid:
        log.info(f"[DELETE FLAG]: Could not find flag: {flag}.")
        return

    # Create a session with the authentication token
    session = requests.Session()
    session.headers.update({"Authorization": f"Token {token}"})

    # Delete the flag
    r = session.delete(f"{url}/api/v1/flags/{fid}", headers={"Content-Type": "application/json"})

    log.debug("[DELETE FLAG]:")
    log.debug(pformat(r.json()))


# Function to patch a flag for a challenge
def patch_flag(
    url: str,  # URL of the CTFd instance
    token: str,  # Authentication token
    challenge: str | int,  # ID or name of the challenge
    new_flag: str,  # New flag content
    old_flag: str,  # Old flag content
) -> None:
    """
    Patch a flag for a given challenge on the specified URL using the provided token.
    The function takes the URL, token, challenge ID, new flag content, and old flag content as parameters,
    and returns None.
    """
    # Get the ID of the challenge
    try:
        cid = get_chall_id(url, token, challenge)
    except requests.exceptions.ConnectionError as e:
        log.info(f"[PATCH FLAG]: Failed to connect to {url}: {e}")
        return

    # If the challenge ID is not found, print an error message and return
    if not cid:
        log.info(f"[PATCH FLAG]: Could not find challenge: {challenge}.")
        return

    # Get the ID of the old flag
    ofid = get_flag_id(url, token, old_flag, cid)

    # If the old flag ID is not found, print an error message and return
    if not ofid:
        log.info(f"[PATCH FLAG]: Could not find flag: {old_flag}.")
        return

    # Create a session with the authentication token
    session = requests.Session()
    session.headers.update({"Authorization": f"Token {token}"})

    # Patch the old flag with the new flag content
    r = session.patch(
        f"{url}/api/v1/flags/{ofid}",
        json={"content": new_flag, "data": "", "type": "static", "challenge": cid},
        headers={"Content-Type": "application/json"},
    )

    log.debug("[PATCH FLAG]:")
    log.debug(pformat(r.json()))


# Function to post a challenge
def post_challenge(
    url: str,  # URL of the CTFd instance
    token: str,  # Authentication token
    challenge: str | int,  # ID or name of the challenge
    description: str,  # Description of the challenge
    category: str | None = None,  # Category of the challenge (optional)
    score: int | None = None,  # Score awarded for solving the challenge (optional)
    conn_info: str | None = None,  # Connection information for the challenge (optional)
    prereq: int | str | None = None,  # ID or name of the prerequisite challenge (optional)
) -> bool:
    """
    Posts a challenge to a given URL using the provided token.

    Args:
        url (str): The URL of the CTFd instance.
        token (str): The authentication token.
        challenge (str | int): The ID or name of the challenge.
        description (str): The description of the challenge.
        category (str, optional): The category of the challenge. Defaults to None.
        score (int, optional): The score awarded for solving the challenge. Defaults to None.
        conn_info (str, optional): The connection information for the challenge. Defaults to None.
        prereq (int | str, optional): The ID or name of the prerequisite challenge. Defaults to None.
    """
    data: Dict[str, Any] = {
        "name": challenge,
        "category": category,
        "description": description,
        "connection_info": conn_info,
        "value": score,
        "state": "visible",
        "type": "standard",
        "requirements": {},
    }

    log.debug("[POST CHALLENGE]:")
    log.debug(pformat(data))

    # Retrieve the challenge ID
    try:
        cid = get_chall_id(url, token, challenge)
    except (requests.exceptions.ConnectionError, requests.exceptions.MissingSchema) as e:
        # If there's a connection error, print the error message and return
        log.error(f"[POST CHALLENGE]: {challenge=} Failed to connect to {url=}")
        log.debug(f"{e=}")
        return False

    # If the challenge ID is already found, print a message and return
    if cid:
        log.debug(f"[POST CHALLENGE]: Challenge {challenge} already exists.")
        return False

    # Retrieve the prerequisite challenge ID (if provided)
    preq = [get_chall_id(url, token, prereq)] if prereq else []
    data["requirements"] = {"prerequisites": preq}
    # Create a session with the authorization token
    session = requests.Session()
    session.headers.update({"Authorization": f"Token {token}"})

    # Send the POST request with the challenge details
    r = session.post(
        f"{url}/api/v1/challenges",
        json=data,
        headers={"Content-Type": "application/json"},
    )

    log.info(f"[POST CHALLENGE]: Challenge {challenge} posted.")
    log.debug("[POST CHALLENGE]:")
    log.debug(pformat(r.json()))

    return True


# Function to post a hint for a challenge
def post_hint(url: str, token: str, challenge: str | int, content: str, cost: int, prereqs: List[int]) -> None | int:
    """
    Posts a hint for a challenge.

    Args:
        url (str): The URL of the challenge.
        token (str): The authentication token.
        challenge (str | int): The challenge ID or name.
        content (str): The content of the hint.
        cost (int): The cost of the hint.
        prereqs (List[int]): The list of prerequisite hints.
    """

    # Get the challenge ID
    try:
        cid = get_chall_id(url, token, challenge)
    except requests.exceptions.ConnectionError as e:
        log.info(f"[POST HINT]: Failed to connect to {url}: {e}")
        return None

    # If the challenge ID is not found, print a message and return
    if not cid:
        log.info(f"[POST HINT]: Could not find challenge: {challenge}.")
        return None

    # Get the IDs of the prerequisite hints
    hints = get_hint_ids(url, token, cid) if len(prereqs) > 0 else []

    # Create a session with the authentication token
    session = requests.Session()
    session.headers.update({"Authorization": f"Token {token}"})

    # Send a POST request to the API endpoint to create the hint
    r = session.post(
        f"{url}/api/v1/hints",
        json={
            "challenge_id": cid,
            "content": content,
            "cost": cost,
            "requirements": {"prerequisites": [i for i in prereqs if i in hints]},
        },
        headers={"Content-Type": "application/json"},
    )

    hint_id = int(r.json().get("data", {}).get("id"))
    log.info(f"[POST HINT]: Hint (#{hint_id}) for {challenge} posted.")
    log.debug("[POST HINT]:")
    log.debug(pformat(r.json()))
    return hint_id


# Function to get a list of player names
def get_players(url: str, token: str) -> List[str]:
    """
    Retrieves a list of players' names from the given URL using the provided token.

    Args:
        url (str): The URL to fetch the players' names from.
        token (str): The authorization token for accessing the URL.

    Returns:
        List[str]: A list of players' names retrieved from the URL.
    """
    # Create a session with the provided authorization token
    session = requests.Session()
    session.headers.update({"Authorization": f"Token {token}"})

    # Fetch the list of players from the specified URL
    # The URL should be in the format: "{url}/api/v1/users"
    players = session.get(f"{url}/api/v1/users", headers={"Content-Type": "application/json"}).json()

    # Extract the name of each player from the fetched data and return the list of names
    return [p["name"] for p in players["data"]]


# Function to post a new player
def post_player(
    url: str,  # The URL to post the player to.
    token: str,  # The token for authorization.
    name: str,  # The name of the player.
    email: str,  # The email of the player.
    password: str,  # The password of the player.
    registration_code: str,  # The registration code of the player.
) -> None:
    """
    Post a player to a specified URL using the provided token, name, email, password, and registration code.

    Args:
        url (str): The URL to post the player to.
        token (str): The token for authorization.
        name (str): The name of the player.
        email (str): The email of the player.
        password (str): The password of the player.
        registration_code (str): The registration code of the player.

    Returns:
        None
    """
    # Create a new session and set the authorization token.
    session = requests.Session()
    session.headers.update({"Authorization": f"Token {token}"})

    # Send a POST request to the specified URL with the player's information.
    r = session.post(
        f"{url}/api/v1/users",  # The URL to post the player to.
        json={
            "name": name,  # The name of the player.
            "email": email,  # The email of the player.
            "password": password,  # The password of the player.
            "registration_code": registration_code,  # The registration code of the player.
        },
        headers={"Content-Type": "application/json"},
    )

    log.debug("[POST PLAYER]:")  # Print a header indicating the start of the response.
    log.debug(pformat(r.json()))  # Pretty print the response.


# Function to post an attempt for a challenge
def post_attempt(url: str, token: str, challenge: str | int, flag: str) -> None:
    """
    Posts an attempt to a challenge.

    Args:
        url (str): The URL of the challenge.
        token (str): The authorization token.
        challenge (str | int): The ID or name of the challenge.
        flag (str): The flag to be submitted.

    Returns:
        None. Prints the message from the server's response.
    """
    # Retrieve the challenge ID
    try:
        cid = get_chall_id(url, token, challenge)
    except requests.exceptions.ConnectionError as e:
        # If there's a connection error, print the error message and return
        log.info(f"[POST ATTEMPT]: Failed to connect to {url}: {e}")
        return
    if not cid:
        # If the challenge ID is not found, print the error message and return
        log.info(f"[POST ATTEMPT]: Could not find challenge: {challenge}.")
        return

    # Create a session with the authorization token
    session = requests.Session()
    session.headers.update({"Authorization": f"Token {token}"})

    # Send the POST request with the challenge ID and flag
    r = session.post(
        f"{url}/api/v1/challenges/attempt",
        json={"challenge_id": cid, "submission": flag},
        headers={"Content-Type": "application/json"},
    )

    log.debug(pformat(r.json()["data"]["message"]))


# Function to get the scoreboard
def get_scoreboard(url: str, token: str) -> List[Tuple[int, str, int]]:
    """
    Retrieve the scoreboard data from the specified URL using the provided authentication token.

    Args:
        url (str): The URL to retrieve the scoreboard data from.
        token (str): The authentication token to access the scoreboard data.

    Returns:
        List[Tuple[int, str, int]]: A list of tuples containing the account ID (int), name (str), and score (int)
        for each entry in the scoreboard data.

    Raises:
        requests.exceptions.RequestException: If there is an error with the request.
    """
    # Create a session and set the authorization header
    session = requests.Session()
    session.headers.update({"Authorization": f"Token {token}"})

    # Send a GET request to retrieve the scoreboard data
    try:
        response = session.get(f"{url}/api/v1/scoreboard", headers={"Content-Type": "application/json"})
        response.raise_for_status()  # Raise an exception for any HTTP errors
    except requests.exceptions.RequestException as e:
        raise requests.exceptions.RequestException(f"Error retrieving scoreboard data: {e}")

    # Parse the JSON response and extract the scoreboard data
    scoreboard = response.json()

    # Extract the account ID, name, and score for each entry in the scoreboard data
    return [(int(row["account_id"]), row["name"], int(row["score"])) for row in scoreboard["data"]]


# Function to post a file for a challenge
def post_file(url: str, token: str, challenge: str | int, fname: str) -> None:
    """
    Posts a file to a specified URL with authentication token, challenge ID, and file name.

    Args:
        url (str): The URL to post the file to.
        token (str): The authentication token for the request.
        challenge (str | int): The challenge ID or name to post the file for.
        fname (str): The name of the file to be posted.
    """

    log.debug("[POST FILE]")
    log.debug(pformat(f"{challenge=}, {fname=}"))

    # Retrieve the challenge ID
    try:
        cid = get_chall_id(url, token, challenge)
    except (requests.exceptions.ConnectionError, requests.exceptions.MissingSchema) as e:
        # Print error message if failed to connect
        log.info(f"[POST FILE]: {challenge=} Failed to connect to {url=}")
        log.debug(f"{e=}")
        return
    # Check if challenge ID was found
    if not cid:
        # Print error message if challenge was not found
        log.info(f"[POST FILE]: Could not find challenge: {challenge}.")
        return
    # Create a session and set the authorization header
    session = requests.Session()
    session.headers.update({"Authorization": f"Token {token}"})
    # Send the POST request to post the file
    r = session.post(
        f"{url}/api/v1/files",
        files={"file": open(fname, mode="rb")},  # Open the file in binary mode
        data={"challenge_id": cid, "type": "challenge"},  # Set the challenge ID and type in the data
    )
    log.debug(pformat(r.json()))


# Main function
def main() -> None:
    """
    Main function that parses command line arguments and performs the corresponding action.

    This function parses the command line arguments using the `argparse` module.
    It expects the following arguments:
        - `--url` or `-d`: The URL of the CTFd instance. Default is "https://dvad25.kauotic.se".
        - `--challenge` or `-c`: The name of the challenge. Default is an empty string.
        - `--flag` or `-f`: The flag to post or patch.
        - `--old` or `-o`: The old flag to patch. Default is an empty string.
        - `--token` or `-t`: The admin API access token.
        - `--post`: If present, the function will post a flag.
        - `--delete`: If present, the function will delete a flag.
        - `--patch`: If present, the function will patch a flag.

    If no valid action is provided, the function will exit with the message "[MAIN]: No valid action."
    """

    # Create the argument parser
    parser = argparse.ArgumentParser()

    # Add the arguments to the parser
    parser.add_argument("--url", "-d", default="https://dvad25.kauotic.se", help="CTFd URL")
    parser.add_argument("--challenge", "-c", default="", help="Challenge name")
    parser.add_argument("--flag", "-f", help="Flag to post")
    parser.add_argument("--old", "-o", default="", help="Old flag to patch")
    parser.add_argument("--token", "-t", help="Admin API access token")
    parser.add_argument("--post", action="store_true", help="Post a flag")
    parser.add_argument("--delete", action="store_true", help="Delete a flag")
    parser.add_argument("--patch", action="store_true", help="Patch a flag")

    # Parse the command line arguments
    args = parser.parse_args()

    # Perform the corresponding action based on the provided arguments
    if args.post:
        post_flag(args.url, args.token, args.flag, args.challenge)
    elif args.delete:
        delete_flag(args.url, args.token, args.flag, args.challenge)
    elif args.patch:
        patch_flag(args.url, args.token, args.challenge, args.flag, args.old)
    else:
        exit("[MAIN]: No valid action.")


# Entry point of the script
if __name__ == "__main__":
    main()
