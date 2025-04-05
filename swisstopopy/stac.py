"""STAC utils."""

import warnings
from collections.abc import Iterator

import geopandas as gpd
import numpy as np
import pandas as pd
import pystac_client
from pyregeon import CRSType, RegionMixin, RegionType
from pystac_client.item_search import DatetimeLike
from shapely import box

# import all constants too
# __all__ = ["get_latest", "SwissTopoClient"]


CLIENT_URL = "https://data.geo.admin.ch/api/stac/v0.9"
# CLIENT_CRS = "EPSG:4326"  # CRS used by the client
CLIENT_CRS = "OGC:CRS84"
CH_CRS = "EPSG:2056"

SWISSALTI3D_COLLECTION_ID = "ch.swisstopo.swissalti3d"
# SWISSALTI3D_CRS = "EPSG:2056"
SWISSALTI3D_NODATA = -9999
SWISSIMAGE10_COLLECTION_ID = "ch.swisstopo.swissimage-dop10"
# SWISSIMAGE10_CRS = "EPSG:2056"
SWISSIMAGE10_NODATA = 0
SWISSSURFACE3D_COLLECTION_ID = "ch.swisstopo.swisssurface3d"
# SWISSSURFACE3D_CRS = "EPSG:2056"
SWISSSURFACE3D_RASTER_COLLECTION_ID = "ch.swisstopo.swisssurface3d-raster"
# SWISSSURFACE3D_RASTER_CRS = "EPSG:2056"

# TODO: get CRS and resolution from collection's metadata, i.e.:
# `"summaries":{"proj:epsg":[2056],"eo:gsd":[2.0,0.1]}`
# TODO: do we need this? or all datasets in EPSG:2056?
# COLLECTION_CRS_DICT = {
#     SWISSSURFACE3D_RASTER_COLLECTION_ID: SWISSSURFACE3D_RASTER_CRS,
#     SWISSSURFACE3D_COLLECTION_ID: SWISSSURFACE3D_CRS,
#     SWISSALTI3D_COLLECTION_ID: SWISSALTI3D_CRS,
# }


# convert a list of STAC Items into a GeoDataFrame
# see pystac-client.readthedocs.io/en/stable/tutorials/stac-metadata-viz.html#GeoPandas
def _items_to_gdf(items: Iterator) -> gpd.GeoDataFrame:
    """Convert a list of STAC Items into a geo-data frame."""
    # TODO: use polars or stacrs to improve performance
    gdf = pd.json_normalize(list(items))
    if gdf.empty:
        # there is no data for the specified datetime, warn and return empty gdf
        warnings.warn(
            "No data available for the specified datetime and collection. Returning an "
            "empty data frame."
        )
        return gdf
    return gpd.GeoDataFrame(gdf, geometry=box(*np.array(gdf["bbox"].tolist()).T))


def _postprocess_items_gdf(items_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Swisstopo specific postprocessing of items geo-data frame."""
    base_columns = items_gdf.columns[~items_gdf.columns.str.startswith("assets.")]

    # the `json_normalize` function creates meta columns for each asset so we end up
    # with many nan columns, this function cleans them up by getting the only non-nan
    # value for each asset
    def expand_row(row):
        meta_ser = row[row.index.str.contains(row["id"])]

        split_ser = meta_ser.index.str.split(".")
        df = (
            pd.DataFrame(
                {
                    "values": meta_ser.values,
                    "meta": split_ser.str[-1].values,
                    "asset": split_ser.str[:-1].str.join("."),
                }
            )
            .pivot(columns="meta", values="values", index="asset")
            .reset_index(drop=True)
            .rename(columns=lambda col: f"assets.{col}")
        )

        return pd.concat(
            [
                _df.reset_index(drop=True)
                for _df in [
                    pd.concat(
                        [row[base_columns].to_frame().T for _ in range(len(df.index))],
                        axis="rows",
                    ),
                    df,
                ]
            ],
            axis="columns",
        )

    gdf = pd.concat(
        [expand_row(row) for _, row in items_gdf.iterrows()], ignore_index=True
    )

    # set datetime columns to datetime
    for field in ["properties.datetime", "properties.created", "properties.updated"]:
        if field in gdf:
            gdf[field] = pd.to_datetime(gdf[field])

    return gdf


def get_latest(
    collection_gdf: gpd.GeoDataFrame,
    *,
    tile_id_col: str = "id",
    datetime_col: str = "properties.datetime",
) -> gpd.GeoDataFrame:
    """Get the latest item for each tile and file metadata.

    Parameters
    ----------
    collection_gdf : geopandas.GeoDataFrame
        Collection geo-data frame.
    tile_id_col : str, default "id"
        Column name for the tile ID.
    datetime_col : str, default "properties.datetime"
        Column name for the datetime.

    Returns
    -------
    collection_gdf : geopandas.GeoDataFrame
        Collection geo-data frame with the latest item for each tile and file metadata.
    """
    by = [
        collection_gdf[tile_id_col].str.split("_").str[-1],
        collection_gdf["assets.type"],
    ]
    if "assets.eo:gsd" in collection_gdf:
        by.append(collection_gdf["assets.eo:gsd"])
    return (
        collection_gdf.sort_values(
            datetime_col,
            ascending=False,
        )
        .groupby(by)
        .first()
        .rename_axis(index={tile_id_col: "tile_id"})
        .reset_index(drop=True)
        .set_crs(collection_gdf.crs)
    )


class SwissTopoClient:
    """swisstopo client.

    Parameters
    ----------
    region : region-like
        Region to get the data for. Can any argument accepted by the pyregeon library.
    region_crs : crs-like, optional
        Coordinate reference system (CRS) of the region. Required if `region` is a naive
        geometry or a list of bounding box coordinates. Ignored if `region` already has
        a CRS.

    """

    def __init__(
        self,
        region: RegionType,
        *,
        region_crs: CRSType = None,
    ):
        """Initialize a swisstopo client."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            client = pystac_client.Client.open(CLIENT_URL)
        client.add_conforms_to("ITEM_SEARCH")
        client.add_conforms_to("COLLECTIONS")
        self._client = client

        if region is not None:
            # rather than inheriting from `RegionMixin`, we just use the
            # `_process_region_arg` static method
            self.region = (
                RegionMixin._process_region_arg(region, crs=region_crs)
                .to_crs(CLIENT_CRS)["geometry"]
                .iloc[0]
            )
        else:
            # set it to so that it passes the default `None` value to the `intersects`
            # keyword argument in `pystac_client.client.Search`.
            self.region = None

    def get_collection_gdf(
        self,
        collection_id: str,
        *,
        datetime: DatetimeLike | None = None,
        dst_crs: CRSType | None = None,
    ) -> gpd.GeoDataFrame:
        """Get geo-data frame of tiles of a collection.

        Parameters
        ----------
        collection_id : str
            Collection ID to get the data for.
        datetime : datetime-like, optional
            Datetime-like object forwarded to `pystac_client.Client.search` to filter
            the items. If None, all the items of the collection will be returned.
        dst_crs : crs-like, optional
            Coordinate reference system (CRS) of the returned geo-data frame. If None,
            the CRS of the collection tiles will be used - note that this is not
            (necessarily) the same as the CRS of the tile data itself.

        Returns
        -------
        collection_gdf : geopandas.GeoDataFrame
            Geo-data frame of the collection tiles.
        """
        if dst_crs is None:
            dst_crs = self._client.get_collection(collection_id).extra_fields["crs"][0]
        search = self._client.search(
            collections=[collection_id], intersects=self.region, datetime=datetime
        )
        gdf = _items_to_gdf(search.items_as_dicts())
        if gdf.empty:
            # the warning has already been raised in `_items_to_gdf`, do not raise it
            # again, just return an empty data frame
            # TODO: best approach to handle this? i.e., where to raise the warning?
            return gdf
        return gpd.GeoDataFrame(_postprocess_items_gdf(gdf)).set_crs(dst_crs)
