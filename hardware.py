# hardware.py
import time

# --- GPIO SETUP (cross-platform safe) ---
try:
    from gpiozero import Button, DigitalOutputDevice
    print("✅ GPIO detected: running on Raspberry Pi hardware.")

    # STRIKE PLATE
    targets_any = Button(17, pull_up=True, bounce_time=0.15)

    # BUMPERS (2 inputs + 2 solenoid gates)
    BUMPER1_PIN = 22
    BUMPER2_PIN = 23
    BUMPER1_GATE = 5
    BUMPER2_GATE = 6

    bumper1 = Button(BUMPER1_PIN, pull_up=True, bounce_time=0.1)
    bumper2 = Button(BUMPER2_PIN, pull_up=True, bounce_time=0.1)
    gate1 = DigitalOutputDevice(BUMPER1_GATE, active_high=True, initial_value=False)
    gate2 = DigitalOutputDevice(BUMPER2_GATE, active_high=True, initial_value=False)

    # ---------------------------------------------
    # 4 TARGET DROP BANK (for JACKPOT sequence)
    # ---------------------------------------------
    TARGET1_PIN = 12
    TARGET2_PIN = 13
    TARGET3_PIN = 16
    TARGET4_PIN = 19

    target1 = Button(TARGET1_PIN, pull_up=True, bounce_time=0.1)
    target2 = Button(TARGET2_PIN, pull_up=True, bounce_time=0.1)
    target3 = Button(TARGET3_PIN, pull_up=True, bounce_time=0.1)
    target4 = Button(TARGET4_PIN, pull_up=True, bounce_time=0.1)

    # GOAL SENSOR BEHIND THE TARGETS
    GOAL_PIN = 20
    goal_sensor = Button(GOAL_PIN, pull_up=True, bounce_time=0.15)

    # BALL DRAIN / TROUGH SENSOR
    # Wire one side of the switch to GND, the other to this pin.
    # With pull_up=True:
    #   - ball sitting in drain (switch closed)  → LOW  → is_pressed = True
    #   - no ball (switch open)                  → HIGH → is_pressed = False
    BALL_DRAIN_PIN = 24
    ball_drain = Button(BALL_DRAIN_PIN, pull_up=True, bounce_time=0.1)

    # Solenoid to reset the drop target bank
    JACKPOT_RESET_GATE = 26
    jackpot_gate = DigitalOutputDevice(JACKPOT_RESET_GATE, active_high=True, initial_value=False)

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
    target4 = MockButton()
    goal_sensor = MockButton()
    ball_drain = MockButton()

    gate1 = MockGate()
    gate2 = MockGate()
    jackpot_gate = MockGate()


# --- SOLENOID PULSE FUNCTION ---
def pulse_solenoid(gate, pulse_time):
    print(f"[SOLENOID] ON {gate} for {pulse_time}s")
    gate.on()
    time.sleep(pulse_time)
    gate.off()
    print(f"[SOLENOID] OFF {gate}")
