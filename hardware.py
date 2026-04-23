# hardware.py - GPIO inputs and outputs for Raspberry Pi pinball hardware.
# Falls back to mocks when GPIO is not available (e.g. on Windows).

import atexit
import threading
import time
from typing import Any

# Serialize coil pulses so two drivers never energize at once (power / thermal headroom).
_solenoid_lock = threading.Lock()

# Drop targets: True = gpiozero "pressed" is closed when the target is physically DOWN.
# Set to False if your hardware reads pressed when targets are UP (your current behavior).
DROP_TARGET_PRESSED_WHEN_DOWN = False

# SWITCH TEST reads target1/2/3 with col OFF. Gameplay used to turn COL_PIN on for the whole poll,
# which can change opto readings so "all down" never matches. Default False = same as test mode.
# Set True only if your board needs GPIO COL_PIN high to power IR emitters while reading.
DROP_TARGET_USE_COL_FOR_READ = False
DROP_TARGET_COL_SETTLE_S = 0.005

# Coil driver polarity. Typical MOSFET gate drivers are active-high:
# - gate.off() drives LOW (coil de-energized)
# - gate.on() drives HIGH (coil energized)
# Using active_low here can keep a coil energized in the "off" state.
POPPER_GATE_ACTIVE_HIGH = True

# ---------------------------------------------------------------------------
# GPIO setup (cross-platform safe)
# ---------------------------------------------------------------------------
try:
    from gpiozero import Button, DigitalOutputDevice
    print("GPIO detected: running on Raspberry Pi hardware.")

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
    # ---------------------------------------------
    TARGET1_PIN = 12
    TARGET2_PIN = 13
    TARGET3_PIN = 16
    # Start button uses 19; column IR was moved to 27 (see START_BUTTON_PIN).
    COL_PIN = 27  # optional: drives common IR LED column

    target1 = Button(TARGET1_PIN, pull_up=True, bounce_time=0.1)
    target2 = Button(TARGET2_PIN, pull_up=True, bounce_time=0.1)
    target3 = Button(TARGET3_PIN, pull_up=True, bounce_time=0.1)

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

    # Popper / goal solenoid that fires when jackpot sensor (goal_sensor) is hit
    # to pop the ball up to a ramp. The "goal gate" uses the same physical coil.
    POPPER_GATE = 11
    popper_gate = DigitalOutputDevice(
        POPPER_GATE, active_high=POPPER_GATE_ACTIVE_HIGH, initial_value=False
    )
    # Explicitly ensure gate is OFF immediately after initialization
    popper_gate.off()

    # Ball‑kicker solenoid that launches a new ball from the trough
    # when the ball drain switch is triggered.
    BALL_KICKER_PIN = 18
    ball_kicker_gate = DigitalOutputDevice(
        BALL_KICKER_PIN, active_high=True, initial_value=False
    )
    ball_kicker_gate.off()

    # Dedicated service button to enter TEST MODE (optional hardware)
    # Wire a momentary switch between this pin and GND.
    SERVICE_BUTTON_PIN = 14
    service_button = Button(SERVICE_BUTTON_PIN, pull_up=True, bounce_time=0.15)

    # Start game from attract / restart after game over (optional hardware)
    # Wire a momentary switch between this pin and GND (same wiring as service button).
    START_BUTTON_PIN = 19
    start_button = Button(START_BUTTON_PIN, pull_up=True, bounce_time=0.15)

    # BCM numbers for all N-MOS / coil gate outputs (kept off the bus at process exit).
    _OUTPUT_BCM_PINS = (
        BUMPER1_GATE,
        BUMPER2_GATE,
        COL_PIN,
        JACKPOT_RESET_GATE,
        POPPER_GATE,
        BALL_KICKER_PIN,
    )

    USE_GPIO = True

except Exception as e:
    print(f"GPIO not available ({e}). Using mock mode for testing.")
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
    start_button = MockButton()

    gate1 = MockGate()
    gate2 = MockGate()
    col = MockGate()
    jackpot_gate = MockGate()
    popper_gate = MockGate()
    ball_kicker_gate = MockGate()

    _OUTPUT_BCM_PINS = ()


# ---------------------------------------------------------------------------
# gpiozero exit: keep coil gates low (see _patch_gpiozero_atexit_for_coil_pins)
# ---------------------------------------------------------------------------


def _drive_coil_pins_low_after_gpiozero() -> None:
    """After gpiozero releases pins, drive BCM outputs low so MOSFET gates do not float on.

    Floating lines often read high enough to keep an N-channel gate on (e.g. bumper 1 / GPIO 5).
    Uses RPi.GPIO after gpiozero teardown; omits GPIO.cleanup() so lines stay outputs at LOW
    until the process exits (kernel may still reclaim them). If this fails, add ~10k pull-downs
    on each gate at the board.
    """
    if not USE_GPIO or not _OUTPUT_BCM_PINS:
        return
    try:
        import RPi.GPIO as GPIO  # type: ignore[import-not-found]

        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        for pin in _OUTPUT_BCM_PINS:
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, GPIO.LOW)
    except Exception:
        pass


def _patch_gpiozero_atexit_for_coil_pins() -> None:
    """Wrap gpiozero's atexit so process exit does not leave coil pins floating high."""
    if not USE_GPIO:
        return
    try:
        from gpiozero import devices as gz_devices
    except ImportError:
        return

    orig = gz_devices._shutdown
    try:
        atexit.unregister(orig)
    except ValueError:
        return

    def _shutdown_with_coil_pins_held_low() -> None:
        orig()
        _drive_coil_pins_low_after_gpiozero()

    atexit.register(_shutdown_with_coil_pins_held_low)


_patch_gpiozero_atexit_for_coil_pins()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def initialize_all_gates() -> None:
    """Ensure all solenoid gates are off (safe state at startup)."""
    if USE_GPIO:
        gate1.off()
        gate2.off()
        col.off()
        jackpot_gate.off()
        popper_gate.off()
        ball_kicker_gate.off()


def pulse_solenoid(gate: Any, pulse_time: float) -> None:
    """Turn gate on for pulse_time seconds, then off."""
    with _solenoid_lock:
        gate.on()
        time.sleep(pulse_time)
        gate.off()
