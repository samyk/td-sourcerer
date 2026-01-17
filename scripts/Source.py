from json import loads, dumps
import traceback

from CallbacksExt import CallbacksExt
from TDStoreTools import StorageManager
TDF = op.TDModules.mod.TDFunctions

class Source(CallbacksExt):
    """ A source playback component """

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

        self.movieFileIn = self.ownerComp.op('moviefilein')
        self.loops = 0  # track loops for file source

        self.timerFile = self.ownerComp.op('timerFile')
        self.timerTOP = self.ownerComp.op('timerTOP')

    def Start(self):
        self.loops = 0
        source_type = str(self.ownerComp.par.Sourcetype)
        if source_type == 'file':
            self.movieFileIn.par.reload.pulse()
            done_on = self.ownerComp.par.Doneonfile.eval()
            if done_on == 'timer':
                self.timerFile.par.initialize.pulse()
                run(self.timerFile.par.start.pulse, delayFrames=1)
            pass
        elif source_type == 'top':
            done_on = self.ownerComp.par.Doneontop.eval()
            if done_on == 'timer':
                self.timerTOP.par.initialize.pulse()
                run(self.timerTOP.par.start.pulse, delayFrames=1)

            cue_vid = self.ownerComp.par.Enablecuetop.eval()
            if cue_vid:
                vid = self.ownerComp.par.Cuetop.eval()
                op(vid).par.cuepulse.pulse()
        else:
            pass
        return

    def _handleFollowAction(self):
        """Handle follow action when source is done playing."""
        source_type = str(self.ownerComp.par.Sourcetype)
        if source_type == 'file':
            follow_action = self.ownerComp.par.Followactionfile
        elif source_type == 'top':
            follow_action = self.ownerComp.par.Followactiontop
        else:
            return

        if self.ownerComp.par.Active:
            if self.ownerComp.name in ['source0', 'source1']:
                if self.ownerComp.digits == ext.SOURCERER.State:
                    # Fire the onSourceDone callback
                    ext.SOURCERER.OnSourceDone()

                    # play next
                    if follow_action == 'play_next':
                        ext.SOURCERER.SwitchToSource(ext.SOURCERER.activeIndex + 1)

                    # go to index
                    elif follow_action == 'goto_index':
                        if source_type == 'file':
                            goto_index = self.ownerComp.par.Gotoindexfile
                        else:
                            goto_index = self.ownerComp.par.Gotoindextop
                        ext.SOURCERER.SwitchToSource(int(goto_index))

                    # go to name
                    elif follow_action == 'goto_name':
                        if source_type == 'file':
                            goto_name = self.ownerComp.par.Gotonamefile
                        else:
                            goto_name = self.ownerComp.par.Gotonametop
                        ext.SOURCERER.SwitchToSource(str(goto_name))
    
    # called whenever a parameter value is changed
    def onValueChange(self, par, prev):
        # we should evaluate whether or not to store the source data here
        # if we are updating the source data (e.g. loading a source) we should not pass up any changes
        ext.SOURCERER.StoreSourceToSelected(self.ownerComp)
    
    def onTimerFileDone(self):
        """Callback for when file source is done playing."""
        self._handleFollowAction()
        return

    def onTimerTOPDone(self):
        """Callback for when TOP source is done playing."""
        self._handleFollowAction()
        return

    def onFileLastFrame(self):
        """Callback for when file source reaches last frame."""
        # self._handleFollowAction()
        # need to consider play n times

        return

    ### Pulse methods ###

    # pulse parameter to cue the movie file in
    def pulse_Cuepulse(self):
        """Pulse the cue on the movie file in."""
        self.ownerComp.op('moviefilein').par.cuepulse.pulse()

    # pulse parameter to execute command script
    def pulse_Commandpulse(self):
        """Execute the command script."""
        parent.SOURCERER.op('commandScript').text = parent().par.Command
        parent.SOURCERER.op('commandScript').run()

    def pulse_Donepulsefile(self):
        """Pulse the done pulse for file source."""
        self._handleFollowAction()

    def pulse_Commandpulsetop(self):
        """Pulse the done pulse for TOP source."""
        self._handleFollowAction()

    # pulse parameter to open extension
    def pulse_Editextension(self):
        self.ownerComp.op('Source').par.edit.pulse()
