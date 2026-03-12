# Project Report Update - Pinball Scoreboard (Raspberry Pi)

## 1) Goals achieved and outside resources used

### Goals achieved
- Built a working digital pinball scoreboard that runs in real time with Python + Pygame.
- Implemented core game flow:
  - Attract/start screen
  - Gameplay mode
  - Game-over screen
  - Service test mode
- Completed core scoring logic and progression:
  - Strike plate, bumper, goal, and drop-target scoring
  - "PIONEER" letter progression and mega jackpot behavior
  - Ball drain tracking and remaining-ball management
- Added persistent high score storage (`pinball_highscore.txt`).
- Integrated audio feedback (hit, bumper, jackpot, ambient loops).
- Added Raspberry Pi GPIO integration with safe fallback mock mode for non-Pi development.
- Added diagnostic/service tools in test mode:
  - Switch test
  - Solenoid test (with cooldown for safety)
  - Display test
  - Audio test
  - Basic system status (CPU temperature, uptime, load average)

### Outside resources used
- Official documentation:
  - Pygame documentation (graphics, events, audio, mixer channels)
  - gpiozero documentation (Button/DigitalOutputDevice usage and debounce settings)
  - Python documentation (threading, file I/O, exception handling)
- Raspberry Pi/Linux references:
  - `vcgencmd` usage for temperature checks
  - Raspberry Pi GPIO wiring and pin reference materials
- Team support resources:
  - Mentor and instructor feedback for implementation checks and project-direction guidance

---

## 2) Leadership and collaboration (LOW)

Collaboration level for this period is **LOW**, but there were consistent communication touchpoints:

- Attended team check-ins and recorded meeting minutes for task tracking.
- Sent short progress/risk updates to mentor and instructor (status, blockers, next steps).
- Offered targeted support to teammates when hardware/software integration questions came up.

Evidence style for submission:
- Meeting minutes (date, attendees, decisions, action items)
- Email updates to mentor/instructor (summary, blockers, asks, next-step commitments)

---

## 3) What is next? Task summary

### Immediate next tasks
1. Validate full gameplay on physical hardware for longer sessions (stability + switch reliability).
2. Tune gameplay values (point values, cooldown timings, jackpot/reset behavior).
3. Improve error handling for missing assets and audio initialization edge cases.
4. Clean project packaging/setup:
   - Fix dependency file naming and dependency list quality
   - Add clear run instructions for both Raspberry Pi and non-Pi mock mode
5. Add lightweight automated checks for scoring/state transitions where possible.

### Short-term outcomes expected
- More reliable hardware behavior during demos
- Cleaner onboarding for new contributors
- Better maintainability through clearer validation and documentation

---

## 4) Additional task: poster draft

A poster draft tailored to this project is provided in:

- `POSTER_DRAFT.md`

It includes ready-to-use sections for problem statement, architecture, implementation highlights, current results, collaboration notes, and future work.
