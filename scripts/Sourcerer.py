"""
Sourcerer Lite - Media source management for TouchDesigner.

A streamlined component for managing, switching, and transitioning between
file-based media and TOP-based generative content.

Author: Matthew Wachter
License: MIT
"""

import copy
import json
import os
from TDStoreTools import StorageManager, DependList
import TDFunctions as TDF
from CallbacksExt import CallbacksExt


class TransitionState:
    """State machine states for source transitions."""
    IDLE = 'idle'
    TRANSITIONING = 'transitioning'


class Sourcerer(CallbacksExt):
    """
    Main Sourcerer extension for managing media sources and transitions.

    Provides centralized source management with a list-based interface,
    built-in transitions, follow actions, and real-time display properties.
    """

    def __init__(self, ownerComp):
        self.ownerComp = ownerComp
        
        self.callbackDat = self.ownerComp.par.Callbackdat.eval()

        try:
            super().__init__(ownerComp)
        except Exception:
            error_msg = traceback.format_exc()
            self.ownerComp.addScriptError(
                f"{error_msg} Error in CallbacksExt __init__. See textport."
            )
            print(f"Error initializing callbacks - {self.ownerComp.path}")
            print(error_msg)

        try:
            self.DoCallback('onInit', {'ownerComp': self.ownerComp})
        except Exception:
            error_msg = traceback.format_exc()
            self.ownerComp.addScriptError(
                f"{error_msg} Error in custom onInit callback. See textport."
            )
            print(error_msg)
        
        self.DataComp = ownerComp.op('data')
        self.transitionComp = ownerComp.op('transitions')
        self.switcherState = ownerComp.op('state')
        self.selectedSourceComp = ownerComp.op('selectedSource')

        storedItems = [
            {'name': 'Sources', 'default': [], 'dependable': False},
            {
                'name': 'SelectedSource',
                'default': {'index': 0, 'name': ''},
                'dependable': True
            },
            {
                'name': 'ActiveSource',
                'default': {'index': -1, 'name': ''},
                'dependable': True
            },
            {'name': 'State', 'default': 0, 'dependable': True},
            {'name': 'Safety', 'default': False, 'dependable': True},
            {'name': 'Log', 'default': [], 'dependable': True},
            {'name': 'LogFormatted', 'default': [], 'dependable': True}
        ]

        self.stored = StorageManager(self, self.DataComp, storedItems)

        # State machine for transitions
        self.transitionState = TransitionState.IDLE

        # Dependable properties for UI binding
        TDF.createProperty(self, 'PendingQueue', value=[], dependable=True, readOnly=False)
        source_names = [str(s['Settings']['Name']) for s in self.stored['Sources']]
        TDF.createProperty(self, 'SourceNames', value=source_names, dependable=True, readOnly=False)
        TDF.createProperty(self, 'SelectedIndex', value=self.stored['SelectedSource']['index'], dependable=True, readOnly=False)
        TDF.createProperty(self, 'ActiveName', value=self.stored['ActiveSource']['name'], dependable=True, readOnly=False)

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    @property
    def SelectedName(self):
        """Currently selected source name."""
        return self.stored['SelectedSource']['name']

    @property
    def ActiveIndex(self):
        """Index of the currently active source."""
        return self.stored['ActiveSource']['index']

    @property
    def ActiveSourceComp(self):
        """The currently active source component (source0 or source1)."""
        return self.ownerComp.op('source' + str(self.stored['State']))

    @property
    def isTransitioning(self):
        """Whether a transition is currently in progress."""
        return self.transitionState == TransitionState.TRANSITIONING

    @property
    def isQueueEnabled(self):
        """Whether the pending queue is enabled."""
        return self.ownerComp.par.Enablependingqueue.eval()

    @property
    def isEditingActive(self):
        """Whether the selected source is the active source (for UI warnings)."""
        return self.stored['SelectedSource']['index'] == self.stored['ActiveSource']['index']

    @property
    def Safety(self):
        """Get safety state."""
        return self.stored['Safety']

    def ToggleSafety(self):
        """Toggle safety mode on or off."""
        self.stored['Safety'] = not self.stored['Safety']

    def _confirmSafetyAction(self, action_name, force=False):
        """
        Prompt user to confirm a destructive action.

        Args:
            action_name: Name of the action for the dialog
            force: If True, always prompt regardless of safety mode

        Returns True if action should proceed, False if cancelled.
        """
        if not force and not self.stored['Safety']:
            return True
        result = ui.messageBox(f'Confirm {action_name}',
                               f'Are you sure you want to {action_name.lower()}?',
                               buttons=['OK', 'Cancel'])
        return result == 0  # 0 = OK, 1 = Cancel

    # -------------------------------------------------------------------------
    # Logging
    # -------------------------------------------------------------------------

    # Log colors (RGB 0-255) based on list color palette
    LOG_COLORS = {
        'time': (178, 178, 178),        # label_font gray
        'SwitchToSource': (51, 127, 204),       # blue
        'TransitionComplete': (140, 220, 180),  # green
        'SourceDone': (255, 200, 50),           # yellow
        'StoreDefault': (200, 150, 255),        # purple
        'AddSource': (100, 200, 100),           # green
        'DeleteSource': (255, 100, 100),        # red
        'RenameSource': (100, 200, 200),        # cyan
        'MoveSource': (100, 150, 255),          # light blue
        'Init': (200, 200, 200),                # gray
        'FileOpenFailed': (255, 80, 80),        # bright red for errors
        'data': (255, 255, 255),                # white
    }

    def _log(self, event, data, level='INFO'):
        """Add an entry to the log with timestamp. Newest first, max 10 entries.

        Args:
            event: Event name (e.g., 'SwitchToSource', 'AddSource')
            data: Dict of event data
            level: Log level for external logger ('INFO', 'WARNING', 'ERROR')
        """
        import datetime

        # Format time with 2 decimal places on seconds
        now = datetime.datetime.now()
        time_str = now.strftime('%Y-%m-%d %H:%M:%S') + f'.{now.microsecond // 10000:02d}'

        entry = {
            'time': time_str,
            'event': event,
            'data': data
        }
        self.stored['Log'].insert(0, entry)

        # Build formatted string with colors
        tc = self.LOG_COLORS['time']
        ec = self.LOG_COLORS.get(event, (255, 255, 255))
        dc = self.LOG_COLORS['data']

        # Format data as "key: value" pairs
        data_str = ', '.join(f'{k}: {v}' for k, v in data.items())

        # Pad event name to 18 chars (length of "TransitionComplete")
        event_padded = f"{event:<18}"

        formatted = (
            f"{{#color({tc[0]}, {tc[1]}, {tc[2]});}}{time_str}  "
            f"{{#color({ec[0]}, {ec[1]}, {ec[2]});}}{event_padded}  "
            f"{{#color({dc[0]}, {dc[1]}, {dc[2]});}}{data_str}"
        )
        self.stored['LogFormatted'].insert(0, formatted)

        # Keep only the first 10 entries (newest)
        if len(self.stored['Log']) > 10:
            self.stored['Log'] = self.stored['Log'][:10]
        if len(self.stored['LogFormatted']) > 10:
            self.stored['LogFormatted'] = self.stored['LogFormatted'][:10]

        # Write to external Logger if enabled
        if self.ownerComp.par.Enablelogging.eval():
            logger = self.ownerComp.par.Logger.eval()
            if logger is not None:
                log_msg = f"{time_str} | {event} | {data_str}"
                match level:
                    case 'INFO':
                        logger.Info(log_msg)
                    case 'WARNING':
                        logger.Warning(log_msg)
                    case 'ERROR':
                        logger.Error(log_msg)
                    case _:
                        logger.Info(log_msg)

        # Fire onLog callback
        self.DoCallback('onLog', {
            'time': time_str,
            'event': event,
            'data': data,
            'level': level
        })

    def ClearLog(self):
        """Clear all log entries."""
        self.stored['Log'].clear()
        self.stored['LogFormatted'].clear()

    def InitData(self):
        """Reset to clean state - delete all sources and create one new default source."""
        # Clear all sources
        self.stored['Sources'] = []

        # Clear pending queue and reset transition state
        self.PendingQueue.clear()
        self.transitionState = TransitionState.IDLE

        # Create one default source
        source = self._getSourceTemplate('defaultSource')
        source['Settings']['Name'] = 'Source 0'
        self.stored['Sources'].append(source)

        # Reset selection and active source
        self.stored['SelectedSource']['index'] = 0
        self.stored['SelectedSource']['name'] = 'Source 0'
        self.stored['ActiveSource']['index'] = 0
        self.stored['ActiveSource']['name'] = 'Source 0'
        self.stored['State'] = 0

        # Update dependable properties
        self.SelectedIndex = 0
        self.ActiveName = 'Source 0'

        # Update the source list and UI
        self._updateSourceList()
        self.UpdateSelectedSourceComp()

        self._log('Init', {'method': 'InitData'})

    def _updateSourceList(self):
        """Update the SourceNames dependable property from stored Sources."""
        self.SourceNames = [str(s['Settings']['Name']) for s in self.stored['Sources']]

    def _getSource(self, source):
        """
        Look up a source by index or name.

        Args:
            source: Source index (int) or name (str).

        Returns:
            Tuple of (source_data, index, name) or (None, None, None) if not found.
        """
        source_json = None
        name = None
        index = None

        if isinstance(source, str):
            sources = self.stored['Sources']
            source_names = [s['Settings']['Name'] for s in sources]
            if source in source_names:
                s = source_names.index(source)
                source_json = self.stored['Sources'][s]
                name = source
                index = s
            else:
                debug('no source', source, 'in', source_names)

        elif isinstance(source, int):
            s = source
            index = source
            if source <= len(self.stored['Sources']) - 1:
                source_json = self.stored['Sources'][s]
                name = source_json['Settings']['Name']
            else:
                debug('source index', s, 'is out of range')

        else:
            debug('wrong source type', source)

        return source_json, index, name

    def SwitchToSource(self, source, force=False):
        """Switch to a source.

        Args:
            source: Source index or name to switch to
            force: If True, clears pending queue and switches immediately,
                   ignoring Enablependingqueue setting
        """
        # Force mode: clear queue and switch right away
        if force:
            self.PendingQueue.clear()
            self._beginTransition(source)
            return

        # Check if pending queue is enabled
        queue_enabled = self.ownerComp.par.Enablependingqueue.eval()

        # If already transitioning, decide whether to queue or switch immediately
        if self.transitionState == TransitionState.TRANSITIONING:
            if queue_enabled:
                # Avoid duplicate consecutive entries
                if not self.PendingQueue or self.PendingQueue[-1] != source:
                    self.PendingQueue.append(source)
            else:
                # Queue disabled - begin transition immediately (will interrupt current)
                self._beginTransition(source)
            return

        self._beginTransition(source)

    def SwitchToSourceData(self, source_data):
        """Switch to a temporary source from a source data dictionary.

        The source is not added to the source list. ActiveIndex will be -1.
        Temp sources always switch immediately (not queued) and do not support
        follow actions since they have no index in the source list.

        Use GetDefaultSource() or CopySourceData() to get a template, modify it,
        then pass it here.

        Args:
            source_data: Complete source dict (from GetDefaultSource() or CopySourceData())

        Example:
            source = op('Sourcerer').GetDefaultSource()
            source['Settings']['Name'] = 'Emergency Override'
            source['Settings']['Transitiontype'] = 'dissolve'
            source['Settings']['Transitiontime'] = 0.5
            source['File']['File'] = '/path/to/emergency.mp4'
            op('Sourcerer').SwitchToSourceData(source)
        """
        # Temp sources always switch immediately - clear any pending queue
        self.PendingQueue.clear()
        self._beginTransition(None, source_data=source_data)

    def _beginTransition(self, source, source_data=None):
        """Start the actual transition to a source.

        Args:
            source: Source index or name (ignored if source_data provided)
            source_data: Optional complete source dict for temp sources
        """
        self.transitionState = TransitionState.TRANSITIONING

        state = self.stored['State']
        next_state = 1 - state
        source_comp = self.ownerComp.op('source' + str(next_state))

        # Temp source: use provided data directly
        if source_data is not None:
            name = source_data.get('Settings', {}).get('Name', 'Temp')
            index = -1
            source_comp.UpdateFromData(source_data, active=True, store_changes=False, index=-1)
        # Normal source: look up from storage
        else:
            source_data, index, name = self._getSource(source)
            if source_data is None:
                self.transitionState = TransitionState.IDLE
                return
            self.UpdateSourceCompQuick(source_comp, index)

        source_comp.Start()

        # Configure transition parameters
        settings = source_data['Settings']
        tcomp_par = self.transitionComp.par
        trans_type = settings['Transitiontype']
        tcomp_par.Transitiontype = trans_type

        if trans_type == 'dip':
            self._setParVal('Dipcolor', settings['Dipcolor'], self.transitionComp)
        elif trans_type in ('slide', 'wipe'):
            tcomp_par.Transitiondirection = settings['Transitiondirection']
        elif trans_type == 'file':
            tcomp_par.Transitionfile = settings['Transitionfile']
        elif trans_type == 'top':
            tcomp_par.Transitiontop = settings['Transitiontop']
        elif trans_type == 'blur':
            tcomp_par.Bluramount = settings.get('Bluramount', 8.0)

        if settings['Useglobaltransitiontime']:
            trans_time = self.ownerComp.par.Globaltransitiontime.eval()
        else:
            trans_time = settings['Transitiontime']
        tcomp_par.Transitiontime = trans_time

        trans_shape = settings['Transitionshape']
        tcomp_par.Transitionshape = trans_shape
        if trans_shape == 'custom':
            tcomp_par.Customtransitionshape = settings['Customtransitionshape']

        # Update state
        self.stored['State'] = next_state
        self.stored['ActiveSource']['index'] = index
        self.stored['ActiveSource']['name'] = name
        self.ActiveName = name

        self.DoCallback('onSwitchToSource', {
            'index': index,
            'name': name,
            'source_data': source_data
        })
        self._log('SwitchToSource', {'index': index, 'name': name})

    def OnTransitionComplete(self):
        """Called when the transition animation finishes.
        Hook this up to be called when the transition timer/animation ends."""
        self.transitionState = TransitionState.IDLE

        self.DoCallback('onTransitionComplete', {
            'index': self.ActiveIndex,
            'name': self.ActiveName
        })

        self._log('TransitionComplete', {'index': self.ActiveIndex, 'name': self.ActiveName})

        # Process next item in queue if any
        if self.PendingQueue:
            next_source = self.PendingQueue.pop(0)
            self.SwitchToSource(next_source)

    def OnSourceDone(self):
        """Called when the current source finishes (timer ends, video ends, etc.).
        Hook this up to source timer/video completion events."""
        self.DoCallback('onSourceDone', {
            'index': self.ActiveIndex,
            'name': self.ActiveName
        })

        self._log('SourceDone', {'index': self.ActiveIndex, 'name': self.ActiveName})

    def ClearPendingQueue(self):
        """Clear all pending source switches."""
        self.PendingQueue.clear()

    def SkipToLastPending(self):
        """Clear queue but keep last item - jump to final destination."""
        if len(self.PendingQueue) > 1:
            last = self.PendingQueue[-1]
            self.PendingQueue.clear()
            self.PendingQueue.append(last)

    def SwitchToSelectedSource(self):
        """Switch to the currently selected source."""
        self.SwitchToSource(self.stored['SelectedSource']['index'])

    def DelaySwitchToSource(self, source, delay=0):
        """Switch to a source after a delay in frames."""
        run(self.SwitchToSource, source, delayFrames=delay)

    def RunCommand(self, command):
        """Execute a Python command string."""
        run(command)

    # -------------------------------------------------------------------------
    # Import/Export
    # -------------------------------------------------------------------------

    def Import(self):
        """Import sources from a JSON file with location selection dialog."""
        f = ui.chooseFile(load=True, fileTypes=['json'], title='Import Sources')
        if f is None:
            return

        with open(f, 'r') as json_file:
            imported_sources = json.load(json_file)

        if not imported_sources:
            return

        location = ui.messageBox(
            'Sourcerer Import Location',
            'Select a location:',
            buttons=['Prepend', 'Insert (above selected)', 'Append']
        )
        sources = list(self.stored['Sources'])

        if location == 0:  # Prepend
            new_sources = imported_sources.copy()
            new_sources.extend(sources)
            self.stored['Sources'] = new_sources
            for i in range(len(imported_sources)):
                self._checkUniqueName(self.stored['Sources'][i], exclude_index=i)

        elif location == 1:  # Insert
            s = self.stored['SelectedSource']['index']
            new_sources = sources[:s] + imported_sources + sources[s:]
            self.stored['Sources'] = new_sources
            for i in range(s, s + len(imported_sources)):
                self._checkUniqueName(self.stored['Sources'][i], exclude_index=i)

        elif location == 2:  # Append
            new_sources = sources + imported_sources
            self.stored['Sources'] = new_sources
            for i in range(len(sources), len(new_sources)):
                self._checkUniqueName(self.stored['Sources'][i], exclude_index=i)

        self._updateSourceList()

    def ExportAll(self):
        """Export all sources to a JSON file."""
        f = ui.chooseFile(load=False, fileTypes=['json'], title='Export Sources')
        if f is None:
            return

        with open(f, 'w') as json_file:
            json.dump(self.stored['Sources'], json_file)

    def ExportSelected(self):
        """Export the selected source to a JSON file."""
        f = ui.chooseFile(load=False, fileTypes=['json'], title='Export Sources')
        if f is None:
            return

        selected = self.stored['SelectedSource']['index']
        with open(f, 'w') as json_file:
            json.dump([self.stored['Sources'][selected]], json_file)

    def ExportRange(self, range_start=None, range_end=None):
        """Export a range of sources to a JSON file."""
        f = ui.chooseFile(load=False, fileTypes=['json'], title='Export Sources')
        if f is None:
            return

        if range_start is None:
            range_start = self.ownerComp.par.Exportrangeval1
        if range_end is None:
            range_end = self.ownerComp.par.Exportrangeval2

        sources = self.stored['Sources'].getRaw()[range_start:range_end + 1]
        with open(f, 'w') as json_file:
            json.dump(sources, json_file)

    def InitSources(self, force_confirm=False):
        """Reset all sources to initial state with one default source."""
        if not self._confirmSafetyAction(
            'Initialize Sources (this will clear all sources)',
            force=force_confirm
        ):
            return

        self.stored['Sources'] = []
        self.stored['SelectedSource']['index'] = 0
        self.stored['SelectedSource']['name'] = ''
        self.SelectedIndex = 0

        self._addSource()
        self._updateSourceList()
        self._log('Init', {'method': 'InitSources'})

    def _getSourceTemplate(self, template):
        """Get a source template as a simple value dictionary from a template component."""
        template_op = self.ownerComp.op(template)
        return self._extractValues(template_op)

    def StoreDefaultFromSelected(self):
        """Store the selected source's settings as the default template."""
        # Get the selected source data
        idx = self.stored['SelectedSource']['index']
        name = self.stored['SelectedSource']['name']
        source_data = self.stored['Sources'][idx]

        # Get the default template component
        default_comp = self.ownerComp.op('defaultSource')

        # Write all parameter values to the default template
        for page_name, page_data in source_data.items():
            for par_name, value in page_data.items():
                self._setParVal(par_name, value, default_comp)

        self._log('StoreDefault', {'index': idx, 'name': name})

    # Suffix patterns for multi-value parameters that don't have a base accessor
    PAR_SUFFIXES = {
        'r': ['r', 'g', 'b'],      # Color parameters
        'x': ['x', 'y'],           # Translate, Scale, etc.
    }

    def _setParVal(self, par_name, value, target_comp):
        """Set a parameter value on a component, handling multi-value parameters."""
        if hasattr(target_comp.par, par_name):
            par = getattr(target_comp.par, par_name)
            if isinstance(value, (list, tuple)):
                for i, p in enumerate(par.tuplet):
                    if i < len(value):
                        p.val = value[i]
            else:
                par.val = value
        else:
            # Handle suffix-based parameters (color, xy, etc.)
            for first_suffix, suffixes in self.PAR_SUFFIXES.items():
                if hasattr(target_comp.par, par_name + first_suffix):
                    for i, suffix in enumerate(suffixes):
                        if i < len(value):
                            getattr(target_comp.par, par_name + suffix).val = value[i]
                    break

    # Parameters that are derived/read-only and should not be stored
    EXCLUDE_FROM_STORAGE = {'Filelengthframes', 'Filesamplerate'}

    def _extractValues(self, comp):
        """Extract parameter values from a component as a nested dictionary."""
        source_dict = {}
        for page in comp.customPages:
            page_dict = {}
            for par in page.pars:
                if par.name in self.EXCLUDE_FROM_STORAGE:
                    continue
                if len(par.tuplet) > 1 and par == par.tuplet[0]:
                    if par.tupletName in self.EXCLUDE_FROM_STORAGE:
                        continue
                    page_dict[par.tupletName] = [p.val for p in par.tuplet]
                elif len(par.tuplet) == 1:
                    page_dict[par.name] = par.val
            source_dict[page.name] = page_dict
        return source_dict

    def UpdateSelectedSourceComp(self):
        """Update the selected source component from storage."""
        s = self.stored['SelectedSource']['index']
        self.UpdateSourceCompQuick(self.selectedSourceComp, s, active=False, store_changes=True)

    def UpdateSourceCompQuick(self, source_comp, source_index, active=True, store_changes=False):
        """Update a source component with data from storage."""
        source_data = self.stored['Sources'][source_index]
        source_comp.UpdateFromData(source_data, active=active, store_changes=store_changes, index=source_index)

    def UpdateSourceComp(self, source_comp, source_index, active=True, store_changes=False):
        """Full source update - same as quick in lite version."""
        self.UpdateSourceCompQuick(source_comp, source_index, active, store_changes)

    def StoreSourceToSelected(self, source_comp, update_selected_comp=False):
        """Store source component parameters to the selected source in storage."""
        source = self.stored['SelectedSource']['index']
        self.StoreSource(source_comp, source)

        if update_selected_comp:
            self.UpdateSelectedSourceComp()

        # Update active source in real-time if editing it
        if source == self.ActiveIndex:
            active_comp = self.ownerComp.op('source' + str(self.stored['State']))
            self.UpdateSourceCompQuick(active_comp, source, active=True, store_changes=False)

        self._updateSourceList()

    def StoreSource(self, source_comp, source):
        """Store source component parameters to storage at given index."""
        self.stored['Sources'][source] = self._extractValues(source_comp)
        self._updateSourceList()

    def InitSource(self):
        """Reset the selected source to default template values."""
        source_dict = self._getSourceTemplate('defaultSource')
        s = self.stored['SelectedSource']['index']
        self.stored['Sources'][s] = source_dict
        self._updateSourceList()

    def _getUniqueName(self, name, exclude_index=None):
        """Get a unique name, optionally excluding an index (for renames)."""
        names = [s['Settings']['Name'] for i, s in enumerate(self.stored['Sources'])
                 if i != exclude_index]

        if name not in names:
            return name

        # Find next available number suffix
        base = name.rstrip('0123456789 ')
        i = 1
        while f"{base} {i}" in names:
            i += 1
        return f"{base} {i}"

    def _checkUniqueName(self, source, exclude_index=None):
        """Ensure source has a unique name. Returns the modified source."""
        name = str(source['Settings']['Name'])
        source['Settings']['Name'] = self._getUniqueName(name, exclude_index)
        self._updateSourceList()
        return source

    def GetDefaultSource(self):
        """Get a source template for customization.

        Returns a new dict that can be modified and passed to AddSource().

        Example:
            source = op('Sourcerer').GetDefaultSource()
            source['Settings']['Name'] = 'My Source'
            source['Settings']['Transitiontype'] = 'blur'
            source['File']['File'] = '/path/to/video.mp4'
            op('Sourcerer').AddSource(source_data=source)
        """
        return self._getSourceTemplate('defaultSource')

    def _addSource(self, source_data=None, source_type=None, source_path=None, source_name=None):
        """Internal add source without safety check. Used by InitSources."""
        # get the selected source index
        s = self.stored['SelectedSource']['index']

        # use provided source or default template
        if source_data is None:
            source_data = self._getSourceTemplate('defaultSource')

            # set the source type and path if provided
            if source_type == 'file':
                source_data['Settings']['Sourcetype'] = 'file'
                if source_path is not None:
                    source_data['File']['File'] = source_path

            elif source_type == 'top':
                source_data['Settings']['Sourcetype'] = 'top'
                if source_path is not None:
                    source_data['TOP']['Top'] = source_path

            # source_type=None leaves Sourcetype at its default value (likely 'none')

            # set the name - use provided name or default to "Source"
            source_data['Settings']['Name'] = source_name if source_name is not None else 'new_source'

        source_data = self._checkUniqueName(source_data)

        # insert the template into the sources list
        # handle empty list case - insert at 0 instead of s+1
        insert_index = s + 1 if self.stored['Sources'] else 0
        self.stored['Sources'].insert(insert_index, source_data)

        self.SelectSource(insert_index)

        # update the source comp parameters
        self.UpdateSourceCompQuick(self.selectedSourceComp, insert_index, store_changes=True)
        self._updateSourceList()

        self._log('AddSource', {'index': insert_index, 'name': source_data['Settings']['Name']})

    def AddSource(self, source_data=None, source_type=None, source_path=None, source_name=None):
        """Add a new source.

        Args:
            source_data: Optional complete source dict (from GetDefaultSource()).
                         When provided, other arguments are ignored.
            source_type: 'file' or 'top' (ignored if source_data is provided)
            source_path: Path to file or TOP (ignored if source_data is provided)
            source_name: Display name (ignored if source_data is provided)
        """
        # Confirm if safety is on
        if not self._confirmSafetyAction('Add Source'):
            return
        self._addSource(source_data, source_type, source_path, source_name)
        return

    def DropSource(self, args):
        """Handle dropped files or TOPs, creating sources for valid items."""
        for dropped in args:
            if isinstance(dropped, str):
                if os.path.isfile(dropped):
                    base = os.path.basename(dropped)
                    source_name = os.path.splitext(base)[0]
                    file_ext = os.path.splitext(base)[1][1:]

                    if file_ext in tdu.fileTypes['movie'] or file_ext in tdu.fileTypes['image']:
                        self.AddSource(source_type='file', source_path=dropped, source_name=source_name)

            elif hasattr(dropped, 'family') and dropped.family == 'TOP':
                self.AddSource(source_type='top', source_path=dropped.path, source_name=dropped.name)

    def CopySource(self):
        """Duplicate the selected source."""
        s = self.stored['SelectedSource']['index']
        source = copy.deepcopy(self.stored['Sources'][s])
        source = self._checkUniqueName(source)
        self.stored['Sources'].insert(s, source)
        self.SelectSource(s)
        self._updateSourceList()

    def DeleteSource(self):
        """Delete the selected source."""
        if not self._confirmSafetyAction('Delete Source'):
            return

        s = self.stored['SelectedSource']['index']
        sources = self.stored['Sources']

        if len(sources) <= 1:
            self._updateSourceList()
            return

        deleted_name = sources[s]['Settings']['Name']
        is_active = (self.stored['ActiveSource']['index'] == s)

        sources.pop(s)

        if is_active:
            self.stored['ActiveSource']['index'] = -1
            self.stored['ActiveSource']['name'] = ''
            self.ActiveName = ''
        elif self.stored['ActiveSource']['index'] > s:
            self.stored['ActiveSource']['index'] -= 1

        if s >= len(sources):
            self.SelectSource(len(sources) - 1)
        else:
            self.SelectSource(s)

        self._log('DeleteSource', {'index': s, 'name': deleted_name})
        self._updateSourceList()

    def RenameSource(self, index, new_name):
        """Rename a source at the given index."""
        if not self._confirmSafetyAction('Rename Source'):
            return

        if not (0 <= index < len(self.stored['Sources'])):
            return

        old_name = self.stored['Sources'][index]['Settings']['Name']
        name = self._getUniqueName(str(new_name), exclude_index=index)
        self.stored['Sources'][index]['Settings']['Name'] = name

        if self.stored['SelectedSource']['index'] == index:
            self.stored['SelectedSource']['name'] = name

        if self.stored['ActiveSource']['index'] == index:
            self.stored['ActiveSource']['name'] = name
            self.ActiveName = name

        self._updateSourceList()
        self.UpdateSelectedSourceComp()
        self._log('RenameSource', {'index': index, 'from': old_name, 'to': name})

    def MoveSource(self, from_index, to_index):
        """Move a source from one position to another."""
        if not self._confirmSafetyAction('Move Source'):
            return

        sources = self.stored['Sources']
        if from_index < 0 or from_index >= len(sources):
            return

        to_index = max(0, min(to_index, len(sources)))

        active_index = self.stored['ActiveSource']['index']
        moving_active = (from_index == active_index)

        source = sources.pop(from_index)
        moved_name = source['Settings']['Name']

        if from_index < to_index:
            to_index -= 1

        sources.insert(to_index, source)

        # Update ActiveSource index based on the move
        if moving_active:
            self.stored['ActiveSource']['index'] = to_index
        elif active_index >= 0:
            if from_index < active_index <= to_index:
                self.stored['ActiveSource']['index'] -= 1
            elif to_index <= active_index < from_index:
                self.stored['ActiveSource']['index'] += 1

        self.stored['SelectedSource']['index'] = to_index
        self.stored['SelectedSource']['name'] = moved_name
        self.SelectedIndex = to_index
        self._updateSourceList()
        self.UpdateSelectedSourceComp()
        self._log('MoveSource', {'name': moved_name, 'from': from_index, 'to': to_index})

    def CopySourceData(self, source):
        """Copy source data by index or name.

        Args:
            source: Source index (int) or name (str).

        Returns:
            Deep copy of the source data dict, or None if not found.
        """
        source_data, _, _ = self._getSource(source)
        if source_data is not None:
            return copy.deepcopy(source_data)
        return None

    def PasteSourceData(self, index, data):
        """Paste source data after the given index."""
        if not self._confirmSafetyAction('Paste Source'):
            return

        if data is None:
            return

        new_source = copy.deepcopy(data)
        new_source = self._checkUniqueName(new_source)
        self.stored['Sources'].insert(index + 1, new_source)
        self.SelectSource(index + 1)
        self._updateSourceList()

    def SelectSource(self, index):
        """Select a source by index for editing."""
        if index > len(self.stored['Sources']) - 1:
            index = index - 1

        self.stored['SelectedSource']['index'] = index
        self.SelectedIndex = index
        if 0 <= index < len(self.stored['Sources']):
            self.stored['SelectedSource']['name'] = self.stored['Sources'][index]['Settings']['Name']
        else:
            self.stored['SelectedSource']['name'] = ''

        self.UpdateSelectedSourceComp()

    def SelectSourceUp(self):
        """Select the previous source in the list."""
        s = self.stored['SelectedSource']['index']
        if s > 0:
            self.SelectSource(s - 1)

    def SelectSourceDown(self):
        """Select the next source in the list."""
        s = self.stored['SelectedSource']['index']
        if s < len(self.stored['Sources']) - 1:
            self.SelectSource(s + 1)

    def MoveSourceUp(self):
        """Move the selected source up one position."""
        if not self._confirmSafetyAction('Move Source Up'):
            return

        s = self.stored['SelectedSource']['index']
        if s > 0:
            source = self.stored['Sources'].pop(s)
            self.stored['Sources'].insert(s - 1, source)
            self.SelectSourceUp()
        self._updateSourceList()

    def MoveSourceDown(self):
        """Move the selected source down one position."""
        if not self._confirmSafetyAction('Move Source Down'):
            return

        s = self.stored['SelectedSource']['index']
        sources = self.stored['Sources']
        if s < len(sources) - 1:
            source = sources.pop(s)
            sources.insert(s + 1, source)
            self.SelectSourceDown()
        self._updateSourceList()

    # -------------------------------------------------------------------------
    # Pulse Parameter Handlers
    # -------------------------------------------------------------------------

    def pulse_Editextension(self):
        """Open the extension script for editing."""
        self.ownerComp.op('SourcererLite').par.edit.pulse()

    def pulse_Import(self):
        """Handle Import pulse parameter."""
        self.Import()

    def pulse_Exportall(self):
        """Handle Export All pulse parameter."""
        self.ExportAll()

    def pulse_Exportselected(self):
        """Handle Export Selected pulse parameter."""
        self.ExportSelected()

    def pulse_Exportrange(self):
        """Handle Export Range pulse parameter."""
        self.ExportRange()

    def pulse_Initsources(self):
        """Handle Init Sources pulse parameter."""
        self.InitSources(force_confirm=True)

    def pulse_Clearpendingqueue(self):
        """Handle Clear Pending Queue pulse parameter."""
        self.ClearPendingQueue()