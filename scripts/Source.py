from json import loads, dumps
import traceback

from CallbacksExt import CallbacksExt
from TDStoreTools import StorageManager
import TDFunctions as TDF

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
        self.timerFile = self.ownerComp.op('timerFile')
        self.timerTOP = self.ownerComp.op('timerTOP')

        # flag to suppress callbacks during bulk parameter updates
        self._isUpdating = False

        # flag to prevent multiple done triggers during same playthrough
        self._doneTriggered = False

        # internal file state
        self._currentFrame = 0
        self._totalFrames = 0
        self._sampleRate = 30.0
        self._lastFrameState = 0  # track last_frame channel for edge detection

        # public display properties with dependency tracking for UI updates
        TDF.createProperty(self, 'Timecode', value='00:00:00:00', dependable=True, readOnly=False)
        TDF.createProperty(self, 'TimeRemaining', value='00:00:00:00', dependable=True, readOnly=False)
        TDF.createProperty(self, 'LoopCount', value=0, dependable=True, readOnly=False)
        TDF.createProperty(self, 'LoopsRemaining', value=0, dependable=True, readOnly=False)
        TDF.createProperty(self, 'Progress', value=0.0, dependable=True, readOnly=False)

    # Suffix patterns for multi-value parameters that don't have a base accessor
    PAR_SUFFIXES = {
        'r': ['r', 'g', 'b'],      # Color parameters
        'x': ['x', 'y'],           # Translate, Scale, etc.
    }

    def _setParVal(self, par_name, value):
        """Set a parameter value on this component."""
        if hasattr(self.ownerComp.par, par_name):
            par = getattr(self.ownerComp.par, par_name)
            if isinstance(value, (list, tuple)):
                # Multi-value parameter
                for i, p in enumerate(par.tuplet):
                    if i < len(value):
                        p.val = value[i]
            else:
                par.val = value
        else:
            # Check for suffix-based parameters (color, xy, etc.)
            for first_suffix, suffixes in self.PAR_SUFFIXES.items():
                if hasattr(self.ownerComp.par, par_name + first_suffix):
                    for i, suffix in enumerate(suffixes):
                        if i < len(value):
                            getattr(self.ownerComp.par, par_name + suffix).val = value[i]
                    break

    def _formatTimecode(self, frames, fps):
        """Format frame count as timecode string HH:MM:SS:FF"""
        if fps <= 0:
            return '00:00:00:00'
        total_seconds = frames / fps
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = int(total_seconds % 60)
        frame = int(frames % fps)
        return f'{hours:02d}:{minutes:02d}:{seconds:02d}:{frame:02d}'

    def _getTransitionTimeForFollowAction(self):
        """
        Get the transition time (in seconds) for the target of the current follow action.
        Returns 0.0 if no transition is needed or target is invalid.
        """
        follow_action = str(self.ownerComp.par.Followactionfile)

        if follow_action == 'none':
            return 0.0

        target_source = None
        current_index = int(self.ownerComp.par.Index)

        if follow_action == 'play_next':
            next_index = current_index + 1
            if next_index < len(ext.SOURCERER.Sources):
                target_source = ext.SOURCERER.Sources[next_index]

        elif follow_action == 'goto_index':
            goto_index = int(self.ownerComp.par.Gotoindexfile)
            if 0 <= goto_index < len(ext.SOURCERER.Sources):
                target_source = ext.SOURCERER.Sources[goto_index]

        elif follow_action == 'goto_name':
            goto_name = str(self.ownerComp.par.Gotonamefile)
            source_data, idx, name = ext.SOURCERER._getSource(goto_name)
            target_source = source_data

        if target_source is None:
            return 0.0

        # check if target uses global transition time
        settings = target_source.get('Settings', {})
        if settings.get('Useglobaltransitiontime', False):
            return float(parent.SOURCERER.par.Globaltransitiontime)
        else:
            return float(settings.get('Transitiontime', 0.0))

    def _updateDisplayState(self):
        """Update public display attributes from internal state."""
        self.Timecode = self._formatTimecode(self._currentFrame, self._sampleRate)

        frames_remaining = max(0, self._totalFrames - self._currentFrame)
        self.TimeRemaining = self._formatTimecode(frames_remaining, self._sampleRate)

        self.Progress = self._currentFrame / self._totalFrames if self._totalFrames > 0 else 0.0

    def UpdateFromData(self, source_data, active=False, store_changes=False, index=None):
        """
        Update this source component from a source data dictionary.

        Args:
            source_data: Dictionary of {page_name: {par_name: value}}
            active: Whether this source is actively playing
            store_changes: Whether parameter changes should be stored back to Sourcerer
            index: The source index this component represents
        """
        self._isUpdating = True

        # set all parameters from source_data
        for page_name, page_data in source_data.items():
            for par_name, value in page_data.items():
                self._setParVal(par_name, value)

        # set control parameters
        self.ownerComp.par.Storechanges = store_changes
        self.ownerComp.par.Active = active
        if index is not None:
            self.ownerComp.par.Index = index

        self._isUpdating = False

        # handle activation actions (command script, cue TOP)
        if active:
            if self.ownerComp.par.Enablecommand:
                try:
                    run(str(self.ownerComp.par.Command))
                except:
                    pass

            if self.ownerComp.par.Enablecuetop:
                try:
                    op(self.ownerComp.par.Cuetop).par.cue.pulse()
                except:
                    pass

    def Start(self):
        # reset playback state
        self.LoopCount = 0
        self._doneTriggered = False
        self._lastFrameState = 0
        self._currentFrame = 0
        self._totalFrames = 0
        self.Progress = 0.0
        self.Timecode = '00:00:00:00'
        self.TimeRemaining = '00:00:00:00'
        self.LoopsRemaining = int(self.ownerComp.par.Playntimes)

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
        # don't propagate changes while we're bulk updating from data
        if self._isUpdating:
            return
        # only store if this comp is meant to store changes (e.g. selectedSource)
        if not self.ownerComp.par.Storechanges:
            return
        ext.SOURCERER.StoreSourceToSelected(self.ownerComp)

    def onFileValueChange(self, channel, val):
        """Callback for when file info chop channels change.

        Channels:
            true_length - file length in frames
            length - file length in frames adjusted for in/out crop
            last_frame - 1.0 when last frame is reached
            index - current frame index
            sample_rate - sample rate of video file (e.g. 30 or 60)
        """
        print('onFileValueChange', channel.name, val)
        # only process if this is an active playback source
        if not self.ownerComp.par.Active:
            return

        # only process for source0/source1 that match current state
        if self.ownerComp.name not in ['source0', 'source1']:
            return
        if self.ownerComp.digits != ext.SOURCERER.State:
            return

        # update internal state based on channel
        chan_name = channel.name
        if chan_name == 'index':
            self._currentFrame = int(val)
        elif chan_name == 'length':
            self._totalFrames = int(val)
        elif chan_name == 'sample_rate':
            self._sampleRate = float(val) if val > 0 else 30.0
        elif chan_name == 'last_frame':
            # detect rising edge of last_frame for loop counting
            if val == 1.0 and self._lastFrameState == 0:
                self.LoopCount += 1
                play_n_times = int(self.ownerComp.par.Playntimes)
                self.LoopsRemaining = max(0, play_n_times - self.LoopCount)
            self._lastFrameState = val

        # update display state
        self._updateDisplayState()

        # check for done condition (only for play_n_times mode)
        done_on = str(self.ownerComp.par.Doneonfile)
        if done_on != 'play_n_times':
            return

        if self._doneTriggered:
            return

        # calculate if we should trigger done
        play_n_times = int(self.ownerComp.par.Playntimes)
        transition_time = self._getTransitionTimeForFollowAction()

        # convert transition time (seconds) to file frames
        transition_frames = transition_time * self._sampleRate

        # frames remaining in current loop
        frames_remaining = self._totalFrames - self._currentFrame

        # check if this is the final loop
        is_final_loop = (self.LoopCount >= play_n_times - 1)

        if is_final_loop and frames_remaining <= transition_frames:
            # trigger done early to allow transition to complete
            self._doneTriggered = True
            self._handleFollowAction()
    
    def onTimerFileDone(self):
        """Callback for when file source is done playing."""
        self._handleFollowAction()
        return

    def onTimerTOPDone(self):
        """Callback for when TOP source is done playing."""
        self._handleFollowAction()
        return

    ### Pulse methods ###

    # pulse parameter to cue the movie file in
    def pulse_Cuepulse(self):
        """Pulse the cue on the movie file in."""
        self.ownerComp.op('moviefilein').par.cuepulse.pulse()

    # pulse parameter to execute command script
    def pulse_Commandpulse(self):
        """Execute the command script."""
        run(str(self.ownerComp.par.Command))

    def pulse_Donepulsefile(self):
        """Pulse the done pulse for file source."""
        self._handleFollowAction()

    def pulse_Commandpulsetop(self):
        """Pulse the done pulse for TOP source."""
        self._handleFollowAction()

    # pulse parameter to open extension
    def pulse_Editextension(self):
        self.ownerComp.op('Source').par.edit.pulse()
