import click as click

from asfanit import utils
from asfanit.recorders.purpleair import lan
from asfanit.recorders.purpleair import web


@click.group()
def cli():
    utils.setup_logging()


cli.add_command(lan.main, name="lan")
cli.add_command(web.main, name="web")

if __name__ == "__main__":
    cli()
