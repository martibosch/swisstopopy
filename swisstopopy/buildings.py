"""Building features.

Extract building features from OpenStreetMap and height data from the swissSURFACE3D
Raster and swissALTI3D products provided by swisstopo's STAC API.
"""

import geopandas as gpd
import osmnx as ox
import pandas as pd
import pooch
import rasterio as rio
import rasterstats
from pyregeon import CRSType, RegionMixin, RegionType
from pystac_client.item_search import DatetimeLike
from tqdm import tqdm

from swisstopopy import stac, utils

tqdm.pandas()

__all__ = ["get_bldg_gdf"]

OSMNX_TAGS = {"building": True}


def _get_bldg_heights(
    bldg_gdf,
    row,
    dsm_href_col,
    dem_href_col,
    *,
    stats="mean",
    **pooch_retrieve_kwargs,
):
    dsm_img_filepath = pooch.retrieve(
        row[dsm_href_col],
        known_hash=None,
        **pooch_retrieve_kwargs,
    )
    dem_img_filepath = pooch.retrieve(
        row[dem_href_col],
        known_hash=None,
        **pooch_retrieve_kwargs,
    )
    with rio.open(dsm_img_filepath) as dsm_src:
        with rio.open(dem_img_filepath) as dem_src:
            height_arr = dsm_src.read(1) - dem_src.read(1)

        group_bldg_gser = bldg_gdf[bldg_gdf.intersects(row["geometry"])]["geometry"]
        # we could also do a try/except approach to catch rasterstats' ValueError
        if group_bldg_gser.empty:
            # # test if stats is list-like
            # if not pd.api.types.is_list_like(stats):
            #     stats = [stats]
            # return pd.DataFrame(columns=stats, index=[])
            # return `None` to avoid https://stackoverflow.com/questions/77254777/
            # alternative-to-concat-of-empty-dataframe-now-that-it-is-being-deprecated
            return None
        else:
            return pd.DataFrame(
                rasterstats.zonal_stats(
                    group_bldg_gser,
                    height_arr,
                    # we could also use `src_surface3d.transform` because it is the same
                    affine=dsm_src.transform,
                    stats=stats,
                ),
                group_bldg_gser.index,
            )


def get_bldg_gdf(
    region: RegionType,
    *,
    region_crs: CRSType = None,
    surface3d_datetime: DatetimeLike | None = None,
    alti3d_datetime: DatetimeLike | None = None,
    alti3d_res: float = 0.5,
    **pooch_retrieve_kwargs: utils.KwargsType,
) -> gpd.GeoDataFrame:
    """Get buildings geo-data frame with height information.

    Parameters
    ----------
    region : region-like
        Region to get the data for. Can any argument accepted by the pyregeon library.
    region_crs : crs-like, optional
        Coordinate reference system (CRS) of the region. Required if `region` is a naive
        geometry or a list of bounding box coordinates. Ignored if `region` already has
        a CRS.
    surface3d_datetime, alti3d_datetime : datetime-like, optional
        Datetime to filter swissSURFACE3D and swissALTI3D data respectively, forwarded
        to `pystac_client.Client.search`. If None, the latest data for each tile is
        used.
    alti3d_res : {0.5, 2}, default 2
        Resolution of the swissALTI3D data to get, can be 0.5 or 2 (meters).
    pooch_retrieve_kwargs : mapping, optional
        Additional keyword arguments to pass to `pooch.retrieve`.

    Returns
    -------
    bldg_gdf : geopandas.GeoDataFrame
        Geo-data frame with building footprints and height information.
    """
    # note that:
    # 1. we first need to project the region to OSM CRS (EPSG:4326) to query via osmnx
    # 2. we drop the "node" column to keep only the "way" and "relation" columns that
    # correspond to polygon geometries
    region_gser = RegionMixin._process_region_arg(region, crs=region_crs)
    bldg_gdf = (
        ox.features_from_polygon(
            region_gser.to_crs(ox.settings.default_crs).iloc[0],
            tags=OSMNX_TAGS,
        )
        .to_crs(stac.CH_CRS)
        .drop("node")
    )

    # use the STAC API to get building heights from swissSURFACE3D and swissALTI3D
    client = stac.SwissTopoClient(region_gser)

    # surface3d-raster (raster dsm)
    surface3d_gdf = client.gdf_from_collection(
        stac.SWISSSURFACE3D_RASTER_COLLECTION_ID,
        datetime=surface3d_datetime,
    )
    # filter to get tiff images only
    surface3d_gdf = surface3d_gdf[surface3d_gdf["assets.href"].str.endswith(".tif")]
    # if no datetime specified, get the latest data for each tile (location)
    if surface3d_datetime is None:
        surface3d_gdf = stac.get_latest(surface3d_gdf)

    # alti3d (raster dem)
    alti3d_gdf = client.gdf_from_collection(
        stac.SWISSALTI3D_COLLECTION_ID,
        datetime=alti3d_datetime,
    )
    # filter to get tiff images only
    alti3d_gdf = alti3d_gdf[alti3d_gdf["assets.href"].str.endswith(".tif")]
    # filter to get the resolution data at the specified resolution
    alti3d_gdf = alti3d_gdf[alti3d_gdf["assets.eo:gsd"] == alti3d_res]
    # if no datetime specified, get the latest data for each tile (location)
    if alti3d_datetime is None:
        alti3d_gdf = stac.get_latest(alti3d_gdf)

    # compute the building heights as zonal statistics. To that end, we first compute
    # a "building height raster" as the difference between the swissSURFACE3D (surface
    # height including natural and man-made objects) and swissALTI3D (digital elevation
    # model without vegetation and development). Then, we consider each building polygon
    # as a "zone" so that its height is the zonal average of the "building height
    # raster".

    # surface3d and alti3d have the same tiling - actually, it could be derived from the
    # filenames without need for (more expensive) spatial operations

    # we need to project the gdf of tiles to the same CRS as the actual swissSURFACE3D
    # and swissALTI3D products (again, EPSG:2056)
    tile_gdf = surface3d_gdf.sjoin(
        alti3d_gdf, how="inner", predicate="contains"
    ).to_crs(stac.CH_CRS)

    # we could do a data frame apply approach returning a series of of building heights
    # that correspond to a single zonal statistic (e.g., "mean"). However, we use
    # concatenation because this would allow us to compute multiple zonal statistics for
    # each row.
    if pooch_retrieve_kwargs is None:
        pooch_retrieve_kwargs = {}

    bldg_height_df = pd.concat(
        [
            _get_bldg_heights(
                bldg_gdf,
                row,
                "assets.href_left",
                "assets.href_right",
                **pooch_retrieve_kwargs,
            )
            for _, row in tqdm(tile_gdf.iterrows(), total=tile_gdf.shape[0])
        ]
    )

    # merge duplicates (i.e., buildings that are in multiple tiles) taking their mean
    # TODO: better approach?
    bldg_height_df = bldg_height_df.groupby(bldg_height_df.index).mean()

    # since the obtained (estimated) heights indexed by the `osmid`, it is
    # straightforward to add them as a column of the building footprint geo-data frame.
    # We further select only the columns of interest, and we remove the buildings with
    # zero or negative height - which are likely due to the mismatch between the
    # building footprint dates and the swissSURFACE3D and swissALTI3D dates (e.g.,
    # post-2019 buildings that are on OSM).
    bldg_gdf = bldg_gdf.assign(height=bldg_height_df["mean"])[["height", "geometry"]]
    return bldg_gdf[bldg_gdf["height"] > 0]
