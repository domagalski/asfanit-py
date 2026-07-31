#!/usr/bin/env python3

import abc
from typing import Any


class MeasurementBase(abc.ABC):
    def __init__(self, sensor_data: dict[str, Any]):
        self._data = sensor_data

    @property
    def data(self) -> dict[str, Any]:
        """Return the internal data dictionary"""
        return self._data

    @staticmethod
    def get_aqi(pm_2_5: float) -> float:
        """Convert a pm 2.5 value to an AQI"""
        # NOTE: since the table on wikipedia is ambiguous to what happens at
        # jump points if there is more than a decimal of precision. Therefore,
        # we multiplying pm2.5 by 10 and convert to and int for detecting the
        # concentration limits of the pm2.5 value.
        pm_2_5 = int(pm_2_5 * 10)

        # Taken from wikipedia: https://en.wikipedia.org/wiki/Air_quality_index
        concentration_limits = [
            (0, 120),
            (121, 354),
            (355, 554),
            (555, 1504),
            (1505, 2504),
            (2505, 3504),
            (3505, 5004),
        ]
        aqi_limits = [
            (0, 50),
            (51, 100),
            (101, 150),
            (151, 200),
            (201, 300),
            (301, 400),
            (401, 500),
        ]

        limit = None
        index_breakpoints = None
        ii = 0
        low = 0
        high = 0
        for ii, (low, high) in enumerate(concentration_limits):
            if low <= pm_2_5 <= high:
                break
        pm_2_5 /= 10
        limit = (low / 10, high / 10)
        index_breakpoints = aqi_limits[ii]

        c_low, c_high = limit
        i_low, i_high = index_breakpoints
        aqi = (i_high - i_low) * (pm_2_5 - c_low) / (c_high - c_low) + i_low
        return aqi

    @staticmethod
    def get_epa_correction(pm2_5_cf_1: float | None, humidity: float | None) -> float | None:
        """Run the EPA correction on purpleair sensors

        Ref:
            - https://cfpub.epa.gov/si/si_public_record_report.cfm?Lab=CEMM&dirEntryId=349513

        Note:
            This doesn't run the 1-hour averages that are recommended as the
            measurement class only deals with current readings.

        Note:
            The web sensor has the possibility of null-values.

        Args:
            pm2_5_cf_1: (float) Mean of channel readings of pm2.5 concentration with CF 1
            humidity: (float) Current humidity measured by the sensor.

        Returns:
            corrected pm2.5 value
        """
        if None in [pm2_5_cf_1, humidity]:
            return None
        assert pm2_5_cf_1 is not None
        assert humidity is not None

        # Using the equation on page 25 of the EPA report pdf
        # constants on that page are different than at page 8 for some reason.
        # TODO check for a newer API correction

        # It's possible when pm2_5 is near zero and the humidty is high that pm2.5
        # could go negative after correction. Assume anything less than zero is zero.
        return max(0.0, 0.534 * pm2_5_cf_1 - 0.0844 * humidity + 5.604)

    @property
    def pm2_5_epa_correction(self) -> float | None:
        return self.get_epa_correction(self.pm2_5_cf_1, self.humidity)

    @property
    def pm2_5_aqi_epa(self) -> float | None:
        pm2_5_epa = self.pm2_5_epa_correction
        if pm2_5_epa is None:
            return None

        return self.get_aqi(pm2_5_epa)

    #
    # Data fields as properties
    #

    # See https://api.purpleair.com/ for reference

    @property
    @abc.abstractmethod
    def sensor_id(self) -> str:
        """Sensor ID"""
        ...

    @property
    @abc.abstractmethod
    def timestamp(self) -> float:
        """Sensor timestamp"""
        ...

    @property
    @abc.abstractmethod
    def logging_rate(self) -> int:
        """Sensor logging rate"""
        ...

    @property
    @abc.abstractmethod
    def lat(self) -> float:
        """latitude"""
        ...

    @property
    @abc.abstractmethod
    def lon(self) -> float:
        """longitude"""
        ...

    @property
    @abc.abstractmethod
    def place(self) -> str | None:
        """inside vs outside"""
        ...

    @property
    @abc.abstractmethod
    def rssi(self) -> int | None:
        """wifi signal strength"""
        ...

    @property
    @abc.abstractmethod
    def uptime(self) -> int | None:
        """uptime"""
        ...

    @property
    @abc.abstractmethod
    def temp_f(self) -> int | None:
        """temperature in fahrenheit"""
        ...

    @property
    @abc.abstractmethod
    def humidity(self) -> int | None:
        """humidty"""
        ...

    @property
    @abc.abstractmethod
    def pressure(self) -> float | None:
        """pressure"""
        ...

    @property
    @abc.abstractmethod
    def pm2_5_aqi(self) -> float:
        """AQI"""
        ...

    @property
    @abc.abstractmethod
    def p_0_3_um(self) -> float:
        """sensor data"""
        ...

    @property
    @abc.abstractmethod
    def p_0_5_um(self) -> float:
        """sensor data"""
        ...

    @property
    @abc.abstractmethod
    def p_1_0_um(self) -> float:
        """sensor data"""
        ...

    @property
    @abc.abstractmethod
    def p_2_5_um(self) -> float:
        """sensor data"""
        ...

    @property
    @abc.abstractmethod
    def p_5_0_um(self) -> float:
        """sensor data"""
        ...

    @property
    @abc.abstractmethod
    def p_10_0_um(self) -> float:
        """sensor data"""
        ...

    @property
    @abc.abstractmethod
    def pm1_0_atm(self) -> float:
        """sensor data"""
        ...

    @property
    @abc.abstractmethod
    def pm1_0_cf_1(self) -> float:
        """sensor data"""
        ...

    @property
    @abc.abstractmethod
    def pm2_5_atm(self) -> float:
        """sensor data"""
        ...

    @property
    @abc.abstractmethod
    def pm2_5_cf_1(self) -> float:
        """sensor data"""
        ...

    @property
    @abc.abstractmethod
    def pm10_0_atm(self) -> float:
        """sensor data"""
        ...

    @property
    @abc.abstractmethod
    def pm10_0_cf_1(self) -> float:
        """sensor data"""
        ...
