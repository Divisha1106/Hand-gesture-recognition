# Professional AI Virtual Mouse

Welcome to the AI Virtual Mouse. This system uses `OpenCV` and `MediaPipe` to track your hand gestures and convert them to accurate cursor control via `PyAutoGUI`.

## Dependencies
Ensure you have the required packages installed:
```bash
pip install -r requirements.txt
```

## How to Run
```bash
python main.py
```

## Shortcuts and Settings
- Press `ESC` at any time to cleanly exit the camera feed.
- Press `s` to open the configuration menu (adjust tracking speeds and camera settings).

## Available Gestures

- **Move Cursor:** Held UP Index Finger only.
- **Left Click:** Quick pinch with Thumb and Index finger.
- **Drag & Drop:** Pinch Thumb and Index finger and **Hold**. Release to drop.
- **Right Click:** Pinch Thumb and Middle finger.
- **Double Click:** Pinch Thumb and Ring finger.
- **Scroll Data:** Hold Index and Middle fingers up, then move your hand to the top or bottom third of the camera frame.
- **Zoom In / Out:** Hold Index and Middle fingers up. Spread them apart to zoom IN, compress them together to zoom OUT.
- **Screenshot:** Open Palm (all 5 fingers spread) and hold still for 2 seconds. Screen will save as `screenshot_[timestamp].png`.
- **Pause Tracking:** Close your fist completely at any time.

Enjoy the smooth workflow!
