#!/usr/bin/env python3

"""Read PurpleAir sensor data on a LAN"""

import datetime
import re
from typing import cast, Any

from asfanit.sensors.purpleair import measurement_base
from asfanit.sensors.purpleair import sensor_base


class MeasurementLAN(measurement_base.MeasurementBase):
    def _get_average(self, field: str) -> float:
        return (self.data[field] + self.data[field + "_b"]) / 2.0

    @property
    def sensor_id(self) -> str:
        return self.data["SensorId"]

    @property
    def timestamp(self) -> float:
        timestamp = self.data["DateTime"].upper().replace("/", "-")
        return datetime.datetime.fromisoformat(timestamp).timestamp()

    @property
    def lat(self) -> float:
        return self.data["lat"]

    @property
    def lon(self) -> float:
        return self.data["lon"]

    @property
    def place(self) -> str:
        return self.data["place"]

    @property
    def rssi(self) -> int:
        return self.data["rssi"]

    @property
    def uptime(self) -> int:
        return self.data["uptime"]

    @property
    def temp_f(self) -> int:
        return self.data["current_temp_f"]

    @property
    def humidity(self) -> int:
        return self.data["current_humidity"]

    @property
    def dew_point_f(self) -> int:
        return self.data["current_dewpoint_f"]

    @property
    def pressure(self) -> float:
        return self.data["pressure"]

    @property
    def pm2_5_aqi(self) -> float:
        return self._get_average("pm2.5_aqi")

    @property
    def p_0_3_um(self) -> float:
        return self._get_average("p_0_3_um")

    @property
    def p_0_5_um(self) -> float:
        return self._get_average("p_0_5_um")

    @property
    def p_1_0_um(self) -> float:
        return self._get_average("p_1_0_um")

    @property
    def p_2_5_um(self) -> float:
        return self._get_average("p_2_5_um")

    @property
    def p_5_0_um(self) -> float:
        return self._get_average("p_5_0_um")

    @property
    def p_10_0_um(self) -> float:
        return self._get_average("p_10_0_um")

    @property
    def pm1_0_atm(self) -> float:
        return self._get_average("pm1_0_atm")

    @property
    def pm1_0_cf_1(self) -> float:
        return self._get_average("pm1_0_cf_1")

    @property
    def pm2_5_atm(self) -> float:
        return self._get_average("pm2_5_atm")

    @property
    def pm2_5_cf_1(self) -> float:
        return self._get_average("pm2_5_cf_1")

    @property
    def pm10_0_atm(self) -> float:
        return self._get_average("pm10_0_atm")

    @property
    def pm10_0_cf_1(self) -> float:
        return self._get_average("pm10_0_cf_1")


class SensorLAN(sensor_base.SensorBase):
    """LAN Sensor class.

    A Purpleair sensor's data can be found at the following:
    http://<IP_ADDRESS>/json

    For live data (updates roughly 10 seconds):
    http://<IP_ADDRESS>/json?live=true
    """

    def __init__(self, addr: str, port: int | None = None):
        """Create a sensor object

        Args:
            addr: (str) The IP address to query. Do not include the http://
            port: (int) The TCP port for the IP address.
            db: Optional database client.
        """
        super().__init__()
        if not re.fullmatch(r"\d+.\d+.\d+.\d+", addr):
            if not re.match(r"^purpleair-\d+", addr.lower()):
                raise ValueError("addr must be an IP or PurpleAir hostname.")

        self._addr = addr
        self._port = port

    @property
    def _measurement_klass(self) -> type:
        return MeasurementLAN

    @property
    def _lost_connection_msg(self):
        return f"Cannot connect to sensor: {self._addr}"

    @property
    def _regained_connection_msg(self):
        return f"Connected to sensor: {self._addr}"

    def _construct_url(self, live: bool) -> str:
        """Construct a URL to request.

        Args:
            live: (bool) Get live data instead of a 120 second average.

        Returns:
            The URL to be used for requests
        """
        port = f":{self._port}" if self._port else ""
        url = f"http://{self._addr}{port}/json"
        if live:
            url = f"{url}?live=true"
        return url

    def _url_params(self) -> dict[str, str] | None:
        return None

    def read_measurement(self, *, live: bool = True) -> MeasurementLAN | None:
        """Get a reading of the PurpleAir sensor.

        Args:
            live: (bool) Get live data instead of a 120 second average.

        Returns:
            A SensorReading object if the query succeeds else None
        """
        return cast(MeasurementLAN | None, super().read_measurement(live=live))

    def query_sensor(self, *, live: bool = True) -> dict[str, Any] | None:
        """Query a sensor and return a dict from the json result

        Args:
            live: (bool) Get live data instead of a 120 second average.

        Returns:
            The dict of the sensor json blob if the query succeeds else None
        """
        return super().query_sensor(live=live)


if __name__ == "__main__":
    import json
    import logging
    import sys
    import click
    from asfanit import utils

    utils.setup_logging()

    @click.command(context_settings={"show_default": True})
    @click.option("--ip-address", required=True, type=str, help="IP address of the sensor")
    @click.option("--port", type=int, help="Override the HTTP port of the sensor")
    @click.option(
        "--live", is_flag=True, help="Whether to fetch live data (true) or averages (false)"
    )
    def _main(*, ip_address: str, port: int | None, live: bool):
        sensor = SensorLAN(ip_address, port)
        logging.info("Fetching local sensor data")
        if (measurement := sensor.read_measurement(live=live)) is None:
            logging.critical("Failed to read local sensor")
            sys.exit(1)

        measurement_json = json.dumps(measurement.data, indent=4)
        logging.info(f"Sensor data:\n{measurement_json}")
        logging.info(f"AQI: {measurement.pm2_5_aqi_epa}")

    _main()
