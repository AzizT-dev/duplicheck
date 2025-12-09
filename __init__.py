# -*- coding: utf-8 -*-
"""
DupliCheck - Interactive Duplicate Detection and Management
============================================================

A QGIS plugin for detecting and managing duplicate features in vector layers.
Provides interactive control over which features to keep or remove.

Author: Aziz TRAORE
Copyright: (C) 2024-2025
License: GNU General Public License v3
"""


def classFactory(iface):
    """
    Load the DupliCheck plugin.
    
    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    :returns: Plugin instance
    :rtype: DupliCheck
    """
    from .plugin import DupliCheck
    return DupliCheck(iface)
