# -*- coding: utf-8 -*-
"""
DupliCheck - Attribute Checker
===================================

Handles attribute comparison for duplicate detection.
Supports normalization, composite keys, and NULL handling.
"""

import unicodedata
from typing import List, Optional, Tuple, Any

from qgis.core import QgsFeature, QgsField
from qgis.PyQt.QtCore import QVariant


class AttributeChecker:
    """
    Attribute comparison utility.
    
    Compares feature attributes with options for:
    - Value normalization (trim, lowercase, Unicode NFKC)
    - Composite keys (multiple fields)
    - NULL value handling
    - Fuzzy matching (optional)
    """
    
    def __init__(
        self,
        fields: List[str],
        normalize: bool = True,
        ignore_null: bool = False,
        case_sensitive: bool = False,
        fuzzy_threshold: float = 0.0
    ):
        """
        Initialize the attribute checker.
        
        :param fields: List of field names to compare
        :param normalize: Whether to normalize values
        :param ignore_null: Whether to skip features with NULL values
        :param case_sensitive: Whether comparison is case-sensitive
        :param fuzzy_threshold: Similarity threshold for fuzzy matching (0 = exact)
        """
        self.fields = fields
        self.normalize = normalize
        self.ignore_null = ignore_null
        self.case_sensitive = case_sensitive
        self.fuzzy_threshold = fuzzy_threshold
    
    def get_key(self, feature: QgsFeature) -> Optional[tuple]:
        """
        Get a comparison key for a feature.
        
        The key is a tuple of normalized field values that can be
        used for grouping duplicates.
        
        :param feature: QgsFeature to get key from
        :returns: Tuple of values, or None if should be skipped
        """
        values = []
        
        for field_name in self.fields:
            try:
                value = feature[field_name]
            except KeyError:
                value = None
            
            # Handle NULL values
            if value is None or (isinstance(value, QVariant) and value.isNull()):
                if self.ignore_null:
                    return None  # Skip this feature
                value = None
            
            # Normalize value
            if self.normalize and value is not None:
                value = self._normalize_value(value)
            
            values.append(value)
        
        return tuple(values)
    
    def _normalize_value(self, value: Any) -> Any:
        """
        Normalize a value for comparison.
        
        :param value: Value to normalize
        :returns: Normalized value
        """
        if value is None:
            return None
        
        # Convert to string for text normalization
        if isinstance(value, str):
            # Trim whitespace
            value = value.strip()
            
            # Unicode normalization (NFKC)
            value = unicodedata.normalize('NFKC', value)
            
            # Case normalization
            if not self.case_sensitive:
                value = value.lower()
            
            # Collapse multiple spaces
            value = ' '.join(value.split())
            
            return value
        
        elif isinstance(value, (int, float)):
            # For numeric types, just return as-is
            return value
        
        else:
            # For other types, convert to string and normalize
            return self._normalize_value(str(value))
    
    def compare(
        self,
        feature1: QgsFeature,
        feature2: QgsFeature
    ) -> Tuple[bool, float, str]:
        """
        Compare two features by their attributes.
        
        :param feature1: First feature
        :param feature2: Second feature
        :returns: Tuple of (is_match, confidence_score, reason)
        """
        key1 = self.get_key(feature1)
        key2 = self.get_key(feature2)
        
        # Handle NULL keys
        if key1 is None or key2 is None:
            return False, 0.0, 'One or both features have NULL key values'
        
        # Exact match
        if key1 == key2:
            return True, 1.0, f'Exact match on fields: {", ".join(self.fields)}'
        
        # Fuzzy matching (if enabled)
        if self.fuzzy_threshold > 0:
            similarity = self._calculate_similarity(key1, key2)
            if similarity >= self.fuzzy_threshold:
                return True, similarity, f'Fuzzy match ({similarity:.2%} similarity)'
        
        return False, 0.0, 'No match'
    
    def _calculate_similarity(
        self,
        key1: tuple,
        key2: tuple
    ) -> float:
        """
        Calculate similarity between two keys using Levenshtein distance.
        
        :param key1: First key tuple
        :param key2: Second key tuple
        :returns: Similarity score between 0 and 1
        """
        if len(key1) != len(key2):
            return 0.0
        
        similarities = []
        
        for v1, v2 in zip(key1, key2):
            if v1 is None or v2 is None:
                if v1 == v2:
                    similarities.append(1.0)
                else:
                    similarities.append(0.0)
            elif isinstance(v1, str) and isinstance(v2, str):
                sim = self._levenshtein_similarity(v1, v2)
                similarities.append(sim)
            elif v1 == v2:
                similarities.append(1.0)
            else:
                similarities.append(0.0)
        
        return sum(similarities) / len(similarities) if similarities else 0.0
    
    def _levenshtein_similarity(self, s1: str, s2: str) -> float:
        """
        Calculate Levenshtein similarity between two strings.
        
        :param s1: First string
        :param s2: Second string
        :returns: Similarity score between 0 and 1
        """
        if s1 == s2:
            return 1.0
        
        if len(s1) == 0 or len(s2) == 0:
            return 0.0
        
        # Calculate Levenshtein distance
        distance = self._levenshtein_distance(s1, s2)
        max_len = max(len(s1), len(s2))
        
        return 1.0 - (distance / max_len)
    
    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """
        Calculate Levenshtein distance between two strings.
        
        :param s1: First string
        :param s2: Second string
        :returns: Edit distance
        """
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = range(len(s2) + 1)
        
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    def get_field_values(
        self,
        feature: QgsFeature,
        all_fields: bool = False
    ) -> dict:
        """
        Get field values from a feature.
        
        :param feature: QgsFeature to extract values from
        :param all_fields: Whether to get all fields or just comparison fields
        :returns: Dictionary of field name -> value
        """
        result = {}
        
        fields_to_get = (
            [f.name() for f in feature.fields()]
            if all_fields
            else self.fields
        )
        
        for field_name in fields_to_get:
            try:
                value = feature[field_name]
                if isinstance(value, QVariant) and value.isNull():
                    value = None
                result[field_name] = value
            except KeyError:
                result[field_name] = None
        
        return result
    
    def find_differences(
        self,
        feature1: QgsFeature,
        feature2: QgsFeature
    ) -> dict:
        """
        Find differences between two features.
        
        :param feature1: First feature
        :param feature2: Second feature
        :returns: Dictionary with difference information
        """
        values1 = self.get_field_values(feature1, all_fields=True)
        values2 = self.get_field_values(feature2, all_fields=True)
        
        same = {}
        different = {}
        only_in_1 = {}
        only_in_2 = {}
        
        all_fields = set(values1.keys()) | set(values2.keys())
        
        for field in all_fields:
            v1 = values1.get(field)
            v2 = values2.get(field)
            
            if field not in values2:
                only_in_1[field] = v1
            elif field not in values1:
                only_in_2[field] = v2
            elif v1 == v2:
                same[field] = v1
            else:
                different[field] = {'feature1': v1, 'feature2': v2}
        
        return {
            'same': same,
            'different': different,
            'only_in_feature1': only_in_1,
            'only_in_feature2': only_in_2
        }
    
    def count_null_fields(self, feature: QgsFeature) -> int:
        """
        Count NULL fields in a feature.
        
        :param feature: QgsFeature to analyze
        :returns: Number of NULL fields
        """
        count = 0
        
        for field in feature.fields():
            value = feature[field.name()]
            if value is None or (isinstance(value, QVariant) and value.isNull()):
                count += 1
        
        return count
    
    def get_completeness_score(self, feature: QgsFeature) -> float:
        """
        Calculate completeness score for a feature.
        
        :param feature: QgsFeature to analyze
        :returns: Score between 0 and 1 (1 = all fields filled)
        """
        total_fields = len(feature.fields())
        if total_fields == 0:
            return 1.0
        
        null_count = self.count_null_fields(feature)
        return 1.0 - (null_count / total_fields)
