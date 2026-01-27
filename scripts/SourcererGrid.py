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



        # the component to which data is stored
        self.dataComp = ownerComp.op('data')


        # stored items (persistent across saves and re-initialization):
        storedItems = [
            # Only 'name' is required...
            {'name': 'Data', 'default': None, 'readOnly': False,
                                     'property': True, 'dependable': True},
        ]
        self.stored = StorageManager(self, self.dataComp, storedItems)

        self.buttonGrid = self.ownerComp.op('buttonGrid')
        TDF.createProperty(self, 'ButtonSize', value=self._calcButtonSize(), readOnly=True, dependable=True)
        TDF.createProperty(self, 'MaxRows', value=self._calcMaxRows(), readOnly=True, dependable=True)

    def _calcButtonSize(self):
        bg = self.buttonGrid
        bg_width = bg.width
        bg_margins = bg.par.marginl.eval() + bg.par.marginr.eval()
        bg_spacing = bg.par.spacing.eval()
        bg_max_per_row = bg.par.alignmax.eval()
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
        button_size = self.ButtonSize
        max_rows = int((bg_height - bg_margins + bg_spacing) / (button_size + bg_spacing))
        return max_rows
    
    def updateButtonSize(self):
        self.ButtonSize = self._calcButtonSize()
        self.MaxRows = self._calcMaxRows()




    def onSelectSource(self, index):
        sourcerer = self.ownerComp.par.Sourcerer.eval()
        if sourcerer is None:
            return
        
        sourcerer.Take(index)


    # pulse parameter to open extension
    def pulse_Editextension(self):
        self.ownerComp.op('SourcererGrid').par.edit.pulse()
