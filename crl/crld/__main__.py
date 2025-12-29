import os
import sys
from argparse import ArgumentParser, Namespace

from pathvalidate.argparse import validate_filepath_arg

from crld import crld


def create_args() -> Namespace:
    parser = ArgumentParser(prog="crld", description="Cyber Range Lite Daemon")

    parser.add_argument(
        "--listen-addr",
        default="0.0.0.0",
        type=str,
        help="Default listening address",
    )

    parser.add_argument(
        "--port",
        default=5000,
        type=int,
        help="Default listening port",
    )

    parser.add_argument(
        "--config-dir",
        default=".",
        type=validate_filepath_arg,
        help="The base path where the config (blueprints/stored-events/events) are stored",
    )

    return parser.parse_args()


def main() -> None:
    args = create_args()
    crld.main(
        listen_addr=args.listen_addr,
        port=args.port,
        configdir=args.config_dir,
        log_level=os.environ.get("CRLD_LOG_LEVEL", "INFO"),
    )
    sys.exit(1)


if __name__ == "__main__":
    main()
