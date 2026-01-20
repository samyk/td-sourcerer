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
        self.doneTimer = self.ownerComp.op('doneTimer')

        # flag to suppress callbacks during bulk parameter updates
        self._isUpdating = False

        # flag to prevent multiple done triggers during same playthrough
        self._doneTriggered = False

        # internal file state
        self._currentFrame = 0
        self._totalFrames = 0
        self._sampleRate = 30.0
        self._lastFrameState = 0  # track last_frame channel for edge detection
        self._loopCount = 0
        self._loopsRemaining = 0

        # internal timer state
        self._timerProgress = 0.0  # 0.0 to 1.0
        self._timerLengthSeconds = 0.0
        self._timerTimeRemaining = 0.0

        # public display properties with dependency tracking for UI updates
        # Note: Using strings for properties that may show "N/A"
        TDF.createProperty(self, 'Timecode', value='N/A', dependable=True, readOnly=False)
        TDF.createProperty(self, 'TimeRemaining', value='N/A', dependable=True, readOnly=False)
        TDF.createProperty(self, 'LoopCount', value='N/A', dependable=True, readOnly=False)
        TDF.createProperty(self, 'LoopsRemaining', value='N/A', dependable=True, readOnly=False)
        TDF.createProperty(self, 'Progress', value='N/A', dependable=True, readOnly=False)
        TDF.createProperty(self, 'Next', value='N/A', dependable=True, readOnly=False)

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

    def _getNextSourceDisplay(self):
        """
        Get the display string for the next source based on follow action.
        Returns 'N/A' if no next source, or 'index: name' format.
        """
        source_type = str(self.ownerComp.par.Sourcetype)

        if source_type == 'file':
            follow_action = str(self.ownerComp.par.Followactionfile)
        elif source_type == 'top':
            follow_action = str(self.ownerComp.par.Followactiontop)
        else:
            return 'N/A'

        if follow_action == 'none':
            return 'N/A'

        current_index = int(self.ownerComp.par.Index)
        target_index = None
        target_name = None

        if follow_action == 'play_next':
            next_index = current_index + 1
            if next_index < len(ext.SOURCERER.Sources):
                target_index = next_index
                target_source = ext.SOURCERER.Sources[next_index]
                target_name = target_source.get('Settings', {}).get('Name', '')

        elif follow_action == 'goto_index':
            if source_type == 'file':
                goto_index = int(self.ownerComp.par.Gotoindexfile)
            else:
                goto_index = int(self.ownerComp.par.Gotoindextop)
            if 0 <= goto_index < len(ext.SOURCERER.Sources):
                target_index = goto_index
                target_source = ext.SOURCERER.Sources[goto_index]
                target_name = target_source.get('Settings', {}).get('Name', '')

        elif follow_action == 'goto_name':
            if source_type == 'file':
                goto_name = str(self.ownerComp.par.Gotonamefile)
            else:
                goto_name = str(self.ownerComp.par.Gotonametop)
            source_data, idx, name = ext.SOURCERER._getSource(goto_name)
            if source_data is not None:
                target_index = idx
                target_name = name

        if target_index is None:
            return 'N/A'

        return f'{target_name}'

    def _formatSeconds(self, seconds):
        """Format seconds as timecode string HH:MM:SS:FF (assuming 30fps for frame display)."""
        if seconds <= 0:
            return '00:00:00:00'
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        # Use fractional seconds for frame portion (display at 30fps equivalent)
        frame = int((seconds % 1) * 30)
        return f'{hours:02d}:{minutes:02d}:{secs:02d}:{frame:02d}'

    def _updateDisplayState(self):
        """Update public display attributes based on source type and state.

        Display logic:
        - TOP sources: LoopCount, LoopsRemaining → "N/A"
        - File sources with play_n_times: show file-based progress and time remaining
        - File sources with timer: show timer-based progress and time remaining
        - TOP sources with timer: show timer-based progress and time remaining
        - Next: shows index and name of next source based on follow action

        Note: _currentFrame is a 0-based index, so frame 0 is the first frame
        and frame (totalFrames-1) is the last frame.
        """
        # Check if display updates are enabled on SOURCERER
        if not parent.SOURCERER.par.Updatedisplay:
            return

        source_type = str(self.ownerComp.par.Sourcetype)

        if source_type == 'file':
            done_on = str(self.ownerComp.par.Doneonfile)
            self._updateFileDisplay(done_on)
        elif source_type == 'top':
            done_on = str(self.ownerComp.par.Doneontop)
            self._updateTopDisplay(done_on)
        else:
            # No source type - show N/A for everything
            self._setAllDisplayNA()

    def _updateFileDisplay(self, done_on):
        """Update display properties for file source type."""
        # Timecode is always file-based for file sources
        self.Timecode = self._formatTimecode(self._currentFrame, self._sampleRate)

        # Loop count is always relevant for file sources
        self.LoopCount = self._loopCount

        # Next source based on follow action
        self.Next = self._getNextSourceDisplay()

        if done_on == 'play_n_times':
            # Calculate total progress across all loops
            play_n_times = int(self.ownerComp.par.Playntimes)
            total_frames_all_loops = self._totalFrames * play_n_times

            # Frames completed so far: full loops + current position
            # _loopCount is completed loops, _currentFrame is 0-indexed position in current loop
            frames_completed = (self._loopCount * self._totalFrames) + self._currentFrame

            # Progress across all loops
            if total_frames_all_loops > 1:
                progress_pct = (frames_completed / (total_frames_all_loops - 1)) * 100
            else:
                progress_pct = 100.0 if total_frames_all_loops == 1 else 0.0
            self.Progress = round(progress_pct, 2)

            # Time remaining: frames left in current loop + frames in remaining loops
            frames_remaining_current = max(0, self._totalFrames - 1 - self._currentFrame)
            frames_remaining_future = self._loopsRemaining * self._totalFrames
            total_frames_remaining = frames_remaining_current + frames_remaining_future
            self.TimeRemaining = self._formatTimecode(total_frames_remaining, self._sampleRate)

            # Loops remaining only relevant for play_n_times mode
            self.LoopsRemaining = self._loopsRemaining

        elif done_on == 'timer':
            # Timer-based progress and time remaining
            self.Progress = round(self._timerProgress * 100, 2)
            self.TimeRemaining = self._formatSeconds(self._timerTimeRemaining)

            # Loops remaining not relevant for timer mode
            self.LoopsRemaining = 'N/A'

        else:  # 'none' or manual
            # No automatic end - show single-loop file progress and time remaining
            if self._totalFrames > 1:
                progress_pct = (self._currentFrame / (self._totalFrames - 1)) * 100
            else:
                progress_pct = 100.0 if self._totalFrames == 1 else 0.0
            self.Progress = round(progress_pct, 2)

            # Show time remaining in current loop so user knows when file ends
            frames_remaining = max(0, self._totalFrames - 1 - self._currentFrame)
            self.TimeRemaining = self._formatTimecode(frames_remaining, self._sampleRate)
            self.LoopsRemaining = 'N/A'

    def _updateTopDisplay(self, done_on):
        """Update display properties for TOP source type."""
        # File-specific info is not relevant for TOP sources
        self.LoopCount = 'N/A'
        self.LoopsRemaining = 'N/A'

        # Next source based on follow action
        self.Next = self._getNextSourceDisplay()

        if done_on == 'timer':
            # Timer-based progress and time remaining
            self.Progress = round(self._timerProgress * 100, 2)
            self.TimeRemaining = self._formatSeconds(self._timerTimeRemaining)
            self.Timecode = self._formatSeconds(self._timerLengthSeconds * self._timerProgress)

        else:  # 'none' or manual
            # No automatic timing - show N/A
            self.Progress = 'N/A'
            self.TimeRemaining = 'N/A'
            self.Timecode = 'N/A'

    def _setAllDisplayNA(self):
        """Set all display properties to N/A."""
        self.Timecode = 'N/A'
        self.TimeRemaining = 'N/A'
        self.Progress = 'N/A'
        self.LoopCount = 'N/A'
        self.LoopsRemaining = 'N/A'
        self.Next = 'N/A'

    def whileDoneTimerActive(self, fraction):
        """Callback for when doneTimer is running.

        Args:
            fraction: Timer progress from 0.0 to 1.0
        """
        self._timerProgress = float(fraction)
        self._timerTimeRemaining = self._timerLengthSeconds * (1.0 - self._timerProgress)

        # Update display
        self._updateDisplayState()

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

        # Update file info after parameters are set (delay 1 frame to let file load)
        run('args[0].UpdateFileInfo()', self, delayFrames=1)

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

    def UpdateFileInfo(self):
        """Update file length and rate from the movieFileIn operator."""
        source_type = str(self.ownerComp.par.Sourcetype)
        if source_type != 'file':
            return

        # Check if file is ready (numImages > 0 indicates file is loaded)
        num_frames = int(self.movieFileIn.numImages)
        if num_frames > 0:
            # Update length
            self.ownerComp.par.Filelengthframes = num_frames
            self._totalFrames = num_frames
            # Update sample rate
            sample_rate = float(self.movieFileIn.rate) if self.movieFileIn.rate > 0 else 30.0
            self.ownerComp.par.Filesamplerate = sample_rate
            self._sampleRate = sample_rate

    def Start(self):
        # reset playback state
        self._doneTriggered = False
        self._lastFrameState = 0
        self._currentFrame = 0
        self._timerProgress = 0.0
        self._timerTimeRemaining = self._timerLengthSeconds

        # Reset loop tracking (will show as N/A for non-play_n_times modes)
        # _loopCount: number of completed loops (starts at 0)
        # _loopsRemaining: loops left after current one (play_n_times=1 means 0 remaining)
        self._loopCount = 0
        self._loopsRemaining = max(0, int(self.ownerComp.par.Playntimes) - 1)

        # Update display will set appropriate values based on source type
        self._updateDisplayState()

        source_type = str(self.ownerComp.par.Sourcetype)
        if source_type == 'file':
            self.movieFileIn.par.reload.pulse()
            done_on = self.ownerComp.par.Doneonfile.eval()
            if done_on == 'timer' and self.doneTimer is not None:
                self._timerLengthSeconds = float(self.ownerComp.par.Timertimefile)
                self._timerTimeRemaining = self._timerLengthSeconds
                self.doneTimer.par.initialize.pulse()
                run(self.doneTimer.par.start.pulse, delayFrames=1)
        elif source_type == 'top':
            done_on = self.ownerComp.par.Doneontop.eval()
            if done_on == 'timer' and self.doneTimer is not None:
                self._timerLengthSeconds = float(self.ownerComp.par.Timertimetop)
                self._timerTimeRemaining = self._timerLengthSeconds
                self.doneTimer.par.initialize.pulse()
                run(self.doneTimer.par.start.pulse, delayFrames=1)

            cue_vid = self.ownerComp.par.Enablecuetop.eval()
            if cue_vid:
                vid = self.ownerComp.par.Cuetop.eval()
                op(vid).par.cuepulse.pulse()
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

        # If file path changed, update file info after 1 frame to let file load
        if par.name == 'File' and par.val != prev:
            run('args[0].UpdateFileInfo()', self, delayFrames=1)

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
            open - 1.0 when file is open and ready
            preloading - 1.0 when file is preloading
        """
        chan_name = channel.name

        # File info updates - always process (for any source, active or not)
        if chan_name in ('open', 'preloading'):
            if val == 1.0:
                # File is ready - read info directly from movieFileIn
                num_frames = int(self.movieFileIn.numImages)
                self.ownerComp.par.Filelengthframes = num_frames
                self._totalFrames = num_frames
                # Update sample rate
                sample_rate = float(self.movieFileIn.rate) if self.movieFileIn.rate > 0 else 30.0
                self.ownerComp.par.Filesamplerate = sample_rate
                self._sampleRate = sample_rate
            return

        # Playback state updates - only for active source
        is_active_playback = (
            self.ownerComp.par.Active and
            self.ownerComp.name in ['source0', 'source1'] and
            self.ownerComp.digits == ext.SOURCERER.State
        )
        if not is_active_playback:
            return

        if chan_name == 'index':
            self._currentFrame = int(val)
        elif chan_name == 'length':
            self._totalFrames = int(val)
        elif chan_name == 'sample_rate':
            self._sampleRate = float(val) if val > 0 else 30.0
        elif chan_name == 'last_frame':
            # detect rising edge of last_frame for loop counting
            if val == 1.0 and self._lastFrameState == 0:
                done_on = str(self.ownerComp.par.Doneonfile)
                play_n_times = int(self.ownerComp.par.Playntimes)

                # Increment loop count first (we've completed a loop)
                self._loopCount += 1
                # loopsRemaining decrements: starts at play_n_times-1, goes to 0
                self._loopsRemaining = max(0, play_n_times - self._loopCount)

                # Check done condition AFTER incrementing loop count
                # _loopCount now represents completed loops
                # Trigger done when we've completed play_n_times loops
                if done_on == 'play_n_times' and not self._doneTriggered:
                    if self._loopCount >= play_n_times:
                        self._doneTriggered = True
                        self._handleFollowAction()

            self._lastFrameState = val

        # update display state
        self._updateDisplayState()

        # Early trigger for transitions: only check on index changes
        # (not on last_frame, which is handled above)
        if chan_name != 'index':
            return

        # Early trigger for transitions: check if we're close enough to the end
        # to start the transition early (only for play_n_times mode)
        done_on = str(self.ownerComp.par.Doneonfile)
        if done_on != 'play_n_times':
            return

        if self._doneTriggered:
            return

        play_n_times = int(self.ownerComp.par.Playntimes)
        transition_time = self._getTransitionTimeForFollowAction()

        # Only do early trigger if there's a transition time
        if transition_time <= 0:
            return

        # convert transition time (seconds) to file frames
        transition_frames = transition_time * self._sampleRate

        # frames remaining in current loop (0-based index: last frame = totalFrames-1)
        frames_remaining = max(0, self._totalFrames - 1 - self._currentFrame)

        # We're on the final loop when loopCount (completed loops) equals play_n_times - 1
        # (meaning we're currently playing the last loop)
        is_final_loop = (self._loopCount >= play_n_times - 1)

        # Early trigger: frames_remaining must be > 0 (not at the last frame)
        # and <= transition_frames. The last frame itself is handled by the
        # last_frame channel logic, not the early trigger.
        if is_final_loop and frames_remaining > 0 and frames_remaining <= transition_frames:
            # trigger done early to allow transition to complete
            self._doneTriggered = True
            self._handleFollowAction()
    
    def onDoneTimerDone(self):
        """Callback for when the doneTimer completes (used for both file and TOP sources)."""
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
