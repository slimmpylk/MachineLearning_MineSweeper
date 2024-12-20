import pyautogui
import time
import os
import cv2
import numpy as np
import csv
from pynput import keyboard



# Global variable to track exit signal
exit_signal = False

# Path to the templates folder
TEMPLATE_PATH = os.path.expanduser("~/minexseeper/templates")

# Define game board region
TOP_LEFT = (1190, 120)  # Top-left corner of the game window
BOTTOM_RIGHT = (1687, 595)  # Bottom-right corner of the game window
BOARD_REGION = (TOP_LEFT[0], TOP_LEFT[1], BOTTOM_RIGHT[0] - TOP_LEFT[0], BOTTOM_RIGHT[1] - TOP_LEFT[1])

# Define RGB color ranges for opened and unopened cells
opened_lower = np.array([210, 210, 210])
opened_upper = np.array([230, 230, 225])

unopened_lower = np.array([176, 179, 172])
unopened_upper = np.array([196, 199, 192])

# Define RGB color ranges for numbers
NUMBER_COLORS = {
    1: ([210, 240, 180], [230, 255, 210]),  # Number 1: rgba(221,250,195,255)
    2: ([220, 225, 180], [245, 245, 210]),  # Number 2: rgba(236,237,191,255)
    3: ([220, 200, 170], [250, 230, 190]),  # Number 3: rgba(237,218,180,255)
    4: ([220, 180, 120], [250, 210, 150])   # Number 4: rgba(237,195,138,255)
}

DATA_COLLECTION_PATH = os.path.expanduser("~/minexseeper/data")
if not os.path.exists(DATA_COLLECTION_PATH):
    os.makedirs(DATA_COLLECTION_PATH)

DATA_FILE = os.path.join(DATA_COLLECTION_PATH, "minesweeper_data.csv")



def on_press(key):
    """
    Set the exit signal when the panic key (e.g., 'q') is pressed.
    """
    global exit_signal
    try:
        if key.char == 'q':  # Change 'q' to your preferred panic key
            print("Panic key pressed. Exiting...")
            exit_signal = True
    except AttributeError:
        pass


# Start a listener in a separate thread
listener = keyboard.Listener(on_press=on_press)
listener.start()


def locate_image(image_name, confidence=0.9):
    """
    Locate an image on the screen and return its position.
    """
    image_path = os.path.join(TEMPLATE_PATH, image_name)
    print(f"Looking for {image_path} with confidence {confidence}")
    try:
        location = pyautogui.locateOnScreen(image_path, confidence=confidence)
        if location:
            print(f"Found {image_name} at {location}")
        else:
            print(f"{image_name} not found.")
        return location
    except pyautogui.ImageNotFoundException:
        print(f"ImageNotFoundException: {image_name} not detected on screen.")
        return None


def click_location(location):
    """
    Click at the given location (x, y).
    """
    if location:
        pyautogui.click(location[0], location[1])
        time.sleep(0.2)
        return True
    return False


def flag_location(location):
    """
    Right-click at the given location to flag a cell as a bomb.
    """
    if location:
        pyautogui.rightClick(location[0], location[1])
        time.sleep(0.2)
        return True
    return False


def detect_cells(image, lower_bound, upper_bound):
    """
    Detect cells of a specific color range.
    Returns the center coordinates of detected regions.
    """
    hsv_image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    mask = cv2.inRange(hsv_image, lower_bound, upper_bound)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    centers = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        centers.append((TOP_LEFT[0] + x + w // 2, TOP_LEFT[1] + y + h // 2))
    return centers


def scan_board(region):
    """
    Scans the board for opened, unopened, flagged, and numbered cells.
    """
    screenshot = pyautogui.screenshot(region=region)
    board_image = np.array(screenshot)

    # Detect unopened and opened cells by color
    unopened_cells = detect_cells(board_image, unopened_lower, unopened_upper)
    opened_cells = detect_cells(board_image, opened_lower, opened_upper)

    # Detect numbered cells
    numbered_cells = detect_numbered_cells(board_image)

    # Initialize board state
    board_state = {cell: "unopened" for cell in unopened_cells}
    board_state.update({cell: "opened" for cell in opened_cells})
    board_state.update({cell: f"number_{number}" for cell, number in numbered_cells.items()})

    print(f"Detected numbered cells: {numbered_cells}")
    return board_state


def start_game():
    """
    Ensures the game is ready to play by clicking 'Play Again' or clicking an unopened cell
    if the game board is visible.
    """
    global exit_signal
    while not exit_signal:
        play_again_button = locate_image("cells/PlayAgainButton.png", confidence=0.7)
        unopened_cell = locate_image("buttons/UnOpenedCell.png", confidence=0.7)

        if play_again_button:
            print("Game not started. Clicking 'Play Again'.")
            click_location(pyautogui.center(play_again_button))
            time.sleep(1)  # Allow some time for the game to reset
        elif unopened_cell:
            print("Game board detected. Starting game by clicking an unopened cell.")
            click_location(pyautogui.center(unopened_cell))
            break
        else:
            print("Waiting for the game board or play button...")
            time.sleep(0.5)  # Retry after a short delay


def detect_game_over():
    """
    Detect if a bomb has been clicked by checking for the 'ClickedBomb' image.
    """
    clicked_bomb = locate_image("buttons/ClickedBomb.png", confidence=0.8)
    if clicked_bomb:
        print("Bomb clicked! Game over.")
        return True
    return False

def detect_numbered_cells(image):
    """
    Detect numbered cells and their corresponding values.
    Returns a dictionary of cell positions mapped to their number (e.g., {(x, y): 1}).
    """
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


def certain_bombs_logic(board_state):
    """
    Determine cells to flag as bombs based on simple logic.
    """
    bombs_to_flag = set()
    for cell, state in board_state.items():
        if state.startswith("number_"):
            number = int(state.split("_")[1])
            unopened_neighbors = [
                neighbor for neighbor in get_neighbors(cell)
                if board_state.get(neighbor) == "unopened"
            ]
            flagged_neighbors = [
                neighbor for neighbor in get_neighbors(cell)
                if board_state.get(neighbor) == "flagged"
            ]

            # Debugging neighbor states
            debug_neighbors(cell, board_state)

            print(f"Cell {cell} has number {number}, {len(unopened_neighbors)} unopened, "
                  f"{len(flagged_neighbors)} flagged neighbors.")

            # If unopened neighbors match remaining bombs, they are bombs
            if len(unopened_neighbors) + len(flagged_neighbors) == number:
                bombs_to_flag.update(unopened_neighbors)

    print(f"Bombs to flag: {bombs_to_flag}")
    return bombs_to_flag




def save_data_for_ai(board_state):
    """
    Save board state to CSV for AI training.
    """
    with open(DATA_FILE, mode='a', newline='') as file:
        writer = csv.writer(file)
        for cell, state in board_state.items():
            if state.startswith("number_"):
                number = int(state.split("_")[1])
                unopened_neighbors = count_neighbors(cell, board_state, "unopened")
                flagged_neighbors = count_neighbors(cell, board_state, "flagged")
                row = [cell[0], cell[1], number, unopened_neighbors, flagged_neighbors]
                writer.writerow(row)
        file.flush()  # Ensure data is written
    print("Data written to file successfully.")



def count_neighbors(cell, board_state, target_state):
    """
    Count the neighbors of a cell with a specific state.
    """
    x, y = cell
    neighbors = [
        (x + dx, y + dy)
        for dx, dy in [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
    ]
    return sum(1 for neighbor in neighbors if board_state.get(neighbor) == target_state)

def debug_neighbors(cell, board_state):
    """
    Debug the states of neighboring cells.
    """
    x, y = cell
    neighbors = [
        (x + dx, y + dy)
        for dx, dy in [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
    ]
    neighbor_states = {neighbor: board_state.get(neighbor, "unknown") for neighbor in neighbors}
    print(f"Neighbors of {cell}: {neighbor_states}")


def improved_logic(board_state):
    """
    Improved logic for determining which cells to click and flag.
    """
    bombs_to_flag = set()
    cells_to_click = set()

    for cell, state in board_state.items():
        if state.startswith("number_"):
            number = int(state.split("_")[1])
            unopened_neighbors = [
                neighbor for neighbor in get_neighbors(cell)
                if board_state.get(neighbor) == "unopened"
            ]
            flagged_neighbors = [
                neighbor for neighbor in get_neighbors(cell)
                if board_state.get(neighbor) == "flagged"
            ]

            # If all bombs are accounted for, mark the rest as safe
            if len(flagged_neighbors) == number:
                cells_to_click.update(unopened_neighbors)

            # If unopened neighbors equal the remaining bombs, flag them
            if len(unopened_neighbors) + len(flagged_neighbors) == number:
                bombs_to_flag.update(unopened_neighbors)

    return bombs_to_flag, cells_to_click


def get_neighbors(cell):
    """
    Get the neighboring cells of a given cell.
    """
    x, y = cell
    return [
        (x + dx, y + dy)
        for dx, dy in [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
    ]

def play_game_with_data(region):
    """
    Main gameplay loop with data collection and improved logic.
    """
    global exit_signal
    clicked_cells = set()
    flagged_cells = set()

    while not exit_signal:
        # Detect if the game is over
        if detect_game_over():
            print("Game over! Restarting...")
            start_game()
            clicked_cells.clear()
            flagged_cells.clear()
            continue

        print("Scanning board...")
        board_state = scan_board(region)
        print(f"Board state: {len(board_state)} cells detected.")

        # Save data for AI
        save_data_for_ai(board_state)

        # Apply flagging logic
        bombs_to_flag = certain_bombs_logic(board_state)
        for cell in bombs_to_flag:
            if cell not in flagged_cells:
                print(f"Flagging cell {cell} as a bomb.")
                if flag_location(cell):  # Ensure the flagging is successful
                    flagged_cells.add(cell)

        # Find safe cells to click
        unclicked_cells = [
            cell for cell, state in board_state.items()
            if state == "unopened" and cell not in clicked_cells and cell not in flagged_cells
        ]

        if unclicked_cells:
            next_cell = unclicked_cells[0]
            if click_location(next_cell):
                clicked_cells.add(next_cell)
                print(f"Clicked at {next_cell}.")
        else:
            print("No logical moves left. Waiting...")
            time.sleep(0.5)



if __name__ == "__main__":
    print("Starting Minesweeper automation with data collection...")
    while not exit_signal:
        start_game()
        play_game_with_data(BOARD_REGION)
    print("Exiting automation...")