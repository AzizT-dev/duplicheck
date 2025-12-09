# -*- coding: utf-8 -*-
"""
DupliCheck - Main Plugin Class
===============================

Handles plugin initialization, toolbar integration, and i18n setup.
"""

import os
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, QLocale
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction
from qgis.core import QgsApplication

from .ui.main_dialog import DupliCheckDialog


class DupliCheck:
    """
    Main plugin class for DupliCheck.
    
    Manages plugin lifecycle, toolbar actions, and internationalization.
    """
    
    # Supported languages with their locale codes
    SUPPORTED_LANGUAGES = {
        'en': 'English',
        'fr': 'Français',
        'es': 'Español',
        'ar': 'العربية',
        'ru': 'Русский',
        'de': 'Deutsch',
        'it': 'Italiano',
        'pt': 'Português',
        'zh': '中文'
    }
    
    def __init__(self, iface):
        """
        Constructor.
        
        :param iface: QGIS interface instance
        :type iface: QgsInterface
        """
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        
        # Initialize translator
        self.translator = None
        self._setup_translation()
        
        # Plugin state
        self.actions = []
        self.menu = self.tr('&Vector')
        self.toolbar = self.iface.addToolBar('DupliCheck')
        self.toolbar.setObjectName('DupliCheckToolbar')
        
        # Dialog reference
        self.dialog = None
    
    def _setup_translation(self):
        """
        Set up the translation system based on QGIS locale or user preference.
        """
        # Get locale from QGIS settings
        locale = QSettings().value('locale/userLocale', QLocale.system().name())
        locale_code = locale[:2] if locale else 'en'
        
        # Check if we support this locale
        if locale_code not in self.SUPPORTED_LANGUAGES:
            locale_code = 'en'
        
        # Load translation file
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            f'duplicheck_{locale_code}.qm'
        )
        
        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)
    
    def tr(self, message):
        """
        Get the translation for a string using Qt translation API.
        
        :param message: String for translation.
        :type message: str
        :returns: Translated string
        :rtype: str
        """
        return QCoreApplication.translate('DupliCheck', message)
    
    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None
    ):
        """
        Add a toolbar icon and menu item.
        
        :param icon_path: Path to the icon file
        :param text: Text for the menu item
        :param callback: Function to call when action is triggered
        :param enabled_flag: Whether the action is enabled
        :param add_to_menu: Add to plugin menu
        :param add_to_toolbar: Add to toolbar
        :param status_tip: Status bar message on hover
        :param whats_this: What's This help text
        :param parent: Parent widget
        :returns: The created action
        :rtype: QAction
        """
        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)
        
        if status_tip is not None:
            action.setStatusTip(status_tip)
        
        if whats_this is not None:
            action.setWhatsThis(whats_this)
        
        if add_to_toolbar:
            self.toolbar.addAction(action)
        
        if add_to_menu:
            self.iface.addPluginToVectorMenu(self.menu, action)
        
        self.actions.append(action)
        return action
    
    def initGui(self):
        """
        Create the menu entries and toolbar icons inside the QGIS GUI.
        """
        icon_path = os.path.join(self.plugin_dir, 'resources', 'icons', 'duplicheck.png')
        
        # Fallback to default icon if custom icon doesn't exist
        if not os.path.exists(icon_path):
            icon_path = ':/images/themes/default/algorithms/mAlgorithmDeleteDuplicateGeometries.svg'
        
        self.add_action(
            icon_path,
            text=self.tr('DupliCheck'),
            callback=self.run,
            parent=self.iface.mainWindow(),
            status_tip=self.tr('Detect and manage duplicate features interactively'),
            whats_this=self.tr(
                'DupliCheck allows you to detect geometric and attribute '
                'duplicates in vector layers and decide interactively which '
                'features to keep or remove.'
            )
        )
    
    def unload(self):
        """
        Remove the plugin menu items and toolbar icons from QGIS GUI.
        """
        for action in self.actions:
            self.iface.removePluginVectorMenu(self.tr('&Vector'), action)
            self.iface.removeToolBarIcon(action)
        
        # Remove the toolbar
        del self.toolbar
        
        # Clean up dialog
        if self.dialog:
            self.dialog.close()
            self.dialog = None
    
    def run(self):
        """
        Run method that performs the main plugin functionality.
        """
        # Create dialog if it doesn't exist or was closed
        if self.dialog is None:
            self.dialog = DupliCheckDialog(self.iface, parent=self.iface.mainWindow())
        
        # Show the dialog (non-modal for map interaction)
        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()
