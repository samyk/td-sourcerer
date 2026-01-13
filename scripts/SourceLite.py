# Author: Matthew Wachter
# License: MIT
# SourceLite - Simplified version with no parameter enable/disable logic


class SourceLite:
    def __init__(self, ownerComp):
        self.ownerComp = ownerComp

    def SaveChanges(self):
        return

    def _HandleParChange(self, par):
        """Route parameter changes to handler methods if they exist."""
        if hasattr(self, par.name):
            getattr(self, par.name)(par)

    def Cuepulse(self, par):
        """Pulse the cue on the movie file in."""
        self.ownerComp.op('moviefilein1').par.cuepulse.pulse()

    def Commandpulse(self, par):
        """Execute the command script."""
        parent.SOURCERER.op('commandScript').text = parent().par.Command
        parent.SOURCERER.op('commandScript').run()

    def Name(self, par):
        """Ensure unique source names and store changes."""
        names = [s['Settings']['Name'] for s in ext.SOURCERER.Sources]

        name = str(par.val)
        i = 0
        while name in names:
            name = name.rstrip('0123456789')
            name = name + str(i)
            i += 1

        if par.val != name:
            par.val = name

        if self.ownerComp.par.Storechanges.val:
            ext.SOURCERER.StoreSourceToSelected(self.ownerComp)

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
                    # play next
                    if follow_action == 'play_next':
                        cur_index = parent.SOURCERER.ActiveSource['index']
                        parent.SOURCERER.SwitchToSource(cur_index + 1)

                    # go to index
                    elif follow_action == 'goto_index':
                        if source_type == 'file':
                            goto_index = self.ownerComp.par.Gotoindexfile
                        else:
                            goto_index = self.ownerComp.par.Gotoindextop
                        parent.SOURCERER.SwitchToSource(int(goto_index))

                    # go to name
                    elif follow_action == 'goto_name':
                        if source_type == 'file':
                            goto_name = self.ownerComp.par.Gotonamefile
                        else:
                            goto_name = self.ownerComp.par.Gotonametop
                        parent.SOURCERER.SwitchToSource(str(goto_name))
