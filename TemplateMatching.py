import pyautogui

# Replace these coordinates with the region for a specific element (e.g., unopened cell)
region = (x, y, width, height)  # Example: (1152, 219, 30, 30)
screenshot = pyautogui.screenshot(region=region)
screenshot.save("templates/buttons/UnOpenedCell.png")
print("Updated 'UnOpenedCell.png' template.")
