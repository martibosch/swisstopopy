"""Tests for swisstopopy."""

import importlib
import logging as lg
import sys
import tempfile
import unittest
from collections.abc import Generator
from os import path

import geopandas as gpd
import pytest
import rasterio as rio

import swisstopopy


@pytest.fixture
def unload_pdal(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Fake that pdal is not installed.

    Source: https://stackoverflow.com/a/79280624
    """
    modules = {
        module: sys.modules[module]
        for module in list(sys.modules)
        if module.startswith("pdal") or module == "pdal"
    }
    for module in modules:
        # ensure that `pdal` and all its submodules are not loadable
        monkeypatch.setitem(sys.modules, module, None)

    with pytest.raises(ImportError):
        # ensure that `pdal` cannot be imported
        import pdal  # noqa: F401

    import swisstopopy.tree_canopy as tree_canopy

    importlib.reload(tree_canopy)
    yield  # undo the monkeypatch
    for module, original in modules.items():
        if original is None:
            sys.modules.pop(module, None)
        else:
            sys.modules[module] = original
    importlib.reload(tree_canopy)  # make `pdal` available again


class TestSwissTopoPy(unittest.TestCase):
    def setUp(self):
        self.region = "EPFL"
        self.collection_ids = [
            swisstopopy.SWISSALTI3D_COLLECTION_ID,
            swisstopopy.SWISSIMAGE10_COLLECTION_ID,
            swisstopopy.SWISSSURFACE3D_COLLECTION_ID,
            swisstopopy.SWISSSURFACE3D_RASTER_COLLECTION_ID,
        ]

    def test_stac_client(self):
        # # test without region (all collection items)
        # client = swisstopopy.SwissTopoClient()

        # # since this is slow, test init one collection only
        # collection_id = self.collection_ids[0]
        # gdf = client.gdf_from_collection(collection_id)

        # test with region
        region_client = swisstopopy.SwissTopoClient(region=self.region)
        # # test that there are at most as many items as when not filtering spatially
        # self.assertLessEqual(
        #     len(region_client.gdf_from_collection(collection_id).index),
        #     len(gdf.index)
        # )
        # test init all collections
        for collection_id in self.collection_ids:
            gdf = region_client.get_collection_gdf(collection_id)
            # test that we get a non empty geo-data frame
            self.assertIsInstance(gdf, gpd.GeoDataFrame)
            self.assertFalse(gdf.empty)

        # test that get latest returns at most the same number of items
        self.assertLessEqual(len(swisstopopy.get_latest(gdf).index), len(gdf.index))

    def test_buildings(self):
        def _test_buildings(kwargs):
            bldg_gdf = swisstopopy.get_bldg_gdf(self.region, **kwargs)
            # test that we get a non empty geo-data frame
            self.assertIsInstance(bldg_gdf, gpd.GeoDataFrame)
            self.assertFalse(bldg_gdf.empty)
            return bldg_gdf

        for kwargs in [
            {},
            {"item_datetime": "2019"},
        ]:
            bldg_gdf = _test_buildings(kwargs)
            # test that we get a "height" column
            self.assertIn("height", bldg_gdf.columns)
        # test that setting an unavailable datetime issues a warning and returns the
        # geo-data frame without height information
        with self.assertWarns(Warning):
            bldg_gdf = _test_buildings({"item_datetime": "2018"})
            # test that we do NOT get a "height" column
            self.assertNotIn("height", bldg_gdf.columns)

    def _test_raster(self, func, kwargs_combinations):
        for kwargs in kwargs_combinations:
            with tempfile.TemporaryDirectory() as tmp_dir:
                dst_filepath = path.join(tmp_dir, "foo.tif")
                func(
                    self.region,
                    dst_filepath,
                    **kwargs,
                )
                # test that we get a non empty raster
                with rio.open(dst_filepath) as src:
                    self.assertEqual(src.count, 1)
                    self.assertEqual(len(src.read(1).shape), 2)

    def _test_wrong_datetime(self, func, kwargs):
        with tempfile.TemporaryDirectory() as tmp_dir:
            dst_filepath = path.join(tmp_dir, "foo.tif")
            with self.assertRaises(ValueError):
                func(
                    self.region,
                    dst_filepath,
                    **kwargs,
                )

    def test_dem(self):
        self._test_raster(
            swisstopopy.get_dem_raster,
            [
                {},
                {"alti3d_datetime": "2019"},
                {"alti3d_res": 2},
            ],
        )
        self._test_wrong_datetime(
            swisstopopy.get_dem_raster,
            {"alti3d_datetime": "2018"},
        )

    def test_tree_canopy(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            # cache lidar files in the temporary directory to speed-up and avoid
            # re-downloading
            _base_kwargs = {
                "cache_lidar": True,
                "pooch_retrieve_kwargs": {"path": tmp_dir},
            }
            self._test_raster(
                swisstopopy.get_tree_canopy_raster,
                [
                    {**kwargs, **_base_kwargs}
                    for kwargs in [
                        {},
                        {"surface3d_datetime": "2019"},
                        {"count_threshold": 48},
                        {"dst_res": 2},
                        {"dst_tree_val": 255, "dst_dtype": "int16", "dst_nodata": -255},
                    ]
                ],
            )
            self._test_wrong_datetime(
                swisstopopy.get_tree_canopy_raster,
                {"surface3d_datetime": "2018"},
            )

    @pytest.mark.usefixtures("unload_pdal")
    def test_tree_canopy_no_pdal(self):
        # test that calling `get_tree_canopy_raster` without pdal installed returns None
        # and logs a warning
        with tempfile.TemporaryDirectory() as tmp_dir:
            dst_filepath = path.join(tmp_dir, "foo.tif")
            with self.assertLogs(level=lg.WARNING) as cm:
                result = swisstopopy.get_tree_canopy_raster(
                    self.region,
                    dst_filepath,
                )
            self.assertIsNone(result)
            self.assertTrue(
                any("PDAL" in message for message in cm.output),
                "Expected a PDAL warning to be logged.",
            )
            self.assertTrue(
                any("Returning `None`." in message for message in cm.output),
                "Expected a warning about returning None to be logged.",
            )
