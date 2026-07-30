import logging

import coloredlogs


def setup_logging() -> None:
    coloredlogs.install(
        level=logging.getLevelName(logging.INFO), fmt="%(asctime)s %(levelname)s %(message)s"
    )
