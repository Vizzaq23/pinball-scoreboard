# Pinball Scoreboard (Raspberry Pi)

A simple digital scoring screen for a custom-built pinball machine.  
Runs on a Raspberry Pi and outputs to any HDMI monitor.  

## Features
- Displays current score
- Updates in real-time when targets are hit
- Simulated input via keyboard (replaceable with GPIO for real machine)
- Built with Python + Pygame

## Setup

1. Clone the repo:
   ```bash
   git clone https://github.com/Vizzaq23/pinball-scoreboard.git
   cd pinball-scoreboard
   ```

2. Create and activate a virtual environment (recommended):
   ```bash
   python -m venv .venv
   .venv\Scripts\activate   # Windows
   # source .venv/bin/activate   # Linux / Raspberry Pi
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

   **Dependencies:** `pygame` (display and audio), `gpiozero` (GPIO on Raspberry Pi).

4. Ensure the `assets` folder contains the required files:
   - **Images:** `icerink.png`, `jumboT.png`
   - **Sounds:** `hit.wav`, `bumper.wav`, `jackpot.wav`, `hockey_theme.wav`, `hockey_theme1.wav`

## Run

- **Main game (attract mode + gameplay):**
  ```bash
  python game.py
  ```

- **Test / diagnostics mode** (optional):
  ```bash
  python test_mode.py
  ```

- **Solenoid test** (optional, for hardware check):
  ```bash
  python test_solenoid.py
  ```
  On Windows or when GPIO is not available, this script will report that `USE_GPIO` is False.

## Keyboard controls (development / testing)

When running without Raspberry Pi hardware, the game uses **mock GPIO** and you can simulate inputs with the keyboard:

| Key | Action |
|-----|--------|
| **Enter** | Start game (from attract) / trigger strike plate hit during gameplay |
| **F9** | Enter Test Mode (service/diagnostics) from attract screen |
| **Space** | Bumper 2 hit |
| **T** | Strike plate / target hit |
| **G** | Goal sensor (advance PIONEER, jackpot) |
| **B** | Ball drain (lose a ball) |
| **R** | Reset score and balls (restart current game) |
| **D** | Toggle debug overlay (jumbotron grid) |

Close the window or quit the app to exit.

## Raspberry Pi vs Windows

- **On Raspberry Pi** (with GPIO available): The game uses real hardware—buttons, bumpers, drop targets, goal sensor, ball drain, and solenoids. The service button enters Test Mode.
- **On Windows or other platforms**: GPIO is not available, so the game runs in **mock mode**. Use the keyboard controls above to simulate hits and test the scoreboard.
