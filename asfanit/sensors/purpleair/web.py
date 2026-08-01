#!/usr/bin/env python3

import json
import logging
import pathlib
import sys
from typing import Any

import click

from asfanit import utils
from asfanit.sensors.purpleair import measurement_base
from asfanit.sensors.purpleair import sensor_base


class MeasurementWeb(measurement_base.MeasurementBase):
    def __init__(self, sensor_data: dict[str, Any]):
        super().__init__(sensor_data.get("sensor", {}))

    @property
    def sensor_id(self) -> str:
        return str(self.data["sensor_index"])

    @property
    def timestamp(self) -> float:
        return float(self.data["last_seen"])

    @property
    def logging_rate(self) -> int:
        # TODO make this variable
        return 60

    @property
    def lat(self) -> float:
        return self.data["latitude"]

    @property
    def lon(self) -> float:
        return self.data["longitude"]

    @property
    def place(self) -> str | None:
        location_type = self.data["location_type"]
        if location_type == 0:
            return "outside"
        elif location_type == 1:
            return "inside"
        return None

    @property
    def rssi(self) -> int | None:
        return self.data["rssi"]

    @property
    def uptime(self) -> int | None:
        return self.data["uptime"]

    @property
    def temp_f(self) -> int | None:
        return self.data["temperature"]

    @property
    def humidity(self) -> int | None:
        return self.data["humidity"]

    @property
    def pressure(self) -> float | None:
        return self.data["pressure"]

    @property
    def pm2_5_aqi(self) -> float:
        pm_2_5 = self.data["pm2.5"]
        return self.get_aqi(pm_2_5)

    @property
    def p_0_3_um(self) -> float:
        return float(self.data["0.3_um_count"])

    @property
    def p_0_5_um(self) -> float:
        return float(self.data["0.5_um_count"])

    @property
    def p_1_0_um(self) -> float:
        return float(self.data["1.0_um_count"])

    @property
    def p_2_5_um(self) -> float:
        return float(self.data["2.5_um_count"])

    @property
    def p_5_0_um(self) -> float:
        return float(self.data["5.0_um_count"])

    @property
    def p_10_0_um(self) -> float:
        return float(self.data["10.0_um_count"])

    @property
    def pm1_0_atm(self) -> float:
        return self.data["pm1.0_atm"]

    @property
    def pm1_0_cf_1(self) -> float:
        return self.data["pm1.0_cf_1"]

    @property
    def pm2_5_atm(self) -> float:
        return self.data["pm2.5_atm"]

    @property
    def pm2_5_cf_1(self) -> float:
        return self.data["pm2.5_cf_1"]

    @property
    def pm10_0_atm(self) -> float:
        return self.data["pm10.0_atm"]

    @property
    def pm10_0_cf_1(self) -> float:
        return self.data["pm10.0_cf_1"]


class SensorWeb(sensor_base.SensorBase):
    """Web sensor class.

    This uses the JSON API for querying all online sensors.
    """

    def __init__(self, *, api_key: str, sensor_id: int, timeout_s: int = 20):
        """Create a web sensor

        Args:
            api_key: (str) The API key for making queries
            sensor_id: (int) Numerical ID of the sensor.
            timeout_s: (int) the number of seconds before requests time out
        """
        super().__init__(timeout_s)
        self._sensor_id = sensor_id
        self._api_key = api_key

    @property
    def _measurement_klass(self) -> type:
        return MeasurementWeb

    def _construct_url(self) -> str:
        url = f"https://api.purpleair.com/v1/sensors/{self._sensor_id}"
        return url

    def _url_params(self) -> dict[str, str] | None:
        return {"api_key": self._api_key}

    @property
    def _lost_connection_msg(self) -> str:
        return "Cannot connect: purpleair.com"

    @property
    def _regained_connection_msg(self) -> str:
        return "Connected: purpleair.com"


@click.command(context_settings={"show_default": True})
@click.option("--api-key", required=True, type=click.Path(exists=True), help="Path to the API key")
@click.option("--sensor-id", required=True, type=int, help="The ID of the PurpleAir sensor")
def main(*, api_key: str, sensor_id: int):
    utils.setup_logging()

    with pathlib.Path(api_key).open() as f:
        api_key_str = f.read().strip()

    sensor = SensorWeb(api_key=api_key_str, sensor_id=sensor_id)
    logging.info(f"Fetching data for sensor: {sensor_id}")
    if (measurement := sensor.read_measurement()) is None:
        logging.critical("Failed to read sensor")
        sys.exit(1)

    measurement_json = json.dumps(measurement.data, indent=4)
    logging.info(f"Sensor data:\n{measurement_json}")
    logging.info(f"AQI: {measurement.pm2_5_aqi_epa}")


if __name__ == "__main__":
    main()
