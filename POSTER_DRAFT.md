# Poster Draft - SHU Pioneer Arena Pinball Scoreboard

## Title
**SHU Pioneer Arena: Real-Time Raspberry Pi Pinball Scoreboard**

## Team / Course Info
- Team: [Add names]
- Course: [Add course name/number]
- Mentor: [Add mentor name]
- Instructor: [Add instructor name]
- Term: [Add term]

---

## 1) Problem Statement
Traditional custom pinball builds often lack a flexible digital scoreboard and diagnostics workflow.  
We needed a low-cost, real-time scoring display that could integrate with physical hardware and still be testable without full GPIO access.

## 2) Project Objectives
- Build a real-time digital scoreboard for a custom pinball machine.
- Integrate Raspberry Pi GPIO inputs/outputs for switches and solenoids.
- Provide safe, testable software behavior in both hardware and mock environments.
- Add service diagnostics for maintenance and troubleshooting.

## 3) System Overview
**Software stack**
- Python
- Pygame (rendering, event loop, audio)
- gpiozero (Raspberry Pi hardware interface)

**Architecture modules**
- `game.py`: main loop, scoring, states, rendering
- `hardware.py`: GPIO devices + mock fallback + solenoid control
- `audio.py`: sound effects + ambient audio channels
- `test_mode.py`: switch/solenoid/display/audio/system diagnostics
- `assets.py`: image/sound/font loading helpers

## 4) Core Features Implemented
- Live score display on HDMI monitor
- Multi-state flow (attract, gameplay, test mode, game over)
- Scoring events:
  - strike plate
  - bumpers
  - goal sensor
  - drop-target bank + jackpot reset
- High score persistence
- Audio effects and ambient loops
- Solenoid pulse control with safety timing
- Service diagnostics with keyboard navigation

## 5) Current Results
- Functional playable scoring prototype is complete.
- GPIO-safe design supports:
  - real hardware operation on Raspberry Pi
  - software-only mock testing off-device
- Test mode reduces troubleshooting time for switches, solenoids, display, and audio checks.

## 6) Leadership and Collaboration (LOW)
- Participation level: **LOW**
- Collaboration contributions:
  - maintained meeting minutes
  - sent progress emails to mentor and instructor
  - shared blockers and requested guidance when needed

## 7) Challenges
- Hardware timing/debounce tuning for reliable hit detection
- Balancing software responsiveness with safe solenoid control
- Ensuring stable behavior across Raspberry Pi and non-Pi environments

## 8) Next Steps
- Perform longer on-device reliability testing and tune cooldown values.
- Improve setup/deployment documentation and dependency management.
- Add automated checks for core state and scoring logic.
- Refine visual polish and final UX for demo readiness.

## 9) Impact / Takeaways
- Demonstrates a practical embedded-software pipeline from hardware signals to real-time visual feedback.
- Shows maintainable separation of concerns (game logic, hardware I/O, diagnostics, assets).
- Establishes a base for future expansion (multiball rules, richer animations, analytics).

## 10) Poster Visuals to Add
- System diagram (switches -> GPIO -> game logic -> display/audio/solenoids)
- Gameplay screenshot (score + PIONEER indicators)
- Test mode screenshot (switch and solenoid diagnostics)
- Table of scoring events and point values

---

## References (for poster footer)
- Pygame Documentation: https://www.pygame.org/docs/
- gpiozero Documentation: https://gpiozero.readthedocs.io/
- Python Documentation: https://docs.python.org/3/
