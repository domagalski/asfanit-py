#!/usr/bin/env python3

import abc
import json
import logging
from typing import Any

import requests
from requests import exceptions as rq_err

from asfanit.sensors.purpleair import measurement_base


class SensorBase(abc.ABC):
    """Sensor base class."""

    @abc.abstractmethod
    def __init__(self, timeout_s: int):
        """Create a sensor object

        Args:
            timeout_s: (int) the number of seconds before requests time out
        """
        self._connected = None
        self._last_measurement_valid = False
        self._timeout_s = timeout_s

    @abc.abstractmethod
    def _construct_url(self, *args, **kwargs) -> str:
        """Construct a URL to request."""
        ...

    @abc.abstractmethod
    def _url_params(self) -> dict[str, str] | None:
        """Create URL parameters for requests"""
        ...

    @property
    @abc.abstractmethod
    def _measurement_klass(self) -> type:
        """Return the class definition of the sensor reading type"""
        ...

    def read_measurement(self, *args, **kwargs) -> measurement_base.MeasurementBase | None:
        """Get a reading of the PurpleAir sensor.

        Args and kwargs go into self.query_sensor()

        Returns:
            A SensorReading object if the query succeeds else None
        """
        sensor_data = self.query_sensor(*args, **kwargs)
        if not sensor_data:
            return None
        return self._measurement_klass(sensor_data)

    def query_sensor(self, *args, **kwargs) -> dict[str, Any] | None:
        """Query a sensor and return a dict from the json result

        Args and kwargs go into self._construct_url()

        Returns:
            The dict of the sensor json blob if the query succeeds else None
        """
        url = self._construct_url(*args, **kwargs)
        json_str = self._make_request(url)
        if not json_str:
            return None

        return json.loads(json_str)

    def _make_request(self, url) -> str | None:
        """Perform the http get request

        Returns:
            A string in json format from the sensor
        """
        try:
            response = requests.get(url, params=self._url_params(), timeout=self._timeout_s)
        except (rq_err.ConnectionError, rq_err.ReadTimeout) as err:
            if self._set_connection_state(False):
                logging.error(str(err))
            return None

        if response.status_code != 200:
            logging.error(f"Cannot query URL: {url}")
            logging.error(f"Response status code: {response.status_code}")
            logging.error(f"Response text:\n{response.text}")
            return None

        return response.text

    @property
    @abc.abstractmethod
    def _lost_connection_msg(self) -> str:
        """message to print after losing a connection"""
        ...

    @property
    @abc.abstractmethod
    def _regained_connection_msg(self) -> str:
        """message to print after regaining a connection"""
        ...

    def _set_connection_state(self, state: bool) -> bool:
        """Set the connection state to the sensor and report any changes"""
        connected = False
        state_changed = False
        if self._connected is None:
            state_changed = True
        else:
            connected = self._connected

        if state and not connected:
            logging.info(self._regained_connection_msg)
            state_changed = True
        elif connected and not state:
            logging.error(self._lost_connection_msg)
            state_changed = True

        self._connected = state
        return state_changed
