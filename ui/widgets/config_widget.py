# -*- coding: utf-8 -*-
"""
DupliCheck - Configuration Widget
======================================

Widget for configuring duplicate detection parameters.
"""

from qgis.PyQt.QtCore import Qt, QCoreApplication, pyqtSignal
from qgis.PyQt.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout,
    QLabel, QComboBox, QDoubleSpinBox, QCheckBox, QPushButton,
    QListWidget, QListWidgetItem, QAbstractItemView, QRadioButton,
    QButtonGroup, QSpinBox, QFrame, QFileDialog, QMessageBox,
    QTabWidget, QScrollArea
)
from qgis.core import QgsProject, QgsVectorLayer, QgsMapLayerProxyModel, QgsWkbTypes
from qgis.gui import QgsMapLayerComboBox, QgsFieldComboBox


class ConfigWidget(QWidget):
    """
    Configuration widget for duplicate detection settings.
    
    Provides options for layer selection, detection type,
    tolerance settings, and priority rules.
    """
    
    # Signals
    run_detection = pyqtSignal(dict)  # Emits configuration dict
    layer_changed = pyqtSignal(object)  # Emits QgsVectorLayer or None
    
    def __init__(self, iface, parent=None):
        """
        Initialize the configuration widget.
        
        :param iface: QGIS interface instance
        :param parent: Parent widget
        """
        super().__init__(parent)
        self.iface = iface
        self._setup_ui()
        self._connect_signals()
    
    def tr(self, message):
        """Get translation for a string."""
        return QCoreApplication.translate('ConfigWidget', message)
    
    def _setup_ui(self):
        """Set up the user interface."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Scroll area for smaller screens
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(15)
        
        # === Layer Selection Group ===
        layer_group = QGroupBox(self.tr('Layer Selection'))
        layer_layout = QVBoxLayout()
        
        # Source selection
        source_layout = QHBoxLayout()
        self.source_project_radio = QRadioButton(self.tr('From current project'))
        self.source_file_radio = QRadioButton(self.tr('From file'))
        self.source_project_radio.setChecked(True)
        
        source_layout.addWidget(self.source_project_radio)
        source_layout.addWidget(self.source_file_radio)
        source_layout.addStretch()
        layer_layout.addLayout(source_layout)
        
        # Layer combo (project layers)
        self.layer_combo = QgsMapLayerComboBox()
        self.layer_combo.setFilters(QgsMapLayerProxyModel.VectorLayer)
        self.layer_combo.setAllowEmptyLayer(True)
        self.layer_combo.setShowCrs(True)
        layer_layout.addWidget(self.layer_combo)
        
        # File selection (hidden by default)
        file_layout = QHBoxLayout()
        self.file_path_label = QLabel(self.tr('No file selected'))
        self.file_path_label.setStyleSheet('color: gray; font-style: italic;')
        self.browse_btn = QPushButton(self.tr('Browse...'))
        file_layout.addWidget(self.file_path_label, 1)
        file_layout.addWidget(self.browse_btn)
        
        self.file_frame = QFrame()
        self.file_frame.setLayout(file_layout)
        self.file_frame.setVisible(False)
        layer_layout.addWidget(self.file_frame)
        
        # === ID Field Selection (ALWAYS VISIBLE) ===
        id_field_layout = QHBoxLayout()
        id_field_label = QLabel(self.tr('ID Field:'))
        id_field_label.setToolTip(self.tr('Field used to identify features in results'))
        self.id_field_combo = QgsFieldComboBox()
        self.id_field_combo.setAllowEmptyFieldName(True)
        id_field_layout.addWidget(id_field_label)
        id_field_layout.addWidget(self.id_field_combo, 1)
        layer_layout.addLayout(id_field_layout)
        
        # Layer info
        self.layer_info_label = QLabel()
        self.layer_info_label.setStyleSheet('color: #666;')
        layer_layout.addWidget(self.layer_info_label)
        
        layer_group.setLayout(layer_layout)
        scroll_layout.addWidget(layer_group)
        
        # === Detection Type Group ===
        detection_group = QGroupBox(self.tr('Detection Type'))
        detection_layout = QVBoxLayout()
        
        # Type selection
        self.type_button_group = QButtonGroup(self)
        
        self.geometry_radio = QRadioButton(self.tr('Geometric (spatial duplicates)'))
        self.attribute_radio = QRadioButton(self.tr('Attribute (field value duplicates)'))
        self.geometry_radio.setChecked(True)
        
        self.type_button_group.addButton(self.geometry_radio, 0)
        self.type_button_group.addButton(self.attribute_radio, 1)
        
        detection_layout.addWidget(self.geometry_radio)
        detection_layout.addWidget(self.attribute_radio)
        
        # Geometry options
        self.geometry_frame = QFrame()
        geom_layout = QFormLayout(self.geometry_frame)
        geom_layout.setContentsMargins(20, 10, 0, 0)
        
        # Tolerance
        tolerance_layout = QHBoxLayout()
        self.tolerance_spin = QDoubleSpinBox()
        self.tolerance_spin.setRange(0, 1000000)
        self.tolerance_spin.setDecimals(6)
        self.tolerance_spin.setValue(0)
        self.tolerance_spin.setSuffix('')
        self.tolerance_spin.setToolTip(self.tr('0 = exact match, >0 = features within this distance'))
        
        self.tolerance_unit_label = QLabel(self.tr('map units'))
        tolerance_layout.addWidget(self.tolerance_spin)
        tolerance_layout.addWidget(self.tolerance_unit_label)
        tolerance_layout.addStretch()
        
        geom_layout.addRow(self.tr('Tolerance:'), tolerance_layout)
        
        # Compare method - RENAMED with clearer terms
        self.compare_method_combo = QComboBox()
        self.compare_method_combo.addItems([
            self.tr('Exact match (identical geometry)'),
            self.tr('By center point distance'),
            self.tr('By shape similarity'),
            self.tr('By bounding box overlap')
        ])
        # Tooltips for each method
        self.compare_method_combo.setItemData(0, self.tr(
            'Detects geometries that are perfectly identical (same coordinates).\n'
            'Best for finding exact copies.'
        ), Qt.ToolTipRole)
        self.compare_method_combo.setItemData(1, self.tr(
            'Compares the distance between feature centers (centroids).\n'
            'Useful for point features or when positions are slightly different.'
        ), Qt.ToolTipRole)
        self.compare_method_combo.setItemData(2, self.tr(
            'Compares the overall shape of geometries (Hausdorff distance).\n'
            'Useful for detecting features with similar shapes but different positions.'
        ), Qt.ToolTipRole)
        self.compare_method_combo.setItemData(3, self.tr(
            'Detects features whose bounding boxes overlap.\n'
            'Fast but less precise, useful for initial screening.'
        ), Qt.ToolTipRole)
        
        geom_layout.addRow(self.tr('Method:'), self.compare_method_combo)
        
        # Handle multipart
        self.multipart_check = QCheckBox(self.tr('Decompose multipart geometries'))
        self.multipart_check.setToolTip(self.tr('Compare individual parts of multipart features'))
        geom_layout.addRow('', self.multipart_check)
        
        detection_layout.addWidget(self.geometry_frame)
        
        # Attribute options
        self.attribute_frame = QFrame()
        attr_layout = QVBoxLayout(self.attribute_frame)
        attr_layout.setContentsMargins(20, 10, 0, 0)
        
        attr_label = QLabel(self.tr('Select fields to compare (Ctrl+click for multiple):'))
        attr_layout.addWidget(attr_label)
        
        self.fields_list = QListWidget()
        self.fields_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.fields_list.setMaximumHeight(120)
        attr_layout.addWidget(self.fields_list)
        
        # Normalize options
        self.normalize_check = QCheckBox(self.tr('Normalize values (trim, lowercase, Unicode NFKC)'))
        self.normalize_check.setChecked(True)
        attr_layout.addWidget(self.normalize_check)
        
        self.ignore_null_check = QCheckBox(self.tr('Ignore NULL values'))
        attr_layout.addWidget(self.ignore_null_check)
        
        self.attribute_frame.setVisible(False)
        detection_layout.addWidget(self.attribute_frame)
        
        detection_group.setLayout(detection_layout)
        scroll_layout.addWidget(detection_group)
        
        # === Performance Options Group ===
        perf_group = QGroupBox(self.tr('Performance Options'))
        perf_layout = QFormLayout()
        
        # Sample size
        sample_layout = QHBoxLayout()
        self.sample_check = QCheckBox(self.tr('Preview mode (sample):'))
        self.sample_spin = QSpinBox()
        self.sample_spin.setRange(100, 100000)
        self.sample_spin.setValue(5000)
        self.sample_spin.setSuffix(self.tr(' features'))
        self.sample_spin.setEnabled(False)
        
        sample_layout.addWidget(self.sample_check)
        sample_layout.addWidget(self.sample_spin)
        sample_layout.addStretch()
        
        perf_layout.addRow(sample_layout)
        
        # Memory threshold
        self.disk_threshold_spin = QSpinBox()
        self.disk_threshold_spin.setRange(1000, 1000000)
        self.disk_threshold_spin.setValue(50000)
        self.disk_threshold_spin.setSuffix(self.tr(' features'))
        self.disk_threshold_spin.setToolTip(
            self.tr('Use disk-backed storage for layers larger than this')
        )
        perf_layout.addRow(self.tr('Disk storage threshold:'), self.disk_threshold_spin)
        
        perf_group.setLayout(perf_layout)
        scroll_layout.addWidget(perf_group)
        
        # Spacer
        scroll_layout.addStretch()
        
        # Run button
        self.run_btn = QPushButton(self.tr('▶ Run Detection'))
        self.run_btn.setMinimumHeight(40)
        self.run_btn.setStyleSheet('''
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                font-size: 14px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        ''')
        scroll_layout.addWidget(self.run_btn)
        
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)
    
    def _connect_signals(self):
        """Connect signals and slots."""
        # Source selection
        self.source_project_radio.toggled.connect(self._on_source_changed)
        self.source_file_radio.toggled.connect(self._on_source_changed)
        self.browse_btn.clicked.connect(self._browse_file)
        
        # Layer selection
        self.layer_combo.layerChanged.connect(self._on_layer_changed)
        
        # Detection type
        self.type_button_group.buttonToggled.connect(self._on_type_changed)
        
        # Sample option
        self.sample_check.toggled.connect(self.sample_spin.setEnabled)
        
        # Run button
        self.run_btn.clicked.connect(self._on_run_clicked)
        
        # Initialize with current layer
        self._on_layer_changed(self.layer_combo.currentLayer())
    
    def _on_source_changed(self, checked):
        """Handle source type change."""
        is_project = self.source_project_radio.isChecked()
        self.layer_combo.setVisible(is_project)
        self.file_frame.setVisible(not is_project)
        
        if is_project:
            self._on_layer_changed(self.layer_combo.currentLayer())
    
    def _browse_file(self):
        """Open file browser to select a vector file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr('Select Vector Layer'),
            '',
            self.tr('Vector Files (*.shp *.gpkg *.geojson *.kml *.gml);;All Files (*)')
        )
        
        if file_path:
            layer = QgsVectorLayer(file_path, '', 'ogr')
            if layer.isValid():
                self.file_path_label.setText(file_path)
                self.file_path_label.setStyleSheet('color: black;')
                self._on_layer_changed(layer)
            else:
                QMessageBox.warning(
                    self,
                    self.tr('Invalid File'),
                    self.tr('Could not load the selected file as a vector layer.')
                )
    
    def _on_layer_changed(self, layer):
        """
        Handle layer selection change.
        
        :param layer: Selected QgsVectorLayer or None
        """
        # Update layer info
        if layer and layer.isValid():
            geom_type = QgsWkbTypes.displayString(layer.wkbType())
            crs = layer.crs().authid() or self.tr('Unknown CRS')
            feature_count = layer.featureCount()
            
            self.layer_info_label.setText(
                self.tr('{0} features | {1} | {2}').format(
                    feature_count, geom_type, crs
                )
            )
            
            # Update tolerance unit based on CRS
            if layer.crs().isGeographic():
                self.tolerance_unit_label.setText(self.tr('degrees'))
            else:
                units = layer.crs().mapUnits()
                unit_str = ['meters', 'feet', 'degrees', 'unknown', 'unknown', 
                           'nautical miles', 'kilometers', 'yards', 'miles'][units]
                self.tolerance_unit_label.setText(self.tr(unit_str))
            
            # Update ID field combo
            self.id_field_combo.setLayer(layer)
            # Select first field by default
            if layer.fields().count() > 0:
                self.id_field_combo.setCurrentIndex(0)
            
            # Update fields list for attribute detection
            self.fields_list.clear()
            for field in layer.fields():
                item = QListWidgetItem(f"{field.name()} ({field.typeName()})")
                item.setData(Qt.UserRole, field.name())
                self.fields_list.addItem(item)
            
            self.run_btn.setEnabled(True)
        else:
            self.layer_info_label.setText('')
            self.fields_list.clear()
            self.run_btn.setEnabled(False)
        
        # Emit signal
        self.layer_changed.emit(layer)
    
    def _on_type_changed(self, button, checked):
        """Handle detection type change."""
        if not checked:
            return
        
        is_geometry = button == self.geometry_radio
        self.geometry_frame.setVisible(is_geometry)
        self.attribute_frame.setVisible(not is_geometry)
    
    def _on_run_clicked(self):
        """Handle run button click."""
        config = self.get_config()
        
        # Validate configuration
        if config['detection_type'] == 'attribute' and not config['fields']:
            QMessageBox.warning(
                self,
                self.tr('No Fields Selected'),
                self.tr('Please select at least one field for attribute comparison.')
            )
            return
        
        self.run_detection.emit(config)
    
    def get_config(self):
        """
        Get current configuration as a dictionary.
        
        :returns: Configuration dictionary
        :rtype: dict
        """
        # Get selected layer
        if self.source_project_radio.isChecked():
            layer = self.layer_combo.currentLayer()
        else:
            # File-based layer (stored in label data)
            path = self.file_path_label.text()
            layer = QgsVectorLayer(path, '', 'ogr') if path != self.tr('No file selected') else None
        
        # Get detection type
        detection_type = 'geometry' if self.geometry_radio.isChecked() else 'attribute'
        
        # Get selected fields for attribute detection
        selected_fields = []
        for item in self.fields_list.selectedItems():
            selected_fields.append(item.data(Qt.UserRole))
        
        # Get ID field
        id_field = self.id_field_combo.currentField()
        
        return {
            'layer': layer,
            'id_field': id_field,
            'detection_type': detection_type,
            'tolerance': self.tolerance_spin.value(),
            'compare_method': self.compare_method_combo.currentIndex(),
            'decompose_multipart': self.multipart_check.isChecked(),
            'fields': selected_fields,
            'normalize_attributes': self.normalize_check.isChecked(),
            'ignore_null': self.ignore_null_check.isChecked(),
            'sample_mode': self.sample_check.isChecked(),
            'sample_size': self.sample_spin.value(),
            'disk_threshold': self.disk_threshold_spin.value()
        }
    
    def get_current_layer(self):
        """
        Get the currently selected layer.
        
        :returns: Current QgsVectorLayer or None
        """
        if self.source_project_radio.isChecked():
            return self.layer_combo.currentLayer()
        else:
            path = self.file_path_label.text()
            if path != self.tr('No file selected'):
                return QgsVectorLayer(path, '', 'ogr')
        return None
    
    def reset(self):
        """Reset all configuration to defaults."""
        # Reset source
        self.source_project_radio.setChecked(True)
        self.file_path_label.setText(self.tr('No file selected'))
        self.file_path_label.setStyleSheet('color: gray; font-style: italic;')
        
        # Reset detection type
        self.geometry_radio.setChecked(True)
        
        # Reset geometry options
        self.tolerance_spin.setValue(0)
        self.compare_method_combo.setCurrentIndex(0)
        self.multipart_check.setChecked(False)
        
        # Reset attribute options
        self.fields_list.clearSelection()
        self.normalize_check.setChecked(True)
        self.ignore_null_check.setChecked(False)
        
        # Reset performance options
        self.sample_check.setChecked(False)
        self.sample_spin.setValue(5000)
        self.disk_threshold_spin.setValue(50000)
        
        # Refresh layer combo
        self._on_layer_changed(self.layer_combo.currentLayer())
