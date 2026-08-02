import click

from asfanit import utils
from asfanit.sensors import aranet
from asfanit.sensors import bluetooth
from asfanit.sensors import purpleair


@click.group()
def cli():
    utils.setup_logging()


cli.add_command(aranet.cli, name="aranet")
cli.add_command(bluetooth.cli, name="bluetooth")
cli.add_command(purpleair.cli, name="purpleair")

if __name__ == "__main__":
    cli()
