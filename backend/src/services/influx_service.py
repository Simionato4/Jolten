from datetime import datetime, timezone
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

from src.config import settings

_client = InfluxDBClient(
    url=settings.influx_url,
    token=settings.influx_token,
    org=settings.influx_org,
)
_write_api = _client.write_api(write_options=SYNCHRONOUS)
_query_api = _client.query_api()


def write_movement(sala_id: str, valor: int) -> None:
    point = (
        Point("sensor_pir")
        .tag("sala", sala_id)
        .field("movimento", valor)
    )
    _write_api.write(bucket=settings.influx_bucket, org=settings.influx_org, record=point)


def write_luminosity(sala_id: str, valor: int) -> None:
    point = (
        Point("sensor_ldr")
        .tag("sala", sala_id)
        .field("luminosidade", valor)
    )
    _write_api.write(bucket=settings.influx_bucket, org=settings.influx_org, record=point)


def query_history(sala_id: str, range_minutes: int = 60) -> list[dict]:
    # Target ~90 data points — 20s base gives enough resolution to see individual pulses
    window_seconds = max(20, (range_minutes * 60) // 90)

    flux = f"""
        from(bucket: "{settings.influx_bucket}")
          |> range(start: -{range_minutes}m)
          |> filter(fn: (r) => r._measurement == "sensor_pir" and r.sala == "{sala_id}")
          |> aggregateWindow(every: {window_seconds}s, fn: max, createEmpty: false)
          |> keep(columns: ["_time", "_value"])
          |> sort(columns: ["_time"])
    """
    tables = _query_api.query(flux, org=settings.influx_org)
    return [
        {"timestamp": record.get_time().isoformat(), "movimento": record.get_value()}
        for table in tables
        for record in table.records
    ]
