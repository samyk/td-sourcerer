# me - this DAT
# 
# comp - the List Component that holds this panel
# row - the row number of the cell being updated
# col - the column number of the cell being updated
#
# attribs contains the following members:
#
# text				   str            cell contents
# help                 str       	  help text
#
# textColor            r g b a        font color
# textOffsetX		   n			  horizontal text offset
# textOffsetY		   n			  vertical text offset
# textJustify		   m			  m is one of:  JustifyType.TOPLEFT, JustifyType.TOPCENTER,
#													JustifyType.TOPRIGHT, JustifyType.CENTERLEFT,
#													JustifyType.CENTER, JustifyType.CENTERRIGHT,
#													JustifyType.BOTTOMLEFT, JustifyType.BOTTOMCENTER,
#													JustifyType.BOTTOMRIGHT
#
# bgColor              r g b a        background color
#
# leftBorderInColor	   r g b a		  inside left border color
# rightBorderInColor   r g b a		  inside right border color
# topBorderInColor	   r g b a		  inside top border color
# bottomBorderInColor  r g b a		  inside bottom border color
#
# leftBorderOutColor   r g b a		  outside left border color
# rightBorderOutColor  r g b a		  outside right border color
# topBorderOutColor	   r g b a		  outside top border color
# bottomBorderOutColor r g b a		  outside bottom border color
#
# colWidth             w              sets column width
# colStetch            True/False     sets column stretchiness (width is min width)
# rowHeight            h              sets row height
#
# editable			   bool			  contents are editable
# fontBold             True/False     render font bolded
# fontItalic           True/False     render font italicized
# fontSizeX            float		  font X size in pixels
# fontSizeX            float		  font Y size in pixels, if not specified, uses X size
# fontFace             str			  font face, example 'Verdana'
# wordWrap             True/False     word wrap
#
# top                  TOP			  background TOP operator
#
# select   true when the cell/row/col is currently being selected by the mouse
# rollover true when the mouse is currently over the cell/row/col
# radio    true when the cell/row/col was last selected
# focus    true when the cell/row/col is being edited
#
# currently not implemented:
#
# type                str             cell type: 'field' or 'label'
# fieldtype           str             field type: 'float' 'string' or  'integer'
# setpos              True/False x y  set cell absolute when first argument is True
# padding             l r b t         cell padding from each edge, expressed in pixels
# margin              l r b t         cell margin from neighbouring cells, expressed in pixels
#
# fontpath            path            File location to font. Don't use with 'font'
# fontformat          str             font format: 'polygon', 'outline' or 'bitmap'
# fontantialiased     True/False      render font antialiased
# fontcharset         str             font character set
#
# textjustify         h v             left/right/center top/center/bottom
# textoffset          x y             text position offset
# comp.par.Headercolorr.tuplet

# called when Reset parameter is pulsed, or on load
def onInitCell(comp, row, col, attribs):
	# grab the cell content from the Folder DAT
	#print(dir(attribs))
	data_list = comp.par.Listobject.evalExpression()

	if comp.par.Showindex == False:
		attribs.textOffsetX = 6
		textJustify = JustifyType.CENTERLEFT
		if (col == 0):
			if (row == 0):
				cellContent = comp.par.Label
			else:
				cellContent = data_list[row-1]
	else:
		
		
		if (col == 0):
			text_offset = 0
			textJustify = JustifyType.CENTER
			if (row == 0):
				cellContent = '#'
			else:
				cellContent = row-1
		if(col == 1):
			text_offset = 6
			textJustify = JustifyType.CENTERLEFT
			if(row == 0):
				cellContent = comp.par.Label
			else:
				cellContent = data_list[row-1]

		attribs.textOffsetX = text_offset
	 
	
	attribs.rightBorderOutColor =  comp.par.Cellborderrightr.tuplet
	attribs.leftBorderOutColor =  comp.par.Cellborderleftr.tuplet
	attribs.textJustify = textJustify
	
	attribs.text = cellContent
	return
def onInitRow(comp, row, attribs):
	# if this is the first row make the background slightly red, otherwise keep it grey
	if row == 0:
		bgColor = comp.par.Labelcolorr.tuplet
		textColor = comp.par.Labelfontr.tuplet
		fontBold = comp.par.Labelfontbold.val
		rowHeight = comp.par.Labelheight.val
		fontSizeX = comp.par.Labelfontsize.val
	else:
		data_list = comp.par.Listobject.evalExpression()

		rowHeight = comp.par.Cellheight.val
		fontSizeX = comp.par.Cellfontsize.val

		if comp.par.Selected.mode == ParMode.EXPRESSION:
			selected = comp.par.Selected.evalExpression()
		else:
			selected = int(comp.par.Selected)

		#print(str(comp.par.Live), attribs.text)

		if(row-1 == selected):
			fontBold = comp.par.Cellfontactbold.val
			textColor = comp.par.Cellfontactr.tuplet
			
			if(str(comp.par.Live) == data_list[row-1]):
				bgColor = comp.par.Cellbgliveactr.tuplet
			else:
				bgColor = comp.par.Cellbgactr.tuplet
		elif(str(comp.par.Live) == data_list[row-1]):
			fontBold = comp.par.Cellfontbold.val
			bgColor = comp.par.Cellbgliver.tuplet
			textColor = comp.par.Cellfontr.tuplet
		else:
			fontBold = comp.par.Cellfontbold.val
			bgColor = comp.par.Cellbgr.tuplet
			textColor = comp.par.Cellfontr.tuplet
 
	# assign the bgColor to the rows attributes
	attribs.rowHeight = rowHeight
	attribs.fontBold = fontBold
	attribs.textColor = textColor
	attribs.bgColor = bgColor
	attribs.fontSizeX = fontSizeX
	return
	return
def onInitCol(comp, col, attribs):
	
	if comp.par.Showindex == False:
		colWidth = [100]
		stretch = [1]
	else:
		colWidth= [comp.par.Cellheight, 100]
		stretch = [0, 1]
 
	# assign the width and stretch to the column attributes
	attribs.colWidth = colWidth[col]
	attribs.colStretch = stretch[col]
	return
def onInitTable(comp, attribs):
	# set every cells justify to be center left
	
 
	# set every cells bottom border to a slight blue
	attribs.bottomBorderOutColor = comp.par.Cellborderbottomr.tuplet
	return

def onRollover(comp, row, col, coords, prevRow, prevCol, prevCoords):
	# make sure to only change the layout if row and prevRow are different
	data_list = comp.par.Listobject.evalExpression()

	if comp.par.Selected.mode == ParMode.EXPRESSION:
		selected = comp.par.Selected.evalExpression()
	else:
		selected = int(comp.par.Selected)

	if row != None:
		if row != prevRow:
			# we don't want to change the header row so test for row being larger then 0
			# this also takes care of when rolling out of the List where row would return -1
			if row > 0:
				rowAttribs = comp.rowAttribs[row]


				if(row-1 == selected):

					if(str(comp.par.Live) == data_list[row-1]):
						bgColor = comp.par.Cellbgovrliveactr.tuplet
					else:
						bgColor = comp.par.Cellbgovractr.tuplet

					textColor = comp.par.Cellfontovractr.tuplet
				else:
					if(str(comp.par.Live) == data_list[row-1]):
						bgColor = comp.par.Cellbgovrliver.tuplet
					else:
						bgColor = comp.par.Cellbgovrr.tuplet

					textColor = comp.par.Cellfontovrr.tuplet

				rowAttribs.topBorderOutColor = comp.par.Cellbordertopr.tuplet
				rowAttribs.bottomBorderOutColor = comp.par.Cellborderbottomr.tuplet
				rowAttribs.textColor = textColor
				rowAttribs.bgColor = bgColor
			# same as before, we check that prevRow is not the header row and
			# we are not entering the List from the outside
	if prevRow != None:
		if row != prevRow:
			if prevRow > 0:
				rowAttribs = comp.rowAttribs[prevRow]


				if(prevRow-1 == selected):
					if(str(comp.par.Live) == data_list[prevRow-1]):
						bgColor = comp.par.Cellbgliveactr.tuplet
					else:
						bgColor = comp.par.Cellbgactr.tuplet
					textColor = comp.par.Cellfontactr.tuplet
				else:
					if(str(comp.par.Live) == data_list[prevRow-1]):
						bgColor = comp.par.Cellbgliver.tuplet
					else:
						bgColor = comp.par.Cellbgr.tuplet
					textColor = comp.par.Cellfontr.tuplet
				
				rowAttribs.topBorderOutColor = comp.par.Cellbordertopr.tuplet
				rowAttribs.bottomBorderOutColor = comp.par.Cellborderbottomr.tuplet
				rowAttribs.textColor = textColor
				rowAttribs.bgColor = bgColor
	return

def onSelect(comp, startRow, startCol, startCoords, endRow, endCol, endCoords, start, end):
	if(start == True and startRow > 0):
		comp.mod.callbacks.onSelect(startRow-1)
		#comp.par.reset.pulse()
	return

def onRadio(comp, row, col, prevRow, prevCol):
	return

def onFocus(comp, row, col, prevRow, prevCol):
	return

def onEdit(comp, row, col, val):
	return

# return True if interested in this drop event, False otherwise
def onHover(comp, row, col, coords, prevRow, prevCol, prevCoords, dragItems):
	return True

def onDrop(comp, row, col, coords, prevRow, prevCol, prevCoords, dragItems):
	ext.SOURCERER._DropSource(dragItems)
	return True

	