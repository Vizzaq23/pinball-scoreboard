# Pinball Scoreboard – Demo Script

Short steps to demonstrate the SHU Pioneer Arena pinball scoreboard for a capstone or presentation.

## Prerequisites

- Run from project root: `python game.py`
- On Windows/without Pi: use keyboard to simulate inputs (see README).

## Demo flow

1. **Attract mode**
   - App shows “SHU PIONEER PINBALL”, high score, and “PRESS ENTER TO START” (blinking).
   - Optional: press **F9** to show Test Mode, then exit test mode to return to attract.

2. **Start game**
   - Press **Enter**.
   - Brief fade, then gameplay view: rink, jumbotron, score 0, PIONEER letters, Balls: 2.

3. **Hit targets (keyboard simulation)**
   - **T** – strike plate hit (score +500, “hit” sound).
   - **Space** – bumper 2 (score +100, bumper sound).
   - **G** – goal sensor (score +2000, advance one PIONEER letter, jackpot sound; popper fires on hardware).
   - Press **G** seven times to light all PIONEER letters and trigger **MEGA JACKPOT** (+10,000); letters reset.

4. **Ball drain and game over**
   - Press **B** to simulate ball drain (lose one ball).
   - Press **B** again to drain the second ball → **Game Over** screen (final score, high score, “PRESS ENTER TO RESTART”).

5. **Restart**
   - Press **Enter** to return to attract mode; press **Enter** again to start a new game.

6. **Test Mode (optional)**
   - From attract, press **F9**.
   - Test Mode shows switch states and solenoid tests; use on-screen prompts to test hardware or sounds. Exit to return to attract.

## On Raspberry Pi

Same flow; use physical switches/sensors instead of keyboard (strike plate, bumpers, drop targets, goal sensor, ball drain). Service button enters Test Mode.
