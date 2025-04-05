"""Building features.

Extract building features from OpenStreetMap and height data from the swissSURFACE3D
Raster and swissALTI3D products provided by swisstopo's STAC API.
"""

import warnings

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
    item_datetime: DatetimeLike | None = None,
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
    item_datetime : datetime-like, optional
        Datetime to filter swissSURFACE3D Raster and swissALTI3D data to use (must be
        the same for both collections), forwarded to `pystac_client.Client.search`.
        If None, the latest data for each tile is used.
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
    region_gser = RegionMixin._process_region_arg(region, crs=region_crs)["geometry"]
    bldg_gdf = (
        ox.features_from_polygon(
            region_gser.to_crs(ox.settings.default_crs).iloc[0],
            tags=OSMNX_TAGS,
        )
        .to_crs(stac.CH_CRS)
        .drop("node", errors="ignore")
    )

    # use the STAC API to get building heights from swissSURFACE3D and swissALTI3D
    client = stac.SwissTopoClient(region_gser)

    def _get_and_process_gdf(collection_id):
        gdf = client.get_collection_gdf(
            collection_id,
            datetime=item_datetime,
        )
        if gdf.empty:
            # warn and return gdf without heights
            warnings.warn(
                f"No '{collection_id}' data available for the specified region and "
                "datetime."
            )
            return gdf
        # filter to get tiff images only
        gdf = gdf[gdf["assets.href"].str.endswith(".tif")]
        # filter to get the resolution data at the specified resolution
        # AFAIK, there is no swissSURFACE3D Raster collection with 2 m resolution, so we
        # can only set the resolution to 0.5 m
        gdf = gdf[gdf["assets.eo:gsd"] == 0.5]
        # if no datetime specified, get the latest data for each tile (location)
        if item_datetime is None:
            gdf = stac.get_latest(gdf)
        return gdf

    # surface3d-raster (raster dsm)
    surface3d_raster_gdf = _get_and_process_gdf(
        stac.SWISSSURFACE3D_RASTER_COLLECTION_ID
    )

    # alti3d (raster dem)
    alti3d_gdf = _get_and_process_gdf(
        stac.SWISSALTI3D_COLLECTION_ID,
    )

    # both collections need to have items for the selected datetimes
    if surface3d_raster_gdf.empty or alti3d_gdf.empty:
        # warn and return gdf without heights
        # note that warnings will have already been raised above, so this follows from
        # there
        warnings.warn("Returning building footprints without height information.")
        return bldg_gdf

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
    tile_gdf = surface3d_raster_gdf.sjoin(
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
