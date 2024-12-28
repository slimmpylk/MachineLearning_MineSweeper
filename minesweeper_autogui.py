import pyautogui
import time
import os
import cv2
import numpy as np
import csv
from pynput import keyboard
from PIL import Image

###############################################################################
# Global Script Settings
###############################################################################

# Speed up PyAutoGUI's actions slightly
pyautogui.PAUSE = 0.05

# Flag to stop the script with a panic key
exit_signal = False

###############################################################################
# Paths and Basic Setup
###############################################################################

# Path where all template images are stored
TEMPLATE_PATH = os.path.expanduser("~/MachineLearning_MineSweeper/templates")

# Attempt to locate the game board from a known reference image.
# This helps us adapt if the window is moved or resized.
reference_image = os.path.join(TEMPLATE_PATH, "board/GameBoardWhenStart.png")
game_region = pyautogui.locateOnScreen(reference_image, confidence=0.6)

if game_region:
    TOP_LEFT = (int(game_region.left), int(game_region.top))
    BOTTOM_RIGHT = (
        int(game_region.left + game_region.width),
        int(game_region.top + game_region.height)
    )
    BOARD_REGION = (
        TOP_LEFT[0],
        TOP_LEFT[1],
        BOTTOM_RIGHT[0] - TOP_LEFT[0],
        BOTTOM_RIGHT[1] - TOP_LEFT[1]
    )
    print(f"Detected game board at: {BOARD_REGION}")
else:
    print("Could not detect the game board. Using default coordinates.")
    TOP_LEFT = (1190, 120)
    BOTTOM_RIGHT = (1687, 595)
    BOARD_REGION = (
        TOP_LEFT[0],
        TOP_LEFT[1],
        BOTTOM_RIGHT[0] - TOP_LEFT[0],
        BOTTOM_RIGHT[1] - TOP_LEFT[1]
    )

# Determine cell width and height from the UnOpenedCell template
cell_img_path = os.path.join(TEMPLATE_PATH, "buttons/UnOpenedCell.png")
cell_img = Image.open(cell_img_path)
CELL_WIDTH, CELL_HEIGHT = cell_img.size

###############################################################################
# Color Thresholds
# We detect "opened" vs "unopened" cells, and numbers 1-5 by color.
###############################################################################
opened_lower = np.array([210, 210, 210])
opened_upper = np.array([230, 230, 225])

unopened_lower = np.array([176, 179, 172])
unopened_upper = np.array([196, 199, 192])

# Adding number 5 with approximate ±10 color bounds around (247,161,162).
# Adjust these if detection is inaccurate.
NUMBER_COLORS = {
    1: ([210, 240, 180], [230, 255, 210]),
    2: ([220, 225, 180], [245, 245, 210]),
    3: ([220, 200, 170], [250, 230, 190]),
    4: ([220, 180, 120], [250, 210, 150]),
    # New addition for number 5:
    5: ([237, 151, 152], [255, 171, 172])  # (247 ±10, 161 ±10, 162 ±10)
}

###############################################################################
# Data Collection Setup
###############################################################################

# Directory where we store the CSV data
DATA_COLLECTION_PATH = os.path.expanduser("/mnt/varasto/data/data")
if not os.path.exists(DATA_COLLECTION_PATH):
    os.makedirs(DATA_COLLECTION_PATH)

# CSV file for storing Minesweeper data
DATA_FILE = os.path.join(DATA_COLLECTION_PATH, "minesweeper_data.csv")

# If the CSV doesn't exist, create it with headers
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([
            "row",
            "col",
            "number",
            "unopened_neighbors",
            "flagged_neighbors",
            "bombs_flagged_from_cell",
            "safe_cells_identified_from_cell",
            "game_over"
        ])

###############################################################################
# Keyboard Listener for Panic Key ('q')
###############################################################################
def on_press(key):
    """
    If 'q' is pressed at any time, exit_signal becomes True, which stops the script.
    """
    global exit_signal
    try:
        if key.char == 'q':
            print("Panic key pressed. Exiting...")
            exit_signal = True
    except AttributeError:
        pass

listener = keyboard.Listener(on_press=on_press)
listener.start()

###############################################################################
# Utility Functions
###############################################################################
def locate_image(image_name, confidence=0.9):
    """
    Attempts to locate 'image_name' on the screen with a given confidence.
    Returns a Box object (left, top, width, height) if found, or None if not.
    """
    image_path = os.path.join(TEMPLATE_PATH, image_name)
    try:
        return pyautogui.locateOnScreen(image_path, confidence=confidence)
    except pyautogui.ImageNotFoundException:
        return None

def click_location(location):
    """
    Left-click at the center of 'location' if it exists.
    location can be a Box or (x, y) tuple.
    Returns True if successful, otherwise False.
    """
    if location:
        if hasattr(location, 'left'):
            x, y = pyautogui.center(location)
        else:
            x, y = location
        pyautogui.click(x, y)
        return True
    return False

def flag_location(location):
    """
    Right-click at the center of 'location' if it exists to place a flag.
    Returns True if successful, otherwise False.
    """
    if location:
        if hasattr(location, 'left'):
            x, y = pyautogui.center(location)
        else:
            x, y = location
        pyautogui.click(x, y, button='right')
        return True
    return False

def cell_to_grid(cell_x, cell_y):
    """
    Convert pixel coordinates (cell_x, cell_y) to (row, col) indices
    for easier logic and data collection.
    """
    row = (cell_y - TOP_LEFT[1]) // CELL_HEIGHT
    col = (cell_x - TOP_LEFT[0]) // CELL_WIDTH
    return row, col

def get_neighbors(cell):
    """
    Return the 8 adjacent cell coordinates (including diagonals) for (x, y).
    """
    x, y = cell
    deltas = [
        (-1, -1), (-1, 0), (-1, 1),
        (0, -1),           (0, 1),
        (1, -1),  (1, 0),  (1, 1)
    ]
    return [(x + dx, y + dy) for dx, dy in deltas]

###############################################################################
# Image Processing Functions
###############################################################################
def detect_cells(image, lower_bound, upper_bound):
    """
    Detect cells in 'image' whose color is within 'lower_bound' and 'upper_bound'.
    Returns a list of (x, y) centers.
    """
    hsv_image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    mask = cv2.inRange(hsv_image, lower_bound, upper_bound)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    centers = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        center_x = TOP_LEFT[0] + x + (w // 2)
        center_y = TOP_LEFT[1] + y + (h // 2)
        centers.append((center_x, center_y))
    return centers

def detect_numbered_cells(image):
    """
    Detect numbered cells (1 through 5) within 'image'.
    Returns a dict mapping (x, y) -> number.
    """
    numbered_cells = {}
    for number, (lower, upper) in NUMBER_COLORS.items():
        lower_bound = np.array(lower, dtype="uint8")
        upper_bound = np.array(upper, dtype="uint8")

        mask = cv2.inRange(image, lower_bound, upper_bound)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            center_x = TOP_LEFT[0] + x + (w // 2)
            center_y = TOP_LEFT[1] + y + (h // 2)
            numbered_cells[(center_x, center_y)] = number

    return numbered_cells

def scan_board(region):
    """
    Take a screenshot of 'region' and detect:
      - 'unopened' cells
      - 'opened' cells
      - 'numbered' cells (1-5)
    Returns a dict with entries:
      (x,y) -> "unopened" / "opened" / "number_<n>"
    """
    screenshot = pyautogui.screenshot(region=region)
    board_image = np.array(screenshot)

    # Identify unopened vs opened
    unopened_cells = detect_cells(board_image, unopened_lower, unopened_upper)
    opened_cells = detect_cells(board_image, opened_lower, opened_upper)
    # Identify numbered cells
    numbered_cells = detect_numbered_cells(board_image)

    board_state = {}
    for cell in unopened_cells:
        board_state[cell] = "unopened"
    for cell in opened_cells:
        board_state[cell] = "opened"
    for cell, num in numbered_cells.items():
        board_state[cell] = f"number_{num}"

    print(f"Detected numbered cells: {numbered_cells}")
    return board_state

###############################################################################
# Core Game Flow Functions
###############################################################################
def detect_game_over():
    """
    Check if a bomb has been clicked (i.e., 'ClickedBomb' image is found).
    Return True if so, False otherwise.
    """
    if exit_signal:
        return True

    clicked_bomb = locate_image("buttons/ClickedBomb.png", confidence=0.8)
    if clicked_bomb:
        print("Bomb clicked! Game over.")
        return True
    return False

def start_game():
    """
    If the game board isn't started or is finished, click 'Play Again'.
    Otherwise, click an unopened cell to begin playing.
    """
    global exit_signal
    while not exit_signal:
        play_again_button = locate_image("cells/PlayAgainButton.png", confidence=0.7)
        unopened_cell = locate_image("buttons/UnOpenedCell.png", confidence=0.7)

        if play_again_button:
            print("Clicking 'Play Again' to reset the game.")
            click_location(play_again_button)
            time.sleep(0.1)
        elif unopened_cell:
            print("Game board found. Clicking an unopened cell to start.")
            click_location(unopened_cell)
            break
        else:
            print("Waiting for the game board or 'Play Again' button...")
            time.sleep(0.1)

        if exit_signal:
            break

def record_game_over():
    """
    Append a special row marking 'game_over=1' to the CSV.
    """
    with open(DATA_FILE, mode='a', newline='') as file:
        writer = csv.writer(file)
        # Use -1 for all columns except last to indicate 'game_over=1'
        writer.writerow([-1, -1, -1, -1, -1, -1, -1, 1])

def apply_logic(board_state, clicked_cells, flagged_cells):
    """
    Basic Minesweeper logic:
      - If (#unopened + #flagged) == number: all unopened must be bombs
      - If (#flagged) == number: all unopened must be safe

    Writes reasoning to CSV, flags bombs, and clicks safe cells.
    Returns True if any moves were made, False otherwise.
    """
    bombs_to_flag = set()
    cells_to_click = set()
    reasoning_data = []

    # Evaluate every numbered cell
    for cell, state in list(board_state.items()):
        if state.startswith("number_"):
            number = int(state.split("_")[1])
            neighbors = get_neighbors(cell)

            unopened_neighbors = [nbr for nbr in neighbors if board_state.get(nbr) == "unopened"]
            flagged_neighbors = [nbr for nbr in neighbors if board_state.get(nbr) == "flagged"]

            deduced_bombs = []
            deduced_safe = []

            if len(unopened_neighbors) + len(flagged_neighbors) == number and unopened_neighbors:
                deduced_bombs = unopened_neighbors

            if len(flagged_neighbors) == number and unopened_neighbors:
                deduced_safe = unopened_neighbors

            # Convert this cell's absolute coords to (row, col) for data
            row, col = cell_to_grid(cell[0], cell[1])
            reasoning_data.append([
                row,
                col,
                number,
                len(unopened_neighbors),
                len(flagged_neighbors),
                len(deduced_bombs),
                len(deduced_safe),
                0
            ])

            bombs_to_flag.update(deduced_bombs)
            cells_to_click.update(deduced_safe)

    # Write logic reasoning to CSV
    with open(DATA_FILE, mode='a', newline='') as file:
        writer = csv.writer(file)
        for row_data in reasoning_data:
            writer.writerow(row_data)

    # Flag bombs
    for bomb_cell in bombs_to_flag:
        if bomb_cell not in flagged_cells:
            if flag_location(bomb_cell):
                flagged_cells.add(bomb_cell)
                board_state[bomb_cell] = "flagged"
                print(f"Flagged a bomb at {bomb_cell}")

    # Click safe cells
    for safe_cell in cells_to_click:
        if safe_cell not in clicked_cells and safe_cell not in flagged_cells:
            if click_location(safe_cell):
                clicked_cells.add(safe_cell)
                print(f"Clicked a safe cell at {safe_cell}")

    return bool(bombs_to_flag or cells_to_click)

def play_game_with_data(region):
    """
    Main gameplay loop:
      1. Check if the game ended (bomb clicked).
      2. Scan the board and apply logic.
      3. If no moves, click a random unopened cell to reveal more info.
      4. Repeat until 'q' is pressed or the script is stopped.
    """
    global exit_signal
    clicked_cells = set()
    flagged_cells = set()

    while not exit_signal:
        # Check for game over
        if detect_game_over():
            if exit_signal:
                break
            print("Game over! Restarting...")
            record_game_over()
            start_game()
            clicked_cells.clear()
            flagged_cells.clear()
            continue

        print("Scanning board...")
        board_state = scan_board(region)
        if exit_signal:
            break

        print(f"Board state: {len(board_state)} cells detected.")

        # Apply standard logic
        made_moves = apply_logic(board_state, clicked_cells, flagged_cells)
        if exit_signal:
            break

        # If no logical moves, pick a random unopened cell
        if not made_moves:
            unopened_cells = [
                c for c, s in board_state.items()
                if s == "unopened" and c not in clicked_cells and c not in flagged_cells
            ]
            if unopened_cells:
                random_cell = unopened_cells[0]
                if click_location(random_cell):
                    clicked_cells.add(random_cell)
                    print(f"No logical step found; clicked at {random_cell}")
            else:
                print("No moves left. Waiting...")
            # Short sleep to detect 'q' presses
            time.sleep(0.1)

        time.sleep(0.05)

###############################################################################
# Main
###############################################################################
if __name__ == "__main__":
    print("Starting Minesweeper automation with data collection...")
    while not exit_signal:
        start_game()
        if exit_signal:
            break
        play_game_with_data(BOARD_REGION)
    print("Exiting automation... Bye!")
