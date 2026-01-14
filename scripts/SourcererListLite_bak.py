# SourcererListLite - List component for Sourcerer Lite
# Features: double-click rename, drag-drop reorder, right-click context menu


class SourcererListLite:
    """List UI for displaying and managing sources."""

    def __init__(self, ownerComp):
        self.ownerComp = ownerComp
        self.list = ownerComp.op('list')

        # Drag state tracking
        self.dragRow = False
        self.dropType = None  # 'above' or 'below'
        self.endRow = None

        # Clipboard for copy/paste
        self.clipboard = None

    def Refresh(self):
        """Refresh the list display."""
        self.list.par.reset.pulse()

    # -------------------------------------------------------------------------
    # List Callbacks
    # -------------------------------------------------------------------------

    def onInitCell(self, comp, row, col, attribs):
        """Initialize cell content and appearance."""
        data_list = comp.par.Listobject.evalExpression()
        if data_list is None:
            return

        if comp.par.Showindex == False:
            # Single column mode - just names
            attribs.textOffsetX = 6
            attribs.textJustify = JustifyType.CENTERLEFT
            if row == 0:
                attribs.text = comp.par.Label
            else:
                attribs.text = data_list[row - 1]
                attribs.editable = 2  # Double-click to edit
                attribs.help = 'Click to select, drag to reorder, double-click to rename'
        else:
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
                    attribs.text = comp.par.Label
                else:
                    attribs.text = data_list[row - 1]
                    print(data_list[row - 1])
                    attribs.editable = 2  # Double-click to edit
                    attribs.help = 'Click to select, drag to reorder, double-click to rename'

        # Cell borders
        attribs.rightBorderOutColor = comp.par.Cellborderrightr.tuplet
        attribs.leftBorderOutColor = comp.par.Cellborderleftr.tuplet
        return

    def onInitRow(self, comp, row, attribs):
        """Initialize row appearance based on selection/live state."""
        if row == 0:
            # Header row
            attribs.bgColor = comp.par.Labelcolorr.tuplet
            attribs.textColor = comp.par.Labelfontr.tuplet
            attribs.fontBold = comp.par.Labelfontbold.val
            attribs.rowHeight = comp.par.Labelheight.val
            attribs.fontSizeX = comp.par.Labelfontsize.val
        else:
            # Data rows
            data_list = comp.par.Listobject.evalExpression()
            if data_list is None:
                return

            attribs.rowHeight = comp.par.Cellheight.val
            attribs.fontSizeX = comp.par.Cellfontsize.val

            # Get selected index
            if comp.par.Selected.mode == ParMode.EXPRESSION:
                selected = comp.par.Selected.evalExpression()
            else:
                selected = int(comp.par.Selected)

            source_index = row - 1
            is_selected = (source_index == selected)
            is_live = (str(comp.par.Live) == data_list[source_index])

            # Set colors based on state
            if is_selected:
                attribs.fontBold = comp.par.Cellfontactbold.val
                attribs.textColor = comp.par.Cellfontactr.tuplet
                if is_live:
                    attribs.bgColor = comp.par.Cellbgliveactr.tuplet
                else:
                    attribs.bgColor = comp.par.Cellbgactr.tuplet
            elif is_live:
                attribs.fontBold = comp.par.Cellfontbold.val
                attribs.bgColor = comp.par.Cellbgliver.tuplet
                attribs.textColor = comp.par.Cellfontr.tuplet
            else:
                attribs.fontBold = comp.par.Cellfontbold.val
                attribs.bgColor = comp.par.Cellbgr.tuplet
                attribs.textColor = comp.par.Cellfontr.tuplet

        return

    def onInitCol(self, comp, col, attribs):
        """Initialize column widths."""
        if comp.par.Showindex == False:
            colWidth = [100]
            stretch = [1]
        else:
            colWidth = [comp.par.Cellheight, 100]
            stretch = [0, 1]

        attribs.colWidth = colWidth[col]
        attribs.colStretch = stretch[col]
        return

    def onInitTable(self, comp, attribs):
        """Initialize table-wide settings."""
        attribs.bottomBorderOutColor = comp.par.Cellborderbottomr.tuplet
        return

    def onRollover(self, comp, row, col, coords, prevRow, prevCol, prevCoords):
        """Handle mouse rollover for hover effects."""
        data_list = comp.par.Listobject.evalExpression()
        if data_list is None:
            return

        # Get selected index
        if comp.par.Selected.mode == ParMode.EXPRESSION:
            selected = comp.par.Selected.evalExpression()
        else:
            selected = int(comp.par.Selected)

        # Handle current row hover
        if row is not None and row > 0 and row != prevRow:
            source_index = row - 1
            is_selected = (source_index == selected)
            is_live = (str(comp.par.Live) == data_list[source_index])

            rowAttribs = comp.rowAttribs[row]

            if is_selected:
                if is_live:
                    rowAttribs.bgColor = comp.par.Cellbgovrliveactr.tuplet
                else:
                    rowAttribs.bgColor = comp.par.Cellbgovractr.tuplet
                rowAttribs.textColor = comp.par.Cellfontovractr.tuplet
            else:
                if is_live:
                    rowAttribs.bgColor = comp.par.Cellbgovrliver.tuplet
                else:
                    rowAttribs.bgColor = comp.par.Cellbgovrr.tuplet
                rowAttribs.textColor = comp.par.Cellfontovrr.tuplet

        # Reset previous row
        if prevRow is not None and prevRow > 0 and row != prevRow:
            source_index = prevRow - 1
            is_selected = (source_index == selected)
            is_live = (str(comp.par.Live) == data_list[source_index])

            prevRowAttribs = comp.rowAttribs[prevRow]

            if is_selected:
                if is_live:
                    prevRowAttribs.bgColor = comp.par.Cellbgliveactr.tuplet
                else:
                    prevRowAttribs.bgColor = comp.par.Cellbgactr.tuplet
                prevRowAttribs.textColor = comp.par.Cellfontactr.tuplet
            else:
                if is_live:
                    prevRowAttribs.bgColor = comp.par.Cellbgliver.tuplet
                else:
                    prevRowAttribs.bgColor = comp.par.Cellbgr.tuplet
                prevRowAttribs.textColor = comp.par.Cellfontr.tuplet

        return

    def onSelect(self, comp, startRow, startCol, startCoords, endRow, endCol, endCoords, start, end):
        """Handle selection, drag-drop reordering, and right-click menu."""
        if startRow is None or startRow <= 0:
            return

        source_index = startRow - 1

        # Default colors for reset
        data_list = comp.par.Listobject.evalExpression()
        if data_list is None:
            return

        # --- LEFT CLICK: Select or start drag ---
        if comp.panel.lselect:
            if start:
                # Start selection/drag
                self.dragRow = True
                self.endRow = startRow

                # Select this source
                comp.par.Selected = source_index
                ext.SOURCERER.SelectSource(source_index)

            elif end and self.dragRow:
                # End drag
                self.dragRow = False

                if startRow != endRow and endRow is not None and endRow > 0:
                    # Perform move
                    from_index = startRow - 1
                    to_index = endRow - 1

                    if self.dropType == 'above':
                        ext.SOURCERER.MoveSource(from_index, to_index)
                    elif self.dropType == 'below':
                        ext.SOURCERER.MoveSource(from_index, to_index + 1)

                # Reset drop target visuals
                if self.endRow is not None and self.endRow > 0:
                    self._resetRowVisuals(comp, self.endRow)

                self.dropType = None
                self.endRow = None

            elif not start and not end and self.dragRow:
                # During drag - show drop indicator
                if endRow is not None and endRow > 0 and startRow != endRow:
                    rowAttribs = comp.rowAttribs[endRow]
                    highlightColor = (0.2, 0.5, 0.8, 1)

                    if endCoords.v > 0.5:
                        # Drop above
                        rowAttribs.topBorderOutColor = highlightColor
                        rowAttribs.bottomBorderOutColor = comp.par.Cellborderbottomr.tuplet
                        self.dropType = 'above'
                    else:
                        # Drop below
                        rowAttribs.bottomBorderOutColor = highlightColor
                        rowAttribs.topBorderOutColor = comp.par.Cellbordertopr.tuplet
                        self.dropType = 'below'

                    # Reset previous hover row
                    if self.endRow != endRow and self.endRow is not None and self.endRow > 0:
                        self._resetRowVisuals(comp, self.endRow)

                    self.endRow = endRow

        # --- RIGHT CLICK: Context menu ---
        elif comp.panel.rselect and start:
            # Select the row first
            comp.par.Selected = source_index
            ext.SOURCERER.SelectSource(source_index)

            # Open context menu
            self._openContextMenu(source_index)

        return

    def _resetRowVisuals(self, comp, row):
        """Reset a row's visual state to default."""
        if row <= 0:
            return

        data_list = comp.par.Listobject.evalExpression()
        if data_list is None or row - 1 >= len(data_list):
            return

        rowAttribs = comp.rowAttribs[row]
        rowAttribs.topBorderOutColor = comp.par.Cellbordertopr.tuplet
        rowAttribs.bottomBorderOutColor = comp.par.Cellborderbottomr.tuplet

        # Reset background based on state
        source_index = row - 1
        if comp.par.Selected.mode == ParMode.EXPRESSION:
            selected = comp.par.Selected.evalExpression()
        else:
            selected = int(comp.par.Selected)

        is_selected = (source_index == selected)
        is_live = (str(comp.par.Live) == data_list[source_index])

        if is_selected:
            if is_live:
                rowAttribs.bgColor = comp.par.Cellbgliveactr.tuplet
            else:
                rowAttribs.bgColor = comp.par.Cellbgactr.tuplet
        elif is_live:
            rowAttribs.bgColor = comp.par.Cellbgliver.tuplet
        else:
            rowAttribs.bgColor = comp.par.Cellbgr.tuplet

    def _openContextMenu(self, source_index):
        """Open right-click context menu."""
        items = ['Trigger', 'Copy', 'Paste', 'Delete']
        disabled = []

        # Disable paste if clipboard is empty
        if self.clipboard is None:
            disabled.append('Paste')

        op.TDResources.op('popMenu').Open(
            items=items,
            callback=self._onContextMenuSelect,
            callbackDetails={'source_index': source_index},
            disabledItems=disabled,
        )

    def _onContextMenuSelect(self, info):
        """Handle context menu selection."""
        action = info['item']
        source_index = info['details']['source_index']

        if action == 'Trigger':
            ext.SOURCERER.SwitchToSource(source_index)
        elif action == 'Copy':
            self.clipboard = ext.SOURCERER.CopySourceData(source_index)
        elif action == 'Paste':
            if self.clipboard is not None:
                ext.SOURCERER.PasteSourceData(source_index, self.clipboard)
        elif action == 'Delete':
            ext.SOURCERER.DeleteSource()

    def onRadio(self, comp, row, col, prevRow, prevCol):
        return

    def onFocus(self, comp, row, col, prevRow, prevCol):
        return

    def onEdit(self, comp, row, col, val):
        """Handle inline editing (rename)."""
        if row > 0:
            source_index = row - 1
            ext.SOURCERER.RenameSource(source_index, val)
        return

    def onHover(self, comp, row, col, coords, prevRow, prevCol, prevCoords, dragItems):
        """Handle external drag hover."""
        return True

    def onDrop(self, comp, row, col, coords, prevRow, prevCol, prevCoords, dragItems):
        """Handle external file/TOP drops."""
        ext.SOURCERER._DropSource(dragItems)
        return True
