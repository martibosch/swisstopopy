"""Utilities."""

import os
from collections.abc import Mapping

########################################################################################
# type annotations
# type hint for path-like objects
PathType = str | os.PathLike
# type hint for keyword arguments
KwargsType = Mapping | None
