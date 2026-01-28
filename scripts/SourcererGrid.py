"""
SourcererGrid - Touch-friendly grid UI for Sourcerer.

Displays source thumbnails in a grid layout for quick visual selection,
ideal for touch screen performances and live show control.

Author: Matthew Wachter
License: MIT
"""

import traceback
from math import floor

from CallbacksExt import CallbacksExt
from TDStoreTools import StorageManager


class SourcererGrid(CallbacksExt):
    """
    Grid-based source selector for Sourcerer.

    Displays source thumbnails in a configurable grid layout with support
    for pagination or scrollbar overflow handling. Click any cell to
    trigger that source.

    Features:
        - Automatic button sizing based on grid dimensions
        - Configurable max buttons per row
        - Pagination or scrollbar overflow modes
        - Automatic updates when sources change or panel resizes
    """

    def __init__(self, ownerComp):
        self.ownerComp = ownerComp

        # Initialize callbacks
        self.callbackDat = self.ownerComp.par.Callbackdat.eval()
        try:
            CallbacksExt.__init__(self, ownerComp)
        except:
            self.ownerComp.addScriptError(
                traceback.format_exc() + "Error in CallbacksExt __init__. See textport."
            )
            print()
            print("Error initializing callbacks - " + self.ownerComp.path)
            print(traceback.format_exc())

        try:
            self.DoCallback('onInit', {'ownerComp': self.ownerComp})
        except:
            self.ownerComp.addScriptError(
                traceback.format_exc() + "Error in custom onInit callback. See textport."
            )
            print(traceback.format_exc())

        # Internal operator references
        self.buttonGrid = self.ownerComp.op('buttonGrid')
        self.dataComp = ownerComp.op('data')

        # Stored items (persistent across saves and re-initialization)
        storedItems = [
            {'name': 'Data', 'default': None, 'readOnly': False,
             'property': True, 'dependable': True},
            {'name': 'MaxRows', 'default': 0, 'readOnly': False,
             'property': True, 'dependable': True},
            {'name': 'ButtonSize', 'default': 1, 'readOnly': False,
             'property': True, 'dependable': True},
            {'name': 'ButtonsMax', 'default': 0, 'readOnly': False,
             'property': True, 'dependable': True},
            {'name': 'ButtonsNum', 'default': 0, 'readOnly': False,
             'property': True, 'dependable': True},
            {'name': 'ButtonsStart', 'default': 0, 'readOnly': False,
             'property': True, 'dependable': True},
            {'name': 'CurPage', 'default': 1, 'readOnly': False,
             'property': True, 'dependable': True},
            {'name': 'NumPages', 'default': 1, 'readOnly': False,
             'property': True, 'dependable': True},
        ]
        self.stored = StorageManager(self, self.dataComp, storedItems)

        self.updateDisplay()

    # -------------------------------------------------------------------------
    # Layout Calculations
    # -------------------------------------------------------------------------

    def _calcButtonSize(self):
        """Calculate the button size in pixels based on grid dimensions.

        Accounts for margins, spacing, and scrollbar width to ensure
        buttons fit evenly within the available space.
        """
        bg = self.buttonGrid
        bg_width = bg.width
        bg_margins = bg.par.marginl.eval() + bg.par.marginr.eval()
        bg_spacing = bg.par.spacing.eval()
        bg_max_per_row = self.ownerComp.par.Maxperrow.eval()

        # Account for scrollbar if enabled
        bg_scrollbar_width = 0
        if bg.par.pvscrollbar.eval() == 'on':
            bg_scrollbar_width = bg.par.scrollbarthickness.eval()

        button_size = (bg_width - bg_margins - bg_scrollbar_width -
                       (bg_spacing * (bg_max_per_row - 1))) / bg_max_per_row
        return floor(button_size)

    def _calcMaxRows(self):
        """Calculate the maximum number of rows that fit in the grid height."""
        bg = self.buttonGrid
        bg_height = bg.height
        bg_margins = bg.par.margint.eval() + bg.par.marginb.eval()
        bg_spacing = bg.par.spacing.eval()
        button_size = self.stored['ButtonSize']
        max_rows = int((bg_height - bg_margins + bg_spacing) / (button_size + bg_spacing))
        return max_rows

    def _calcButtonsMax(self):
        """Calculate maximum buttons that fit on one page."""
        return self.ownerComp.par.Maxperrow.eval() * self.stored['MaxRows']

    def _calcButtonsNum(self):
        """Calculate the number of buttons to display.

        In scrollbar mode, shows all sources.
        In pagination mode, shows only sources for the current page.
        """
        sourcerer = self.ownerComp.par.Sourcerer.eval()
        if sourcerer is None:
            return 0

        if self.ownerComp.par.Overflow.eval() == 'scrollbar':
            return len(sourcerer.Sources)
        else:
            # Pagination mode - calculate buttons for current page
            total_sources = len(sourcerer.Sources)
            buttons_per_page = self.ownerComp.par.Maxperrow.eval() * self.stored['MaxRows']
            start_index = (self.stored['CurPage'] - 1) * buttons_per_page
            remaining_sources = total_sources - start_index
            return min(remaining_sources, buttons_per_page)

    def _calcButtonsStart(self):
        """Calculate the starting source index for pagination mode."""
        if self.ownerComp.par.Overflow.eval() == 'scrollbar':
            return 0
        else:
            return (self.stored['CurPage'] - 1) * self.stored['ButtonsMax']

    def _calcPages(self):
        """Calculate the total number of pages needed for all sources."""
        sourcerer = self.ownerComp.par.Sourcerer.eval()
        if sourcerer is None:
            self.NumPages = 1
            return

        total_sources = len(sourcerer.Sources)
        buttons_per_page = self.ownerComp.par.Maxperrow.eval() * self.stored['MaxRows']
        num_pages = (total_sources + buttons_per_page - 1) // buttons_per_page
        if num_pages < 1:
            num_pages = 1
        self.NumPages = num_pages

    # -------------------------------------------------------------------------
    # Public Methods
    # -------------------------------------------------------------------------

    def updateDisplay(self):
        """Refresh the entire grid display."""
        self.updateButtons()
        self.updatePages()

    def updateButtons(self):
        """Recalculate button layout and update stored values."""
        self.stored['ButtonSize'] = self._calcButtonSize()
        self.stored['MaxRows'] = self._calcMaxRows()
        self.stored['ButtonsMax'] = self._calcButtonsMax()
        self.stored['ButtonsNum'] = self._calcButtonsNum()
        self.stored['ButtonsStart'] = self._calcButtonsStart()

    def updatePages(self):
        """Recalculate pagination and ensure current page is valid."""
        self._calcPages()
        if self.stored['CurPage'] > self.stored['NumPages']:
            self.stored['CurPage'] = self.stored['NumPages']

    def NextPage(self):
        """Navigate to the next page (pagination mode only)."""
        if self.stored['CurPage'] < self.stored['NumPages']:
            self.stored['CurPage'] += 1
            self.updateDisplay()

    def PrevPage(self):
        """Navigate to the previous page (pagination mode only)."""
        if self.stored['CurPage'] > 1:
            self.stored['CurPage'] -= 1
            self.updateDisplay()

    # -------------------------------------------------------------------------
    # Event Handlers
    # -------------------------------------------------------------------------

    def onSelectSource(self, index):
        """Handle source selection from the grid.

        Args:
            index: The source index to trigger.
        """
        sourcerer = self.ownerComp.par.Sourcerer.eval()
        if sourcerer is None:
            return

        sourcerer.Take(index)

    def onPanelSizeChange(self):
        """Handle panel resize events."""
        self.updateDisplay()

    def onSourcesChange(self):
        """Handle changes to the Sourcerer source list."""
        self.updateDisplay()

    # -------------------------------------------------------------------------
    # Pulse Parameter Handlers
    # -------------------------------------------------------------------------

    def pulse_Editextension(self):
        """Open extension for editing."""
        self.ownerComp.op('SourcererGrid').par.edit.pulse()
