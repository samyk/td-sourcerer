# Author: Matthew Wachter
# License: MIT
# SourcererLite - Optimized version storing only parameter values (no TDJSON)

import json
import os
from TDStoreTools import StorageManager, DependList


class SourcererLite:
    def __init__(self, ownerComp):
        # The component to which this extension is attached
        self.ownerComp = ownerComp
        self.DataComp = ownerComp.op('data')
        self.transitionComp = ownerComp.op('transitions')
        self.switcherState = ownerComp.op('state')
        self.selectedSourceComp = ownerComp.op('selectedSource')

        storedItems = [
            {'name': 'Sources', 'default': [], 'dependable': False},
            {'name': 'SourceList', 'default': [], 'dependable': True},
            {'name': 'SelectedSource', 'default': 0, 'dependable': True},
            {
                'name': 'ActiveSource',
                'default': {'index': 0, 'name': ''},
                'dependable': True
            },
            {'name': 'State', 'default': 0, 'dependable': True}
        ]

        self.stored = StorageManager(self, self.DataComp, storedItems)
        self._updateSourceList()

    def _updateSourceList(self):
        source_list = [str(s['Settings']['Name']) for s in self.stored['Sources']]
        self.stored['SourceList'] = source_list

    def _getSource(self, source):
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
                print('no source', source, 'in', source_names)

        elif isinstance(source, int):
            s = source
            index = source
            source_json = self.stored['Sources'][s]
            if source <= len(self.stored['Sources'])-1:
                name = source_json['Settings']['Name']
            else:
                print('source index', s, 'is out of range')

        else:
            print('wrong source type', source)

        return source_json, index, name

    def SwitchToSource(self, source):
        state = self.stored['State']
        next_state = 1-state

        source_comp = self.ownerComp.op('source' + str(next_state))

        source, index, name = self._getSource(source)

        # update the source comp
        self.UpdateSourceCompQuick(source_comp, index)

        # set the timers and reload the movie
        source_type = source['Settings']['Sourcetype']

        source_comp.op('count1').par.resetpulse.pulse()
        source_comp.op('timerFile').par.initialize.pulse()
        source_comp.op('timerTOP').par.initialize.pulse()

        if source_type == 'file':
            source_comp.op('moviefilein0').par.reloadpulse.pulse()

            done_on = source['File']['Doneonfile']
            if done_on == 'timer':
                source_comp.op('startTimerFile').run(delayFrames=1)

        else:
            done_on = source['TOP']['Doneontop']
            if done_on == 'timer':
                source_comp.op('startTimerTOP').run(delayFrames=1)

            cue_vid = source['TOP']['Enablecuetop']

            if cue_vid:
                vid = source['TOP']['Cuetop']
                op(vid).par.cuepulse.pulse()

        # set the transition (lite version: GLSL only - Fade, Fade Color, Slide)
        settings = source['Settings']
        tcomp_par = self.transitionComp.par

        glsl_trans = settings['Glsltransition']
        tcomp_par.Glsltransition = glsl_trans

        # Only 3 transitions supported in lite version
        glsl_transitions = {
            'Fade': [],
            'Fade Color': ['Fadecolor'],
            'Slide': ['Slidedirection']
        }
        if glsl_trans in glsl_transitions:
            transition_pars = glsl_transitions[glsl_trans]
            for p in transition_pars:
                val = source['GLSL Transition'][p]
                self._setParVal(p, val, self.transitionComp)

        # set the transition time
        if settings['Useglobaltransitiontime']:
            trans_time = self.ownerComp.par.Globaltransitiontime.eval()
        else:
            trans_time = settings['Transitiontime']
        tcomp_par.Transitiontime = trans_time

        # set the progress shape
        trans_shape = settings['Transitionshape']
        tcomp_par.Transitionshape = trans_shape
        if trans_shape == 'custom':
            tcomp_par.Customtransitionshape = settings['Customtransitionshape']

        # update the stored information
        self.stored['State'] = next_state
        self.stored['ActiveSource'] = {
            'index': index,
            'name': name,
            'source': source
        }

        try:
            self.ownerComp.mod.callbacks.onSwitchToSource(index, name, source)
        except Exception as e:
            debug('switch to source callback error')
            debug(e)
        return

    def SwitchToSelectedSource(self):
        s = self.stored['SelectedSource']
        self.SwitchToSource(s)

    def DelaySwitchToSource(self, source, delay=0):
        self.ownerComp.op('delaySwitchToSource').run(source, delayMilliSeconds=delay)

    def RunCommand(self, command):
        self.ownerComp.op('commandScript').text = command
        self.ownerComp.op('commandScript').run(delayFrames=1)

    # SOURCES
    def Import(self):
        f = ui.chooseFile(load=True, fileTypes=['json'], title='Import Sources')

        if f is not None:
            with open(f, 'r') as json_file:
                imported_sources = json.load(json_file)

                if imported_sources:
                    a = ui.messageBox('Sourcerer Import Location', 'Select a location:', buttons=['Prepend', 'Insert (above selected)', 'Append'])

                    sources = []
                    sources.extend(self.stored['Sources'].getRaw())

                    # prepend
                    if a == 0:
                        new_sources = imported_sources.copy()
                        new_sources.extend(sources)
                        self.stored['Sources'] = new_sources

                        for i in range(0, len(imported_sources)):
                            self._checkUniqueName(self.stored['Sources'][i], count=1)

                    # insert
                    elif a == 1:
                        s = self.stored['SelectedSource']
                        new_sources = sources[:s].copy()
                        new_sources.extend(imported_sources)
                        new_sources.extend(sources[s:].copy())
                        self.stored['Sources'] = new_sources

                        for i in range(s, s + len(imported_sources)):
                            self._checkUniqueName(self.stored['Sources'][i], count=1)

                    # append
                    elif a == 2:
                        new_sources = sources.copy()
                        new_sources.extend(imported_sources)
                        self.stored['Sources'] = new_sources

                        for i in range(len(sources), len(new_sources)):
                            self._checkUniqueName(self.stored['Sources'][i], count=1)
                    self._updateSourceList()
        return

    def ExportAll(self):
        f = ui.chooseFile(load=False, fileTypes=['json'], title='Export Sources')

        if f is not None:
            sources = self.stored['Sources'].getRaw()

            with open(f, 'w') as json_file:
                json.dump(sources, json_file)
        return

    def ExportSelected(self):
        f = ui.chooseFile(load=False, fileTypes=['json'], title='Export Sources')

        if f is not None:
            selected_source = self.stored['SelectedSource']
            sources = [self.stored['Sources'][selected_source].getRaw()]

            with open(f, 'w') as json_file:
                json.dump(sources, json_file)
        return

    def ExportRange(self, range_start=None, range_end=None):
        f = ui.chooseFile(load=False, fileTypes=['json'], title='Export Sources')

        if f is not None:
            if range_start is None:
                range_start = self.ownerComp.par.Exportrangeval1
            if range_end is None:
                range_end = self.ownerComp.par.Exportrangeval2

            sources = self.stored['Sources'].getRaw()
            sources = sources[range_start:range_end+1]

            with open(f, 'w') as json_file:
                json.dump(sources, json_file)
        return

    # set the sources to their initial state
    def InitSources(self):
        # clear the sources list
        self.stored['Sources'] = []

        # set the selected source to 0
        self.stored['SelectedSource'] = 0

        # add a default source
        self.AddSource()
        self._updateSourceList()
        return

    def _getSourceTemplate(self, template):
        """Get a source template as a simple value dictionary from a template component."""
        template_op = self.ownerComp.op(template)
        return self._extractValues(template_op)

    def _setParVal(self, par_name, value, target_comp):
        """Set a parameter value directly on a component."""
        if hasattr(target_comp.par, par_name):
            par = getattr(target_comp.par, par_name)
            if isinstance(value, (list, tuple)):
                # Multi-value parameter
                for i, p in enumerate(par.tuplet):
                    if i < len(value):
                        p.val = value[i]
            else:
                par.val = value

    def _extractValues(self, comp):
        """Extract parameter values from a component as a simple dictionary."""
        source_dict = {}
        for page in comp.customPages:
            page_dict = {}
            for par in page.pars:
                # Store just the value, handling tuplets
                if len(par.tuplet) > 1 and par == par.tuplet[0]:
                    # Multi-value parameter - store as list
                    page_dict[par.tupletName] = [p.val for p in par.tuplet]
                elif len(par.tuplet) == 1:
                    # Single value parameter
                    page_dict[par.name] = par.val
                # Skip non-first tuplet members (captured above)
            source_dict[page.name] = page_dict
        return source_dict

    def UpdateSelectedSourceComp(self):
        # get the selected source
        s = self.stored['SelectedSource']

        # update the source comp
        self.UpdateSourceCompQuick(self.selectedSourceComp, s, active=False, store_changes=True)
        return

    def UpdateSourceCompQuick(self, source_comp, source_index, active=True, store_changes=False):
        """Fast source update - directly sets parameter values."""
        # disable the callbacks for changing parameters
        source_comp.op('parexec1').par.active = False

        # get the source data
        source_data = self.stored['Sources'][source_index]

        # iterate through pages and parameters, setting values directly
        for page_name, page_data in source_data.items():
            for par_name, value in page_data.items():
                self._setParVal(par_name, value, source_comp)

        # re-enable parameter change callbacks
        source_comp.op('enable').run(delayFrames=1)
        source_comp.par.Storechanges = store_changes
        source_comp.par.Active = active
        source_comp.par.Index = source_index

        if active:
            if source_comp.par.Enablecommand:
                try:
                    source_comp.op('command').run()
                except:
                    pass

            if source_comp.par.Enablecuetop:
                try:
                    op(source_comp.par.Cuetop).par.cue.pulse()
                except:
                    pass

    def UpdateSourceComp(self, source_comp, source_index, active=True, store_changes=False):
        """Full source update - same as quick in lite version."""
        self.UpdateSourceCompQuick(source_comp, source_index, active, store_changes)
        return

    def StoreSourceToSelected(self, source_comp, update_selected_comp=False):
        # get the selected source
        source = self.stored['SelectedSource']

        self.StoreSource(source_comp, source)

        if update_selected_comp:
            self.UpdateSelectedSourceComp()
        self._updateSourceList()
        return

    def StoreSource(self, source_comp, source):
        """Store source by extracting parameter values directly."""
        self.stored['Sources'][source] = self._extractValues(source_comp)
        self._updateSourceList()
        return

    def InitSource(self):
        # get the default source template
        source_dict = self._getSourceTemplate('defaultSource')

        # get the selected source
        s = self.stored['SelectedSource']

        # store to the selected source
        self.stored['Sources'][s] = source_dict
        self._updateSourceList()
        return

    def _checkUniqueName(self, source, count=0):
        names = [s['Settings']['Name'] for s in self.stored['Sources']]

        orig_name = str(source['Settings']['Name'])

        if names.count(orig_name) > count:
            name = orig_name
            i = 0
            while name in names:
                name = name.rstrip('0123456789')
                name = name + str(i)
                i += 1

            if orig_name != name:
                source['Settings']['Name'] = name
        self._updateSourceList()
        return source

    def AddSource(self, source_type=None, source_path=None, source_name=None):
        # get the selected source
        s = self.stored['SelectedSource']

        # get the appropriate template
        if source_type is None:
            source = self._getSourceTemplate('defaultSource')

        elif source_type == 'file':
            source = self._getSourceTemplate('fileSource')
            if source_path is not None:
                source['File']['File'] = source_path

        elif source_type == 'top':
            source = self._getSourceTemplate('topSource')
            if source_path is not None:
                source['TOP']['Top'] = source_path

        if source_name is not None:
            source['Settings']['Name'] = source_name

        source = self._checkUniqueName(source)

        # insert the template into the sources list
        self.stored['Sources'].insert(s+1, source)

        self.SelectSource(s+1)

        # update the source comp parameters
        self.UpdateSourceCompQuick(self.selectedSourceComp, s+1, store_changes=True)
        self._updateSourceList()
        return

    def _DropSource(self, args):
        # for each dropped item
        for dropped in args:

            # file source
            if isinstance(dropped, str):
                if os.path.isfile(dropped):
                    source_type = 'file'
                    source_path = dropped
                    base = os.path.basename(dropped)
                    source_name = os.path.splitext(base)[0]
                    file_ext = os.path.splitext(base)[1][1:]

                    if file_ext in tdu.fileTypes['movie'] or file_ext in tdu.fileTypes['image']:
                        self.AddSource(source_type, source_path, source_name)

            # top source
            elif hasattr(dropped, 'family'):
                if dropped.family == 'TOP':
                    source_type = 'top'
                    source_path = dropped.path
                    source_name = dropped.name
                    self.AddSource(source_type, source_path, source_name)

            else:
                debug('not valid source type')
                debug(type(source_type))
                debug(source_type)
        return

    def CopySource(self):
        # get the selected source
        s = self.stored['SelectedSource']

        # get a copy of the source (deep copy to avoid reference issues)
        source = json.loads(json.dumps(self.stored['Sources'][s]))

        source = self._checkUniqueName(source)

        # insert the new source
        self.stored['Sources'].insert(s, source)

        # select the new source
        self.SelectSource(s)
        self._updateSourceList()
        return

    def DeleteSource(self):
        # get the selected source
        s = self.stored['SelectedSource']
        # get the list of sources
        a = self.stored['Sources']

        if len(a) > 1:
            # pop the source from the list
            a.pop(s)
            # If we deleted the last item, select the new last item
            if s >= len(a):
                self.SelectSource(len(a) - 1)
            else:
                self.SelectSource(s)
        self._updateSourceList()
        return

    def SelectSource(self, index):

        if index > len(self.stored['Sources'])-1:
            index = index - 1

        # set the selected source
        self.stored['SelectedSource'] = index

        # update the sources comp
        self.UpdateSelectedSourceComp()
        return

    def SelectSourceUp(self):
        # get the selected source
        s = self.stored['SelectedSource']

        # select a source up if it exists
        if(s > 0):
            self.SelectSource(s - 1)
        return

    def SelectSourceDown(self):
        # get the selected source
        s = self.stored['SelectedSource']

        # get a list of sources
        a = self.stored['Sources']

        # select a source down if it exists
        if(s < len(a) - 1):
            self.SelectSource(s+1)
        return

    def MoveSourceUp(self):
        # get the selected source
        s = self.stored['SelectedSource']

        # check if the selected source can go up
        if(s > 0):
            # get the source
            a = self.stored['Sources'][s]

            # delete the selected source
            self.stored['Sources'].pop(s)

            # insert it again a spot up
            self.stored['Sources'].insert(s - 1, a)

            # select the source
            self.SelectSourceUp()
        self._updateSourceList()
        return

    def MoveSourceDown(self):
        # get the selected source
        s = self.stored['SelectedSource']

        # get the sources list
        a = self.stored['Sources']

        # check if the selected source can go down
        if(s < len(a) - 1):
            # get the selected source
            a = self.stored['Sources'][s]

            # delete the selected source
            self.stored['Sources'].pop(s)

            # insert the source one spot down
            self.stored['Sources'].insert(s + 1, a)

            # select the source
            self.SelectSourceDown()
        self._updateSourceList()
        return
