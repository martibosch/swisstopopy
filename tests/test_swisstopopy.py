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

        # since this is slow, test init one collection only
        collection_id = self.collection_ids[0]
        gdf = client.gdf_from_collection(collection_id)

        # test with region
        region_client = swisstopopy.SwissTopoClient(region=self.nominatim_query)
        # test that there are at most as many items as when not filtering spatially
        self.assertLessEqual(
            len(region_client.gdf_from_collection(collection_id).index), len(gdf.index)
        )
        # test init all collections
        for collection_id in self.collection_ids:
            gdf = region_client.gdf_from_collection(collection_id)
            # test that we get a non empty geo-data frame
            self.assertIsInstance(gdf, gpd.GeoDataFrame)
            self.assertFalse(gdf.empty)
