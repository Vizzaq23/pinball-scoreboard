# hardware.py
import time

# --- GPIO SETUP (cross-platform safe) ---
try:
    from gpiozero import Button, DigitalOutputDevice
    print("✅ GPIO detected: running on Raspberry Pi hardware.")

    # -----------------------------
    # STRIKE PLATE / MAIN TARGET
    # -----------------------------
    # Equivalent to a "standup" switch in the playfield.
    targets_any = Button(17, pull_up=True, bounce_time=0.15)

    # -----------------------------
    # BUMPERS (2 inputs + 2 gates)
    # -----------------------------
    BUMPER1_PIN = 22
    BUMPER2_PIN = 23
    BUMPER1_GATE = 5
    BUMPER2_GATE = 6


    bumper1 = Button(BUMPER1_PIN, pull_up=True, bounce_time=0.1)
    bumper2 = Button(BUMPER2_PIN, pull_up=True, bounce_time=0.1)

    # Initialize bumper solenoid gates with explicit OFF state
    # to prevent firing on boot.
    gate1 = DigitalOutputDevice(BUMPER1_GATE, active_high=True, initial_value=False)
    gate2 = DigitalOutputDevice(BUMPER2_GATE, active_high=True, initial_value=False)
    # Explicitly ensure gates are OFF immediately after initialization
    gate1.off()
    gate2.off()

    # ---------------------------------------------
    # 3‑TARGET DROP BANK (for JACKPOT sequence)
    #
    # Mapping vs. Arduino sketch:
    # - TARGET1_PIN/2/3 ~= rowPins[] (three opto receivers / switches)
    # - COL_PIN / col   ~= colPin    (IR LED column drive, if used)
    # The game logic that waits for all three down and fires the
    # reset solenoid lives in game.py (on_drop_target_hit / jackpot_gate).
    # ---------------------------------------------
    TARGET1_PIN = 12
    TARGET2_PIN = 13
    TARGET3_PIN = 16
    COL_PIN = 19  # optional: drives common IR LED column

    target1 = Button(TARGET1_PIN, pull_up=True, bounce_time=0.1)
    target2 = Button(TARGET2_PIN, pull_up=True, bounce_time=0.1)
    target3 = Button(TARGET3_PIN, pull_up=True, bounce_time=0.1)

    # Column driver for the opto LEDs on the drop‑target bank.
    # If your A‑13609 board has its IR LEDs powered from 5V directly,
    # you may leave this effectively unused; if instead you run the
    # column from a GPIO‑controlled transistor, this is the control line.
    col = DigitalOutputDevice(
        COL_PIN,
        active_high=True,
        initial_value=False,
    )
    col.off()

    # GOAL SENSOR BEHIND THE DROP TARGETS
    GOAL_PIN = 20
    goal_sensor = Button(GOAL_PIN, pull_up=True, bounce_time=0.15)


    BALL_DRAIN_PIN = 24
    ball_drain = Button(BALL_DRAIN_PIN, pull_up=True, bounce_time=0.1)

    # Solenoid to reset the drop‑target bank (used by game.py when
    # all three drop targets are down).
    JACKPOT_RESET_GATE = 26
    jackpot_gate = DigitalOutputDevice(
        JACKPOT_RESET_GATE, active_high=True, initial_value=False
    )
    # Explicitly ensure gate is OFF immediately after initialization
    jackpot_gate.off()

    # Dedicated service button to enter TEST MODE (optional hardware)
    # Wire a momentary switch between this pin and GND.
    SERVICE_BUTTON_PIN = 21
    service_button = Button(SERVICE_BUTTON_PIN, pull_up=True, bounce_time=0.15)

    USE_GPIO = True

except Exception as e:
    print(f"⚠️ GPIO not available ({e}). Using mock mode for testing.")
    USE_GPIO = False

    class MockButton:
        @property
        def is_pressed(self): 
            return False
        def close(self): 
            pass

    class MockGate:
        def on(self): 
            pass
        def off(self): 
            pass
        def close(self): 
            pass

    # Mock versions
    targets_any = MockButton()
    bumper1 = MockButton()
    bumper2 = MockButton()
    target1 = MockButton()
    target2 = MockButton()
    target3 = MockButton()
    goal_sensor = MockButton()
    ball_drain = MockButton()
    service_button = MockButton()

    gate1 = MockGate()
    gate2 = MockGate()
    col = MockGate()
    jackpot_gate = MockGate()


# --- INITIALIZATION FUNCTION ---
def initialize_all_gates():
    
    if USE_GPIO:
        gate1.off()
        gate2.off()
        col.off()
        jackpot_gate.off()
        print(" All solenoid gates initialized to OFF state")


# --- SOLENOID PULSE FUNCTION ---
def pulse_solenoid(gate, pulse_time):
    print(f"[SOLENOID] ON {gate} for {pulse_time}s")
    gate.on()
    time.sleep(pulse_time)
    gate.off()
    print(f"[SOLENOID] OFF {gate}")
