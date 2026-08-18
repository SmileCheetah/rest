import tempfile
import unittest
from pathlib import Path

import numpy as np
import xarray as xr

from app.ml.era5 import load_era5_netcdf


class Era5LoaderTest(unittest.TestCase):
    def test_converts_hourly_era5_values_to_model_units(self) -> None:
        times = np.array(
            ["2025-08-01T03:00:00", "2025-08-01T04:00:00"],
            dtype="datetime64[ns]",
        )
        dataset = xr.Dataset(
            data_vars={
                "t2m": (("valid_time", "latitude", "longitude"), _cube([303.15, 304.15])),
                "d2m": (("valid_time", "latitude", "longitude"), _cube([293.15, 294.15])),
                "u10": (("valid_time", "latitude", "longitude"), _cube([3.0, 0.0])),
                "v10": (("valid_time", "latitude", "longitude"), _cube([4.0, 2.0])),
                "sp": (("valid_time", "latitude", "longitude"), _cube([101_325.0, 100_800.0])),
                "ssrd": (("valid_time", "latitude", "longitude"), _cube([3_600_000.0, 1_800_000.0])),
                "fdir": (("valid_time", "latitude", "longitude"), _cube([1_800_000.0, 900_000.0])),
            },
            coords={
                "valid_time": times,
                "latitude": [37.5],
                "longitude": [127.0],
            },
        )

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "era5.nc"
            dataset.to_netcdf(path)
            observations = load_era5_netcdf(path)

        np.testing.assert_allclose(observations.temperature, [30.0, 31.0])
        np.testing.assert_allclose(observations.wind_speed, [5.0, 2.0])
        np.testing.assert_allclose(observations.solar_radiation, [1000.0, 500.0])
        np.testing.assert_allclose(observations.direct_solar_fraction, [0.5, 0.5])
        np.testing.assert_allclose(observations.surface_pressure, [1013.25, 1008.0])
        self.assertTrue(((observations.humidity >= 0) & (observations.humidity <= 100)).all())
        self.assertTrue(np.isfinite(observations.cosine_solar_zenith).all())

    def test_requires_coordinates_for_a_multi_point_file(self) -> None:
        dataset = xr.Dataset(
            data_vars={
                name: (("valid_time", "latitude", "longitude"), np.ones((1, 2, 1)))
                for name in ("t2m", "d2m", "u10", "v10", "sp", "ssrd", "fdir")
            },
            coords={
                "valid_time": np.array(["2025-08-01T03:00:00"], dtype="datetime64[ns]"),
                "latitude": [37.5, 37.6],
                "longitude": [127.0],
            },
        )

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "era5.nc"
            dataset.to_netcdf(path)
            with self.assertRaisesRegex(ValueError, "multiple grid points"):
                load_era5_netcdf(path)

    def test_loads_one_time_from_a_selected_grid_point(self) -> None:
        shape = (1, 2, 1)
        dataset = xr.Dataset(
            data_vars={
                "t2m": (("valid_time", "latitude", "longitude"), np.full(shape, 303.15)),
                "d2m": (("valid_time", "latitude", "longitude"), np.full(shape, 293.15)),
                "u10": (("valid_time", "latitude", "longitude"), np.full(shape, 1.0)),
                "v10": (("valid_time", "latitude", "longitude"), np.full(shape, 1.0)),
                "sp": (("valid_time", "latitude", "longitude"), np.full(shape, 101_000.0)),
                "ssrd": (("valid_time", "latitude", "longitude"), np.full(shape, 1_800_000.0)),
                "fdir": (("valid_time", "latitude", "longitude"), np.full(shape, 900_000.0)),
            },
            coords={
                "valid_time": np.array(["2025-08-01T03:00:00"], dtype="datetime64[ns]"),
                "latitude": [37.5, 37.6],
                "longitude": [127.0],
            },
        )

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "era5.nc"
            dataset.to_netcdf(path)
            observations = load_era5_netcdf(
                path,
                latitude=37.6,
                longitude=127.0,
            )

        self.assertEqual(len(observations.observed_at), 1)
        self.assertAlmostEqual(float(observations.temperature[0]), 30.0)


def _cube(values: list[float]) -> np.ndarray:
    return np.asarray(values, dtype=float).reshape(-1, 1, 1)


if __name__ == "__main__":
    unittest.main()
