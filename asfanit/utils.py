import logging

import click
import coloredlogs


class _ClickIntParamType(click.ParamType):
    name = "int"

    def convert(self, value, param, ctx):
        if isinstance(value, int):
            return value
        try:
            return int(value, 0)
        except ValueError:
            self.fail(
                f"{value!r} is not a valid integer (decimal, 0x hex, 0o octal, or 0b binary)",
                param,
                ctx,
            )


CLICK_INT = _ClickIntParamType()


def setup_logging() -> None:
    coloredlogs.install(
        level=logging.getLevelName(logging.INFO), fmt="%(asctime)s %(levelname)s %(message)s"
    )
