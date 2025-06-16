[![PyPI version fury.io](https://badge.fury.io/py/swisstopopy.svg)](https://pypi.python.org/pypi/swisstopopy/)
[![Documentation Status](https://readthedocs.org/projects/swisstopopy/badge/?version=latest)](https://swisstopopy.readthedocs.io/en/latest/?badge=latest)
[![CI/CD](https://github.com/martibosch/swisstopopy/actions/workflows/tests.yml/badge.svg)](https://github.com/martibosch/swisstopopy/blob/main/.github/workflows/tests.yml)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/martibosch/swisstopopy/main.svg)](https://results.pre-commit.ci/latest/github/martibosch/swisstopopy/main)
[![codecov](https://codecov.io/gh/martibosch/swisstopopy/branch/main/graph/badge.svg?token=KXJYk4KcNs)](https://codecov.io/gh/martibosch/swisstopopy)
[![GitHub license](https://img.shields.io/github/license/martibosch/swisstopopy.svg)](https://github.com/martibosch/swisstopopy/blob/main/LICENSE)

# swisstopopy

swisstopo geospatial Python utilities.

## Features

### STAC API utilities

Easily filter swisstopo STAC collections based on geospatial extents, dates, file extensions or data resolutions:

```python
import contextily as cx
import swisstopopy

region = "EPFL"
client = swisstopopy.SwissTopoClient(region)

alti3d_gdf = client.get_collection_gdf(
    swisstopopy.SWISSALTI3D_COLLECTION_ID,
)
ax = alti3d_gdf.plot(alpha=0.1)
cx.add_basemap(ax, crs=alti3d_gdf.crs)
```

![tiles](https://github.com/martibosch/swisstopopy/raw/main/figures/tiles.png)

Filter to get the latest data for each tile:

```python
latest_alti3d_gdf = swisstopopy.get_latest(alti3d_gdf)
latest_alti3d_gdf.head()
```

|     | id                         | collection               | ... | geometry                                          |
| --- | -------------------------- | ------------------------ | --- | ------------------------------------------------- |
| 0   | swissalti3d_2021_2532-1151 | ch.swisstopo.swissalti3d | ... | POLYGON ((6.56572 46.50684, 6.56572 46.51594, ... |
| 1   | swissalti3d_2021_2532-1151 | ch.swisstopo.swissalti3d | ... | POLYGON ((6.56572 46.50684, 6.56572 46.51594, ... |
| 2   | swissalti3d_2021_2532-1151 | ch.swisstopo.swissalti3d | ... | POLYGON ((6.56572 46.50684, 6.56572 46.51594, ... |
| 3   | swissalti3d_2021_2532-1151 | ch.swisstopo.swissalti3d | ... | POLYGON ((6.56572 46.50684, 6.56572 46.51594, ... |
| 4   | swissalti3d_2021_2532-1152 | ch.swisstopo.swissalti3d | ... | POLYGON ((6.56558 46.51584, 6.56558 46.52493, ... |

or filter by other metadata attributes such as ground resolution and/or file extensions:

```python
alti3d_gdf[
    (alti3d_gdf["assets.eo:gsd"] == 0.5)
    & alti3d_gdf["assets.href"].str.endswith(".tif")
]
```

|     | id                         | collection               | ... | geometry                                          |
| --- | -------------------------- | ------------------------ | --- | ------------------------------------------------- |
| 0   | swissalti3d_2019_2532-1151 | ch.swisstopo.swissalti3d | ... | POLYGON ((6.56572 46.50684, 6.56572 46.51594, ... |
| 4   | swissalti3d_2019_2532-1152 | ch.swisstopo.swissalti3d | ... | POLYGON ((6.56558 46.51584, 6.56558 46.52493, ... |
| 8   | swissalti3d_2019_2533-1152 | ch.swisstopo.swissalti3d | ... | POLYGON ((6.57861 46.51594, 6.57861 46.52503, ... |
| 12  | swissalti3d_2021_2532-1151 | ch.swisstopo.swissalti3d | ... | POLYGON ((6.56572 46.50684, 6.56572 46.51594, ... |
| 16  | swissalti3d_2021_2532-1152 | ch.swisstopo.swissalti3d | ... | POLYGON ((6.56558 46.51584, 6.56558 46.52493, ... |
| 20  | swissalti3d_2021_2533-1152 | ch.swisstopo.swissalti3d | ... | POLYGON ((6.57861 46.51594, 6.57861 46.52503, ... |

### STAC data processing

Automated generation of geospatial datasets: building footprints with estimated heights, DEM and tree canopy. For example, a tree canopy raster for any given part of Switzerland can be obtained as in:

```python
import rasterio as rio
from rasterio import plot

dst_filepath = "tree-canopy.tif"
swisstopopy.get_tree_canopy_raster(region, dst_filepath)

with rio.open(dst_filepath) as src:
    plot.show(src)
```

![tree-canopy](https://github.com/martibosch/swisstopopy/raw/main/figures/tree-canopy.png)

See the [overview notebook](https://swisstopopy.readthedocs.io/en/latest/overview.html) and the [API documentation](https://swisstopopy.readthedocs.io/en/latest/api.html) for more details on the geospatial dataset generation functions.

## Installation

Like many other geospatial Python packages, swisstopopy requires many base C libraries that cannot be installed with pip. Accordingly, the best way to install swisstopopy is to use conda/mamba, i.e., in a given conda environment, run:

```bash
# or mamba install -c conda-forge geopandas
conda install -c conda-forge geopandas
```

Within the same conda environment, you can then install swisstopopy using pip:

```bash
pip install swisstopopy
```

Note that the `get_tree_canopy_raster` requires [PDAL and its Python bindings](https://pdal.io/en/2.8.4/python.html), which are not installed by default with swisstopopy. Like with geopandas, the [easiest way to install such requirements is using conda/mamba](https://pdal.io/en/latest/python.html#install-using-conda), e.g.: `conda install -c conda-forge python-pdal`.

## Notes

The `SwissTopoClient` class can be used to process any collection of the [swisstopo STAC API](https://www.geo.admin.ch/en/rest-interface-stac-api), and basic features succh as geospatial and datetime filtering should work out of the box. However, filtering based on further metadata such as the resolution is only fully supported for the following collections:

- "ch.swisstopo.swissalti3d", namely [swissALTI3D](https://www.swisstopo.admin.ch/en/height-model-swissalti3d)
- "ch.swisstopo.swissimage-dop10", namely [SWISSIMAGE 10 cm](https://www.swisstopo.admin.ch/en/orthoimage-swissimage-10)
- "ch.swisstopo.swisssurface3d", namely [swissSURFACE3D](https://www.swisstopo.admin.ch/en/height-model-swisssurface3d)
- "ch.swisstopo.swisssurface3d-raster", namely [swissSURFACE3D Raster](https://www.swisstopo.admin.ch/en/height-model-swisssurface3d-raster).

## Acknowledgements

- This package was created with the [martibosch/cookiecutter-geopy-package](https://github.com/martibosch/cookiecutter-geopy-package) project template.
