# Changelog

## [2.0.1] - 2025-01-28

### Fixed
- onSwitchToSource callback renamed to onTake.
- Changed CopySourceData to return dict rather than DependDict

## [2.0.0] - 2025-01-28

### Added
- **SourcererGrid component** - New touch-friendly grid UI for source selection with pagination and scrollbar overflow modes
- **Temp source support** - Switch to temporary sources without modifying the source list
- **CHOP done validation** - Follow actions only trigger when done-on parameter matches 'chop'
- **Display properties** - `ActiveSource`, `SelectedSource`, `PendingSource` dictionaries with name/index/op
- **Minimized status view** - Compact log display option
- **Source CHOP outputs** - CHOP channels for source state monitoring
- **Context menu** - Right-click menu with Copy, Paste, Delete, Import, Export options
- **Drag-drop reordering** - Reorder sources by dragging in the list

### Changed
- **Transition system overhaul** - Complete rewrite using state machine architecture
- **List system rewrite** - Externalized list component with improved styling and interactions
- **Follow actions** - Improved handling and validation
- **Parameter storage** - Cleaner parameter storing and retrieval

### Fixed
- Blur transition not working correctly
- GLSL transition fade colors
- Pending queue display issues
- Sources with 0 transition time not transitioning
- Play N times logic
- Switching bug in newer TD versions
- Dependency issues with component initialization
- Panels closing on reload

## [1.0.0] - 2019-12-19 - Initial Release

### Added
- Core source management (add, delete, rename, reorder)
- Multiple source types (Movie File, Image File, TOP)
- Transition system with GLSL shader effects (Dissolve, Dip, Slide, Wipe, Blur, File, Top)
- Follow actions (None, Stop, Loop, Next, Previous, Random, First, Last)
- Done conditions (Timer, Play N Times, CHOP)
- Import/Export sources as JSON
- Callbacks for source events
