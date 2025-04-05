"""Tree canopy."""

import os
import tempfile
from collections.abc import Sequence
from os import path

import numpy as np
import numpy.typing as npt
import pdal
import pooch
import rasterio as rio
from pyregeon import CRSType, RegionType
from pystac_client.item_search import DatetimeLike
from rasterio import merge
from tqdm import tqdm

from swisstopopy import settings, stac, utils

__all__ = ["get_tree_canopy_raster"]


def rasterize_lidar(
    lidar_filepath: utils.PathType,
    dst_filepath: utils.PathType,
    lidar_values: list[int],
    **gdal_writer_kwargs,
) -> str:
    """Rasterize LiDAR file."""
    pipeline = (
        pdal.Reader(lidar_filepath)
        | pdal.Filter.expression(
            expression=" || ".join(
                [f"Classification == {value}" for value in lidar_values]
            )
        )
        | pdal.Writer.gdal(
            filename=dst_filepath,
            # resolution=dst_res,
            # output_type="count",
            # data_type="int32",
            # nodata=0,
            # default_srs=stac.SWISSALTI3D_CRS,
            **gdal_writer_kwargs,
        )
    )
    _ = pipeline.execute()
    return dst_filepath


def get_tree_canopy_raster(
    region: RegionType,
    dst_filepath: utils.PathType,
    *,
    region_crs: CRSType = None,
    surface3d_datetime: DatetimeLike | None = None,  # "2019/2019",
    count_threshold: int = 32,
    dst_res: float = 2,
    dst_tree_val: int = 1,
    dst_nodata: int = 0,
    dst_dtype: npt.DTypeLike = "uint32",
    lidar_tree_values: int | Sequence[int] | None = 3,
    cache_lidar: bool = False,
    rasterize_lidar_kwargs: utils.KwargsType = None,
    pooch_retrieve_kwargs: utils.KwargsType = None,
    rio_merge_kwargs: utils.KwargsType = None,
) -> None:
    """Get tree canopy raster.

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
    surface3d_datetime : datetime-like, optional
        Datetime to filter swissSURFACE3D data, forwarded to
        `pystac_client.Client.search`. If None, the latest data for each tile is used.
    count_threshold : int, default 32
        Minimum number of vegetation LiDAR points to consider a pixel as tree canopy.
        Depends on the target pixel resolution `dst_res`. Note that swissSURFACE3D has a
        mean point density of 15-20 pts/m^2.
    dst_res : numeric, default 2
        Target resolution of the raster.
    dst_tree_val : int, default 1
        Value to assign to tree canopy pixels.
    dst_nodata : int, default 0
        Value to assign to no data pixels.
    dst_dtype : dtype-like, default "uint32"
        Data type of the output raster.
    lidar_tree_values : int or sequence of int, default 3.
        LiDAR classification values to use for tree canopy. If None, defaults to
        the "Vegetation" class value of swissSURFACE3D, i.e., 3.
    cache_lidar : bool, default False
        Whether pooch should cache the LiDAR files. If False, the files are downloaded
        to a temporary directory.
    rasterize_lidar_kwargs, pooch_retrieve_kwargs, rio_merge_kwargs : mapping, optional
        Additional keyword arguments to respectively pass to
        `swisstopopy.tree_canopy.rasterize_lidar`, `pooch.retrieve` and
        `rasterio.merge.merge`. If the latter is None, the default values from
        `settings.RIO_MERGE_DST_KWARGS` are used.
    """
    # use the STAC API to get the tree canopy from swissSURFACE3D
    # TODO: dry with `dem.get_dem_raster`?
    # note that we need to pass the STAC client's CRS to both `_process_region_arg` and
    # `to_crs`, because `region` may have another CRS and we need the extend in the
    # client's CRS
    client = stac.SwissTopoClient(region, region_crs=region_crs)
    surface3d_gdf = client.get_collection_gdf(
        stac.SWISSSURFACE3D_COLLECTION_ID,
        datetime=surface3d_datetime,
    )
    if surface3d_gdf.empty:
        raise ValueError(
            "Cannot compute tree canopy raster: no data available for the specified "
            "region and datetime."
        )

    # filter to get zip assets (LiDAR) only
    surface3d_gdf = surface3d_gdf[surface3d_gdf["assets.href"].str.endswith(".zip")]

    # if no datetime specified, get the latest data for each tile (location)
    if surface3d_datetime is None:
        surface3d_gdf = stac.get_latest(surface3d_gdf)

    if rasterize_lidar_kwargs is None:
        _rasterize_lidar_kwargs = {}
    else:
        _rasterize_lidar_kwargs = rasterize_lidar_kwargs.copy()

    _rasterize_lidar_kwargs.update(
        resolution=dst_res,
        output_type="count",
        data_type="uint32",
        nodata=0,
        default_srs=stac.CH_CRS,
    )
    if pooch_retrieve_kwargs is None:
        pooch_retrieve_kwargs = {}

    if isinstance(lidar_tree_values, int):
        lidar_tree_values = [lidar_tree_values]

    if rio_merge_kwargs is None:
        _rio_merge_kwargs = {}
    else:
        _rio_merge_kwargs = rio_merge_kwargs.copy()
    _rio_merge_kwargs.update(dst_kwds=settings.RIO_MERGE_DST_KWARGS)

    img_filepaths = []
    with tempfile.TemporaryDirectory() as tmp_dir:
        _pooch_retrieve_kwargs = pooch_retrieve_kwargs.copy()
        working_dir = _pooch_retrieve_kwargs.pop("path", tmp_dir)
        if cache_lidar:
            las_dir = working_dir
        else:
            las_dir = tmp_dir
        for url in tqdm(surface3d_gdf["assets.href"]):
            # we need to splitext twice because of the .las.zip extension
            img_filepath = path.join(
                working_dir,
                f"{path.splitext(path.splitext(path.basename(url))[0])[0]}.tif",
            )
            # allow resuming
            if not path.exists(img_filepath):
                # download the LiDAR data
                las_filepath = pooch.retrieve(
                    url,
                    known_hash=None,
                    processor=pooch.Unzip(),
                    path=las_dir,
                    **_pooch_retrieve_kwargs,
                )[0]  # only one file (i.e., the .las) is expected
                # use an interim filepath to save the counts, then transform to uint8
                counts_filepath = path.join(
                    tmp_dir,
                    f"{path.splitext(path.basename(img_filepath))[0]}-counts.tif",
                )
                _ = rasterize_lidar(
                    las_filepath,
                    counts_filepath,
                    lidar_tree_values,
                    **_rasterize_lidar_kwargs,
                )

                try:
                    _ = rasterize_lidar(
                        las_filepath,
                        counts_filepath,
                        lidar_tree_values,
                        **_rasterize_lidar_kwargs,
                    )
                except RuntimeError:
                    # some tiles may intersect with the buffered region but not contain
                    # any tree. Skip them.
                    continue
                with rio.open(counts_filepath) as src:
                    meta = src.meta.copy()
                    meta.update(dtype=dst_dtype)
                    with rio.open(img_filepath, "w", **meta) as dst:
                        dst.write(
                            np.where(
                                src.read(1) > count_threshold,
                                dst_tree_val,
                                dst_nodata,
                            ),
                            1,
                        )
                # remove the interim counts file
                os.remove(counts_filepath)
            # add path to list
            img_filepaths.append(img_filepath)

        # merge tiles into the final raster
        merge.merge(
            img_filepaths,
            dst_path=dst_filepath,
            **_rio_merge_kwargs,
        )
