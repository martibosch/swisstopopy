"""Digital elevation model (DEM).

Generate a DEM for a region using the swissALTI3D product of the swisstopo STAC API.
"""

import pooch
from pyregeon import CRSType, RegionType
from pystac_client.item_search import DatetimeLike
from rasterio import merge
from tqdm import tqdm

from swisstopopy import settings, stac, utils

__all__ = ["get_dem_raster"]


def get_dem_raster(
    region: RegionType,
    dst_filepath: utils.PathType,
    *,
    region_crs: CRSType = None,
    alti3d_datetime: DatetimeLike | None = None,
    alti3d_res: float = 0.5,
    pooch_retrieve_kwargs: utils.KwargsType = None,
    rio_merge_kwargs: utils.KwargsType = None,
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
    alti3d_res : {0.5, 2}, default 0.5
        Resolution of the swissALTI3D data to get, can be 0.5 or 2 (meters).
    pooch_retrieve_kwargs, rio_merge_kwargs : mapping, optional
        Additional keyword arguments to respectively pass to `pooch.retrieve` and
        `rasterio.merge.merge`.  If the latter is None, the default values from
        `settings.RIO_MERGE_DST_KWARGS` are used.
    """
    # use the STAC API to get the DEM from swissALTI3D
    client = stac.SwissTopoClient(region, region_crs=region_crs)
    alti3d_gdf = client.get_collection_gdf(
        stac.SWISSALTI3D_COLLECTION_ID,
        datetime=alti3d_datetime,
    )
    if alti3d_gdf.empty:
        raise ValueError(
            "Cannot compute DEM raster: no data available for the specified region and "
            "datetime."
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

    if rio_merge_kwargs is None:
        _rio_merge_kwargs = {}
    else:
        _rio_merge_kwargs = rio_merge_kwargs.copy()
    _rio_merge_kwargs.update(dst_kwds=settings.RIO_MERGE_DST_KWARGS)

    img_filepaths = []
    for url in tqdm(
        alti3d_gdf["assets.href"],
    ):
        img_filepath = pooch.retrieve(url, known_hash=None, **pooch_retrieve_kwargs)
        img_filepaths.append(img_filepath)
    # merge the images into the final raster
    merge.merge(
        img_filepaths,
        dst_path=dst_filepath,
        **_rio_merge_kwargs,
    )
