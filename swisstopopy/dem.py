"""Digital elevation model (DEM).

Generate a DEM for a region using the swissALTI3D product of the swisstopo STAC API.
"""

import pooch
from osgeo import gdal
from pyregeon import CRSType, RegionType
from pystac_client.item_search import DatetimeLike
from tqdm import tqdm

from swisstopopy import stac, utils

__all__ = ["get_dem_raster"]

DST_OPTIONS = ["TILED:YES"]


def get_dem_raster(
    region: RegionType,
    dst_filepath: utils.PathType,
    *,
    region_crs: CRSType = None,
    alti3d_datetime: DatetimeLike | None = None,
    alti3d_res: float = 2,
    pooch_retrieve_kwargs: utils.KwargsType = None,
    gdal_warp_kwargs: utils.KwargsType = None,
) -> None:
    """Get digital elevation model (DEM) raster.

    Parameters
    ----------
    region : region-like
        Region to get the data for. Can any argument accepted by the pyregeon library.
    dst_filepath : path-like
        Output file path to save the raster to.
    region_crs : crs-like, optional
        Coordinate reference system (CRS) of the region. Required if `region` is a naive
        geometry or a list of bounding box coordinates. Ignored if `region` already has
        a CRS.
    alti3d_datetime : datetime-like, optional
        Datetime to filter swissALTI3D data, forwarded to `pystac_client.Client.search`.
        If None, the latest data for each tile is used.
    alti3d_res : {0.5, 2}, default 2
        Resolution of the swissALTI3D data to get, can be 0.5 or 2 (meters).
    pooch_retrieve_kwargs, gdal_warp_kwargs : mapping, optional
        Additional keyword arguments to respectively pass to `pooch.retrieve` and
        `gdal.Warp`.
    """
    # use the STAC API to get the DEM from swissALTI3D
    # TODO: dry with `tree_canopy.get_tree_canopy_raster`?
    # note that we need to reproject the data to the STAC client CRS
    client = stac.SwissTopoClient()
    alti3d_gdf = client.gdf_from_collection(
        stac.SWISSALTI3D_COLLECTION_ID,
        region=region,
        datetime=alti3d_datetime,
    )

    # filter to get tiff images only
    alti3d_gdf = alti3d_gdf[alti3d_gdf["assets.href"].str.endswith(".tif")]
    # filter to get the resolution data at the specified resolution
    alti3d_gdf = alti3d_gdf[alti3d_gdf["assets.eo:gsd"] == alti3d_res]
    # if no datetime specified, get the latest data for each tile (location)
    if alti3d_datetime is None:
        alti3d_gdf = stac.get_latest(alti3d_gdf)

    if pooch_retrieve_kwargs is None:
        pooch_retrieve_kwargs = {}

    if gdal_warp_kwargs is None:
        _gdal_warp_kwargs = {}
    else:
        _gdal_warp_kwargs = gdal_warp_kwargs.copy()
    _gdal_warp_kwargs.update(creationOptions=DST_OPTIONS)

    img_filepaths = []
    for url in tqdm(
        alti3d_gdf["assets.href"],
    ):
        img_filepath = pooch.retrieve(url, known_hash=None, **pooch_retrieve_kwargs)
        img_filepaths.append(img_filepath)
    _ = gdal.Warp(dst_filepath, img_filepaths, format="GTiff", **_gdal_warp_kwargs)
