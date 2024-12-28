# **Minesweeper AI: BombSquadron**

Welcome to **BombSquadron**, a cutting-edge machine learning project aimed at mastering Minesweeper! Designed for GNOME Mines and developed on **Arch Linux** with **PyCharm JetBrains**, this project explores AI-driven gameplay with a focus on achieving a high win rate in Minesweeper games.

---

## **Project Overview**

The ultimate goal of BombSquadron is to create a robust AI capable of consistently solving Minesweeper puzzles. In the current phase, the focus is on:
- Automating gameplay with logic-based heuristics.
- Collecting detailed game state data to train machine learning models.
- Developing AI strategies to minimize random guesses and optimize win rates.

Here is a video demonstration:

https://github.com/user-attachments/assets/b9e75409-8132-49ba-a01f-8452ed0c5ff1

tion:


---

## **Features**

### **Game Automation**
- **PyAutoGUI Integration**: Simulates clicks and interacts with the GNOME Mines GUI.
- **Dynamic Board Detection**: Locates and adapts to game boards, even if the window is moved or resized.
- **Cell State Analysis**: Uses image processing and predefined color ranges to identify cell states (e.g., opened, unopened, numbered).

### **Data Collection**
- **CSV Logging**: Captures board states, cell interactions, and logical deductions.
- **Custom Templates**: Supports adaptive gameplay across different board difficulties and sizes.

### **Heuristic Logic**
- Identifies bombs and safe cells based on Minesweeper rules.
- Flags bombs and clicks safe cells automatically.
- Falls back to random guesses when logical deductions are exhausted.

---

## **Requirements**

### **Operating System**
- Linux

### **Python Packages**
- `pyautogui`
- `pynput`
- `opencv-python`
- `numpy`
- `Pillow`
- `csv`

### **Development Environment**
- **PyCharm JetBrains**: Recommended IDE for streamlined Python development.

---


## **Usage**

### **Start Automation**
- Launch GNOME Mines and position the window on your screen.
- Run and watch as it plays Minesweeper autonomously.

### **Key Features**
- **`q` Key**: Press to exit the program gracefully.
- Automatic restart upon game-over detection.

---

## **Data Collection**

BombSquadron logs every interaction and deduction into a CSV file, which can be used for:
- Training supervised machine learning models.
- Analyzing decision-making patterns.
- Refining AI logic.

The collected data includes:
- Cell coordinates.
- Numbers on opened cells.
- Counts of unopened and flagged neighbors.
- Logical deductions (e.g., bombs flagged, safe cells clicked).

---

## **Future Plans**

1. **Machine Learning Integration**:
   - Train AI models on collected data to predict bomb locations.
   - Implement reinforcement learning for self-improving gameplay.

2. **Advanced Logic**:
   - Develop probabilistic models to reduce guesswork.
   - Enhance pattern recognition for complex board scenarios.

3. **Performance Optimization**:
   - Minimize runtime delays and maximize move efficiency.
   - Optimize image processing pipelines for real-time analysis.

---

## **Acknowledgments**

Special thanks to:
- The GNOME Mines development team for providing a challenging game environment.
- The Arch Linux community for a reliable and customizable OS.
- JetBrains for creating the amazing PyCharm IDE.

---

Embark on the journey to Minesweeper mastery with **BombSquadron**—a fusion of logic, automation, and AI ingenuity!

