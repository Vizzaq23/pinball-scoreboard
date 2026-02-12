# test_mode.py - Service / diagnostics (TEST MODE) for pinball scoreboard.

import os
import time
import threading
from dataclasses import dataclass

import pygame

from audio import play_sound
from hardware import (
    targets_any,
    bumper1,
    bumper2,
    gate1,
    gate2,
    target1,
    target2,
    target3,
    goal_sensor,
    ball_drain,
    jackpot_gate,
    pulse_solenoid,
)


# ============================================================
# TEST MODE CONSTANTS
# ============================================================

TEST_SOLENOID_PULSE_TIME = 0.08  # short, safe pulse
TEST_SOLENOID_COOLDOWN = 0.5    # minimum delay between fires (per solenoid)
TEST_VOLUME_STEP = 0.1

SWITCH_LIST = [
    ("Strike Plate", targets_any),
    ("Bumper 1", bumper1),
    ("Bumper 2", bumper2),
    ("Drop Target 1", target1),
    ("Drop Target 2", target2),
    ("Drop Target 3", target3),
    ("Goal Sensor", goal_sensor),
    ("Ball Drain", ball_drain),
]

SOLENOID_LIST = [
    ("Gate 1 (Bumper 1)", gate1),
    ("Gate 2 (Bumper 2)", gate2),
    ("Jackpot Reset", jackpot_gate),
]

TEST_SOUND_NAMES = ["hit", "bumper", "jackpot"]

# Display
FPS = 60
HEADER_Y = 40
SUBTITLE_Y = 80
COLOR_HEADER = (255, 255, 0)
COLOR_SUBTITLE = (200, 200, 200)
COLOR_ACTIVE = (0, 255, 0)
COLOR_INACTIVE = (200, 0, 0)
COLOR_SELECTED = (255, 255, 0)
COLOR_NORMAL = (220, 220, 220)
COLOR_FOOTER = (220, 220, 220)
COLOR_WHITE = (255, 255, 255)
DISPLAY_PATTERN_COLORS = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 255)]
OVERLAY_ALPHA = 160

# ============================================================
# CONTEXT
# ============================================================


@dataclass
class TestModeContext:
    """Display and asset handles needed to draw test mode screens."""

    screen: pygame.Surface
    clock: pygame.time.Clock
    width: int
    height: int
    rink_img: pygame.Surface
    jumbo_img: pygame.Surface
    jumbo_x: int
    jumbo_y: int
    small_font: pygame.font.Font
    medium_font: pygame.font.Font
    program_start_time: float


# ============================================================
# HELPERS
# ============================================================


def _blit_centered(ctx: TestModeContext, surface: pygame.Surface, y: int) -> None:
    """Blit surface onto ctx.screen horizontally centered at y."""
    x = ctx.width // 2 - surface.get_width() // 2
    ctx.screen.blit(surface, (x, y))


def _draw_header(ctx: TestModeContext, title: str, subtitle: str = "") -> None:
    """Draw the standard TEST MODE header and optional subtitle."""
    ctx.screen.blit(ctx.rink_img, (0, 0))
    ctx.screen.blit(ctx.jumbo_img, (ctx.jumbo_x, ctx.jumbo_y))
    header = ctx.medium_font.render(f"TEST MODE - {title}", True, COLOR_HEADER)
    _blit_centered(ctx, header, HEADER_Y)
    if subtitle:
        sub = ctx.small_font.render(subtitle, True, COLOR_SUBTITLE)
        _blit_centered(ctx, sub, SUBTITLE_Y)


def _get_cpu_temperature() -> str:
    """Best-effort CPU temperature readout (Raspberry Pi). Returns e.g. '47.8 C' or 'N/A'."""
    try:
        out = os.popen("vcgencmd measure_temp").read().strip()
        if out.startswith("temp="):
            value = out.split("=", 1)[1].split("'")[0]
            float(value)
            return f"{value} C"
    except Exception:
        pass
    return "N/A"


def _format_uptime(program_start_time: float) -> str:
    seconds = int(time.time() - program_start_time)
    mins, secs = divmod(seconds, 60)
    hours, mins = divmod(mins, 60)
    return f"{hours:02d}:{mins:02d}:{secs:02d}"


# ============================================================
# MAIN LOOP
# ============================================================


def run_test_mode(ctx: TestModeContext) -> None:
    """Main loop for TEST MODE (service/diagnostics).

    - Isolated from gameplay scoring / progression.
    - Navigable with keyboard arrows or physical bumper buttons.
    - Caller is responsible for setting current_mode before/after.
    """
    screens = ["SWITCH TEST", "SOLENOID TEST", "DISPLAY TEST", "AUDIO TEST", "SYSTEM STATUS"]
    screen_index = 0
    solenoid_index = 0
    sound_index = 0
    display_pattern = 0
    test_volume = 1.0
    last_solenoid_fire = {i: 0.0 for i in range(len(SOLENOID_LIST))}

    running = True
    while running:
        now = time.time()

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit

            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    return

                if e.key == pygame.K_LEFT:
                    screen_index = (screen_index - 1) % len(screens)
                elif e.key == pygame.K_RIGHT:
                    screen_index = (screen_index + 1) % len(screens)

                if screens[screen_index] == "SOLENOID TEST":
                    if e.key == pygame.K_UP:
                        solenoid_index = (solenoid_index - 1) % len(SOLENOID_LIST)
                    elif e.key == pygame.K_DOWN:
                        solenoid_index = (solenoid_index + 1) % len(SOLENOID_LIST)
                    elif e.key in (pygame.K_SPACE, pygame.K_RETURN):
                        last = last_solenoid_fire[solenoid_index]
                        if now - last >= TEST_SOLENOID_COOLDOWN:
                            name, gate = SOLENOID_LIST[solenoid_index]
                            print(f"[TEST] Firing solenoid: {name}")
                            threading.Thread(
                                target=pulse_solenoid,
                                args=(gate, TEST_SOLENOID_PULSE_TIME),
                                daemon=True,
                            ).start()
                            last_solenoid_fire[solenoid_index] = now

                elif screens[screen_index] == "AUDIO TEST":
                    if e.key == pygame.K_UP:
                        test_volume = min(1.0, test_volume + TEST_VOLUME_STEP)
                        pygame.mixer.music.set_volume(test_volume)
                    elif e.key == pygame.K_DOWN:
                        test_volume = max(0.0, test_volume - TEST_VOLUME_STEP)
                        pygame.mixer.music.set_volume(test_volume)
                    elif e.key == pygame.K_LEFT:
                        sound_index = (sound_index - 1) % len(TEST_SOUND_NAMES)
                    elif e.key == pygame.K_RIGHT:
                        sound_index = (sound_index + 1) % len(TEST_SOUND_NAMES)
                    elif e.key in (pygame.K_SPACE, pygame.K_RETURN):
                        sound_name = TEST_SOUND_NAMES[sound_index]
                        print(f"[TEST] Playing sound: {sound_name} (vol={test_volume:.2f})")
                        play_sound(sound_name)

                elif screens[screen_index] == "DISPLAY TEST":
                    if e.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_SPACE):
                        display_pattern = (display_pattern + 1) % 4

        # ---- Render ----
        current_title = screens[screen_index]

        if current_title == "SWITCH TEST":
            _draw_header(ctx, "SWITCH TEST", "Activate any switch to see its state.")
            y = 140
            for name, btn in SWITCH_LIST:
                active = getattr(btn, "is_pressed", False)
                state_text = "ACTIVE" if active else "INACTIVE"
                color = COLOR_ACTIVE if active else COLOR_INACTIVE
                label = ctx.small_font.render(f"{name:>14}: {state_text}", True, color)
                _blit_centered(ctx, label, y)
                y += 30

        elif current_title == "SOLENOID TEST":
            _draw_header(
                ctx,
                "SOLENOID TEST",
                "UP/DOWN to select, SPACE/ENTER to fire (safety cooldown).",
            )
            y = 150
            for idx, (name, _gate) in enumerate(SOLENOID_LIST):
                prefix = ">" if idx == solenoid_index else " "
                color = COLOR_SELECTED if idx == solenoid_index else COLOR_NORMAL
                label = ctx.small_font.render(f"{prefix} {name}", True, color)
                _blit_centered(ctx, label, y)
                y += 32

        elif current_title == "DISPLAY TEST":
            _draw_header(ctx, "DISPLAY TEST", "SPACE/ARROWS to cycle patterns. ESC to exit.")
            overlay_color = DISPLAY_PATTERN_COLORS[display_pattern]
            overlay = pygame.Surface((ctx.width, ctx.height), pygame.SRCALPHA)
            overlay.fill((*overlay_color, OVERLAY_ALPHA))
            ctx.screen.blit(overlay, (0, 0))
            bar_y = ctx.height - 80
            for i in range(0, ctx.width, 10):
                level = int(255 * (i / ctx.width))
                pygame.draw.rect(ctx.screen, (level, level, level), (i, bar_y, 10, 40))

        elif current_title == "AUDIO TEST":
            _draw_header(
                ctx,
                "AUDIO TEST",
                "LEFT/RIGHT to pick sound, UP/DOWN volume, SPACE/ENTER to play.",
            )
            y = 160
            for idx, name in enumerate(TEST_SOUND_NAMES):
                prefix = ">" if idx == sound_index else " "
                color = COLOR_SELECTED if idx == sound_index else COLOR_NORMAL
                label = ctx.small_font.render(f"{prefix} {name}", True, color)
                _blit_centered(ctx, label, y)
                y += 32
            vol_label = ctx.small_font.render(f"Volume: {test_volume:.2f}", True, COLOR_WHITE)
            _blit_centered(ctx, vol_label, y + 20)

        elif current_title == "SYSTEM STATUS":
            _draw_header(ctx, "SYSTEM STATUS", "Basic Raspberry Pi health.")
            cpu_temp = _get_cpu_temperature()
            uptime = _format_uptime(ctx.program_start_time)
            try:
                load1, load5, load15 = os.getloadavg()
                load_text = f"Load avg (1/5/15): {load1:.2f}, {load5:.2f}, {load15:.2f}"
            except (AttributeError, OSError):
                load_text = "Load avg: N/A"
            lines = [f"CPU Temp: {cpu_temp}", f"Uptime: {uptime}", load_text]
            y = 150
            for line in lines:
                label = ctx.small_font.render(line, True, COLOR_WHITE)
                _blit_centered(ctx, label, y)
                y += 30

        footer = ctx.small_font.render(
            "LEFT/RIGHT = Change Screen   ESC = Exit Test Mode",
            True,
            COLOR_FOOTER,
        )
        _blit_centered(ctx, footer, ctx.height - 40)

        pygame.display.flip()
        ctx.clock.tick(FPS)
