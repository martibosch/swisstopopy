"""Documentation configuration."""

import os
import sys

import pkg_resources

project = "swisstopopy"
author = "Martí Bosch"

release = pkg_resources.get_distribution("swisstopopy").version
version = ".".join(release.split(".")[:2])


extensions = [
    "myst_parser",
    "nbsphinx",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
]

autodoc_typehints = "description"
html_theme = "pydata_sphinx_theme"
html_theme_options = {
    "github_url": "https://github.com/martibosch/swisstopopy",
}

# add module to path
sys.path.insert(0, os.path.abspath(".."))

# do NOT execute notebooks
nbsphinx_execute = "never"
