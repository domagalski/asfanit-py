import click

from asfanit import utils
from asfanit.sensors import purpleair


@click.group()
def cli():
    utils.setup_logging()


cli.add_command(purpleair.cli, name="purpleair")

if __name__ == "__main__":
    cli()
