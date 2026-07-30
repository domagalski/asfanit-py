import pathlib
from typing import Any

import click

from asfanit.recorders import influx
from asfanit.recorders.purpleair import recorder_base
from asfanit.sensors.purpleair import web
from asfanit import utils

_SENSOR_KEYS = {
    "pm1_0_atm",  # ATM PM1.0 particulate mass in ug/m3
    "pm2_5_atm",  # ATM PM2.5 particulate mass in ug/m3
    "pm10_0_atm",  # ATM PM10.0 particulate mass in ug/m3
    "pm1_0_cf_1",  # CF=1 PM1.0 particulate mass in ug/m3
    "pm2_5_cf_1",  # CF=1 PM2.5 particulate mass in ug/m3
    "pm10_0_cf_1",  # CF=1 PM10.0 particulate mass in ug/m3
    "p_0_3_um",  # 0.3 micrometer particle counts per deciliter of air
    "p_0_5_um",  # 0.5 micrometer particle counts per deciliter of air
    "p_1_0_um",  # 1.0 micrometer particle counts per deciliter of air
    "p_2_5_um",  # 2.5 micrometer particle counts per deciliter of air
    "p_5_0_um",  # 5.0 micrometer particle counts per deciliter of air
    "p_10_0_um",  # 10.0 micrometer particle counts per deciliter of air
}


class RecoderWeb(recorder_base.RecoderBase[web.MeasurementWeb]):

    @staticmethod
    def make_influx_point(
        sensor_reading: web.MeasurementWeb, measurement_name: str
    ) -> influx.InfluxPoint | None:
        tags: dict[str, str] = {}
        tags["sensor_id"] = sensor_reading.sensor_id
        tags["label"] = sensor_reading.data["name"]
        tags["hidden"] = str(bool(sensor_reading.data["private"]))

        fields: dict[str, Any] = {}
        fields["pm2_5_aqi"] = sensor_reading.pm2_5_aqi
        fields["temp_f"] = sensor_reading.temp_f
        fields["pressure"] = sensor_reading.pressure
        fields["humidity"] = sensor_reading.humidity
        fields["rssi"] = sensor_reading.rssi
        fields["uptime"] = sensor_reading.uptime
        if sensor_reading.place:
            tags["place"] = sensor_reading.place
        for key in _SENSOR_KEYS:
            fields[key] = sensor_reading.__getattribute__(key)

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
@click.option("--api-key", required=True, type=click.Path(exists=True), help="Path to the API key")
@click.option("--sensor-id", required=True, type=int, help="The ID of the PurpleAir sensor")
@click.option(
    "--interval", default=60, type=int, help="Interval (in seconds) to wait between readings"
)
@recorder_base.influx_cli_options
def main(influx_options: influx.InfluxOptions, *, api_key: str, sensor_id: int, interval: int):
    with pathlib.Path(api_key).open() as f:
        api_key_str = f.read().strip()
    utils.setup_logging()
    client = influx.InfluxClient(influx_options)
    sensor = web.SensorWeb(api_key=api_key_str, sensor_id=sensor_id)

    recorder = RecoderWeb(client, sensor, "purpleair")
    recorder.run_forever(interval)


if __name__ == "__main__":
    main()
