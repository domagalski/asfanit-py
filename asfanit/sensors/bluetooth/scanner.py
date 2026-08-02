import asyncio
import logging
import re
from typing import AsyncGenerator

import click

import bleak
from bleak.backends import device as bleak_device

from asfanit import utils
from asfanit.sensors.bluetooth import packet


class ScanError(Exception):
    pass


class BluetoothScanner:
    def __init__(
        self,
        *,
        devices: frozenset[str] | None = None,
        vendors: frozenset[int] | None = None,
        require_name: bool = False,
        regex_patterns: frozenset[str] | None = None,
    ):
        """Scan for bluetooth devices.

        The arguments are filters to narrow down devices to listen to.
        for yielding bluetooth advertisements. If multiple arguments
        are present, this creates multiple filters that all must be
        satisfied for the scanner to yield an advertisement.

        Args:
            devices: Only listen to devices with these addresses.
            vendors: Only listen for devices from these vendors.
            require_name: Only listen for devices advertising with a name.
            regex_patterns: Only listen for devices where the name matches these patterns.
        """
        self._started = False
        self._scanner = bleak.BleakScanner()
        self._devices = None
        if devices:
            self._devices = frozenset({d.upper() for d in devices})
        self._vendors = vendors
        self._regex_patterns = None
        self._require_name = require_name
        if regex_patterns:
            self._require_name = True
            self._regex_patterns = list()
            for pattern in regex_patterns:
                self._regex_patterns.append(re.compile(pattern))

    def _filter_allow(self, advertisement: packet.BluetoothAdvertisement) -> bool:
        if self._require_name:
            if not advertisement.device.name:
                return False

        if self._devices:
            if advertisement.device.address not in self._devices:
                return False

        if self._vendors:
            vendor_found = False
            for v in self._vendors:
                if advertisement.is_vendor(v):
                    vendor_found = True
                    break
            if not vendor_found:
                return False

        if self._regex_patterns:
            assert advertisement.device.name
            match_found = False
            for pattern in self._regex_patterns:
                if re.match(pattern, advertisement.device.name):
                    match_found = True
                    break
            if not match_found:
                return False

        return True

    async def next(self) -> AsyncGenerator[packet.BluetoothAdvertisement, None]:
        """Get the next bluetooth advertisement"""
        if not self._started:
            raise ScanError("bluetooth scanner not started")

        async for device, data in self._scanner.advertisement_data():
            advertisement = packet.BluetoothAdvertisement(device, data)
            if self._filter_allow(advertisement):
                yield packet.BluetoothAdvertisement(device, data)

    async def scan(
        self, timeout_s: float, *, log_discovery: bool = False
    ) -> dict[str, bleak_device.BLEDevice]:
        """Scan for bluetooth advertisements.

        Args:
            timeout_s: How long to scan for
            log_discovery: log when new devices are found
        """
        if not self._started:
            raise ScanError("bluetooth scanner not started")

        devices = dict()
        try:
            async with asyncio.timeout(timeout_s):
                async for advertisement in self.next():
                    if advertisement.device.address in devices:
                        continue
                    devices[advertisement.device.address] = advertisement.device
                    if log_discovery:
                        logging.info(f"Discovered device: {advertisement.device}")
        except TimeoutError:
            pass

        return devices

    async def start(self):
        await self._scanner.start()
        self._started = True

    async def stop(self):
        self._started = False
        await self._scanner.stop()

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, *args, **kwargs):
        del args
        del kwargs
        await self.stop()


async def _main(
    timeout_s: float,
    devices: frozenset[str] | None = None,
    vendors: frozenset[int] | None = None,
    require_name: bool = False,
    regex_patterns: frozenset[str] | None = None,
):
    async with BluetoothScanner(
        devices=devices,
        vendors=vendors,
        require_name=require_name,
        regex_patterns=regex_patterns,
    ) as s:
        logging.info("Scanning for devices...")
        if (count := len(await s.scan(timeout_s=timeout_s, log_discovery=True))) == 0:
            logging.error("No devices discovered")
            return

        plural = "s" * bool(count)
        logging.info(f"Discovered {count} device{plural}")


@click.command(context_settings={"show_default": True})
@click.option("--scan-timeout", required=True, type=float, help="How many seconds to scan for")
@click.option(
    "--device-address",
    multiple=True,
    type=str,
    help="Device address to scan for. Specify multiple to search for multiple devices",
)
@click.option(
    "--vendor",
    multiple=True,
    type=utils.CLICK_INT,
    help="Vendor company ID to scan for. Specify multiple to search for multiple vendors",
)
@click.option("--require-name", is_flag=True, help="Whether to only scan for devices with names")
@click.option(
    "--regex-pattern",
    multiple=True,
    type=str,
    help="Regex patterns in device names to scan for. "
    "Specify multiple to search for multiple patterns",
)
def main(
    *,
    scan_timeout: float,
    device_address: tuple[str],
    vendor: tuple[int],
    require_name: bool,
    regex_pattern: tuple[str],
):
    utils.setup_logging()

    devices = frozenset(device_address) if device_address else None
    vendors = frozenset(vendor) if vendor else None
    regex_patterns = frozenset(regex_pattern) if regex_pattern else None
    try:
        asyncio.run(
            _main(
                timeout_s=scan_timeout,
                devices=devices,
                vendors=vendors,
                require_name=require_name,
                regex_patterns=regex_patterns,
            )
        )
    except KeyboardInterrupt:
        return


if __name__ == "__main__":
    main()
