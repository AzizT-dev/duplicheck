# -*- coding: utf-8 -*-
"""
DupliCheck - Duplicate Detector
====================================

Main detection engine that orchestrates geometry and attribute checking.
Supports spatial indexing, WKB hashing, and configurable tolerance.
"""

import hashlib
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Callable, Any
from collections import defaultdict

from qgis.core import (
    QgsVectorLayer, QgsFeature, QgsGeometry, QgsFeatureRequest,
    QgsSpatialIndex, QgsRectangle, QgsWkbTypes
)


@dataclass
class DuplicateGroup:
    """
    Represents a group of duplicate features.
    
    Attributes:
        feature_ids: Set of feature IDs in this group
        detection_type: 'geometry' or 'attribute'
        confidence_score: Score between 0 and 1 indicating match quality
        match_reason: Human-readable explanation of why these are duplicates
        suggested_keep: Feature ID suggested to keep (based on priority rules)
        metadata: Additional information about the group
    """
    feature_ids: Set[int] = field(default_factory=set)
    detection_type: str = 'geometry'
    confidence_score: float = 1.0
    match_reason: str = ''
    suggested_keep: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_feature(self, fid: int):
        """Add a feature ID to the group."""
        self.feature_ids.add(fid)
    
    def merge_with(self, other: 'DuplicateGroup'):
        """Merge another group into this one."""
        self.feature_ids.update(other.feature_ids)
        # Keep the lower confidence score
        self.confidence_score = min(self.confidence_score, other.confidence_score)


class DuplicateDetector:
    """
    Main duplicate detection engine.
    
    Coordinates geometry and attribute checkers, applies priority rules,
    and manages performance optimizations for large datasets.
    
    Usage:
        detector = DuplicateDetector(
            layer=my_layer,
            detection_type='geometry',
            tolerance=0.01
        )
        groups = detector.detect()
    """
    
    def __init__(
        self,
        layer: QgsVectorLayer,
        detection_type: str = 'geometry',
        tolerance: float = 0.0,
        compare_method: int = 0,
        decompose_multipart: bool = False,
        fields: List[str] = None,
        normalize_attributes: bool = True,
        ignore_null: bool = False,
        priority_rules: Dict = None,
        sample_mode: bool = False,
        sample_size: int = 5000,
        disk_threshold: int = 50000,
        progress_callback: Callable[[int, str], None] = None
    ):
        """
        Initialize the duplicate detector.
        
        :param layer: Vector layer to analyze
        :param detection_type: 'geometry' or 'attribute'
        :param tolerance: Distance tolerance for geometry matching (0 = exact)
        :param compare_method: Geometry comparison method (0=WKB hash, 1=centroid, 2=hausdorff, 3=bbox)
        :param decompose_multipart: Whether to decompose multipart geometries
        :param fields: Fields to compare for attribute detection
        :param normalize_attributes: Whether to normalize attribute values
        :param ignore_null: Whether to ignore NULL values in comparisons
        :param priority_rules: Rules for suggesting which feature to keep
        :param sample_mode: Whether to use sampling for large layers
        :param sample_size: Number of features to sample
        :param disk_threshold: Feature count threshold for disk-backed storage
        :param progress_callback: Callback function for progress updates
        """
        self.layer = layer
        self.detection_type = detection_type
        self.tolerance = tolerance
        self.compare_method = compare_method
        self.decompose_multipart = decompose_multipart
        self.fields = fields or []
        self.normalize_attributes = normalize_attributes
        self.ignore_null = ignore_null
        self.priority_rules = priority_rules or {}
        self.sample_mode = sample_mode
        self.sample_size = sample_size
        self.disk_threshold = disk_threshold
        self.progress_callback = progress_callback
        
        # Internal state
        self._spatial_index = None
        self._feature_cache = {}
        self._groups = []
    
    def _report_progress(self, value: int, message: str = ''):
        """Report progress if callback is set."""
        if self.progress_callback:
            self.progress_callback(value, message)
    
    def detect(self) -> List[DuplicateGroup]:
        """
        Run duplicate detection.
        
        :returns: List of DuplicateGroup objects
        """
        if not self.layer or not self.layer.isValid():
            raise ValueError("Invalid or missing layer")
        
        feature_count = self.layer.featureCount()
        self._report_progress(0, f"Analyzing {feature_count} features...")
        
        # Use sampling for very large layers in preview mode
        if self.sample_mode and feature_count > self.sample_size:
            self._report_progress(5, f"Sampling {self.sample_size} features...")
            features = self._sample_features()
        else:
            features = list(self.layer.getFeatures())
        
        self._report_progress(10, "Building spatial index...")
        
        # Build spatial index for geometry detection
        if self.detection_type == 'geometry':
            self._build_spatial_index(features)
        
        self._report_progress(20, "Detecting duplicates...")
        
        # Run detection based on type
        if self.detection_type == 'geometry':
            groups = self._detect_geometry_duplicates(features)
        else:
            groups = self._detect_attribute_duplicates(features)
        
        self._report_progress(70, "Resolving priorities...")
        
        # Apply priority rules
        if self.priority_rules:
            from .priority_resolver import PriorityResolver
            resolver = PriorityResolver(
                layer=self.layer,
                rules=self.priority_rules
            )
            groups = resolver.resolve(groups)
        
        self._report_progress(90, "Finalizing results...")
        
        # Consolidate overlapping groups
        groups = self._consolidate_groups(groups)
        
        self._report_progress(100, f"Found {len(groups)} duplicate groups")
        
        self._groups = groups
        return groups
    
    def _sample_features(self) -> List[QgsFeature]:
        """
        Sample features from the layer.
        
        :returns: List of sampled features
        """
        import random
        
        all_ids = [f.id() for f in self.layer.getFeatures()]
        sample_ids = random.sample(all_ids, min(self.sample_size, len(all_ids)))
        
        request = QgsFeatureRequest().setFilterFids(sample_ids)
        return list(self.layer.getFeatures(request))
    
    def _build_spatial_index(self, features: List[QgsFeature]):
        """
        Build spatial index for fast geometry lookups.
        
        :param features: List of features to index
        """
        self._spatial_index = QgsSpatialIndex()
        self._feature_cache = {}
        
        for feature in features:
            self._spatial_index.addFeature(feature)
            self._feature_cache[feature.id()] = feature
    
    def _detect_geometry_duplicates(self, features: List[QgsFeature]) -> List[DuplicateGroup]:
        """
        Detect geometric duplicates.
        
        :param features: List of features to check
        :returns: List of DuplicateGroup objects
        """
        from .geometry_checker import GeometryChecker
        
        checker = GeometryChecker(
            tolerance=self.tolerance,
            compare_method=self.compare_method,
            decompose_multipart=self.decompose_multipart
        )
        
        if self.tolerance == 0:
            # Exact match using WKB hash
            return self._detect_by_hash(features, checker)
        else:
            # Tolerance-based using spatial index
            return self._detect_by_tolerance(features, checker)
    
    def _detect_by_hash(self, features: List[QgsFeature], checker) -> List[DuplicateGroup]:
        """
        Detect exact geometry duplicates using WKB hash.
        
        :param features: List of features
        :param checker: GeometryChecker instance
        :returns: List of DuplicateGroup objects
        """
        # Group features by geometry hash
        hash_groups = defaultdict(list)
        
        total = len(features)
        for i, feature in enumerate(features):
            if i % 1000 == 0:
                progress = 20 + int((i / total) * 40)
                self._report_progress(progress, f"Hashing geometries... ({i}/{total})")
            
            geom = feature.geometry()
            if geom.isNull():
                continue
            
            # Normalize and hash geometry
            geom_hash = checker.hash_geometry(geom)
            hash_groups[geom_hash].append(feature.id())
        
        # Create groups for duplicates
        groups = []
        for geom_hash, fids in hash_groups.items():
            if len(fids) > 1:
                group = DuplicateGroup(
                    feature_ids=set(fids),
                    detection_type='geometry',
                    confidence_score=1.0,
                    match_reason='Exact WKB match'
                )
                groups.append(group)
        
        return groups
    
    def _detect_by_tolerance(self, features: List[QgsFeature], checker) -> List[DuplicateGroup]:
        """
        Detect geometry duplicates within tolerance using spatial index.
        
        :param features: List of features
        :param checker: GeometryChecker instance
        :returns: List of DuplicateGroup objects
        """
        processed = set()
        groups = []
        
        total = len(features)
        for i, feature in enumerate(features):
            fid = feature.id()
            
            if fid in processed:
                continue
            
            if i % 100 == 0:
                progress = 20 + int((i / total) * 40)
                self._report_progress(progress, f"Checking tolerance... ({i}/{total})")
            
            geom = feature.geometry()
            if geom.isNull():
                continue
            
            # Find candidates using spatial index
            search_rect = geom.boundingBox()
            search_rect.grow(self.tolerance)
            
            candidate_ids = self._spatial_index.intersects(search_rect)
            
            # Check each candidate
            duplicates = [fid]
            for cid in candidate_ids:
                if cid == fid or cid in processed:
                    continue
                
                candidate = self._feature_cache.get(cid)
                if not candidate:
                    continue
                
                cgeom = candidate.geometry()
                if cgeom.isNull():
                    continue
                
                # Check if within tolerance
                match, score, reason = checker.compare(geom, cgeom, self.tolerance)
                
                if match:
                    duplicates.append(cid)
            
            # Create group if duplicates found
            if len(duplicates) > 1:
                group = DuplicateGroup(
                    feature_ids=set(duplicates),
                    detection_type='geometry',
                    confidence_score=score if 'score' in dir() else 0.9,
                    match_reason=f'Within {self.tolerance} tolerance'
                )
                groups.append(group)
                processed.update(duplicates)
            else:
                processed.add(fid)
        
        return groups
    
    def _detect_attribute_duplicates(self, features: List[QgsFeature]) -> List[DuplicateGroup]:
        """
        Detect attribute duplicates.
        
        :param features: List of features to check
        :returns: List of DuplicateGroup objects
        """
        from .attribute_checker import AttributeChecker
        
        if not self.fields:
            raise ValueError("No fields specified for attribute detection")
        
        checker = AttributeChecker(
            fields=self.fields,
            normalize=self.normalize_attributes,
            ignore_null=self.ignore_null
        )
        
        # Group features by attribute key
        key_groups = defaultdict(list)
        
        total = len(features)
        for i, feature in enumerate(features):
            if i % 1000 == 0:
                progress = 20 + int((i / total) * 40)
                self._report_progress(progress, f"Checking attributes... ({i}/{total})")
            
            key = checker.get_key(feature)
            if key is not None:  # Skip NULL keys if ignore_null
                key_groups[key].append(feature.id())
        
        # Create groups for duplicates
        groups = []
        for key, fids in key_groups.items():
            if len(fids) > 1:
                group = DuplicateGroup(
                    feature_ids=set(fids),
                    detection_type='attribute',
                    confidence_score=1.0,
                    match_reason=f'Matching fields: {", ".join(self.fields)}',
                    metadata={'key': key}
                )
                groups.append(group)
        
        return groups
    
    def _consolidate_groups(self, groups: List[DuplicateGroup]) -> List[DuplicateGroup]:
        """
        Consolidate overlapping groups.
        
        If a feature appears in multiple groups, merge those groups.
        
        :param groups: List of groups to consolidate
        :returns: Consolidated list of groups
        """
        if not groups:
            return []
        
        # Build feature -> group mapping
        feature_to_group = {}
        consolidated = []
        
        for group in groups:
            # Check if any feature is already in another group
            existing_group = None
            for fid in group.feature_ids:
                if fid in feature_to_group:
                    existing_group = feature_to_group[fid]
                    break
            
            if existing_group:
                # Merge into existing group
                existing_group.merge_with(group)
                for fid in group.feature_ids:
                    feature_to_group[fid] = existing_group
            else:
                # New group
                consolidated.append(group)
                for fid in group.feature_ids:
                    feature_to_group[fid] = group
        
        return consolidated
    
    def get_statistics(self) -> Dict:
        """
        Get detection statistics.
        
        :returns: Dictionary with statistics
        """
        if not self._groups:
            return {}
        
        total_features = self.layer.featureCount()
        total_duplicates = sum(len(g.feature_ids) for g in self._groups)
        
        return {
            'total_features': total_features,
            'duplicate_groups': len(self._groups),
            'duplicate_features': total_duplicates,
            'duplication_rate': total_duplicates / total_features if total_features > 0 else 0,
            'detection_type': self.detection_type,
            'tolerance': self.tolerance,
            'fields': self.fields
        }
