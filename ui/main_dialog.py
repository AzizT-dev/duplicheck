# -*- coding: utf-8 -*-
"""
DupliCheck - Main Dialog
=============================

Main dialog window with tabs for Configuration and Results.
Uses QGIS main map canvas for visualization.
"""

import os
from datetime import datetime

from qgis.PyQt.QtCore import Qt, QCoreApplication, pyqtSignal
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QPushButton, QMessageBox, QProgressBar, QLabel,
    QFrame, QMenu, QAction, QApplication
)
from qgis.PyQt.QtGui import QIcon, QColor
from qgis.core import QgsProject, QgsVectorLayer, QgsFeatureRequest, QgsRectangle
from qgis.gui import QgsRubberBand

from .widgets.config_widget import ConfigWidget
from .widgets.results_widget import ResultsWidget

from ..core.detector import DuplicateDetector


class DupliCheckDialog(QDialog):
    """
    Main dialog for DupliCheck plugin.
    
    Provides a tabbed interface for duplicate detection configuration
    and interactive results management.
    """
    
    # Signals
    detection_started = pyqtSignal()
    detection_finished = pyqtSignal(list)  # List of duplicate groups
    detection_error = pyqtSignal(str)
    
    def __init__(self, iface, parent=None):
        """
        Initialize the main dialog.
        
        :param iface: QGIS interface instance
        :param parent: Parent widget
        """
        super().__init__(parent)
        self.iface = iface
        self.plugin_dir = os.path.dirname(os.path.dirname(__file__))
        
        # State
        self.current_layer = None
        self.current_config = {}
        self.duplicate_groups = []
        self.detector = None
        self.snapshot_path = None
        
        # Rubber bands for highlighting on main canvas
        self.rubber_bands = []
        
        self._setup_ui()
        self._connect_signals()
    
    def tr(self, message):
        """Get translation for a string."""
        return QCoreApplication.translate('DupliCheckDialog', message)
    
    def _setup_ui(self):
        """Set up the user interface."""
        self.setWindowTitle(self.tr('DupliCheck - Duplicate Detection & Management'))
        
        # Window flags
        self.setWindowFlags(
            Qt.Window |
            Qt.WindowMinimizeButtonHint |
            Qt.WindowMaximizeButtonHint |
            Qt.WindowCloseButtonHint
        )
        
        self.setMinimumSize(900, 600)
        self.resize(1100, 700)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)
        
        # Tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setDocumentMode(True)
        
        # Create tabs
        self.config_widget = ConfigWidget(self.iface, self)
        self.results_widget = ResultsWidget(self.iface, self)
        
        # Add tabs with icons
        self.tab_widget.addTab(
            self.config_widget,
            self._get_icon('config.png'),
            self.tr('Configuration')
        )
        self.tab_widget.addTab(
            self.results_widget,
            self._get_icon('results.png'),
            self.tr('Results')
        )
        
        # Disable results tab initially
        self.tab_widget.setTabEnabled(1, False)
        
        main_layout.addWidget(self.tab_widget)
        
        # Progress bar
        self.progress_frame = QFrame()
        progress_layout = QHBoxLayout(self.progress_frame)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        
        self.progress_label = QLabel(self.tr('Ready'))
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        
        progress_layout.addWidget(self.progress_label, 1)
        progress_layout.addWidget(self.progress_bar, 2)
        
        main_layout.addWidget(self.progress_frame)
        
        # Bottom buttons
        button_layout = QHBoxLayout()
        
        # Reset button
        self.reset_btn = QPushButton(self.tr('Reset'))
        self.reset_btn.setIcon(self._get_icon('reset.png'))
        self.reset_btn.setToolTip(self.tr('Reset all settings for a new analysis'))
        
        # Export button with dropdown menu
        self.export_btn = QPushButton(self.tr('Export'))
        self.export_btn.setIcon(self._get_icon('export.png'))
        self.export_btn.setEnabled(False)
        
        export_menu = QMenu(self)
        export_menu.addAction(self.tr('Export as CSV'), lambda: self._export('csv'))
        export_menu.addAction(self.tr('Export as Excel'), lambda: self._export('xlsx'))
        export_menu.addAction(self.tr('Export as GeoPackage'), lambda: self._export('gpkg'))
        self.export_btn.setMenu(export_menu)
        
        # Apply button
        self.apply_btn = QPushButton(self.tr('Apply Actions'))
        self.apply_btn.setIcon(self._get_icon('apply.png'))
        self.apply_btn.setEnabled(False)
        self.apply_btn.setToolTip(self.tr('Apply keep/remove actions to features'))
        
        # Restore button
        self.restore_btn = QPushButton(self.tr('Restore'))
        self.restore_btn.setIcon(self._get_icon('restore.png'))
        self.restore_btn.setEnabled(False)
        self.restore_btn.setToolTip(self.tr('Restore layer from snapshot'))
        
        # Help button
        self.help_btn = QPushButton(self.tr('Help'))
        self.help_btn.setIcon(self._get_icon('help.png'))
        
        # Close button
        self.close_btn = QPushButton(self.tr('Close'))
        self.close_btn.setIcon(self._get_icon('close.png'))
        
        button_layout.addWidget(self.reset_btn)
        button_layout.addWidget(self.export_btn)
        button_layout.addWidget(self.apply_btn)
        button_layout.addWidget(self.restore_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.help_btn)
        button_layout.addWidget(self.close_btn)
        
        main_layout.addLayout(button_layout)
    
    def _get_icon(self, name):
        """Get icon from resources directory."""
        icon_path = os.path.join(self.plugin_dir, 'resources', 'icons', name)
        if os.path.exists(icon_path):
            return QIcon(icon_path)
        return QIcon()
    
    def _connect_signals(self):
        """Connect signals and slots."""
        # Config widget signals
        self.config_widget.run_detection.connect(self._run_detection)
        self.config_widget.layer_changed.connect(self._on_layer_changed)
        
        # Results widget signals
        self.results_widget.group_selected.connect(self._on_group_selected)
        self.results_widget.zoom_to_group.connect(self._zoom_to_group)
        self.results_widget.feature_clicked.connect(self._on_feature_clicked)
        self.results_widget.feature_double_clicked.connect(self._on_feature_double_clicked)
        
        # Detection signals
        self.detection_finished.connect(self._on_detection_finished)
        self.detection_error.connect(self._on_detection_error)
        
        # Button signals
        self.reset_btn.clicked.connect(self._reset_all)
        self.apply_btn.clicked.connect(self._apply_actions)
        self.restore_btn.clicked.connect(self._restore_snapshot)
        self.help_btn.clicked.connect(self._show_help)
        self.close_btn.clicked.connect(self.close)
    
    def _on_layer_changed(self, layer):
        """Handle layer selection change."""
        self.current_layer = layer
    
    def _run_detection(self, config):
        """Run duplicate detection with the given configuration."""
        layer = config.get('layer')
        if not layer or not layer.isValid():
            QMessageBox.warning(
                self,
                self.tr('No Layer Selected'),
                self.tr('Please select a layer to analyze.')
            )
            return
        
        self.current_layer = layer
        self.current_config = config
        
        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_label.setText(self.tr('Detecting duplicates...'))
        
        # Disable run button during detection
        self.config_widget.run_btn.setEnabled(False)
        
        try:
            # Create detector with proper parameters
            self.detector = DuplicateDetector(
                layer=layer,
                detection_type=config.get('detection_type', 'geometry'),
                tolerance=config.get('tolerance', 0.0),
                compare_method=config.get('compare_method', 0),
                decompose_multipart=config.get('decompose_multipart', False),
                fields=config.get('fields', []),
                normalize_attributes=config.get('normalize_attributes', True),
                ignore_null=config.get('ignore_null', False),
                sample_mode=config.get('sample_mode', False),
                sample_size=config.get('sample_size', 5000),
                disk_threshold=config.get('disk_threshold', 50000),
                progress_callback=self._on_progress
            )
            
            # Run detection
            self.duplicate_groups = self.detector.detect()
            
            # Emit finished signal
            self.detection_finished.emit(self.duplicate_groups)
            
        except Exception as e:
            self.detection_error.emit(str(e))
        
        finally:
            self.config_widget.run_btn.setEnabled(True)
    
    def _on_progress(self, value, message):
        """Handle progress update."""
        self.progress_bar.setValue(value)
        self.progress_label.setText(message)
        QApplication.processEvents()
    
    def _on_detection_finished(self, groups):
        """Handle detection completion."""
        self.progress_bar.setVisible(False)
        
        if not groups:
            self.progress_label.setText(self.tr('No duplicates found'))
            QMessageBox.information(
                self,
                self.tr('No Duplicates Found'),
                self.tr('No duplicate features were found with the current settings.')
            )
            return
        
        # Reset progress label
        self.progress_label.setText(self.tr('Ready'))
        
        # Pass ID field and config to results widget
        id_field = self.current_config.get('id_field')
        
        # Update results
        self.results_widget.set_results(groups, self.current_layer, id_field, self.current_config)
        
        # Enable tabs and buttons
        self.tab_widget.setTabEnabled(1, True)
        self.export_btn.setEnabled(True)
        self.apply_btn.setEnabled(True)
        
        # Switch to results tab
        self.tab_widget.setCurrentIndex(1)
    
    def _on_detection_error(self, error_message):
        """Handle detection error."""
        self.progress_bar.setVisible(False)
        self.progress_label.setText(self.tr('Error during detection'))
        
        QMessageBox.critical(
            self,
            self.tr('Detection Error'),
            self.tr('An error occurred during detection:\n\n{0}').format(error_message)
        )
    
    # ==================== VISUALIZATION ON MAIN CANVAS ====================
    
    def _clear_highlights(self):
        """Clear all rubber band highlights from main canvas."""
        canvas = self.iface.mapCanvas()
        for rb in self.rubber_bands:
            try:
                canvas.scene().removeItem(rb)
            except:
                pass
        self.rubber_bands = []
    
    def _highlight_features(self, layer, fids, zoom=False):
        """
        Highlight features on the main QGIS canvas.
        
        :param layer: Source QgsVectorLayer
        :param fids: List of feature IDs to highlight
        :param zoom: Whether to zoom to the features
        """
        self._clear_highlights()
        
        if not layer or not fids:
            return
        
        canvas = self.iface.mapCanvas()
        
        # Colors for different features
        colors = [
            QColor(66, 133, 244, 180),   # Blue
            QColor(234, 67, 53, 180),    # Red
            QColor(251, 188, 5, 180),    # Yellow
            QColor(52, 168, 83, 180),    # Green
            QColor(156, 39, 176, 180),   # Purple
        ]
        
        extent = None  # Will be set from first geometry
        
        for i, fid in enumerate(fids):
            request = QgsFeatureRequest().setFilterFid(fid)
            for feature in layer.getFeatures(request):
                geom = feature.geometry()
                if geom.isNull():
                    continue
                
                # Create rubber band
                geom_type = geom.type()
                rb = QgsRubberBand(canvas, geom_type)
                
                color = colors[i % len(colors)]
                
                if geom_type == 0:  # Point
                    rb.setColor(color)
                    rb.setWidth(10)
                elif geom_type == 1:  # Line
                    rb.setColor(color)
                    rb.setWidth(3)
                else:  # Polygon
                    rb.setColor(color)
                    rb.setWidth(2)
                    rb.setFillColor(QColor(
                        color.red(),
                        color.green(),
                        color.blue(),
                        80
                    ))
                
                rb.setToGeometry(geom, layer)
                self.rubber_bands.append(rb)
                
                # Extend combined extent
                bbox = geom.boundingBox()
                if extent is None:
                    extent = QgsRectangle(bbox)
                else:
                    extent.combineExtentWith(bbox)
        
        # Zoom if requested
        if zoom and extent is not None:
            # Ensure minimum extent size (for points)
            min_size = 100
            center = extent.center()
            if extent.width() < min_size:
                extent.setXMinimum(center.x() - min_size / 2)
                extent.setXMaximum(center.x() + min_size / 2)
            if extent.height() < min_size:
                extent.setYMinimum(center.y() - min_size / 2)
                extent.setYMaximum(center.y() + min_size / 2)
            
            extent.scale(1.5)
            canvas.setExtent(extent)
        
        canvas.refresh()
    
    def _zoom_to_feature(self, layer, fid, buffer_scale=1.5):
        """
        Zoom to a single feature on the main QGIS canvas.
        
        :param layer: Source QgsVectorLayer
        :param fid: Feature ID to zoom to
        :param buffer_scale: Scale factor for extent buffer
        """
        if not layer or fid is None:
            return
        
        canvas = self.iface.mapCanvas()
        
        request = QgsFeatureRequest().setFilterFid(fid)
        for feature in layer.getFeatures(request):
            geom = feature.geometry()
            if geom.isNull():
                continue
            
            # Clear and create new highlight
            self._clear_highlights()
            
            geom_type = geom.type()
            rb = QgsRubberBand(canvas, geom_type)
            
            color = QColor(66, 133, 244, 200)  # Blue
            
            if geom_type == 0:  # Point
                rb.setColor(color)
                rb.setWidth(12)
            elif geom_type == 1:  # Line
                rb.setColor(color)
                rb.setWidth(4)
            else:  # Polygon
                rb.setColor(color)
                rb.setWidth(3)
                rb.setFillColor(QColor(66, 133, 244, 100))
            
            rb.setToGeometry(geom, layer)
            self.rubber_bands.append(rb)
            
            # Zoom to feature - ALWAYS create a valid extent
            extent = geom.boundingBox()
            
            # For points or very small geometries, create a minimum extent
            min_size = 100  # minimum extent size in map units
            center = extent.center()
            
            # Always ensure minimum size (fixes point geometries)
            if extent.width() < min_size:
                extent.setXMinimum(center.x() - min_size / 2)
                extent.setXMaximum(center.x() + min_size / 2)
            if extent.height() < min_size:
                extent.setYMinimum(center.y() - min_size / 2)
                extent.setYMaximum(center.y() + min_size / 2)
            
            # Now apply buffer scale
            extent.scale(buffer_scale)
            canvas.setExtent(extent)
            canvas.refresh()
            return
    
    def _on_group_selected(self, group):
        """Handle group selection in results - highlight on main canvas."""
        if group and self.current_layer:
            self._highlight_features(self.current_layer, list(group.feature_ids), zoom=False)
    
    def _zoom_to_group(self, group):
        """Zoom to a duplicate group on the main canvas."""
        if not group or not self.current_layer:
            return
        self._highlight_features(self.current_layer, list(group.feature_ids), zoom=True)
    
    def _on_feature_clicked(self, fid):
        """Handle feature click - highlight and zoom on main canvas."""
        if self.current_layer:
            self._zoom_to_feature(self.current_layer, fid, buffer_scale=2.0)
    
    def _on_feature_double_clicked(self, fid):
        """Handle feature double-click - zoom closer on main canvas."""
        if self.current_layer:
            self._zoom_to_feature(self.current_layer, fid, buffer_scale=1.2)
    
    # ==================== OTHER ACTIONS ====================
    
    def _reset_all(self):
        """Reset all settings and results for a new analysis."""
        reply = QMessageBox.question(
            self,
            self.tr('Reset'),
            self.tr('This will clear all results and reset settings.\n\nContinue?'),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # Reset state
        self.duplicate_groups = []
        self.current_config = {}
        self.snapshot_path = None
        
        # Reset widgets
        self.config_widget.reset()
        self.results_widget.clear()
        self._clear_highlights()
        
        # Disable tabs and buttons
        self.tab_widget.setTabEnabled(1, False)
        self.export_btn.setEnabled(False)
        self.apply_btn.setEnabled(False)
        self.restore_btn.setEnabled(False)
        
        # Switch to config tab
        self.tab_widget.setCurrentIndex(0)
        
        # Reset progress
        self.progress_bar.setVisible(False)
        self.progress_label.setText(self.tr('Ready'))
    
    def _export(self, format_type):
        """Export results to file."""
        if not self.duplicate_groups:
            QMessageBox.warning(
                self,
                self.tr('No Results'),
                self.tr('No detection results to export.')
            )
            return
        
        from qgis.PyQt.QtWidgets import QFileDialog
        
        # File filter based on format
        filters = {
            'csv': self.tr('CSV Files (*.csv)'),
            'xlsx': self.tr('Excel Files (*.xlsx)'),
            'gpkg': self.tr('GeoPackage Files (*.gpkg)')
        }
        
        file_filter = filters.get(format_type, filters['csv'])
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            self.tr('Export Results'),
            '',
            file_filter
        )
        
        if not file_path:
            return
        
        try:
            from ..core.exporter import ResultsExporter
            
            exporter = ResultsExporter(
                groups=self.duplicate_groups,
                layer=self.current_layer,
                config=self.current_config
            )
            
            if format_type == 'csv':
                exporter.export_csv(file_path)
            elif format_type == 'xlsx':
                exporter.export_xlsx(file_path)
            elif format_type == 'gpkg':
                exporter.export_gpkg(file_path)
            
            QMessageBox.information(
                self,
                self.tr('Export Complete'),
                self.tr('Results exported successfully to:\n{0}').format(file_path)
            )
            
        except Exception as e:
            QMessageBox.critical(
                self,
                self.tr('Export Error'),
                self.tr('Failed to export results:\n{0}').format(str(e))
            )
    
    def _apply_actions(self):
        """Apply keep/remove actions to features."""
        actions = self.results_widget.get_actions()
        
        if not actions:
            QMessageBox.warning(
                self,
                self.tr('No Actions'),
                self.tr('No actions have been set. Mark features as "Keep" or "Remove" first.')
            )
            return
        
        to_remove = [fid for fid, action in actions.items() if action == 'remove']
        
        if not to_remove:
            QMessageBox.information(
                self,
                self.tr('No Features to Remove'),
                self.tr('No features have been marked for removal.')
            )
            return
        
        # Confirm
        reply = QMessageBox.warning(
            self,
            self.tr('Confirm Removal'),
            self.tr('This will delete {0} features from the layer.\n\n'
                   'A snapshot will be created before deletion.\n\n'
                   'Continue?').format(len(to_remove)),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        try:
            # Create snapshot
            self._create_snapshot()
            
            # Delete features
            self.current_layer.startEditing()
            self.current_layer.deleteFeatures(to_remove)
            self.current_layer.commitChanges()
            
            self.restore_btn.setEnabled(True)
            
            QMessageBox.information(
                self,
                self.tr('Removal Complete'),
                self.tr('{0} features have been removed.\n\n'
                       'Use "Restore" to undo if needed.').format(len(to_remove))
            )
            
            # Clear results
            self._clear_highlights()
            
        except Exception as e:
            self.current_layer.rollBack()
            QMessageBox.critical(
                self,
                self.tr('Error'),
                self.tr('Failed to remove features:\n{0}').format(str(e))
            )
    
    def _create_snapshot(self):
        """Create a snapshot of the current layer."""
        import tempfile
        from qgis.core import QgsVectorFileWriter
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.snapshot_path = os.path.join(
            tempfile.gettempdir(),
            f'duplicheck_snapshot_{timestamp}.gpkg'
        )
        
        QgsVectorFileWriter.writeAsVectorFormat(
            self.current_layer,
            self.snapshot_path,
            'UTF-8',
            self.current_layer.crs(),
            'GPKG'
        )
    
    def _restore_snapshot(self):
        """Restore layer from snapshot."""
        if not self.snapshot_path or not os.path.exists(self.snapshot_path):
            QMessageBox.warning(
                self,
                self.tr('No Snapshot'),
                self.tr('No snapshot available to restore.')
            )
            return
        
        reply = QMessageBox.question(
            self,
            self.tr('Restore Snapshot'),
            self.tr('This will restore the layer to its state before deletion.\n\nContinue?'),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        try:
            # Load snapshot
            snapshot_layer = QgsVectorLayer(self.snapshot_path, 'snapshot', 'ogr')
            
            if not snapshot_layer.isValid():
                raise Exception(self.tr('Failed to load snapshot'))
            
            # Get features from snapshot
            self.current_layer.startEditing()
            
            # Delete all current features
            self.current_layer.deleteFeatures(
                [f.id() for f in self.current_layer.getFeatures()]
            )
            
            # Copy features from snapshot
            for feature in snapshot_layer.getFeatures():
                self.current_layer.addFeature(feature)
            
            self.current_layer.commitChanges()
            
            QMessageBox.information(
                self,
                self.tr('Restore Complete'),
                self.tr('Layer has been restored to its previous state.')
            )
            
            self.restore_btn.setEnabled(False)
            
        except Exception as e:
            self.current_layer.rollBack()
            QMessageBox.critical(
                self,
                self.tr('Restore Error'),
                self.tr('Failed to restore layer:\n{0}').format(str(e))
            )
    
    def _show_help(self):
        """Show help dialog."""
        QMessageBox.information(
            self,
            self.tr('DupliCheck Help'),
            self.tr('''<h3>DupliCheck - Duplicate Detection</h3>
<p><b>Configuration Tab:</b></p>
<ul>
<li>Select a layer to analyze</li>
<li>Choose detection type (Geometric or Attribute)</li>
<li>Select an ID field for identification</li>
<li>Configure detection method and tolerance</li>
<li>Click "Run Detection" to start analysis</li>
</ul>

<p><b>Results Tab:</b></p>
<ul>
<li>View detected duplicate groups</li>
<li>Click on a feature to highlight and zoom on the map</li>
<li>Double-click for closer zoom</li>
<li>Mark features as "Keep" or "Remove"</li>
<li>Use "Apply Actions" to delete marked features</li>
</ul>

<p><b>Export:</b> Save results as CSV, Excel, or GeoPackage</p>
<p><b>Restore:</b> Undo deletions using the snapshot</p>
''')
        )
    
    def closeEvent(self, event):
        """Handle dialog close."""
        self._clear_highlights()
        event.accept()
