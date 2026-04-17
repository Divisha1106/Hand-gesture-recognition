import cv2
import time
import subprocess
import os
import winsound

from core.hand_tracker import HandTracker
from core.gesture_recognizer import GestureRecognizer
from core.cursor_controller import CursorController
from ui.overlay import OverlayUI
from utils.config import config

def play_click_sound():
    """Play a native click sound asynchronously."""
    try:
        # Playing standard Windows notification blip
        winsound.MessageBeep(winsound.MB_OK)
    except Exception as e:
        pass

def main():
    print("Initializing AI Virtual Mouse...")
    
    # Initialize Core Components
    tracker = HandTracker(max_num_hands=1, min_detection_confidence=0.75, min_tracking_confidence=0.75)
    recognizer = GestureRecognizer()
    cursor = CursorController()
    ui = OverlayUI()

    # Try setting up camera
    cam_index = config.get("camera_index")
    cap = cv2.VideoCapture(cam_index)
    
    if not cap.isOpened():
        print(f"Error: Could not open camera {cam_index}.")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.get("camera_resolution")[0])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.get("camera_resolution")[1])
    
    # State flags
    is_tracking_paused = False
    screenshot_start_time = 0
    pinch_start_time = 0
    is_dragging = False
    prev_zoom_dist = 0
    current_mode = "Idle"

    print("Virtual Mouse is Running! Press 's' for Settings, 'ESC' to Exit.")

    while True:
        # Every loop iteration, reload config if changes occurred (cheap checking is done internally or we can just reload occasionally)
        config.load_config()
        
        success, frame = cap.read()
        if not success:
            continue
            
        frame = cv2.flip(frame, 1) # Mirror display
        h, w, c = frame.shape
        
        # Draw active region early so it's behind hand tools
        active_rect = cursor.get_active_region(w, h)
        frame = ui.draw_active_region(frame, active_rect)

        if not is_tracking_paused:
            results = tracker.process(frame)
            frame = tracker.draw_landmarks(frame, results)
            lm_list, bbox = tracker.get_landmarks(frame, results)

            if len(lm_list) != 0:
                fingers = recognizer.fingers_up(lm_list)
                
                # Check Pause Mechanism: Closed Fist
                if recognizer.is_closed_fist(fingers):
                    current_mode = "Paused (Closed fist)"
                    # Optionally wait logic or true pause flag
                else:
                    # 1. MOVEMENT: Index finger up, everything else down
                    if fingers[1] == 1 and fingers[2] == 0:
                        x, y = lm_list[recognizer.tip_ids[1]][1], lm_list[recognizer.tip_ids[1]][2]
                        # Account for cursor_speed multiplier -> scale movement around center
                        cursor.update_cursor(x, y, w, h)
                        current_mode = "Moving"
                    
                    # 2. LEFT CLICK & DRAG: Thumb and Index Pinch
                    is_left_pinch, cx, cy, dist_L = recognizer.check_pinch(lm_list, 4, 8)
                    if is_left_pinch:
                        if pinch_start_time == 0:
                            pinch_start_time = time.time()
                        
                        held_time = time.time() - pinch_start_time
                        if held_time > 0.4 and not is_dragging:
                            is_dragging = True
                            cursor.drag_start()
                            play_click_sound()
                            current_mode = "Dragging"
                        elif is_dragging:
                            current_mode = "Dragging (Held)"
                            cursor.update_cursor(lm_list[recognizer.tip_ids[1]][1], lm_list[recognizer.tip_ids[1]][2], w, h)
                    else:
                        if pinch_start_time != 0:
                            held_time = time.time() - pinch_start_time
                            if is_dragging:
                                is_dragging = False
                                cursor.drag_end()
                                play_click_sound()
                                current_mode = "Drag Released"
                            elif held_time <= 0.4:
                                if recognizer.can_perform_action():
                                    cursor.click("left")
                                    play_click_sound()
                                    recognizer.reset_cooldown()
                                    frame = ui.draw_click_feedback(frame, (cx, cy), "left_click")
                                    current_mode = "Left Click"
                            
                            pinch_start_time = 0
                    
                    # 3. RIGHT CLICK: Thumb and Middle Pinch
                    is_right_pinch, cx, cy, dist_R = recognizer.check_pinch(lm_list, 4, 12)
                    if is_right_pinch and not is_left_pinch and recognizer.can_perform_action():
                        cursor.click("right")
                        play_click_sound()
                        recognizer.reset_cooldown()
                        frame = ui.draw_click_feedback(frame, (cx, cy), "right_click")
                        current_mode = "Right Click"
                        
                    # 4. SCROLL & ZOOM: Index and Middle Up
                    if fingers[1] == 1 and fingers[2] == 1 and fingers[3] == 0:
                        from utils.math_utils import get_distance
                        dist_im = get_distance((lm_list[8][1], lm_list[8][2]), (lm_list[12][1], lm_list[12][2]))
                        
                        if prev_zoom_dist == 0:
                            prev_zoom_dist = dist_im
                        
                        diff_zoom = dist_im - prev_zoom_dist
                        
                        # Spread detection for Zoom
                        if abs(diff_zoom) > 20: 
                            if diff_zoom > 0:
                                cursor.zoom("in")
                                current_mode = "Zooming In"
                            else:
                                cursor.zoom("out")
                                current_mode = "Zooming Out"
                            prev_zoom_dist = dist_im
                        else:
                            # Scroll logic
                            y = lm_list[recognizer.tip_ids[1]][2]
                            if y < h / 3:
                                cursor.scroll("up")
                                current_mode = "Scrolling Up"
                            elif y > 2 * h / 3:
                                cursor.scroll("down")
                                current_mode = "Scrolling Down"
                            else:
                                current_mode = "Scroll Ready"
                    else:
                        prev_zoom_dist = 0

                    # 5. SCREENSHOT: Open Palm for 2s
                    if recognizer.is_open_palm(fingers):
                        if screenshot_start_time == 0:
                            screenshot_start_time = time.time()
                        elif time.time() - screenshot_start_time > 2.0:
                            import pyautogui
                            pyautogui.screenshot(f'screenshot_{int(time.time())}.png')
                            play_click_sound()
                            screenshot_start_time = 0
                            current_mode = "Screenshot Taken!"
                            recognizer.reset_cooldown()
                    else:
                        screenshot_start_time = 0
                        
                    # 6. DOUBLE CLICK (Thumb and Ring Pinch)
                    is_double_pinch, cx, cy, dist_D = recognizer.check_pinch(lm_list, 4, 16)
                    if is_double_pinch and recognizer.can_perform_action():
                        cursor.double_click()
                        play_click_sound()
                        recognizer.reset_cooldown()
                        frame = ui.draw_click_feedback(frame, (cx, cy), "double_click")
                        current_mode = "Double Click"
                        
            else:
                # No hands in frame, reset smoothing so it doesn't jump wildly when re-entering
                cursor.reset_smoothing()
                current_mode = "No Hands Detected"

        # Draw UI Overlay
        frame = ui.draw_dashboard(frame, current_mode, not is_tracking_paused)
        
        cv2.imshow("AI Virtual Mouse", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == 27: # ESC
            break
        elif key == ord('s'):
            # Launch settings subprocess
            subprocess.Popen(["python", "ui/settings.py", "&"], shell=True)

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
