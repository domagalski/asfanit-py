from typing import Any

import click

from asfanit.recorders import influx
from asfanit.recorders.purpleair import recorder_base
from asfanit.sensors.purpleair import lan
from asfanit import utils

_TAG_KEYS = {
    "SensorId",
    "Geo",
    "ssid",
    "place",
    "version",
    "hardwareversion",
    "hardwarediscovered",
}


class RecoderLAN(recorder_base.RecoderBase[lan.MeasurementLAN]):
    @staticmethod
    def make_influx_point(
        sensor_reading: lan.MeasurementLAN, measurement_name: str
    ) -> influx.InfluxPoint | None:
        # This happens in early boot-phase when data isn't yet available.
        for key, value in sensor_reading.data.items():
            # Only check particle sensor readings. This skips over Adc,
            # which takes a lot longer to initialize after boot.
            if not (key.startswith("p_") or key.startswith("pm")):
                continue
            if value == "nan":
                return None

        tags: dict[str, str] = {}
        for key in _TAG_KEYS:
            tags[key] = str(sensor_reading.data[key])

        fields: dict[str, Any] = {}
        for key in sorted(sensor_reading.data.keys()):
            if key.startswith("current"):
                fields[key] = sensor_reading.data[key]
            if key.startswith("p") and key not in ["pa_latency", "period", "place"]:
                fields[key] = sensor_reading.data[key]
            if key in ["rssi", "uptime"]:
                fields[key] = sensor_reading.data[key]

        fields["pm2_5_epa_correction"] = sensor_reading.pm2_5_epa_correction
        fields["pm2_5_aqi_epa"] = sensor_reading.pm2_5_aqi_epa

        return influx.InfluxPoint(
            measurement=measurement_name,
            fields=fields,
            tags=tags,
            timestamp=sensor_reading.timestamp,
            time_precision=influx.TimePrecision.SECOND,
        )


@click.command(context_settings={"show_default": True})
@click.option("--ip-address", required=True, type=str, help="IP address of the sensor")
@click.option("--port", type=int, help="Override the HTTP port of the sensor")
@click.option("--live", is_flag=True, help="Whether to fetch live data (true) or averages (false)")
@recorder_base.influx_cli_options
def main(influx_options: influx.InfluxOptions, *, ip_address: str, port: int | None, live: bool):
    utils.setup_logging()
    client = influx.InfluxClient(influx_options)
    sensor = lan.SensorLAN(ip_address, port)

    measurement_name = "live" if live else "average"
    interval = 10 if live else 120
    recorder = RecoderLAN(client, sensor, measurement_name, live=live)
    recorder.run_forever(interval)


if __name__ == "__main__":
    main()
