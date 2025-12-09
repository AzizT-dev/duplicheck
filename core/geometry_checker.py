# -*- coding: utf-8 -*-
"""
DupliCheck - Geometry Checker
==================================

Handles geometric comparison of features using various methods:
- WKB hash for exact matching
- Centroid distance
- Hausdorff distance
- Bounding box overlap
"""

import hashlib
from typing import Tuple, Optional

from qgis.core import QgsGeometry, QgsWkbTypes, QgsPointXY


class GeometryChecker:
    """
    Geometry comparison utility.
    
    Provides methods for comparing geometries with configurable
    tolerance and comparison strategies.
    
    Methods:
        0 = WKB Hash (exact geometry match)
        1 = Centroid distance
        2 = Hausdorff distance
        3 = Bounding box overlap
    """
    
    # Comparison method constants
    METHOD_WKB_HASH = 0
    METHOD_CENTROID = 1
    METHOD_HAUSDORFF = 2
    METHOD_BBOX = 3
    
    def __init__(
        self,
        tolerance: float = 0.0,
        compare_method: int = 0,
        decompose_multipart: bool = False,
        precision: int = 8
    ):
        """
        Initialize the geometry checker.
        
        :param tolerance: Distance tolerance for matching
        :param compare_method: Comparison method (0-3)
        :param decompose_multipart: Whether to decompose multipart geometries
        :param precision: Decimal precision for coordinate rounding
        """
        self.tolerance = tolerance
        self.compare_method = compare_method
        self.decompose_multipart = decompose_multipart
        self.precision = precision
    
    def hash_geometry(self, geometry: QgsGeometry) -> str:
        """
        Generate a hash for the geometry.
        
        Normalizes the geometry before hashing to ensure
        equivalent geometries produce the same hash.
        
        :param geometry: QgsGeometry to hash
        :returns: Hash string
        """
        if geometry.isNull():
            return 'NULL'
        
        # Normalize geometry
        normalized = self._normalize_geometry(geometry)
        
        # Get WKB and hash it
        wkb = normalized.asWkb()
        return hashlib.md5(wkb).hexdigest()
    
    def _normalize_geometry(self, geometry: QgsGeometry) -> QgsGeometry:
        """
        Normalize geometry for consistent comparison.
        
        - Rounds coordinates to precision
        - Normalizes polygon ring orientation
        - Removes duplicate vertices
        
        :param geometry: QgsGeometry to normalize
        :returns: Normalized QgsGeometry
        """
        if geometry.isNull():
            return geometry
        
        # Make a copy
        geom = QgsGeometry(geometry)
        
        # Remove duplicate vertices
        geom.removeDuplicateNodes()
        
        # Round coordinates if precision is set
        if self.precision > 0:
            # Simplify with very small tolerance to round coordinates
            snap_tolerance = 10 ** (-self.precision)
            geom = geom.snappedToGrid(snap_tolerance, snap_tolerance)
        
        # Normalize polygon orientation (exterior CCW, holes CW)
        geom_type = geom.type()
        if geom_type == 2:  # Polygon
            geom.normalize()
        
        return geom
    
    def compare(
        self,
        geom1: QgsGeometry,
        geom2: QgsGeometry,
        tolerance: float = None
    ) -> Tuple[bool, float, str]:
        """
        Compare two geometries.
        
        :param geom1: First geometry
        :param geom2: Second geometry
        :param tolerance: Optional override tolerance
        :returns: Tuple of (is_match, confidence_score, reason)
        """
        if tolerance is None:
            tolerance = self.tolerance
        
        if geom1.isNull() or geom2.isNull():
            return False, 0.0, 'One or both geometries are NULL'
        
        # Decompose multipart if enabled
        if self.decompose_multipart:
            parts1 = self._get_parts(geom1)
            parts2 = self._get_parts(geom2)
            
            # Check if any parts match
            for p1 in parts1:
                for p2 in parts2:
                    match, score, reason = self._compare_single(p1, p2, tolerance)
                    if match:
                        return match, score, reason
            
            return False, 0.0, 'No matching parts found'
        else:
            return self._compare_single(geom1, geom2, tolerance)
    
    def _compare_single(
        self,
        geom1: QgsGeometry,
        geom2: QgsGeometry,
        tolerance: float
    ) -> Tuple[bool, float, str]:
        """
        Compare two single geometries using the configured method.
        
        :param geom1: First geometry
        :param geom2: Second geometry
        :param tolerance: Distance tolerance
        :returns: Tuple of (is_match, confidence_score, reason)
        """
        if self.compare_method == self.METHOD_WKB_HASH:
            return self._compare_wkb(geom1, geom2)
        elif self.compare_method == self.METHOD_CENTROID:
            return self._compare_centroid(geom1, geom2, tolerance)
        elif self.compare_method == self.METHOD_HAUSDORFF:
            return self._compare_hausdorff(geom1, geom2, tolerance)
        elif self.compare_method == self.METHOD_BBOX:
            return self._compare_bbox(geom1, geom2, tolerance)
        else:
            return self._compare_wkb(geom1, geom2)
    
    def _compare_wkb(
        self,
        geom1: QgsGeometry,
        geom2: QgsGeometry
    ) -> Tuple[bool, float, str]:
        """
        Compare geometries by WKB hash (exact match).
        
        :param geom1: First geometry
        :param geom2: Second geometry
        :returns: Tuple of (is_match, confidence_score, reason)
        """
        hash1 = self.hash_geometry(geom1)
        hash2 = self.hash_geometry(geom2)
        
        if hash1 == hash2:
            return True, 1.0, 'Exact WKB match'
        else:
            return False, 0.0, 'WKB mismatch'
    
    def _compare_centroid(
        self,
        geom1: QgsGeometry,
        geom2: QgsGeometry,
        tolerance: float
    ) -> Tuple[bool, float, str]:
        """
        Compare geometries by centroid distance.
        
        :param geom1: First geometry
        :param geom2: Second geometry
        :param tolerance: Distance tolerance
        :returns: Tuple of (is_match, confidence_score, reason)
        """
        c1 = geom1.centroid()
        c2 = geom2.centroid()
        
        if c1.isNull() or c2.isNull():
            return False, 0.0, 'Could not compute centroid'
        
        distance = c1.distance(c2)
        
        if distance <= tolerance:
            # Score decreases as distance increases
            score = 1.0 - (distance / tolerance) if tolerance > 0 else 1.0
            return True, max(0.5, score), f'Centroid distance: {distance:.4f}'
        else:
            return False, 0.0, f'Centroid distance {distance:.4f} exceeds tolerance'
    
    def _compare_hausdorff(
        self,
        geom1: QgsGeometry,
        geom2: QgsGeometry,
        tolerance: float
    ) -> Tuple[bool, float, str]:
        """
        Compare geometries by Hausdorff distance.
        
        Hausdorff distance measures the maximum distance of a set
        to the nearest point in another set.
        
        :param geom1: First geometry
        :param geom2: Second geometry
        :param tolerance: Distance tolerance
        :returns: Tuple of (is_match, confidence_score, reason)
        """
        try:
            distance = geom1.hausdorffDistance(geom2)
        except:
            # Fallback if Hausdorff not available
            return self._compare_centroid(geom1, geom2, tolerance)
        
        if distance <= tolerance:
            score = 1.0 - (distance / tolerance) if tolerance > 0 else 1.0
            return True, max(0.5, score), f'Hausdorff distance: {distance:.4f}'
        else:
            return False, 0.0, f'Hausdorff distance {distance:.4f} exceeds tolerance'
    
    def _compare_bbox(
        self,
        geom1: QgsGeometry,
        geom2: QgsGeometry,
        tolerance: float
    ) -> Tuple[bool, float, str]:
        """
        Compare geometries by bounding box overlap.
        
        :param geom1: First geometry
        :param geom2: Second geometry
        :param tolerance: Distance tolerance (used to grow bbox)
        :returns: Tuple of (is_match, confidence_score, reason)
        """
        bbox1 = geom1.boundingBox()
        bbox2 = geom2.boundingBox()
        
        if bbox1.isEmpty() or bbox2.isEmpty():
            return False, 0.0, 'Empty bounding box'
        
        # Grow bboxes by tolerance
        bbox1.grow(tolerance)
        bbox2.grow(tolerance)
        
        if bbox1.intersects(bbox2):
            # Calculate overlap ratio
            intersection = bbox1.intersect(bbox2)
            union_area = bbox1.area() + bbox2.area() - intersection.area()
            
            if union_area > 0:
                overlap_ratio = intersection.area() / union_area
                
                # High overlap = likely duplicate
                if overlap_ratio > 0.9:
                    return True, overlap_ratio, f'BBox overlap: {overlap_ratio:.2%}'
        
        return False, 0.0, 'Insufficient bounding box overlap'
    
    def _get_parts(self, geometry: QgsGeometry) -> list:
        """
        Get individual parts from a geometry.
        
        :param geometry: QgsGeometry (possibly multipart)
        :returns: List of single-part QgsGeometry objects
        """
        if geometry.isNull():
            return []
        
        if geometry.isMultipart():
            parts = []
            for part in geometry.asGeometryCollection():
                parts.append(part)
            return parts
        else:
            return [geometry]
    
    def get_geometry_info(self, geometry: QgsGeometry) -> dict:
        """
        Get information about a geometry.
        
        :param geometry: QgsGeometry to analyze
        :returns: Dictionary with geometry information
        """
        if geometry.isNull():
            return {'type': 'NULL', 'is_valid': False}
        
        return {
            'type': QgsWkbTypes.displayString(geometry.wkbType()),
            'is_valid': geometry.isGeosValid(),
            'is_multipart': geometry.isMultipart(),
            'num_parts': len(geometry.asGeometryCollection()) if geometry.isMultipart() else 1,
            'num_vertices': self._count_vertices(geometry),
            'area': geometry.area() if geometry.type() == 2 else 0,
            'length': geometry.length() if geometry.type() in [1, 2] else 0,
            'centroid': geometry.centroid().asPoint() if not geometry.centroid().isNull() else None,
            'bbox': geometry.boundingBox()
        }
    
    def _count_vertices(self, geometry: QgsGeometry) -> int:
        """
        Count vertices in a geometry.
        
        :param geometry: QgsGeometry
        :returns: Number of vertices
        """
        try:
            return sum(1 for _ in geometry.vertices())
        except:
            return 0
