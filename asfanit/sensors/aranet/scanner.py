import asyncio
import enum
import logging
from typing import AsyncGenerator

import click
import yaml
from aranet4 import client as a4client
from bleak.backends import device as bleak_device

from asfanit.sensors.bluetooth import scanner as bt_scanner
from asfanit.sensors.aranet import measurement
from asfanit import utils


class AranetScanner:
    def __init__(self, devices: dict[str, str | None] | None = None):
        """Scan for Aranet devices

        Args:
            devices: If provided, the devices to listen to. The key is the device address, and the
                value is a label to assign to the device. If the label is None, the label is
                automatically detected from device information on receiving a scan for the device.
        """
        addresses = frozenset({k.upper() for k in devices.keys()}) if devices else None
        if devices and addresses:
            if len(devices) != len(addresses):
                raise ValueError("label shared between multiple addresses")
        self._scanner = bt_scanner.BluetoothScanner(
            devices=addresses,
            vendors=frozenset({a4client.Aranet4.MANUFACTURER_ID}),
        )
        self._labels = {k.upper(): v for k, v in (devices or {}).items()}

    async def scan(
        self, timeout_s: float, *, log_discovery: bool = False
    ) -> dict[str, bleak_device.BLEDevice]:
        return await self._scanner.scan(timeout_s=timeout_s, log_discovery=log_discovery)

    async def next(self) -> AsyncGenerator[measurement.Measurement, None]:
        async for scan in self._scanner.next():
            advertisement = a4client.Aranet4Advertisement(scan.device, scan.data)
            if advertisement.readings:
                yield measurement.Measurement(
                    advertisement,
                    self._labels.get(scan.device.address.upper()),
                )

    async def start(self):
        await self._scanner.start()

    async def stop(self):
        await self._scanner.stop()

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, *args, **kwargs):
        del args
        del kwargs
        await self.stop()


async def _scan(scan_timeout_s: float) -> None:
    async with AranetScanner() as s:
        if (count := len(await s.scan(timeout_s=scan_timeout_s, log_discovery=True))) == 0:
            logging.error("No Aranet devices discovered")
            return

    plural = "s" * bool(count)
    logging.info(f"Discovered {count} Aranet device{plural}")


async def _main(
    *,
    scan_timeout_s: float | None,
    devices: dict[str, str],
    num_readings: int | None,
    display_yaml: bool,
):
    if scan_timeout_s is not None:
        await _scan(scan_timeout_s)
        return

    async with AranetScanner(devices=devices) as s:
        count = 0
        async for point in s.next():
            if display_yaml:
                point_dict = point.as_dict()
                for key, value in point_dict.items():
                    if isinstance(value, enum.Enum):
                        point_dict[key] = value.name
                point_yaml = yaml.safe_dump(point_dict, indent=4, default_flow_style=False)
                logging.info(f"\n{point_yaml}")
            else:
                label = point.label * int(point.address != point.label)
                logging.info(f"{label}\n{point}")
            if num_readings is not None and (count := count + 1) >= num_readings:
                break


@click.command(context_settings={"show_default": True})
@click.option(
    "--scan-timeout",
    default=None,
    type=float,
    help="If present, run a scan for this interval and exist",
)
@click.option(
    "--sensor",
    multiple=True,
    type=str,
    help="Listen to a sensor, using the pattern address::label to assign a label to a device. "
    "Can be provided multiple times to listen to multiple sensors",
)
@click.option(
    "--num-readings", default=None, type=int, help="The number of readings to print before exiting"
)
@click.option("--display-yaml", is_flag=True, help="Format sensor readings as yaml when displaying")
def main(
    *,
    scan_timeout: float | None,
    sensor: tuple[str],
    num_readings: int | None,
    display_yaml: bool,
):
    utils.setup_logging()

    devices = dict()
    for s in sensor:
        dev = s.split("::")
        address = ""
        label = ""
        if len(dev) == 1:
            address = dev.pop()
        elif len(dev) == 2:
            address, label = dev
        else:
            raise ValueError(f"invalid sensor specification: {s!r}")

        if not label:
            label = None

        devices[address] = label

    asyncio.run(
        _main(
            scan_timeout_s=scan_timeout,
            devices=devices,
            num_readings=num_readings,
            display_yaml=display_yaml,
        )
    )


if __name__ == "__main__":
    main()
