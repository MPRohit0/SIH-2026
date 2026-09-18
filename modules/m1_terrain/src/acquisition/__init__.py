"""Module 1 data-acquisition adapters.

Adapters in this package only acquire or cache source files. They do not alter
or invoke the core terrain-processing pipeline.
"""

from .bhuvan import BhuvanAcquisitionError, BhuvanAdapter
from .sentinel2 import Sentinel2Adapter, Sentinel2AcquisitionError
from .srtm import SRTMAcquisitionError, SRTMAdapter

__all__ = [
    "BhuvanAcquisitionError",
    "BhuvanAdapter",
    "Sentinel2Adapter",
    "Sentinel2AcquisitionError",
    "SRTMAcquisitionError",
    "SRTMAdapter",
]
