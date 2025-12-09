# -*- coding: utf-8 -*-
"""
DupliCheck - Priority Resolver
===================================

Applies priority rules to suggest which feature to keep in each duplicate group.
Supports rules based on field values, completeness, area, and FID.
"""

from typing import List, Dict, Optional, Any
from datetime import datetime

from qgis.core import QgsVectorLayer, QgsFeature, QgsFeatureRequest
from qgis.PyQt.QtCore import QVariant

from .detector import DuplicateGroup


class PriorityResolver:
    """
    Resolves which feature to keep in duplicate groups based on priority rules.
    
    Supported rules:
    - field: Keep feature with highest/lowest/most recent value in a field
    - completeness: Keep feature with fewest NULL values
    - area: Keep largest/smallest polygon (for polygon layers)
    - fid_fallback: Keep feature with lowest FID if no other rule applies
    """
    
    def __init__(self, layer: QgsVectorLayer, rules: Dict):
        """
        Initialize the priority resolver.
        
        :param layer: Source vector layer
        :param rules: Dictionary of priority rules
        """
        self.layer = layer
        self.rules = rules
        
        # Rule configuration
        self.field_name = rules.get('field')
        self.field_order = rules.get('field_order', 0)  # 0=highest, 1=lowest, 2=most recent, 3=oldest
        self.use_completeness = rules.get('completeness', False)
        self.area_rule = rules.get('area')  # 'largest' or 'smallest'
        self.fid_fallback = rules.get('fid_fallback', True)
    
    def resolve(self, groups: List[DuplicateGroup]) -> List[DuplicateGroup]:
        """
        Apply priority rules to all groups.
        
        :param groups: List of DuplicateGroup objects
        :returns: List with suggested_keep populated
        """
        for group in groups:
            suggested_fid = self._resolve_group(group)
            group.suggested_keep = suggested_fid
        
        return groups
    
    def _resolve_group(self, group: DuplicateGroup) -> Optional[int]:
        """
        Resolve which feature to keep in a single group.
        
        :param group: DuplicateGroup to resolve
        :returns: Feature ID to keep, or None if no suggestion
        """
        if len(group.feature_ids) < 2:
            return list(group.feature_ids)[0] if group.feature_ids else None
        
        # Get features
        fids = list(group.feature_ids)
        request = QgsFeatureRequest().setFilterFids(fids)
        features = {f.id(): f for f in self.layer.getFeatures(request)}
        
        if not features:
            return None
        
        # Apply rules in order of priority
        candidates = list(features.keys())
        
        # Rule 1: Field value
        if self.field_name and self.field_name in [f.name() for f in self.layer.fields()]:
            result = self._apply_field_rule(features, candidates)
            if result:
                return result
            # If field rule narrows candidates, continue with those
        
        # Rule 2: Completeness
        if self.use_completeness:
            result = self._apply_completeness_rule(features, candidates)
            if result:
                return result
        
        # Rule 3: Area (for polygons)
        if self.area_rule and self.layer.geometryType() == 2:
            result = self._apply_area_rule(features, candidates)
            if result:
                return result
        
        # Rule 4: FID fallback
        if self.fid_fallback:
            return min(candidates)
        
        return None
    
    def _apply_field_rule(
        self,
        features: Dict[int, QgsFeature],
        candidates: List[int]
    ) -> Optional[int]:
        """
        Apply field-based priority rule.
        
        :param features: Dictionary of FID -> QgsFeature
        :param candidates: List of candidate FIDs
        :returns: Best feature ID or None
        """
        if not self.field_name:
            return None
        
        # Get values for each candidate
        values = {}
        for fid in candidates:
            feature = features.get(fid)
            if not feature:
                continue
            
            try:
                value = feature[self.field_name]
                if isinstance(value, QVariant) and value.isNull():
                    value = None
                values[fid] = value
            except KeyError:
                values[fid] = None
        
        # Filter out NULL values
        valid_values = {k: v for k, v in values.items() if v is not None}
        
        if not valid_values:
            return None
        
        # Apply ordering
        try:
            if self.field_order == 0:  # Highest
                return max(valid_values.keys(), key=lambda k: valid_values[k])
            elif self.field_order == 1:  # Lowest
                return min(valid_values.keys(), key=lambda k: valid_values[k])
            elif self.field_order == 2:  # Most recent (for dates)
                return self._get_most_recent(valid_values)
            elif self.field_order == 3:  # Oldest (for dates)
                return self._get_oldest(valid_values)
        except (TypeError, ValueError):
            # Values might not be comparable
            return None
        
        return None
    
    def _get_most_recent(self, values: Dict[int, Any]) -> Optional[int]:
        """
        Get feature with most recent date value.
        
        :param values: Dictionary of FID -> value
        :returns: FID with most recent date
        """
        date_values = {}
        
        for fid, value in values.items():
            parsed = self._parse_date(value)
            if parsed:
                date_values[fid] = parsed
        
        if not date_values:
            # Fall back to string comparison
            return max(values.keys(), key=lambda k: str(values[k]))
        
        return max(date_values.keys(), key=lambda k: date_values[k])
    
    def _get_oldest(self, values: Dict[int, Any]) -> Optional[int]:
        """
        Get feature with oldest date value.
        
        :param values: Dictionary of FID -> value
        :returns: FID with oldest date
        """
        date_values = {}
        
        for fid, value in values.items():
            parsed = self._parse_date(value)
            if parsed:
                date_values[fid] = parsed
        
        if not date_values:
            # Fall back to string comparison
            return min(values.keys(), key=lambda k: str(values[k]))
        
        return min(date_values.keys(), key=lambda k: date_values[k])
    
    def _parse_date(self, value: Any) -> Optional[datetime]:
        """
        Try to parse a value as a date.
        
        :param value: Value to parse
        :returns: datetime object or None
        """
        if isinstance(value, datetime):
            return value
        
        if not isinstance(value, str):
            return None
        
        # Common date formats
        formats = [
            '%Y-%m-%d',
            '%Y/%m/%d',
            '%d-%m-%Y',
            '%d/%m/%Y',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%dT%H:%M:%S',
            '%d/%m/%Y %H:%M:%S',
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(value.strip(), fmt)
            except ValueError:
                continue
        
        return None
    
    def _apply_completeness_rule(
        self,
        features: Dict[int, QgsFeature],
        candidates: List[int]
    ) -> Optional[int]:
        """
        Apply completeness-based priority rule.
        
        :param features: Dictionary of FID -> QgsFeature
        :param candidates: List of candidate FIDs
        :returns: Feature ID with fewest NULLs
        """
        null_counts = {}
        
        for fid in candidates:
            feature = features.get(fid)
            if not feature:
                continue
            
            null_count = 0
            for field in feature.fields():
                value = feature[field.name()]
                if value is None or (isinstance(value, QVariant) and value.isNull()):
                    null_count += 1
            
            null_counts[fid] = null_count
        
        if not null_counts:
            return None
        
        # Return feature with fewest NULLs
        min_nulls = min(null_counts.values())
        best_candidates = [fid for fid, count in null_counts.items() if count == min_nulls]
        
        if len(best_candidates) == 1:
            return best_candidates[0]
        
        # If tie, return None to let next rule decide
        return None
    
    def _apply_area_rule(
        self,
        features: Dict[int, QgsFeature],
        candidates: List[int]
    ) -> Optional[int]:
        """
        Apply area-based priority rule for polygons.
        
        :param features: Dictionary of FID -> QgsFeature
        :param candidates: List of candidate FIDs
        :returns: Feature ID based on area rule
        """
        if not self.area_rule:
            return None
        
        areas = {}
        
        for fid in candidates:
            feature = features.get(fid)
            if not feature:
                continue
            
            geom = feature.geometry()
            if not geom.isNull():
                areas[fid] = geom.area()
        
        if not areas:
            return None
        
        if self.area_rule == 'largest':
            return max(areas.keys(), key=lambda k: areas[k])
        elif self.area_rule == 'smallest':
            return min(areas.keys(), key=lambda k: areas[k])
        
        return None
    
    def get_rule_summary(self) -> str:
        """
        Get a human-readable summary of active rules.
        
        :returns: Summary string
        """
        parts = []
        
        if self.field_name:
            order_names = ['highest', 'lowest', 'most recent', 'oldest']
            parts.append(f"Field '{self.field_name}' ({order_names[self.field_order]})")
        
        if self.use_completeness:
            parts.append("Fewest NULL values")
        
        if self.area_rule:
            parts.append(f"{self.area_rule.capitalize()} area")
        
        if self.fid_fallback:
            parts.append("Lowest FID (fallback)")
        
        return " → ".join(parts) if parts else "No rules configured"
