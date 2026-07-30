#!/usr/bin/env python3

"""Simple wrapper around the InfluxDB client for writing time series"""

import dataclasses
import enum
import json
import logging
import pathlib
import time
from typing import Any, Callable

import click
import influxdb_client_3
import requests
from influxdb_client_3.exceptions import exceptions as influx_err
from influxdb_client_3.write_client.client import write_api as influx_write_api
from requests import exceptions as rq_err
from urllib3 import exceptions as url_err


class TimePrecision(enum.Enum):
    SECOND = influxdb_client_3.WritePrecision.S
    MILLISECOND = influxdb_client_3.WritePrecision.MS
    MICROSECOND = influxdb_client_3.WritePrecision.US
    NANOSECOND = influxdb_client_3.WritePrecision.NS


class InfluxPoint:
    def __init__(
        self,
        *,
        measurement: str,
        fields: dict[str, Any],
        tags: dict[str, str] | None = None,
        timestamp: float | None = None,
        time_precision: TimePrecision = TimePrecision.NANOSECOND,
    ):
        self._measurement = measurement
        self._timestamp = timestamp or time.time()
        self._time_precision = time_precision
        self._fields = fields
        self._tags = tags

    def payload(self) -> influxdb_client_3.Point:
        point = influxdb_client_3.Point(self._measurement)
        point = point.time(self.time, self.time_precision)
        for key, value in self.tags.items():
            if value:
                point = point.tag(key, str(value))
        for key, value in self.fields.items():
            if value is not None:
                point = point.field(key, value)
        return point

    @property
    def time(self) -> int:
        if self._time_precision == TimePrecision.SECOND:
            return int(self._timestamp)
        elif self._time_precision == TimePrecision.MILLISECOND:
            return int(self._timestamp * 1e3)
        elif self._time_precision == TimePrecision.MICROSECOND:
            return int(self._timestamp * 1e6)
        elif self._time_precision == TimePrecision.NANOSECOND:
            return int(self._timestamp * 1e9)
        raise ValueError(f"invalid time precision: {self._time_precision}")

    @property
    def time_precision(self) -> str:
        return self._time_precision.value

    @property
    def fields(self) -> dict[str, Any]:
        return self._fields

    @property
    def tags(self) -> dict[str, str]:
        if not self._tags:
            return dict()
        return self._tags


@dataclasses.dataclass(frozen=True)
class InfluxOptions:
    host: str
    database: str
    token: str


class InfluxClient:
    def __init__(
        self,
        influx_options: InfluxOptions,
        *,
        write_options: influxdb_client_3.WriteOptions | None = None,
        **kwargs,
    ):
        if "write_client_options" in kwargs:
            raise ValueError("Cannot manually provide InfluxDB write_client_options")

        write_options = write_options or influxdb_client_3.WriteOptions()
        if write_options.write_type != influx_write_api.WriteType.batching:
            raise ValueError(f"Influx write type must be batching, got {write_options.write_type}")

        self._client = influxdb_client_3.InfluxDBClient3(
            host=influx_options.host,
            database=influx_options.database,
            token=influx_options.token,
            write_client_options=influxdb_client_3.write_client_options(
                write_options=write_options,
                success_callback=self._write_success_callback,
                error_callback=self._write_error_callback,
                retry_callback=self._write_retry_callback,
            ),
            **kwargs,
        )

        self._options = influx_options
        self._first_write = True
        self._connected = False

    @property
    def database(self) -> str:
        return self._options.database

    def _get_list_databases(self) -> list[str]:
        resp = requests.get(
            f"{self._options.host}/api/v3/configure/database",
            params={"format": "jsonl"},
            headers={"Authorization": f"Bearer {self._options.token}"},
        )
        resp.raise_for_status()
        databases = list()
        for line in resp.iter_lines():
            if db_name := json.loads(line).get("iox::database"):
                databases.append(db_name)
        return databases

    def _get_database_names(self) -> list[str] | None:
        """Get a list of database names in InfluxDB."""
        db_name_list = self._run_request(self._get_list_databases, default_return_value=None)
        if db_name_list is None:
            logging.error("Cannot fetch database names.")
            return None

        return db_name_list

    def _create_database(self, retention_period: str | None) -> bool:
        logging.info(f"Creating InfluxDB database: {self.database!r}")
        req = {"db": self.database}
        if retention_period:
            req["retention_period"] = retention_period
        resp = requests.post(
            f"{self._options.host}/api/v3/configure/database",
            headers={
                "Authorization": f"Bearer {self._options.token}",
                "Content-Type": "application/json",
            },
            json=req,
        )
        resp.raise_for_status()
        return True

    def init_database(self, retention_period: str | None = None) -> bool:
        """Initialize a database in InfluxDB."""
        db_name_list = self._get_database_names()
        if db_name_list is None:
            return False

        if self.database in db_name_list:
            logging.info(f"Using InfluxDB database: {self.database!r}")
        else:
            if not self._run_request(
                self._create_database,
                retention_period,
                default_return_value=False,
            ):
                logging.error(f"Cannot create InfluxDB database: {self.database}")
                return False

        return True

    def _write_success_callback(self, key_tuple: tuple, data: str):
        del key_tuple
        self._set_connection_state(True)
        if self._first_write:
            lines = data.splitlines()
            plural = "s" * int(len(lines) > 1)
            logging.info(f"Measurement{plural} written to InfluxDB.")
            self._first_write = False

    def _write_error_callback(
        self, key_tuple: tuple, data: str, exception: influx_err.InfluxDBError
    ):
        del key_tuple
        del data
        logging.error(f"Failed writing data to InfluxDB with exception:\n{exception}")
        self._set_connection_state(False)

    def _write_retry_callback(
        self, key_tuple: tuple, data: str, exception: influx_err.InfluxDBError
    ):
        del key_tuple
        del data
        logging.error(f"Failed retry writing data to InfluxDB with exception:\n{exception}")
        self._set_connection_state(False)

    def write_one_point(self, point: InfluxPoint) -> None:
        """Write one influx point to InfluxDB

        Args:
            point: A point to write to the database
        """
        return self.write_points([point])

    def write_points(self, points: list[InfluxPoint]) -> None:
        """Write points to InfluxDB

        Args:
            points: A list of points to write to the database
        """
        self._client.write([p.payload() for p in points], database=self.database)

    def _run_request(
        self,
        func,
        *args,
        default_return_value: Any,
        success_request_msg: str | None = None,
        **kwargs,
    ) -> Any:
        """Run a function that makes an InfluxDB request and handle any errors"""
        retval = default_return_value
        try:
            retval = func(*args, **kwargs)
            if self._set_connection_state(True) and success_request_msg:
                logging.info(success_request_msg)
        except (rq_err.ConnectionError, url_err.NewConnectionError) as err:
            if self._set_connection_state(False):
                logging.error("Connection Error:")
                logging.error(str(err))
        except requests.HTTPError as err:
            if self._set_connection_state(False):
                logging.error("Requests HTTP Error:")
                logging.error(str(err))

        return retval

    def _set_connection_state(self, state: bool) -> bool:
        """Set the connection state to InfluxDB and report any changes"""
        state_changed = False
        if state and not self._connected:
            logging.info("Connected to InfluxDB.")
            state_changed = True
        elif self._connected and not state:
            logging.error("Cannot connect to InfluxDB.")
            state_changed = True

        self._connected = state
        return state_changed


def cli_builder(
    *,
    influx_host: str = "http://127.0.0.1:8181",
    influx_database: str | None = None,
) -> Callable[..., Any]:
    def _cli_options(func: Callable[..., Any]) -> Callable[..., Any]:
        @click.option(
            "--influx-host",
            "-H",
            required=influx_host is None,
            default=influx_host,
            type=str,
            help="The influxdb server host+port",
        )
        @click.option(
            "--influx-database",
            "-d",
            required=influx_database is None,
            default=influx_database,
            type=str,
            help="The name of the InfluxDB database/bucket",
        )
        @click.option(
            "--influx-token",
            "-t",
            required=True,
            type=click.Path(exists=True),
            help="The path to the InfluxDB token file",
        )
        @click.pass_context
        def _wrapper(
            ctx: click.Context,
            influx_host: str,
            influx_database: str,
            influx_token: str,
            **kwargs,
        ) -> Any:
            with pathlib.Path(influx_token).open() as f:
                token = f.read().strip()
            opts = InfluxOptions(host=influx_host, database=influx_database, token=token)
            return ctx.invoke(func, opts, **kwargs)

        return _wrapper

    return _cli_options


if __name__ == "__main__":
    import random

    from asfanit import utils

    utils.setup_logging()

    database = "test_db"

    @click.command(context_settings={"show_default": True})
    @cli_builder(influx_database=database)
    def _main(influx_options: InfluxOptions):
        client = InfluxClient(influx_options)
        while not client.init_database(retention_period="1h"):
            time.sleep(1)

        while True:
            point = InfluxPoint(measurement="sample", fields={"random": random.random()})
            client.write_one_point(point)
            time.sleep(0.1)

    _main()
