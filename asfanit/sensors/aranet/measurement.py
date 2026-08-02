import dataclasses
from typing import Any

from aranet4 import client as a4client
from bleak.backends import device as bleak_device


class Measurement:
    def __init__(self, data: a4client.Aranet4Advertisement, label: str | None = None):
        if not data.device:
            raise ValueError("Aranet advertisement contains no device info")
        if not data.readings:
            raise ValueError("Aranet advertisement contains no data readings")
        if not data.manufacturer_data:
            raise ValueError("Aranet advertisement contains no manufacturer_data")

        self._data = data
        self._label = label or data.device.name or data.device.address

    @property
    def address(self) -> str:
        return self._data.device.address

    @property
    def label(self) -> str:
        return self._label

    @property
    def name(self) -> str:
        return self.reading.name

    @property
    def data(self) -> a4client.Aranet4Advertisement:
        return self._data

    @property
    def device(self) -> bleak_device.BLEDevice:
        return self._data.device

    @property
    def manufacturer_data(self) -> a4client.ManufacturerData:
        return self._data.manufacturer_data

    @property
    def reading(self) -> a4client.CurrentReading:
        return self._data.readings

    def __str__(self) -> str:
        return self._data.readings.toString(self._data)

    def as_dict(self) -> dict[str, Any]:
        device = dataclasses.asdict(self.reading)
        keys_to_remove = set()
        for key, value in device.items():
            if value == a4client.Aranet4.AR4_NO_DATA_FOR_PARAM:
                keys_to_remove.add(key)
            if isinstance(value, str) and not value:
                keys_to_remove.add(key)
        for key in keys_to_remove:
            device.pop(key)

        device["label"] = self.label
        device["address"] = self.address
        if self._data.rssi is not None:
            device["rssi"] = self._data.rssi

        if version := self.manufacturer_data.version:
            device["version"] = str(version)

        device["model"] = self.reading.type.model

        if not any(
            [
                self.reading.ago == a4client.Aranet4.AR4_NO_DATA_FOR_PARAM,
                self.reading.interval == a4client.Aranet4.AR4_NO_DATA_FOR_PARAM,
            ]
        ):
            staleness = 100.0 * float(self.reading.ago) / float(self.reading.interval)
            device["staleness"] = staleness

        return device
