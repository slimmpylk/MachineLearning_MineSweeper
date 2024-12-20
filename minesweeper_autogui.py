import pyautogui
import time
import os
import cv2
import numpy as np
import csv
from pynput import keyboard
from PIL import Image

# Speed up PyAutoGUI's actions slightly
pyautogui.PAUSE = 0.05

# Global flag to stop the script with a panic key
exit_signal = False

# Path to templates
TEMPLATE_PATH = os.path.expanduser("~/MachineLearning_MineSweeper/templates")

# Try to find the game board using a known reference screenshot.
# This helps us adapt if the window is moved or resized.
reference_image = os.path.join(TEMPLATE_PATH, "board/GameBoardWhenStart.png")
game_region = pyautogui.locateOnScreen(reference_image, confidence=0.6)
if game_region:
    TOP_LEFT = (int(game_region.left), int(game_region.top))
    BOTTOM_RIGHT = (int(game_region.left + game_region.width), int(game_region.top + game_region.height))
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

# Determine cell size from the unopened cell image to adapt to different difficulties
cell_img_path = os.path.join(TEMPLATE_PATH, "buttons/UnOpenedCell.png")
cell_img = Image.open(cell_img_path)
CELL_WIDTH, CELL_HEIGHT = cell_img.size

# Color ranges for identifying different cell states
opened_lower = np.array([210, 210, 210])
opened_upper = np.array([230, 230, 225])

unopened_lower = np.array([176, 179, 172])
unopened_upper = np.array([196, 199, 192])

# Color ranges for identifying numbers on opened cells
NUMBER_COLORS = {
    1: ([210, 240, 180], [230, 255, 210]),
    2: ([220, 225, 180], [245, 245, 210]),
    3: ([220, 200, 170], [250, 230, 190]),
    4: ([220, 180, 120], [250, 210, 150])
}

def cell_to_grid(cell_x, cell_y):
    # Convert a cell's screen coordinates into (row, col) indices.
    row = (cell_y - TOP_LEFT[1]) // CELL_HEIGHT
    col = (cell_x - TOP_LEFT[0]) // CELL_WIDTH
    return row, col

# Ensure the data directory exists
DATA_COLLECTION_PATH = os.path.expanduser("/mnt/varasto/data/data")
if not os.path.exists(DATA_COLLECTION_PATH):
    os.makedirs(DATA_COLLECTION_PATH)

DATA_FILE = os.path.join(DATA_COLLECTION_PATH, "minesweeper_data.csv")

# If this is the first run, create a CSV file with appropriate headers.
# Updated headers to use row, col instead of rel_x, rel_y.
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

def on_press(key):
    # If 'q' is pressed, set exit_signal to True to stop the script gracefully
    global exit_signal
    try:
        if key.char == 'q':
            print("Panic key pressed. Exiting...")
            exit_signal = True
    except AttributeError:
        pass

# Start a separate thread to listen for key presses
listener = keyboard.Listener(on_press=on_press)
listener.start()

def locate_image(image_name, confidence=0.9):
    # Try to find a given image on the screen and return its location
    image_path = os.path.join(TEMPLATE_PATH, image_name)
    try:
        location = pyautogui.locateOnScreen(image_path, confidence=confidence)
        return location
    except pyautogui.ImageNotFoundException:
        return None

def click_location(location):
    # Click on a given (x, y) location if it exists
    if location:
        pyautogui.click(location[0], location[1])
        return True
    return False

def flag_location(location):
    # Right-click on a given (x, y) location to place a flag
    if location:
        pyautogui.click(location[0], location[1], button='right')
        return True
    return False

def detect_cells(image, lower_bound, upper_bound):
    # Identify cells based on a given color range
    hsv_image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    mask = cv2.inRange(hsv_image, lower_bound, upper_bound)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    centers = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        centers.append((TOP_LEFT[0] + x + w // 2, TOP_LEFT[1] + y + h // 2))
    return centers

def detect_numbered_cells(image):
    # Find cells that show numbers 1-4 and map them to their values
    numbered_cells = {}
    for number, (lower, upper) in NUMBER_COLORS.items():
        lower_bound = np.array(lower, dtype="uint8")
        upper_bound = np.array(upper, dtype="uint8")
        mask = cv2.inRange(image, lower_bound, upper_bound)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            center = (TOP_LEFT[0] + x + w // 2, TOP_LEFT[1] + y + h // 2)
            numbered_cells[center] = number
    return numbered_cells

def scan_board(region):
    # Take a screenshot of the board region and identify cells (opened, unopened, numbered)
    screenshot = pyautogui.screenshot(region=region)
    board_image = np.array(screenshot)

    unopened_cells = detect_cells(board_image, unopened_lower, unopened_upper)
    opened_cells = detect_cells(board_image, opened_lower, opened_upper)
    numbered_cells = detect_numbered_cells(board_image)

    board_state = {cell: "unopened" for cell in unopened_cells}
    board_state.update({cell: "opened" for cell in opened_cells})
    board_state.update({cell: f"number_{num}" for cell, num in numbered_cells.items()})

    print(f"Detected numbered cells: {numbered_cells}")
    return board_state

def start_game():
    # Make sure we have a running game. If not, click "Play Again" or start by clicking an unopened cell.
    global exit_signal
    while not exit_signal:
        play_again_button = locate_image("cells/PlayAgainButton.png", confidence=0.7)
        unopened_cell = locate_image("buttons/UnOpenedCell.png", confidence=0.7)

        if play_again_button:
            print("Game not started or over. Clicking 'Play Again'.")
            click_location(pyautogui.center(play_again_button))
            time.sleep(0.01)
        elif unopened_cell:
            print("Game board detected. Starting game by clicking an unopened cell.")
            click_location(pyautogui.center(unopened_cell))
            break
        else:
            print("Waiting for the game board or play button...")
            time.sleep(0.01)

def detect_game_over():
    # Check if a bomb was clicked and the game ended
    clicked_bomb = locate_image("buttons/ClickedBomb.png", confidence=0.8)
    if clicked_bomb:
        print("Bomb clicked! Game over.")
        return True
    return False

def get_neighbors(cell):
    # Get the 8 neighboring cells around a given cell
    x, y = cell
    return [
        (x + dx, y + dy) for dx, dy in [
            (-1, -1), (-1, 0), (-1, 1),
            (0, -1),          (0, 1),
            (1, -1),  (1, 0),  (1, 1)
        ]
    ]

def apply_logic(board_state, clicked_cells, flagged_cells):
    # Use basic Minesweeper logic to find bombs or safe cells
    bombs_to_flag = set()
    cells_to_click = set()
    reasoning_data = []

    for cell, state in list(board_state.items()):
        if state.startswith("number_"):
            number = int(state.split("_")[1])
            neighbors = get_neighbors(cell)
            unopened_neighbors = [nbr for nbr in neighbors if board_state.get(nbr) == "unopened"]
            flagged_neighbors = [nbr for nbr in neighbors if board_state.get(nbr) == "flagged"]

            deduced_bombs = []
            deduced_safe = []

            # If (#unopened + #flagged) = number, all unopened are bombs
            if len(unopened_neighbors) + len(flagged_neighbors) == number and unopened_neighbors:
                deduced_bombs = unopened_neighbors

            # If (#flagged) = number, the rest of unopened are safe
            if len(flagged_neighbors) == number and unopened_neighbors:
                deduced_safe = unopened_neighbors

            # Convert to row/col for data collection
            row, col = cell_to_grid(cell[0], cell[1])
            reasoning_data.append([
                row, col, number,
                len(unopened_neighbors),
                len(flagged_neighbors),
                len(deduced_bombs),
                len(deduced_safe),
                0  # game_over=0 since not ended
            ])

            bombs_to_flag.update(deduced_bombs)
            cells_to_click.update(deduced_safe)

    # Write the reasoning data to CSV
    with open(DATA_FILE, mode='a', newline='') as file:
        writer = csv.writer(file)
        for row_data in reasoning_data:
            writer.writerow(row_data)

    # Flag identified bombs
    if bombs_to_flag:
        print(f"Flagging {len(bombs_to_flag)} bombs...")
    for cell in bombs_to_flag:
        if cell not in flagged_cells:
            if flag_location(cell):
                flagged_cells.add(cell)
                board_state[cell] = "flagged"
                print(f"Flagged a bomb at {cell}")

    # Click identified safe cells
    if cells_to_click:
        print(f"Clicking {len(cells_to_click)} safe cells...")
    for cell in cells_to_click:
        if cell not in clicked_cells and cell not in flagged_cells:
            if click_location(cell):
                clicked_cells.add(cell)
                print(f"Clicked a safe cell at {cell}")

    # Return True if any moves were made to know if we need a random guess
    return bool(bombs_to_flag or cells_to_click)

def record_game_over():
    # Mark the CSV with a row indicating the game ended
    with open(DATA_FILE, mode='a', newline='') as file:
        writer = csv.writer(file)
        # Using -1 for all fields and game_over=1 to mark this state
        writer.writerow([-1, -1, -1, -1, -1, -1, -1, 1])

def play_game_with_data(region):
    global exit_signal
    clicked_cells = set()
    flagged_cells = set()

    while not exit_signal:
        if detect_game_over():
            print("Game over! Restarting...")
            record_game_over()
            start_game()
            clicked_cells.clear()
            flagged_cells.clear()
            continue

        print("Scanning board...")
        board_state = scan_board(region)
        print(f"Board state: {len(board_state)} cells detected.")

        made_moves = apply_logic(board_state, clicked_cells, flagged_cells)

        # If logic made no moves, pick a random unopened cell to progress the game
        if not made_moves:
            unopened_cells = [
                c for c, s in board_state.items()
                if s == "unopened" and c not in clicked_cells and c not in flagged_cells
            ]
            if unopened_cells:
                next_cell = unopened_cells[0]
                if click_location(next_cell):
                    clicked_cells.add(next_cell)
                    print(f"No logical step found, clicked at {next_cell}")
            else:
                print("No moves left. Waiting...")
                time.sleep(0.01)

if __name__ == "__main__":
    print("Starting Minesweeper automation with data collection...")
    while not exit_signal:
        start_game()
        play_game_with_data(BOARD_REGION)
    print("Exiting automation...")
