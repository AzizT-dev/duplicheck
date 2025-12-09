# -*- coding: utf-8 -*-
"""
DupliCheck - Core Package
==============================

Core detection and processing modules.
"""

from .detector import DuplicateDetector, DuplicateGroup
from .geometry_checker import GeometryChecker
from .attribute_checker import AttributeChecker
from .priority_resolver import PriorityResolver
from .exporter import ResultExporter

__all__ = [
    'DuplicateDetector',
    'DuplicateGroup',
    'GeometryChecker',
    'AttributeChecker',
    'PriorityResolver',
    'ResultExporter'
]
