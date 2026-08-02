import click

from asfanit import utils
from asfanit.recorders import aranet
from asfanit.recorders import purpleair


@click.group()
def cli():
    utils.setup_logging()


cli.add_command(aranet.cli, name="aranet")
cli.add_command(purpleair.cli, name="purpleair")

if __name__ == "__main__":
    cli()
