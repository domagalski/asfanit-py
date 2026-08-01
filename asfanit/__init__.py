import click

from asfanit import utils
from asfanit import recorders
from asfanit import sensors


@click.group()
def cli():
    utils.setup_logging()


cli.add_command(recorders.cli, name="recorder")
cli.add_command(sensors.cli, name="sensor")

if __name__ == "__main__":
    cli()
