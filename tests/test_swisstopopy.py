"""Tests for swisstopopy."""

import glob
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

    def _test_dst_raster(self, dst_filepath):
        # test that we get a non empty image-like raster
        with rio.open(dst_filepath) as src:
            self.assertEqual(src.count, 1)
            self.assertEqual(len(src.read(1).shape), 2)

    def _test_raster(self, func, kwargs_combinations, *, keyword_only=False):
        # define call_func here to avoid checking keyword_only in every iteration.
        if keyword_only:

            def call_func(dst_filepath, **kwargs):
                # note that in this case we get the region from the kwargs first in case
                # it has been provided explicitly
                if "region" in kwargs:
                    region = kwargs.pop("region")
                else:
                    region = self.region
                return func(
                    region=region,
                    dst_filepath=dst_filepath,
                    **kwargs,
                )
        else:

            def call_func(dst_filepath, **kwargs):
                return func(self.region, dst_filepath, **kwargs)

        # test all combinations of kwargs
        for kwargs in kwargs_combinations:
            with tempfile.TemporaryDirectory() as tmp_dir:
                dst_filepath = path.join(tmp_dir, "foo.tif")
                # call the function
                call_func(dst_filepath, **kwargs)
                # test that we get a non empty raster
                self._test_dst_raster(dst_filepath)

    def _test_wrong_datetime(self, func, kwargs, *, keyword_only=False):
        with tempfile.TemporaryDirectory() as tmp_dir:
            dst_filepath = path.join(tmp_dir, "foo.tif")
            with self.assertRaises(ValueError):
                if keyword_only:
                    func(
                        region=self.region,
                        dst_filepath=dst_filepath,
                        **kwargs,
                    )
                else:
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
            # get example surface3d_gdf
            client = swisstopopy.SwissTopoClient(region=self.region)
            surface3d_gdf = client.get_collection_gdf(
                swisstopopy.SWISSSURFACE3D_COLLECTION_ID,
            )
            surface3d_gdf = surface3d_gdf[
                surface3d_gdf["assets.href"].str.endswith(".zip")
            ]
            surface3d_gdf = swisstopopy.get_latest(surface3d_gdf)
            # note that _test_raster only works for dst_filepath, so we will test
            # passing dst_dir separately below
            # also note that the default "None" value for region will default to the
            # region from the test class, so we don't need to specify it in the kwargs
            # combinations except when we set it to None to explicitly test passing
            # None (to use surface3d_gdf instead of region)
            self._test_raster(
                swisstopopy.get_tree_canopy_raster,
                [
                    {**kwargs, **_base_kwargs}
                    for kwargs in [
                        {},
                        {"region": None, "surface3d_gdf": surface3d_gdf},
                        {"surface3d_datetime": "2019"},
                        {"count_threshold": 48},
                        {"dst_res": 2},
                        {"dst_tree_val": 255, "dst_dtype": "int16", "dst_nodata": -255},
                    ]
                ],
                keyword_only=True,
            )
            # test wrong datetime
            self._test_wrong_datetime(
                swisstopopy.get_tree_canopy_raster,
                {"surface3d_datetime": "2018"},
                keyword_only=True,
            )
            # output filepath for the following tests
            # test that when providing both a dir a filepath, the filepath takes
            # precedence
            ignored_dir = path.join(tmp_dir, "ignored-output")
            dst_filepath = path.join(tmp_dir, "foo.tif")
            swisstopopy.get_tree_canopy_raster(
                region=self.region,
                dst_filepath=dst_filepath,
                dst_dir=ignored_dir,
                **_base_kwargs,
            )
            self.assertFalse(path.exists(ignored_dir))
            self._test_dst_raster(dst_filepath)
            # test providing dst_dir only
            dst_dir = path.join(tmp_dir, "tree-canopy")
            swisstopopy.get_tree_canopy_raster(
                region=self.region,
                dst_dir=dst_dir,
                **_base_kwargs,
            )
            # test that dst_dir exists
            self.assertTrue(path.exists(dst_dir))
            # test that dst_dir contains valid tif files
            tif_filepaths = glob.glob(path.join(dst_dir, "*.tif"))
            self.assertGreater(
                len(tif_filepaths), 0, "Expected at least one .tif file in dst_dir."
            )
            for tif_filepath in tif_filepaths:
                # test that tif_filepath is a file
                self.assertTrue(
                    path.isfile(tif_filepath),
                    f"Expected {tif_filepath} to be a file.",
                )
                # test that tif_filepath is a valid raster
                self._test_dst_raster(tif_filepath)

    @pytest.mark.usefixtures("unload_pdal")
    def test_tree_canopy_no_pdal(self):
        # test that calling `get_tree_canopy_raster` without pdal installed returns None
        # and logs a warning
        with tempfile.TemporaryDirectory() as tmp_dir:
            dst_filepath = path.join(tmp_dir, "foo.tif")
            with self.assertLogs(level=lg.WARNING) as cm:
                result = swisstopopy.get_tree_canopy_raster(
                    region=self.region,
                    dst_filepath=dst_filepath,
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
