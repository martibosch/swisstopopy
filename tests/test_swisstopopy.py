"""Tests for swisstopopy."""

import tempfile
import unittest
from os import path

import geopandas as gpd
import numpy as np
import rasterio as rio

import swisstopopy


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
        for kwargs in [
            {},
            {"item_datetime": "2019"},
            {"item_res": 2},
        ]:
            bldg_gdf = swisstopopy.get_bldg_gdf(self.region, **kwargs)
            # test that we get a non empty geo-data frame
            self.assertIsInstance(bldg_gdf, gpd.GeoDataFrame)
            self.assertFalse(bldg_gdf.empty)
            # test that we get a "height" column
            self.assertIn("height", bldg_gdf.columns)

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

    def test_dem(self):
        self._test_raster(
            swisstopopy.get_dem_raster,
            [
                {},
                {"alti3d_datetime": "2019"},
                {"alti3d_res": 2},
            ],
        )

    def test_tree_canopy(self):
        self._test_raster(
            swisstopopy.get_tree_canopy_raster,
            [
                {},
                {"surface3d_datetime": "2019"},
                {"count_threshold": 48},
                {"dst_res": 2},
                {"dst_tree_val": 255},
                {"dst_dtype": "float32", "dst_nodata": np.nan},
            ],
        )
