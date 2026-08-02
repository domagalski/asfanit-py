import asyncio
import enum
import pathlib
import time

import click
import yaml

from asfanit import utils
from asfanit.recorders import influx
from asfanit.sensors.aranet import scanner
from asfanit.sensors.aranet import measurement

DATABASE = "aranet"
RETENTION = "30d"

_TAG_KEYS = frozenset({"address", "label", "model", "name", "type"})


class AranetRecorder:
    def __init__(self, client: influx.InfluxClient, scanner: scanner.AranetScanner):
        self._client = client
        self._scanner = scanner

    @staticmethod
    def make_influx_point(
        sensor_reading: measurement.Measurement, timestamp_s: float
    ) -> influx.InfluxPoint:
        measurement_name = sensor_reading.reading.type.name.lower()
        tags = dict()
        fields = dict()
        for key, value in sensor_reading.as_dict().items():
            if key in _TAG_KEYS:
                tags[key] = value.name if isinstance(value, enum.Enum) else str(value)
            else:
                if isinstance(value, enum.Enum):
                    fields[f"{key}_enum_name"] = value.name
                    fields[f"{key}_enum_value"] = value.value
                else:
                    fields[key] = value
        return influx.InfluxPoint(
            measurement=measurement_name,
            tags=tags,
            fields=fields,
            timestamp=timestamp_s,
        )

    async def _wait_for_database(self) -> None:
        while not self._client.init_database():
            await asyncio.sleep(1)

    async def _record_measurements(self) -> None:
        async for point in self._scanner.next():
            self._client.write_one_point(self.make_influx_point(point, time.time()))

    async def run_forever(self) -> None:
        await self._wait_for_database()
        async with self._scanner:
            await self._record_measurements()


def _load_config(config_path: pathlib.Path) -> dict[str, str | None]:
    with config_path.open() as f:
        config = yaml.safe_load(f)

    if not (device_list := config.get("devices", [])):
        raise ValueError("no devices found")

    labels = set()
    devices = dict()
    for device in device_list:
        if not (address := device.get("address")):
            raise ValueError("device must contain address")

        address = address.upper()
        if label := device.get("label"):
            if label in labels:
                raise ValueError(f"label repeated: {label}")
            labels.add(label)

        if address in devices:
            raise ValueError(f"address repeated: {label}")
        devices[address] = label

    return devices


@click.command(context_settings={"show_default": True})
@click.option(
    "--scan-config",
    required=True,
    type=click.Path(exists=True),
    help="IP address of the sensor",
)
@influx.cli_builder(influx_database=DATABASE, influx_retention=RETENTION)
def main(influx_options: influx.InfluxOptions, *, scan_config: str):
    utils.setup_logging()
    client = influx.InfluxClient(influx_options)
    sensor = scanner.AranetScanner(devices=_load_config(pathlib.Path(scan_config)))
    recorder = AranetRecorder(client, sensor)
    asyncio.run(recorder.run_forever())


if __name__ == "__main__":
    main()

if __name__ == "__main__":
    main()
