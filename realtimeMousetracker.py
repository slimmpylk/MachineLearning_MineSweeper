import pyautogui

print("Move your mouse over the game, and press Ctrl+C to stop.")
try:
    while True:
        x, y = pyautogui.position()
        print(f"Mouse position: ({x}, {y})", end="\r")
except KeyboardInterrupt:
    print("\nDone!")
