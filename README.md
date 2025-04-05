[![PyPI version fury.io](https://badge.fury.io/py/swisstopopy.svg)](https://pypi.python.org/pypi/swisstopopy/)
[![Documentation Status](https://readthedocs.org/projects/swisstopopy/badge/?version=latest)](https://swisstopopy.readthedocs.io/en/latest/?badge=latest)
[![CI/CD](https://github.com/martibosch/swisstopopy/actions/workflows/tests.yml/badge.svg)](https://github.com/martibosch/swisstopopy/blob/main/.github/workflows/tests.yml)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/martibosch/swisstopopy/main.svg)](https://results.pre-commit.ci/latest/github/martibosch/swisstopopy/main)
[![codecov](https://codecov.io/gh/martibosch/swisstopopy/branch/main/graph/badge.svg?token=hKoSSRn58a)](https://codecov.io/gh/martibosch/swisstopopy)
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

<div>
    <table border="1" class="dataframe">
	<thead>
	    <tr style="text-align: right;">
		<th></th>
		<th>id</th>
		<th>collection</th>
		<th>type</th>
		<th>stac_version</th>
		<th>bbox</th>
		<th>stac_extensions</th>
		<th>links</th>
		<th>geometry.type</th>
		<th>geometry.coordinates</th>
		<th>properties.datetime</th>
		<th>properties.created</th>
		<th>properties.updated</th>
		<th>geometry</th>
		<th>assets.checksum:multihash</th>
		<th>assets.created</th>
		<th>assets.eo:gsd</th>
		<th>assets.href</th>
		<th>assets.proj:epsg</th>
		<th>assets.type</th>
		<th>assets.updated</th>
	    </tr>
	</thead>
	<tbody>
	    <tr>
		<th>0</th>
		<td>swissalti3d_2021_2532-1151</td>
		<td>ch.swisstopo.swissalti3d</td>
		<td>Feature</td>
		<td>0.9.0</td>
		<td>[6.5525481, 46.5068432, 6.565723, 46.5159392]</td>
		<td>[https://stac-extensions.github.io/timestamps/...</td>
		<td>[{'rel': 'self', 'href': 'https://data.geo.adm...</td>
		<td>Polygon</td>
		<td>[[[6.5526955, 46.5068432], [6.565723, 46.50694...</td>
		<td>2021-01-01 00:00:00+00:00</td>
		<td>2021-09-02 16:46:12.695971+00:00</td>
		<td>2025-01-18 02:03:21.314035+00:00</td>
		<td>POLYGON ((6.56572 46.50684, 6.56572 46.51594, ...</td>
		<td>1220A1EB829DC0AEFA4B10F687F5C05FC2AA4F59F6B622...</td>
		<td>2021-09-02T19:09:22.472399Z</td>
		<td>0.5</td>
		<td>https://data.geo.admin.ch/ch.swisstopo.swissal...</td>
		<td>2056.0</td>
		<td>application/x.ascii-xyz+zip</td>
		<td>2025-01-18T00:05:10.539193Z</td>
	    </tr>
	    <tr>
		<th>1</th>
		<td>swissalti3d_2021_2532-1151</td>
		<td>ch.swisstopo.swissalti3d</td>
		<td>Feature</td>
		<td>0.9.0</td>
		<td>[6.5525481, 46.5068432, 6.565723, 46.5159392]</td>
		<td>[https://stac-extensions.github.io/timestamps/...</td>
		<td>[{'rel': 'self', 'href': 'https://data.geo.adm...</td>
		<td>Polygon</td>
		<td>[[[6.5526955, 46.5068432], [6.565723, 46.50694...</td>
		<td>2021-01-01 00:00:00+00:00</td>
		<td>2021-09-02 16:46:12.695971+00:00</td>
		<td>2025-01-18 02:03:21.314035+00:00</td>
		<td>POLYGON ((6.56572 46.50684, 6.56572 46.51594, ...</td>
		<td>12203761E09265F46BC92A89AB60D7003202574ADBED5B...</td>
		<td>2021-09-02T16:46:13.207732Z</td>
		<td>2.0</td>
		<td>https://data.geo.admin.ch/ch.swisstopo.swissal...</td>
		<td>2056.0</td>
		<td>application/x.ascii-xyz+zip</td>
		<td>2025-01-17T23:06:08.845852Z</td>
	    </tr>
	    <tr>
		<th>2</th>
		<td>swissalti3d_2021_2532-1151</td>
		<td>ch.swisstopo.swissalti3d</td>
		<td>Feature</td>
		<td>0.9.0</td>
		<td>[6.5525481, 46.5068432, 6.565723, 46.5159392]</td>
		<td>[https://stac-extensions.github.io/timestamps/...</td>
		<td>[{'rel': 'self', 'href': 'https://data.geo.adm...</td>
		<td>Polygon</td>
		<td>[[[6.5526955, 46.5068432], [6.565723, 46.50694...</td>
		<td>2021-01-01 00:00:00+00:00</td>
		<td>2021-09-02 16:46:12.695971+00:00</td>
		<td>2025-01-18 02:03:21.314035+00:00</td>
		<td>POLYGON ((6.56572 46.50684, 6.56572 46.51594, ...</td>
		<td>1220B9AD77D6DD070409D209F5ADF17EC7253FC3FE6CEE...</td>
		<td>2021-09-03T00:35:29.891683Z</td>
		<td>0.5</td>
		<td>https://data.geo.admin.ch/ch.swisstopo.swissal...</td>
		<td>2056.0</td>
		<td>image/tiff; application=geotiff; profile=cloud...</td>
		<td>2025-01-18T01:04:21.184877Z</td>
	    </tr>
	    <tr>
		<th>3</th>
		<td>swissalti3d_2021_2532-1151</td>
		<td>ch.swisstopo.swissalti3d</td>
		<td>Feature</td>
		<td>0.9.0</td>
		<td>[6.5525481, 46.5068432, 6.565723, 46.5159392]</td>
		<td>[https://stac-extensions.github.io/timestamps/...</td>
		<td>[{'rel': 'self', 'href': 'https://data.geo.adm...</td>
		<td>Polygon</td>
		<td>[[[6.5526955, 46.5068432], [6.565723, 46.50694...</td>
		<td>2021-01-01 00:00:00+00:00</td>
		<td>2021-09-02 16:46:12.695971+00:00</td>
		<td>2025-01-18 02:03:21.314035+00:00</td>
		<td>POLYGON ((6.56572 46.50684, 6.56572 46.51594, ...</td>
		<td>122093E32E6D175B9F148409FCAA8708073303A8E94A8E...</td>
		<td>2021-09-03T01:36:23.594881Z</td>
		<td>2.0</td>
		<td>https://data.geo.admin.ch/ch.swisstopo.swissal...</td>
		<td>2056.0</td>
		<td>image/tiff; application=geotiff; profile=cloud...</td>
		<td>2025-01-18T02:03:21.314035Z</td>
	    </tr>
	    <tr>
		<th>4</th>
		<td>swissalti3d_2021_2532-1152</td>
		<td>ch.swisstopo.swissalti3d</td>
		<td>Feature</td>
		<td>0.9.0</td>
		<td>[6.5524006, 46.5158382, 6.5655778, 46.5249343]</td>
		<td>[https://stac-extensions.github.io/timestamps/...</td>
		<td>[{'rel': 'self', 'href': 'https://data.geo.adm...</td>
		<td>Polygon</td>
		<td>[[[6.5525481, 46.5158382], [6.5655778, 46.5159...</td>
		<td>2021-01-01 00:00:00+00:00</td>
		<td>2021-09-02 16:56:28.144164+00:00</td>
		<td>2025-01-18 02:16:20.318007+00:00</td>
		<td>POLYGON ((6.56558 46.51584, 6.56558 46.52493, ...</td>
		<td>122020D17CB98AAE4FECDBC563D0673AF8797EFD2D74C6...</td>
		<td>2021-09-02T20:24:35.219858Z</td>
		<td>0.5</td>
		<td>https://data.geo.admin.ch/ch.swisstopo.swissal...</td>
		<td>2056.0</td>
		<td>application/x.ascii-xyz+zip</td>
		<td>2025-01-18T00:17:16.038110Z</td>
	    </tr>
	</tbody>
    </table>
</div>

or filter by other metadata attributes such as ground resolution and/or file extensions:

```python
alti3d_gdf[
    (alti3d_gdf["assets.eo:gsd"] == 0.5)
    & alti3d_gdf["assets.href"].str.endswith(".tif")
]
```

<div>
    <table border="1" class="dataframe">
	<thead>
	    <tr style="text-align: right;">
		<th></th>
		<th>id</th>
		<th>collection</th>
		<th>type</th>
		<th>stac_version</th>
		<th>bbox</th>
		<th>stac_extensions</th>
		<th>links</th>
		<th>geometry.type</th>
		<th>geometry.coordinates</th>
		<th>properties.datetime</th>
		<th>properties.created</th>
		<th>properties.updated</th>
		<th>geometry</th>
		<th>assets.checksum:multihash</th>
		<th>assets.created</th>
		<th>assets.eo:gsd</th>
		<th>assets.href</th>
		<th>assets.proj:epsg</th>
		<th>assets.type</th>
		<th>assets.updated</th>
	    </tr>
	</thead>
	<tbody>
	    <tr>
		<th>0</th>
		<td>swissalti3d_2019_2532-1151</td>
		<td>ch.swisstopo.swissalti3d</td>
		<td>Feature</td>
		<td>0.9.0</td>
		<td>[6.5525481, 46.5068432, 6.565723, 46.5159392]</td>
		<td>[https://stac-extensions.github.io/timestamps/...</td>
		<td>[{'rel': 'self', 'href': 'https://data.geo.adm...</td>
		<td>Polygon</td>
		<td>[[[6.5526955, 46.5068432], [6.565723, 46.50694...</td>
		<td>2019-01-01 00:00:00+00:00</td>
		<td>2021-02-10 10:47:06.111266+00:00</td>
		<td>2025-01-16 14:51:17.195380+00:00</td>
		<td>POLYGON ((6.56572 46.50684, 6.56572 46.51594, ...</td>
		<td>1220BEF35C33758E7EA4744487F4D8248AABFD50018615...</td>
		<td>2021-02-10T10:47:06.715269Z</td>
		<td>0.5</td>
		<td>https://data.geo.admin.ch/ch.swisstopo.swissal...</td>
		<td>2056.0</td>
		<td>image/tiff; application=geotiff; profile=cloud...</td>
		<td>2025-01-14T19:16:07.401260Z</td>
	    </tr>
	    <tr>
		<th>4</th>
		<td>swissalti3d_2019_2532-1152</td>
		<td>ch.swisstopo.swissalti3d</td>
		<td>Feature</td>
		<td>0.9.0</td>
		<td>[6.5524006, 46.5158382, 6.5655778, 46.5249343]</td>
		<td>[https://stac-extensions.github.io/timestamps/...</td>
		<td>[{'rel': 'self', 'href': 'https://data.geo.adm...</td>
		<td>Polygon</td>
		<td>[[[6.5525481, 46.5158382], [6.5655778, 46.5159...</td>
		<td>2019-01-01 00:00:00+00:00</td>
		<td>2021-02-10 10:49:41.964859+00:00</td>
		<td>2025-01-16 15:06:19.535010+00:00</td>
		<td>POLYGON ((6.56558 46.51584, 6.56558 46.52493, ...</td>
		<td>12205790D9862A7BFB265E59B08814D8E44227441DD80B...</td>
		<td>2021-02-10T10:49:42.615492Z</td>
		<td>0.5</td>
		<td>https://data.geo.admin.ch/ch.swisstopo.swissal...</td>
		<td>2056.0</td>
		<td>image/tiff; application=geotiff; profile=cloud...</td>
		<td>2025-01-14T19:26:09.858728Z</td>
	    </tr>
	    <tr>
		<th>8</th>
		<td>swissalti3d_2019_2533-1152</td>
		<td>ch.swisstopo.swissalti3d</td>
		<td>Feature</td>
		<td>0.9.0</td>
		<td>[6.5654325, 46.5159392, 6.5786075, 46.5250338]</td>
		<td>[https://stac-extensions.github.io/timestamps/...</td>
		<td>[{'rel': 'self', 'href': 'https://data.geo.adm...</td>
		<td>Polygon</td>
		<td>[[[6.5655778, 46.5159392], [6.5786075, 46.5160...</td>
		<td>2019-01-01 00:00:00+00:00</td>
		<td>2021-02-10 10:49:43.859413+00:00</td>
		<td>2025-01-16 15:06:20.632461+00:00</td>
		<td>POLYGON ((6.57861 46.51594, 6.57861 46.52503, ...</td>
		<td>1220788F6FB6067294E92CE78ACBC070B25CB9632D5910...</td>
		<td>2021-02-10T10:49:44.535488Z</td>
		<td>0.5</td>
		<td>https://data.geo.admin.ch/ch.swisstopo.swissal...</td>
		<td>2056.0</td>
		<td>image/tiff; application=geotiff; profile=cloud...</td>
		<td>2025-01-14T19:26:10.809428Z</td>
	    </tr>
	    <tr>
		<th>12</th>
		<td>swissalti3d_2021_2532-1151</td>
		<td>ch.swisstopo.swissalti3d</td>
		<td>Feature</td>
		<td>0.9.0</td>
		<td>[6.5525481, 46.5068432, 6.565723, 46.5159392]</td>
		<td>[https://stac-extensions.github.io/timestamps/...</td>
		<td>[{'rel': 'self', 'href': 'https://data.geo.adm...</td>
		<td>Polygon</td>
		<td>[[[6.5526955, 46.5068432], [6.565723, 46.50694...</td>
		<td>2021-01-01 00:00:00+00:00</td>
		<td>2021-09-02 16:46:12.695971+00:00</td>
		<td>2025-01-18 02:03:21.314035+00:00</td>
		<td>POLYGON ((6.56572 46.50684, 6.56572 46.51594, ...</td>
		<td>1220B9AD77D6DD070409D209F5ADF17EC7253FC3FE6CEE...</td>
		<td>2021-09-03T00:35:29.891683Z</td>
		<td>0.5</td>
		<td>https://data.geo.admin.ch/ch.swisstopo.swissal...</td>
		<td>2056.0</td>
		<td>image/tiff; application=geotiff; profile=cloud...</td>
		<td>2025-01-18T01:04:21.184877Z</td>
	    </tr>
	    <tr>
		<th>16</th>
		<td>swissalti3d_2021_2532-1152</td>
		<td>ch.swisstopo.swissalti3d</td>
		<td>Feature</td>
		<td>0.9.0</td>
		<td>[6.5524006, 46.5158382, 6.5655778, 46.5249343]</td>
		<td>[https://stac-extensions.github.io/timestamps/...</td>
		<td>[{'rel': 'self', 'href': 'https://data.geo.adm...</td>
		<td>Polygon</td>
		<td>[[[6.5525481, 46.5158382], [6.5655778, 46.5159...</td>
		<td>2021-01-01 00:00:00+00:00</td>
		<td>2021-09-02 16:56:28.144164+00:00</td>
		<td>2025-01-18 02:16:20.318007+00:00</td>
		<td>POLYGON ((6.56558 46.51584, 6.56558 46.52493, ...</td>
		<td>122089C474AEF62CC4692D7A944AFC0A13162D3DD8D0CF...</td>
		<td>2021-09-03T00:49:42.276133Z</td>
		<td>0.5</td>
		<td>https://data.geo.admin.ch/ch.swisstopo.swissal...</td>
		<td>2056.0</td>
		<td>image/tiff; application=geotiff; profile=cloud...</td>
		<td>2025-01-18T01:18:11.426964Z</td>
	    </tr>
	    <tr>
		<th>20</th>
		<td>swissalti3d_2021_2533-1152</td>
		<td>ch.swisstopo.swissalti3d</td>
		<td>Feature</td>
		<td>0.9.0</td>
		<td>[6.5654325, 46.5159392, 6.5786075, 46.5250338]</td>
		<td>[https://stac-extensions.github.io/timestamps/...</td>
		<td>[{'rel': 'self', 'href': 'https://data.geo.adm...</td>
		<td>Polygon</td>
		<td>[[[6.5655778, 46.5159392], [6.5786075, 46.5160...</td>
		<td>2021-01-01 00:00:00+00:00</td>
		<td>2021-09-02 16:56:34.537212+00:00</td>
		<td>2025-01-18 02:17:06.919621+00:00</td>
		<td>POLYGON ((6.57861 46.51594, 6.57861 46.52503, ...</td>
		<td>1220B8B7EA9C14DD41021131A873BD5B76DC0642CBC374...</td>
		<td>2021-09-03T00:49:54.457903Z</td>
		<td>0.5</td>
		<td>https://data.geo.admin.ch/ch.swisstopo.swissal...</td>
		<td>2056.0</td>
		<td>image/tiff; application=geotiff; profile=cloud...</td>
		<td>2025-01-18T01:18:15.270233Z</td>
	    </tr>
	</tbody>
    </table>
</div>

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

You can install swisstopopy using pip:

```bash
# or pip install -e git+ssh://git@github.com/martibosch/swisstopopy
pip install https://github.com/martibosch/swisstopopy/archive/main.zip
```

Note that the `get_tree_canopy_raster` requires [PDAL and its Python bindings](https://pdal.io/en/2.8.4/python.html), which are not installed by default with swisstopopy. The [easiest way to install such requirements is using conda/mamba](https://pdal.io/en/latest/python.html#install-using-conda), e.g.: `conda install -c conda-forge python-pdal`.

## Notes

The `SwissTopoClient` class can be used to process any collection of the [swisstopo STAC API](https://www.geo.admin.ch/en/rest-interface-stac-api), and basic features succh as geospatial and datetime filtering should work out of the box. However, filtering based on further metadata such as the resolution is only fully supported for the following collections:

- "ch.swisstopo.swissalti3d", namely [swissALTI3D](https://www.swisstopo.admin.ch/en/height-model-swissalti3d)
- "ch.swisstopo.swissimage-dop10", namely [SWISSIMAGE 10 cm](https://www.swisstopo.admin.ch/en/orthoimage-swissimage-10)
- "ch.swisstopo.swisssurface3d", namely [swissSURFACE3D](https://www.swisstopo.admin.ch/en/height-model-swisssurface3d)
- "ch.swisstopo.swisssurface3d-raster", namely [swissSURFACE3D Raster](https://www.swisstopo.admin.ch/en/height-model-swisssurface3d-raster).

## Acknowledgements

- This package was created with the [martibosch/cookiecutter-geopy-package](https://github.com/martibosch/cookiecutter-geopy-package) project template.
