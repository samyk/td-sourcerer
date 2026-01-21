# SourcererListLite - List component for Sourcerer Lite
# Features: double-click rename, drag-drop reorder, right-click context menu


class SourcererList:
    # Hardcoded color scheme (dark theme)
    COLORS = {
        # Label/Header
        'label_bg': (0.125, 0.125, 0.125, 1),
        'label_font': (0.7, 0.7, 0.7, 1),

        # Cell backgrounds
        'cell_bg': (0.2, 0.2, 0.2, 1),
        'cell_bg_hover': (0.25, 0.25, 0.25, 1),
        'cell_bg_active': (0.3, 0.4, 0.5, 1),
        'cell_bg_active_hover': (0.35, 0.45, 0.55, 1),
        'cell_bg_live': (0.2, 0.35, 0.2, 1),
        'cell_bg_live_hover': (0.25, 0.4, 0.25, 1),
        'cell_bg_live_active': (0.3, 0.5, 0.4, 1),
        'cell_bg_live_active_hover': (0.35, 0.55, 0.45, 1),

        # Cell fonts
        'cell_font': (0.7, 0.7, 0.7, 1),
        'cell_font_hover': (0.85, 0.85, 0.85, 1),
        'cell_font_active': (1.0, 1.0, 1.0, 1),
        'cell_font_active_hover': (1.0, 1.0, 1.0, 1),

        # Borders
        'border_right': (0.1, 0.1, 0.1, 1),
        'border_left': (0.1, 0.1, 0.1, 1),
        'border_top': (0.1, 0.1, 0.1, 1),
        'border_bottom': (0.1, 0.1, 0.1, 1),

        # Drag highlight
        'drag_highlight': (0.2, 0.5, 0.8, 1),
    }

    # Hardcoded sizes
    CELL_HEIGHT = 24
    CELL_FONT_SIZE = 12
    LABEL_HEIGHT = 24
    LABEL_FONT_SIZE = 12

    """List UI for displaying and managing sources."""

    def __init__(self, ownerComp):
        self.ownerComp = ownerComp
        self.list = ownerComp.op('list')
        self.showIndex = True  # Whether to show index column

        # Drag state tracking
        self.dragRow = False
        self.dropType = None  # 'above' or 'below'
        self.endRow = None

        # Clipboard for copy/paste
        self.clipboard = None

    # -------------------------------------------------------------------------
    # Data Getters
    # -------------------------------------------------------------------------

    def getSourceNames(self):
        """Get list of source names from storage."""
        return op(self.ownerComp.par.Sourcerer).SourceNames

    def getSourceName(self, index):
        """Get name of source at given index."""
        names = self.getSourceNames()
        if 0 <= index < len(names):
            return names[index]
        return None

    def getSelectedIndex(self):
        """Get currently selected source index."""
        return op(self.ownerComp.par.Sourcerer).SelectedIndex

    def getActiveName(self):
        """Get the name of the currently active source."""
        return op(self.ownerComp.par.Sourcerer).ActiveName

    def InitData(self):
        """Initialize/rebuild the list data and refresh display.
        Call this when sources change (reorder, rename, add, delete).
        """
        self.list.par.reset.pulse()

    def Refresh(self):
        """Refresh the list display."""
        self.list.par.reset.pulse()

    # -------------------------------------------------------------------------
    # List Callbacks
    # -------------------------------------------------------------------------

    def onInitCell(self, comp, row, col, attribs):
        """Initialize cell content and appearance."""
        names = self.getSourceNames()
        if not names:
            return

        # Two column mode - index + name
        if col == 0:
            attribs.textOffsetX = 0
            attribs.textJustify = JustifyType.CENTER
            if row == 0:
                attribs.text = '#'
            else:
                attribs.text = str(row - 1)
        elif col == 1:
            attribs.textOffsetX = 6
            attribs.textJustify = JustifyType.CENTERLEFT
            if row == 0:
                attribs.text = 'Sources'
            else:
                attribs.text = names[row - 1]
                attribs.editable = 2  # Double-click to edit
                attribs.help = 'Click to select, drag to reorder, double-click to rename'

        # Cell borders
        attribs.rightBorderOutColor = self.COLORS['border_right']
        attribs.leftBorderOutColor = self.COLORS['border_left']
        return

    def onInitRow(self, comp, row, attribs):
        """Initialize row appearance based on selection/live state."""
        if row == 0:
            # Header row
            attribs.bgColor = self.COLORS['label_bg']
            attribs.textColor = self.COLORS['label_font']
            attribs.fontBold = True
            attribs.rowHeight = self.LABEL_HEIGHT
            attribs.fontSizeX = self.LABEL_FONT_SIZE
        else:
            # Data rows - set sizes then use shared reset for state-based styling
            attribs.rowHeight = self.CELL_HEIGHT
            attribs.fontSizeX = self.CELL_FONT_SIZE
            self._resetRowVisuals(comp, row)

        return

    def onInitCol(self, comp, col, attribs):
        """Initialize column widths."""
        if not self.showIndex:
            colWidth = [100]
            stretch = [1]
        else:
            colWidth = [self.CELL_HEIGHT, 100]
            stretch = [0, 1]

        attribs.colWidth = colWidth[col]
        attribs.colStretch = stretch[col]
        return

    def onInitTable(self, comp, attribs):
        """Initialize table-wide settings."""
        attribs.bottomBorderOutColor = self.COLORS['border_bottom']
        return

    def onRollover(self, comp, row, col, coords, prevRow, prevCol, prevCoords):
        """Handle mouse rollover for hover effects."""
        names = self.getSourceNames()
        if not names:
            return

        selected = self.getSelectedIndex()
        active_name = self.getActiveName()

        # Handle current row hover
        if row is not None and row > 0 and row != prevRow:
            source_index = row - 1
            is_selected = (source_index == selected)
            is_active = (source_index < len(names) and names[source_index] == active_name)

            rowAttribs = comp.rowAttribs[row]

            if is_selected:
                if is_active:
                    rowAttribs.bgColor = self.COLORS['cell_bg_live_active_hover']
                else:
                    rowAttribs.bgColor = self.COLORS['cell_bg_active_hover']
                rowAttribs.textColor = self.COLORS['cell_font_active_hover']
            else:
                if is_active:
                    rowAttribs.bgColor = self.COLORS['cell_bg_live_hover']
                else:
                    rowAttribs.bgColor = self.COLORS['cell_bg_hover']
                rowAttribs.textColor = self.COLORS['cell_font_hover']

        # Reset previous row
        if prevRow is not None and prevRow > 0 and row != prevRow:
            source_index = prevRow - 1
            is_selected = (source_index == selected)
            is_active = (source_index < len(names) and names[source_index] == active_name)

            prevRowAttribs = comp.rowAttribs[prevRow]

            if is_selected:
                if is_active:
                    prevRowAttribs.bgColor = self.COLORS['cell_bg_live_active']
                else:
                    prevRowAttribs.bgColor = self.COLORS['cell_bg_active']
                prevRowAttribs.textColor = self.COLORS['cell_font_active']
            else:
                if is_active:
                    prevRowAttribs.bgColor = self.COLORS['cell_bg_live']
                else:
                    prevRowAttribs.bgColor = self.COLORS['cell_bg']
                prevRowAttribs.textColor = self.COLORS['cell_font']

        return

    def onSelect(self, comp, startRow, startCol, startCoords, endRow, endCol, endCoords, start, end):
        """Handle selection, drag-drop reordering, and right-click menu."""
        if startRow is None or startRow <= 0:
            return

        source_index = startRow - 1

        names = self.getSourceNames()
        if not names:
            return

        # --- START: Left click to select and begin drag ---
        if start and comp.panel.lselect:
            self.dragRow = True
            self.endRow = startRow
            op(self.ownerComp.par.Sourcerer).SelectSource(source_index)

        # --- START: Right click for context menu ---
        elif start and comp.panel.rselect:
            # Select the row first
            op(self.ownerComp.par.Sourcerer).SelectSource(source_index)

            # Open context menu
            self._openContextMenu(source_index)

        # --- END: Finish drag operation ---
        elif end and self.dragRow:
            self.dragRow = False
            did_move = False

            if startRow != endRow and endRow is not None:
                from_index = startRow - 1
                num_sources = len(names)

                if endRow == 0:
                    # Dropped on header - move to position 0
                    op(self.ownerComp.par.Sourcerer).MoveSource(from_index, 0)
                    did_move = True
                elif endRow == -1:
                    # Dropped past last row - move to end
                    op(self.ownerComp.par.Sourcerer).MoveSource(from_index, num_sources)
                    did_move = True
                elif endRow > 0:
                    # Dropped on a data row
                    to_index = endRow - 1

                    if self.dropType == 'above':
                        op(self.ownerComp.par.Sourcerer).MoveSource(from_index, to_index)
                        did_move = True
                    elif self.dropType == 'below':
                        op(self.ownerComp.par.Sourcerer).MoveSource(from_index, to_index + 1)
                        did_move = True

            # Reset drop target visuals
            if self.endRow is not None:
                if self.endRow == 0:
                    comp.rowAttribs[0].bottomBorderOutColor = self.COLORS['border_bottom']
                elif self.endRow == -1:
                    # Reset last row's bottom border
                    lastRow = len(names)  # +1 for header, but names already excludes header
                    if lastRow > 0:
                        self._resetRowVisuals(comp, lastRow)
                elif self.endRow > 0:
                    self._resetRowVisuals(comp, self.endRow)

            self.dropType = None
            self.endRow = None

            # Refresh list after move
            if did_move:
                self.InitData()

        # --- DURING: Show drop indicator while dragging ---
        elif not start and not end and self.dragRow:
            if endRow is not None and startRow != endRow:
                num_sources = len(names)
                lastRow = num_sources  # Last data row number

                if endRow == 0:
                    # Header row - show bottom border (insert at position 0)
                    rowAttribs = comp.rowAttribs[endRow]
                    rowAttribs.bottomBorderOutColor = self.COLORS['drag_highlight']
                    self.dropType = 'header'
                elif endRow == -1 and lastRow > 0:
                    # Past last row - show bottom border of last row (insert at end)
                    rowAttribs = comp.rowAttribs[lastRow]
                    rowAttribs.bottomBorderOutColor = self.COLORS['drag_highlight']
                    self.dropType = 'end'
                elif endRow > 0:
                    # Data row
                    rowAttribs = comp.rowAttribs[endRow]
                    if endCoords.v > 0.5:
                        # Drop above
                        rowAttribs.topBorderOutColor = self.COLORS['drag_highlight']
                        rowAttribs.bottomBorderOutColor = self.COLORS['border_bottom']
                        self.dropType = 'above'
                    else:
                        # Drop below
                        rowAttribs.bottomBorderOutColor = self.COLORS['drag_highlight']
                        rowAttribs.topBorderOutColor = self.COLORS['border_top']
                        self.dropType = 'below'

                # Reset previous hover row
                if self.endRow != endRow and self.endRow is not None:
                    if self.endRow == 0:
                        # Reset header border
                        comp.rowAttribs[0].bottomBorderOutColor = self.COLORS['border_bottom']
                    elif self.endRow == -1 and lastRow > 0:
                        # Reset last row
                        self._resetRowVisuals(comp, lastRow)
                    elif self.endRow > 0:
                        self._resetRowVisuals(comp, self.endRow)

                self.endRow = endRow

        return

    def _resetRowVisuals(self, comp, row):
        """Reset a row's visual state to default based on selected/live state."""
        if row <= 0:
            return

        names = self.getSourceNames()
        if not names or row - 1 >= len(names):
            return

        rowAttribs = comp.rowAttribs[row]

        # Reset borders
        rowAttribs.topBorderOutColor = self.COLORS['border_top']
        rowAttribs.bottomBorderOutColor = self.COLORS['border_bottom']

        # Reset colors based on state
        source_index = row - 1
        selected = self.getSelectedIndex()
        active_name = self.getActiveName()

        is_selected = (source_index == selected)
        is_active = (names[source_index] == active_name)

        if is_selected:
            rowAttribs.fontBold = True
            rowAttribs.textColor = self.COLORS['cell_font_active']
            if is_active:
                rowAttribs.bgColor = self.COLORS['cell_bg_live_active']
            else:
                rowAttribs.bgColor = self.COLORS['cell_bg_active']
        elif is_active:
            rowAttribs.fontBold = False
            rowAttribs.textColor = self.COLORS['cell_font']
            rowAttribs.bgColor = self.COLORS['cell_bg_live']
        else:
            rowAttribs.fontBold = False
            rowAttribs.textColor = self.COLORS['cell_font']
            rowAttribs.bgColor = self.COLORS['cell_bg']

    def _openContextMenu(self, source_index):
        """Open right-click context menu."""
        items = ['Trigger', 'Copy', 'Paste', 'Delete', 'Import', 'Export Selected', 'Export All']
        disabled = []

        # Disable paste if clipboard is empty
        if self.clipboard is None:
            disabled.append('Paste')

        op.TDResources.op('popMenu').Open(
            items=items,
            callback=self._onContextMenuSelect,
            callbackDetails={'source_index': source_index},
            disabledItems=disabled,
            dividersAfterItems=['Delete'],
        )

    def _onContextMenuSelect(self, info):
        """Handle context menu selection."""
        action = info['item']
        source_index = info['details']['source_index']

        if action == 'Trigger':
            op(self.ownerComp.par.Sourcerer).SwitchToSource(source_index)
        elif action == 'Copy':
            self.clipboard = op(self.ownerComp.par.Sourcerer).CopySourceData(source_index)
        elif action == 'Paste':
            if self.clipboard is not None:
                op(self.ownerComp.par.Sourcerer).PasteSourceData(source_index, self.clipboard)
        elif action == 'Delete':
            op(self.ownerComp.par.Sourcerer).DeleteSource()
        elif action == 'Import':
            op(self.ownerComp.par.Sourcerer).Import()
        elif action == 'Export Selected':
            op(self.ownerComp.par.Sourcerer).ExportSelected()
        elif action == 'Export All':
            op(self.ownerComp.par.Sourcerer).ExportAll()

    def onRadio(self, comp, row, col, prevRow, prevCol):
        return

    def onFocus(self, comp, row, col, prevRow, prevCol):
        return

    def onEdit(self, comp, row, col, val):
        """Handle inline editing (rename)."""
        if row > 0:
            source_index = row - 1
            op(self.ownerComp.par.Sourcerer).RenameSource(source_index, val)
        return

    def onDragHover(self, comp, info):
        """Handle external drag hover - return True if we accept these items."""
        dragItems = info.get('dragItems', [])
        # Accept files and TOPs
        for item in dragItems:
            if isinstance(item, str):
                # File path
                return True
            elif hasattr(item, 'OPType'):
                # TD operator - accept TOPs
                if item.OPType == 'TOP':
                    return True
        return True  # Accept by default

    def onDrop(self, comp, info):
        """Handle external file/TOP drops."""
        dragItems = info.get('dragItems', [])
        op(self.ownerComp.par.Sourcerer).DropSource(dragItems)
        return {'droppedOn': comp}
