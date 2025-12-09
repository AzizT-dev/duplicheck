# -*- coding: utf-8 -*-
"""
DupliCheck - Results Widget
================================

Widget for displaying and managing duplicate detection results.
"""

from qgis.PyQt.QtCore import Qt, QCoreApplication, pyqtSignal
from qgis.PyQt.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QLabel, QComboBox, QHeaderView, QAbstractItemView,
    QFrame, QSplitter, QGroupBox, QMenu, QFormLayout
)
from qgis.PyQt.QtGui import QColor, QBrush, QFont
from qgis.core import QgsVectorLayer, QgsWkbTypes


class ResultsWidget(QWidget):
    """
    Widget for displaying duplicate detection results.
    
    Shows duplicate groups in a tree view with actions for each feature.
    """
    
    # Signals
    group_selected = pyqtSignal(object)  # Emits DuplicateGroup or None
    zoom_to_group = pyqtSignal(object)  # Emits DuplicateGroup
    feature_clicked = pyqtSignal(int)  # Emits feature ID when clicked
    feature_double_clicked = pyqtSignal(int)  # Emits feature ID when double-clicked
    
    def __init__(self, iface, parent=None):
        """
        Initialize the results widget.
        
        :param iface: QGIS interface instance
        :param parent: Parent widget
        """
        super().__init__(parent)
        self.iface = iface
        self.groups = []
        self.layer = None
        self.config = {}
        self.id_field = None
        self.actions = {}  # {feature_id: 'keep' or 'remove'}
        
        self._setup_ui()
        self._connect_signals()
    
    def tr(self, message):
        """Get translation for a string."""
        return QCoreApplication.translate('ResultsWidget', message)
    
    def _setup_ui(self):
        """Set up the user interface."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Splitter for tree and details
        splitter = QSplitter(Qt.Horizontal)
        
        # Left side: Tree view
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # Toolbar
        toolbar = QHBoxLayout()
        
        self.select_all_btn = QPushButton(self.tr('Select All'))
        self.deselect_all_btn = QPushButton(self.tr('Deselect All'))
        
        toolbar.addWidget(self.select_all_btn)
        toolbar.addWidget(self.deselect_all_btn)
        toolbar.addStretch()
        
        # Filter combo
        self.filter_combo = QComboBox()
        self.filter_combo.addItems([
            self.tr('All Groups'),
            self.tr('Pending (no action)'),
            self.tr('Resolved')
        ])
        toolbar.addWidget(QLabel(self.tr('Filter:')))
        toolbar.addWidget(self.filter_combo)
        
        left_layout.addLayout(toolbar)
        
        # Tree widget
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels([
            self.tr('Group / Feature'),
            self.tr('ID Value'),
            self.tr('Action')
        ])
        self.tree.setAlternatingRowColors(True)
        self.tree.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.setRootIsDecorated(True)
        
        # Column sizes - Interactive mode allows manual resizing
        header = self.tree.header()
        header.setSectionResizeMode(0, QHeaderView.Interactive)
        header.setSectionResizeMode(1, QHeaderView.Interactive)
        header.setSectionResizeMode(2, QHeaderView.Interactive)
        header.setStretchLastSection(False)
        
        # Set initial column widths
        self.tree.setColumnWidth(0, 250)  # Group / Feature
        self.tree.setColumnWidth(1, 150)  # ID Value
        self.tree.setColumnWidth(2, 120)  # Action
        
        left_layout.addWidget(self.tree)
        
        # Summary bar
        self.summary_label = QLabel()
        self.summary_label.setStyleSheet('color: #666; padding: 5px;')
        left_layout.addWidget(self.summary_label)
        
        splitter.addWidget(left_widget)
        
        # Right side: Info panel
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # Layer Information
        layer_group = QGroupBox(self.tr('Layer Information'))
        layer_layout = QFormLayout()
        layer_layout.setSpacing(6)
        
        self.layer_name_label = QLabel('—')
        self.layer_geom_label = QLabel('—')
        self.layer_crs_label = QLabel('—')
        self.layer_source_label = QLabel('—')
        self.layer_source_label.setWordWrap(True)
        self.layer_source_label.setStyleSheet('color: #666; font-size: 10px;')
        
        layer_layout.addRow(self.tr('Name:'), self.layer_name_label)
        layer_layout.addRow(self.tr('Geometry:'), self.layer_geom_label)
        layer_layout.addRow(self.tr('CRS:'), self.layer_crs_label)
        layer_layout.addRow(self.tr('Source:'), self.layer_source_label)
        
        layer_group.setLayout(layer_layout)
        right_layout.addWidget(layer_group)
        
        # Detection Statistics
        stats_group = QGroupBox(self.tr('Detection Statistics'))
        stats_layout = QFormLayout()
        stats_layout.setSpacing(6)
        
        self.detection_type_label = QLabel('—')
        self.tolerance_label = QLabel('—')
        self.total_features_label = QLabel('—')
        self.duplicate_groups_label = QLabel('—')
        self.duplicate_features_label = QLabel('—')
        
        # Style for important numbers
        bold_style = 'font-weight: bold; color: #d32f2f;'
        self.duplicate_groups_label.setStyleSheet(bold_style)
        self.duplicate_features_label.setStyleSheet(bold_style)
        
        stats_layout.addRow(self.tr('Detection Type:'), self.detection_type_label)
        stats_layout.addRow(self.tr('Tolerance:'), self.tolerance_label)
        stats_layout.addRow(self.tr('Total Features:'), self.total_features_label)
        stats_layout.addRow(self.tr('Duplicate Groups:'), self.duplicate_groups_label)
        stats_layout.addRow(self.tr('Duplicate Features:'), self.duplicate_features_label)
        
        stats_group.setLayout(stats_layout)
        right_layout.addWidget(stats_group)
        
        # Attribute comparison
        compare_group = QGroupBox(self.tr('Attribute Comparison'))
        compare_layout = QVBoxLayout()
        
        self.compare_tree = QTreeWidget()
        self.compare_tree.setHeaderLabels([self.tr('Field')])
        self.compare_tree.setAlternatingRowColors(True)
        compare_layout.addWidget(self.compare_tree)
        
        compare_group.setLayout(compare_layout)
        right_layout.addWidget(compare_group)
        
        right_layout.addStretch()
        
        splitter.addWidget(right_widget)
        splitter.setSizes([600, 300])
        
        main_layout.addWidget(splitter)
    
    def _connect_signals(self):
        """Connect signals and slots."""
        self.tree.currentItemChanged.connect(self._on_item_selected)
        self.tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)
        
        self.select_all_btn.clicked.connect(self._select_all)
        self.deselect_all_btn.clicked.connect(self._deselect_all)
        self.filter_combo.currentIndexChanged.connect(self._apply_filter)
    
    def set_results(self, groups, layer, id_field=None, config=None):
        """
        Set detection results.
        
        :param groups: List of DuplicateGroup objects
        :param layer: Source QgsVectorLayer
        :param id_field: Field name to use for displaying feature IDs
        :param config: Detection configuration dictionary
        """
        self.groups = groups
        self.layer = layer
        self.id_field = id_field
        self.config = config or {}
        self.actions = {}
        
        self._update_layer_info()
        self._update_stats_info()
        self._populate_tree()
        self._update_summary()
    
    def _update_layer_info(self):
        """Update layer information panel."""
        if not self.layer or not self.layer.isValid():
            self.layer_name_label.setText('—')
            self.layer_geom_label.setText('—')
            self.layer_crs_label.setText('—')
            self.layer_source_label.setText('—')
            return
        
        self.layer_name_label.setText(self.layer.name())
        self.layer_geom_label.setText(QgsWkbTypes.displayString(self.layer.wkbType()))
        self.layer_crs_label.setText(self.layer.crs().authid() or self.tr('Unknown'))
        
        # Truncate source path if too long
        source = self.layer.source()
        if len(source) > 60:
            source = '...' + source[-57:]
        self.layer_source_label.setText(source)
    
    def _update_stats_info(self):
        """Update detection statistics panel."""
        # Detection type
        detection_type = self.config.get('detection_type', 'geometry')
        type_label = self.tr('Geometric') if detection_type == 'geometry' else self.tr('Attribute')
        self.detection_type_label.setText(type_label)
        
        # Tolerance
        tolerance = self.config.get('tolerance', 0)
        self.tolerance_label.setText(str(tolerance))
        
        # Counts
        total_features = self.layer.featureCount() if self.layer else 0
        total_groups = len(self.groups)
        total_duplicates = sum(len(g.feature_ids) for g in self.groups)
        
        self.total_features_label.setText(str(total_features))
        self.duplicate_groups_label.setText(str(total_groups))
        self.duplicate_features_label.setText(str(total_duplicates))
    
    def _populate_tree(self):
        """Populate the tree widget with duplicate groups."""
        self.tree.clear()
        
        if not self.groups or not self.layer:
            return
        
        # Cache feature data for ID field
        feature_data = {}
        for feature in self.layer.getFeatures():
            fid = feature.id()
            if self.id_field and self.id_field in [f.name() for f in self.layer.fields()]:
                feature_data[fid] = str(feature[self.id_field])
            else:
                feature_data[fid] = f"FID {fid}"
        
        for i, group in enumerate(self.groups):
            # Create group item
            group_item = QTreeWidgetItem()
            group_item.setText(0, self.tr('Group {0} ({1} features)').format(
                i + 1, len(group.feature_ids)
            ))
            group_item.setData(0, Qt.UserRole, ('group', group))
            
            # Bold font for group headers
            font = group_item.font(0)
            font.setBold(True)
            group_item.setFont(0, font)
            
            # Color code group background
            group_item.setBackground(0, QBrush(QColor(230, 240, 250)))
            
            # Add feature children
            for j, fid in enumerate(group.feature_ids):
                feature_item = QTreeWidgetItem()
                feature_item.setText(0, self.tr('Feature {0}').format(j + 1))
                
                # Display ID value from the selected field
                id_value = feature_data.get(fid, str(fid))
                feature_item.setText(1, id_value)
                
                feature_item.setData(0, Qt.UserRole, ('feature', fid, group))
                
                # Action combo
                action_combo = QComboBox()
                action_combo.addItems([
                    self.tr('-- Select --'),
                    self.tr('Keep'),
                    self.tr('Remove')
                ])
                action_combo.setCurrentIndex(0)
                action_combo.currentIndexChanged.connect(
                    lambda idx, f=fid: self._on_action_changed(f, idx)
                )
                
                group_item.addChild(feature_item)
                self.tree.setItemWidget(feature_item, 2, action_combo)
            
            self.tree.addTopLevelItem(group_item)
            group_item.setExpanded(True)
    
    def _on_action_changed(self, fid, index):
        """Handle action combo change."""
        if index == 1:
            self.actions[fid] = 'keep'
        elif index == 2:
            self.actions[fid] = 'remove'
        elif fid in self.actions:
            del self.actions[fid]
        
        self._update_summary()
    
    def _on_item_selected(self, current, previous):
        """Handle tree item selection change."""
        if not current:
            self.compare_tree.clear()
            self.group_selected.emit(None)
            return
        
        data = current.data(0, Qt.UserRole)
        if not data:
            return
        
        if data[0] == 'group':
            group = data[1]
            self._populate_comparison(group)
            self.group_selected.emit(group)
        elif data[0] == 'feature':
            group = data[2]
            fid = data[1]
            self._populate_comparison(group, fid)
            # Only emit feature_clicked - don't emit group_selected to avoid zoom conflict
            self.feature_clicked.emit(fid)
    
    def _on_item_double_clicked(self, item, column):
        """Handle double-click on item."""
        data = item.data(0, Qt.UserRole)
        if not data:
            return
        
        if data[0] == 'group':
            # Double-click on group -> zoom to all features in group
            self.zoom_to_group.emit(data[1])
        elif data[0] == 'feature':
            # Double-click on feature -> zoom closer to this specific feature
            fid = data[1]
            self.feature_double_clicked.emit(fid)
    
    def _populate_comparison(self, group, highlight_fid=None):
        """Populate attribute comparison tree."""
        self.compare_tree.clear()
        
        if not self.layer:
            return
        
        # Get features
        features = {f.id(): f for f in self.layer.getFeatures()
                   if f.id() in group.feature_ids}
        
        fids = list(group.feature_ids)[:5]  # Max 5 columns
        
        # Update headers with ID field values
        headers = [self.tr('Field')]
        for fid in fids:
            if self.id_field and fid in features:
                headers.append(str(features[fid][self.id_field]))
            else:
                headers.append(f'FID {fid}')
        
        self.compare_tree.setHeaderLabels(headers)
        
        # Add field rows
        for field in self.layer.fields():
            item = QTreeWidgetItem()
            item.setText(0, field.name())
            
            values = []
            for i, fid in enumerate(fids):
                if fid in features:
                    value = str(features[fid][field.name()])
                    item.setText(i + 1, value)
                    values.append(value)
                    
                    if fid == highlight_fid:
                        item.setBackground(i + 1, QBrush(QColor(200, 220, 255)))
            
            # Highlight differences
            if len(set(values)) > 1:
                item.setForeground(0, QBrush(QColor(200, 100, 0)))
                font = item.font(0)
                font.setBold(True)
                item.setFont(0, font)
            
            self.compare_tree.addTopLevelItem(item)
    
    def _show_context_menu(self, pos):
        """Show context menu for tree items."""
        item = self.tree.itemAt(pos)
        if not item:
            return
        
        menu = QMenu(self)
        
        keep_action = menu.addAction(self.tr('Mark as Keep'))
        remove_action = menu.addAction(self.tr('Mark as Remove'))
        
        action = menu.exec_(self.tree.viewport().mapToGlobal(pos))
        
        if action == keep_action:
            self._set_action_for_selected('keep')
        elif action == remove_action:
            self._set_action_for_selected('remove')
    
    def _set_action_for_selected(self, action_type):
        """Set action for all selected items."""
        index = 1 if action_type == 'keep' else 2
        
        for item in self.tree.selectedItems():
            data = item.data(0, Qt.UserRole)
            if data and data[0] == 'feature':
                fid = data[1]
                combo = self.tree.itemWidget(item, 2)
                if combo:
                    combo.setCurrentIndex(index)
    
    def _select_all(self):
        """Select all items in the tree."""
        self.tree.selectAll()
    
    def _deselect_all(self):
        """Deselect all items."""
        self.tree.clearSelection()
    
    def _apply_filter(self, index):
        """Apply filter to tree items."""
        for i in range(self.tree.topLevelItemCount()):
            group_item = self.tree.topLevelItem(i)
            data = group_item.data(0, Qt.UserRole)
            
            if not data or data[0] != 'group':
                continue
            
            group = data[1]
            show = True
            
            if index == 1:  # Pending
                has_pending = any(
                    fid not in self.actions 
                    for fid in group.feature_ids
                )
                show = has_pending
            elif index == 2:  # Resolved
                all_resolved = all(
                    fid in self.actions 
                    for fid in group.feature_ids
                )
                show = all_resolved
            
            group_item.setHidden(not show)
    
    def _update_summary(self):
        """Update the summary label."""
        total_groups = len(self.groups)
        total_features = sum(len(g.feature_ids) for g in self.groups)
        to_keep = sum(1 for a in self.actions.values() if a == 'keep')
        to_remove = sum(1 for a in self.actions.values() if a == 'remove')
        pending = total_features - to_keep - to_remove
        
        self.summary_label.setText(
            self.tr('{0} groups | {1} features | Keep: {2} | Remove: {3} | Pending: {4}').format(
                total_groups, total_features, to_keep, to_remove, pending
            )
        )
    
    def get_actions(self):
        """Get all configured actions."""
        return self.actions.copy()
    
    def clear(self):
        """Clear all results."""
        self.tree.clear()
        self.compare_tree.clear()
        self.groups = []
        self.actions = {}
        self.id_field = None
        self.config = {}
        self.summary_label.setText('')
        
        # Reset info panels
        self.layer_name_label.setText('—')
        self.layer_geom_label.setText('—')
        self.layer_crs_label.setText('—')
        self.layer_source_label.setText('—')
        self.detection_type_label.setText('—')
        self.tolerance_label.setText('—')
        self.total_features_label.setText('—')
        self.duplicate_groups_label.setText('—')
        self.duplicate_features_label.setText('—')
