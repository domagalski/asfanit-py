import abc
import logging
import time
from typing import cast, Generic, TypeVar

from asfanit.recorders import influx
from asfanit.sensors.purpleair import sensor_base
from asfanit.sensors.purpleair import measurement_base

SensorReading = TypeVar("SensorReading", bound=measurement_base.MeasurementBase)

DATABASE = "purpleair"

_RETRY_TIME_S = 10


class RecoderBase(abc.ABC, Generic[SensorReading]):
    def __init__(
        self,
        client: influx.InfluxClient,
        sensor: sensor_base.SensorBase,
        measurement_name: str,
        *sensor_read_args,
        **sensor_read_kwargs,
    ):
        self._client = client
        self._sensor = sensor
        self._measurement_name = measurement_name
        self._sensor_read_args = sensor_read_args
        self._sensor_read_kwargs = sensor_read_kwargs

    @staticmethod
    @abc.abstractmethod
    def make_influx_point(
        sensor_reading: SensorReading, measurement_name: str
    ) -> influx.InfluxPoint | None:
        """convert a sensor reading to an InfluxPoint object"""
        ...

    def init_database(self, retention_period: str | None = None) -> bool:
        return self._client.init_database(retention_period=retention_period)

    def wait_for_database(self, retention_period: str | None = None) -> None:
        while not self.init_database(retention_period):
            time.sleep(1)

    def record_sensor(self) -> bool:
        if (
            reading := self._sensor.read_measurement(
                *self._sensor_read_args, **self._sensor_read_kwargs
            )
        ) is None:
            return False

        if (
            point := self.make_influx_point(cast(SensorReading, reading), self._measurement_name)
        ) is None:
            return False

        self._client.write_one_point(point)
        return True

    def run_forever(self, loop_interval_s: int, data_retention: str | None = None) -> None:
        self.wait_for_database(retention_period=data_retention)
        while True:
            start = time.time()
            if not self.record_sensor():
                logging.error("Failed to collect data from sensor")
                time.sleep(_RETRY_TIME_S)
                continue

            elapsed = time.time() - start
            remainder = loop_interval_s - elapsed if loop_interval_s > elapsed else 0.0
            time.sleep(remainder)
