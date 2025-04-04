"""Tests for swisstopopy."""

import unittest

import geopandas as gpd

import swisstopopy


class TestSTACClient(unittest.TestCase):
    def setUp(self):
        self.nominatim_query = "Pully, Switzerland"
        self.collection_ids = [
            swisstopopy.SWISSALTI3D_COLLECTION_ID,
            swisstopopy.SWISSIMAGE10_COLLECTION_ID,
            swisstopopy.SWISSSURFACE3D_COLLECTION_ID,
            swisstopopy.SWISSSURFACE3D_RASTER_COLLECTION_ID,
        ]

    def test_region(self):
        # test without region (all collection items)
        client = swisstopopy.SwissTopoClient()

        # test init all collections
        for collection_id in self.collection_ids:
            gdf = client.gdf_from_collection(collection_id)
            # test that we get a non empty geo-data frame
            self.assertIsInstance(gdf, gpd.GeoDataFrame)
            self.assertFalse(gdf.empty)

        # now only test one collection (the last one)
        region_client = swisstopopy.SwissTopoClient(self.region)
        # test that there are at most as many items as when not filtering spatially
        self.assertLessEqual(
            len(region_client.gdf_from_collection(collection_id).index), len(gdf.index)
        )
