# Sourcerer Lite

**TouchDesigner version 2023.12370**

License: MIT

[Matthew Wachter](https://www.matthewwachter.com) | [VT Pro Design](https://www.vtprodesign.com)

## Overview

Sourcerer Lite is a streamlined media management component for TouchDesigner that provides organized playback, processing, and switching of image files and generative sources.

![sourcerer_screen1](images/screen1.jpg)

## Features

- Centralized source management with a list-based interface
- Support for file-based media and TOP-based generative content
- Built-in transitions with customizable timing and easing
- Post-processing effects (crop, tile, color correction, transform)
- Follow actions for automated playback sequences
- Transition queue system with optional bypass
- Real-time display properties (timecode, progress, loop count)
- Callback system for integration with external logic
- Import/export functionality for source presets

## Usage

### Managing Sources

Sources can be created, arranged, and triggered using the toolbar buttons above the source list. New sources can also be created by dropping files or TOPs directly into the list.

**Toolbar buttons:**
- ![add](images/add_new.jpg) Add new source
- ![switch_to_source](images/switch_to_source.jpg) Switch to selected source
- ![lock](images/lock.jpg) Lock/unlock editing (prevents accidental changes)

Sources can be reordered by dragging within the list.

**Right-click context menu:**
- Trigger - Switch to the selected source
- Copy / Paste - Copy and paste source configurations
- Delete - Remove the selected source
- Import - Import sources from JSON file
- Export Selected - Export selected source to JSON
- Export All - Export all sources to JSON

### Editing Sources

Select a source in the list to view and edit its parameters in the parameter panel. Changes are applied immediately. When editing the currently active (live) source, changes are reflected in real-time.

Use **Save as Default** to store the selected source's settings as the template for newly created sources.

### Extension Methods

Switch to sources programmatically using the `SwitchToSource()` method:

```python
# By index
op('Sourcerer').SwitchToSource(1)

# By name
op('Sourcerer').SwitchToSource('Blackout')

# Force switch (clears queue, ignores pending queue setting)
op('Sourcerer').SwitchToSource('Emergency', force=True)
```

### Pending Queue

When a transition is in progress and a new source switch is requested, the request is added to a pending queue. This ensures transitions complete smoothly without interruption.

**Queue behavior:**
- **Enable Pending Queue ON**: New requests are queued and processed after the current transition completes
- **Enable Pending Queue OFF**: New requests start immediately, interrupting the current transition

The queue can be managed programmatically:

```python
# Clear all pending switches
op('Sourcerer').ClearPendingQueue()

# Skip to the last queued item (useful for rapid navigation)
op('Sourcerer').SkipToLastPending()

# Check queue status
queue = op('Sourcerer').PendingQueue  # List of pending sources
is_transitioning = op('Sourcerer').isTransitioning  # Boolean
is_queue_enabled = op('Sourcerer').isQueueEnabled  # Boolean
```

### Display Properties

Active sources expose real-time display properties that can be bound to UI elements:

| Property | Description |
|----------|-------------|
| `Timecode` | Current playback position (HH:MM:SS:FF) |
| `TimeRemaining` | Time until source completes |
| `Progress` | Playback progress (0-100%) |
| `LoopCount` | Number of completed loops (file sources) |
| `LoopsRemaining` | Loops remaining in play_n_times mode |
| `Next` | Name of the next source based on follow action |

Access via the active source component:
```python
op('Sourcerer').ActiveSourceComp.Timecode
op('Sourcerer').ActiveSourceComp.Progress
```

## Transitions

Each source defines the transition used when switching **to** that source. The transition system uses a GLSL shader located at [scripts/transitions.glsl](scripts/transitions.glsl).

### Transition Types

| Type | Description |
|------|-------------|
| **Dissolve** | Crossfade between sources |
| **Dip** | Fade to a color, then fade to the incoming source |
| **Slide** | Push content in a specified direction (left, right, up, down) |
| **Wipe** | Hard-edge reveal in a specified direction |
| **Blur** | Crossfade with blur peaking at midpoint |
| **File** | Luma matte transition from a file (black to white gradient) |
| **TOP** | Luma matte transition from a TOP operator |

### Transition Timing

Set transition duration using the **Transition Time** parameter (in seconds). Enable **Use Global Transition Time** to use the global setting from Sourcerer's Settings page instead.

### Transition Shape

The **Transition Progress Shape** parameter controls the easing curve:

| Shape | Description |
|-------|-------------|
| Linear | Constant rate |
| Ease In | Accelerates into transition |
| Ease Out | Decelerates out of transition |
| Half Cosine (soft/hard) | S-curve with configurable steepness |
| Logistic (soft/hard) | Sigmoid curve with configurable steepness |
| Arctangent (soft/hard) | Atan-based curve with configurable steepness |
| Custom | User-provided CHOP (single channel, 0 to 1) |

## Follow Actions

Follow actions define what happens when a source finishes playing. This enables automated playback sequences similar to clip follow actions in Ableton Live.

### Done Conditions

The **Done On** parameter determines when the follow action triggers:

**File sources:**
- Play (n) Times - Loop a specified number of times
- Timer - Play for a specified duration
- CHOP - Trigger when a CHOP channel transitions from 0 to 1
- Done Pulse - Manual trigger

**TOP sources:**
- Timer - Play for a specified duration
- CHOP - Trigger when a CHOP channel transitions from 0 to 1
- Done Pulse - Manual trigger

### Follow Action Types

- **None** - No action
- **Play Next** - Advance to the next source in the list
- **Go to Index** - Jump to a specific source by index
- **Go to Name** - Jump to a specific source by name

### Early Trigger for Transitions

When using **Play (n) Times** mode with a follow action, the transition to the next source can start early to allow the transition to complete by the time the current source ends. This is calculated automatically based on the next source's transition time.

## Callbacks

Callbacks are defined in the callbacks script at the root of the Sourcerer component. Access via **Open Callbacks Script** in the Settings page.

| Callback | Parameters | Description |
|----------|------------|-------------|
| `onInit` | ownerComp | Component initialized |
| `onSourceDone` | index, name | Source finished playing |
| `onSwitchToSource` | index, name, source | Source switch initiated |
| `onTransitionComplete` | index, name | Transition animation completed |

## Parameter Reference

### Sourcerer Settings

| Parameter | Description |
|-----------|-------------|
| Version | Component version (read only) |
| Resolution | Output resolution |
| BG Color | Background color |
| Global Transition Time | Default transition duration |
| Enable Pending Queue | Queue source switches during transitions |
| Update Display | Enable/disable display property updates (performance toggle) |
| Import | Import sources from JSON |
| Export All | Export all sources to JSON |
| Export Selected | Export selected source to JSON |
| Export Range | Export a range of sources |
| Edit Callbacks Script | Open the callbacks script |

### Source Settings

| Parameter | Description |
|-----------|-------------|
| Name | Display name (also used for `SwitchToSource()`) |
| Source Type | File or TOP |
| Transition Type | Dissolve, Dip, Slide, Wipe, Blur, File, or TOP |
| Transition Direction | Direction for Slide/Wipe transitions |
| Dip Color | Color for Dip transition |
| Transition File | File path for File transition |
| Transition TOP | TOP path for TOP transition |
| Use Global Transition Time | Use global setting instead of per-source |
| Transition Time | Duration in seconds |
| Transition Progress Shape | Easing curve |
| Custom Transition Shape | CHOP path for custom easing |
| Enable Command | Execute a command on switch |
| Command | Python command to execute |

### File Parameters

| Parameter | Description |
|-----------|-------------|
| File | File path |
| File Length Frames | Duration (read only) |
| File Sample Rate | Frame rate (read only) |
| Trim | Enable trimming |
| Trim Start/End Frames | Trim points |
| Speed | Playback rate multiplier |
| Interpolate Frames | Blend frames at slow speeds |
| Cue / Cue Pulse / Cue Point | Cue controls |
| Loop Crossfade Frames | Crossfade duration for loops |
| Deinterlace | Deinterlace mode |
| Field Precedence | Field order |
| Extend Right | End-of-file behavior |
| Done On | Follow action trigger condition |
| Play (n) Times | Loop count |
| Timer Time | Duration in seconds |
| CHOP | Trigger CHOP path |
| Follow Action | Action type |
| Go To Index / Name | Target source |

### TOP Parameters

| Parameter | Description |
|-----------|-------------|
| TOP | TOP path |
| Enable Cue TOP | Enable cue pulse on switch |
| Cue TOP | MovieFileIn TOP to cue |
| Done On | Follow action trigger condition |
| Timer Time | Duration in seconds |
| CHOP | Trigger CHOP path |
| Follow Action | Action type |
| Go To Index / Name | Target source |

### Crop / Tile Parameters

| Parameter | Description |
|-----------|-------------|
| Crop Left/Right/Bottom/Top | Crop boundaries (0-1) |
| Crop Extend | Out-of-bounds behavior |
| Transpose | Swap X/Y coordinates |
| Flip X/Y | Mirror axes |
| Repeat X/Y | Tile count |
| Reflect X/Y | Mirror tiles |
| Overlap U/V | Soft edge overlap |

### Color Parameters

| Parameter | Description |
|-----------|-------------|
| Invert | Invert colors |
| Black Level | Black point threshold |
| Brightness | Brightness offset |
| Gamma | Gamma correction |
| Contrast | Contrast multiplier |
| Red/Green/Blue | Channel levels |
| Hue | Hue shift |
| Saturation | Saturation adjustment |
| Value | Value adjustment |

### Transform Parameters

| Parameter | Description |
|-----------|-------------|
| Pre-Fit Overlay | Fit mode (Fill, Fit Horizontal, Fit Vertical, Fit Best, Fit Outside, Native) |
| Justify Horizontal | Horizontal alignment |
| Justify Vertical | Vertical alignment |
| Extend Overlay | Out-of-bounds behavior |
| Translate | X/Y offset |
| Scale | X/Y scale |
| Rotate | Rotation angle |
