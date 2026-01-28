from json import loads, dumps
import traceback

from CallbacksExt import CallbacksExt
from TDStoreTools import StorageManager
import TDFunctions as TDF
from math import floor

class SourcererGrid(CallbacksExt):
    """ Grid view for sourcerer sources """

    def __init__(self, ownerComp):
        # the component to which this extension is attached
        self.ownerComp = ownerComp

        # init callbacks
        self.callbackDat = self.ownerComp.par.Callbackdat.eval()
        try:
            CallbacksExt.__init__(self, ownerComp)
        except:
            self.ownerComp.addScriptError(traceback.format_exc() + \
                    "Error in CallbacksExt __init__. See textport.")
            print()
            print("Error initializing callbacks - " + self.ownerComp.path)
            print(traceback.format_exc())
        # run onInit callback
        try:
            self.DoCallback('onInit', {'ownerComp':self.ownerComp})
        except:
            self.ownerComp.addScriptError(traceback.format_exc() + \
                    "Error in custom onInit callback. See textport.")
            print(traceback.format_exc())


        self.buttonGrid = self.ownerComp.op('buttonGrid')

        # the component to which data is stored
        self.dataComp = ownerComp.op('data')

        # stored items (persistent across saves and re-initialization):
        storedItems = [
            # Only 'name' is required...
            {'name': 'Data', 'default': None, 'readOnly': False,
                                     'property': True, 'dependable': True},
            {'name': 'ButtonSize', 'default': 1, 'readOnly': False,
                                     'property': True, 'dependable': True},
            {'name': 'MaxRows', 'default': 0, 'readOnly': False,
                                     'property': True, 'dependable': True},
            {'name': 'MaxButtons', 'default': 0, 'readOnly': False,
                                     'property': True, 'dependable': True},
            {'name': 'CurPage', 'default': 1, 'readOnly': False,
                                     'property': True, 'dependable': True},
            {'name': 'NumPages', 'default': 1, 'readOnly': False,
                                     'property': True, 'dependable': True},
        ]
        self.stored = StorageManager(self, self.dataComp, storedItems)

        self.updateButtonSize()
        self.updatePages()

    def _calcButtonSize(self):
        bg = self.buttonGrid
        bg_width = bg.width
        bg_margins = bg.par.marginl.eval() + bg.par.marginr.eval()
        bg_spacing = bg.par.spacing.eval()
        bg_max_per_row = self.ownerComp.par.Maxperrow.eval()
        bg_scrollbar_width = 0
        if bg.par.pvscrollbar.eval() == 'on':
            bg_scrollbar_width = bg.par.scrollbarthickness.eval()

        button_size = (bg_width - bg_margins - bg_scrollbar_width - \
                       (bg_spacing * (bg_max_per_row - 1))) / bg_max_per_row
        button_size = floor(button_size)
        return button_size
    
    def _calcMaxRows(self):
        bg = self.buttonGrid
        bg_height = bg.height
        bg_margins = bg.par.margint.eval() + bg.par.marginb.eval()
        bg_spacing = bg.par.spacing.eval()
        button_size = self.stored['ButtonSize']
        max_rows = int((bg_height - bg_margins + bg_spacing) / (button_size + bg_spacing))
        return max_rows

    def _calcMaxButtons(self):
        return self.ownerComp.par.Maxperrow.eval() * self.stored['MaxRows']

    def _calcPages(self):
        sourcerer = self.ownerComp.par.Sourcerer.eval()
        if sourcerer is None:
            self.NumPages = 1
            return

        total_sources = len(sourcerer.Sources)
        buttons_per_page = self.buttonGrid.par.alignmax.eval() * self.MaxRows
        num_pages = (total_sources + buttons_per_page - 1) // buttons_per_page
        if num_pages < 1:
            num_pages = 1
        self.NumPages = num_pages
    
    def updateButtonSize(self):
        self.stored['ButtonSize'] = self._calcButtonSize()
        self.stored['MaxRows'] = self._calcMaxRows()
        self.stored['MaxButtons'] = self._calcMaxButtons()

    def updatePages(self):
        self._calcPages()
        if self.stored['CurPage'] > self.stored['NumPages']:
            self.stored['CurPage'] = self.stored['NumPages']

    def onSelectSource(self, index):
        sourcerer = self.ownerComp.par.Sourcerer.eval()
        if sourcerer is None:
            return
        
        sourcerer.Take(index)

    def onPanelSizeChange(self):
        self.updateButtonSize()
        self.updatePages()

    def onSourcesChange(self):
        self.updateButtonSize()
        self.updatePages()
        print('onSourcesChange called')

    def NextPage(self):
        if self.stored['CurPage'] < self.stored['NumPages']:
            self.stored['CurPage'] += 1

    def PrevPage(self):
        if self.stored['CurPage'] > 1:
            self.stored['CurPage'] -= 1



    # pulse parameter to open extension
    def pulse_Editextension(self):
        self.ownerComp.op('SourcererGrid').par.edit.pulse()
