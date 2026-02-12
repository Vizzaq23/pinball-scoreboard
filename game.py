# game.py - SHU Pioneer Arena pinball scoreboard main game loop.
"""Attract mode, gameplay, high score, and hardware polling. Test/diagnostics live in test_mode.py."""

import os
import sys
import time
import threading
from enum import Enum, auto
import pygame

from assets import load_font, load_image
from audio import play_sound, start_music
from hardware import (
    USE_GPIO,
    ball_drain,
    bumper1,
    bumper2,
    col,
    gate1,
    gate2,
    goal_sensor,
    initialize_all_gates,
    jackpot_gate,
    pulse_solenoid,
    service_button,
    target1,
    target2,
    target3,
    targets_any,
)
from test_mode import TestModeContext, run_test_mode

# ============================================================
# CONSTANTS
# ============================================================

HIGH_SCORE_FILE = "pinball_highscore.txt"

# Display
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768
FPS = 60

# Jumbotron layout
JUMBO_SCALE = (800, 600)
JUMBO_TOP = 50
CUTOUT_WIDTH, CUTOUT_HEIGHT = 460, 140
CUTOUT_OFFSET_Y = 60

# Scoring
POINTS_TARGET_HIT = 500
POINTS_BUMPER = 100
POINTS_GOAL = 2000
POINTS_MEGA_JACKPOT = 10_000

# Timing (seconds)
HIT_COOLDOWN = 0.4
BUMPER_COOLDOWN = 0.3
SOLENOID_PULSE_TIME = 0.1
JACKPOT_GATE_PULSE_TIME = 0.25
DROP_TARGET_RESET_DELAY = 0.2
BLINK_INTERVAL_MS = 500
FADE_STEP_START = 6
FADE_STEP_GAME_OVER = 5

# Game state
INITIAL_BALLS = 2
PIONEER_LETTERS = "PIONEER"

# ============================================================
# HIGH SCORE STORAGE
# ============================================================


def load_high_score() -> int:
    """Load saved high score from file."""
    if os.path.exists(HIGH_SCORE_FILE):
        try:
            with open(HIGH_SCORE_FILE, "r") as f:
                return int(f.read().strip())
        except (ValueError, OSError):
            return 0
    return 0


def save_high_score(score_value: int) -> None:
    """Save high score to file (ignore errors so game keeps running)."""
    try:
        with open(HIGH_SCORE_FILE, "w") as f:
            f.write(str(score_value))
    except OSError:
        pass


def update_high_score() -> None:
    """Update global high_score based on current score."""
    global score, high_score
    if score > high_score:
        high_score = score
        save_high_score(high_score)


# ============================================================
# PYGAME INITIALIZATION & ASSETS
# ============================================================

pygame.init()
SCREEN = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("SHU PIONEER ARENA")

# Images
rink_img = load_image("icerink.png", scale=(SCREEN_WIDTH, SCREEN_HEIGHT))
jumbo_img = load_image("jumboT.png", scale=JUMBO_SCALE)
jumbo_x = SCREEN_WIDTH // 2 - jumbo_img.get_width() // 2
jumbo_y = JUMBO_TOP
cutout_x = jumbo_x + (jumbo_img.get_width() - CUTOUT_WIDTH) // 2
cutout_y = jumbo_y + CUTOUT_OFFSET_Y
cutout_rect = pygame.Rect(cutout_x, cutout_y, CUTOUT_WIDTH, CUTOUT_HEIGHT)

# Fonts
small_font = load_font(28, bold=True)
medium_font = load_font(48, bold=True)

clock = pygame.time.Clock()

# ============================================================
# GAME STATE
# ============================================================


class SystemMode(Enum):
    """Overall system mode / high-level state machine."""

    ATTRACT_MODE = auto()
    GAMEPLAY_MODE = auto()
    TEST_MODE = auto()


current_mode: SystemMode = SystemMode.ATTRACT_MODE

score: int = 0
high_score: int = load_high_score()
balls_left: int = INITIAL_BALLS
collected: int = 0  # PIONEER progress (0–len(PIONEER_LETTERS))
mega_jackpot: bool = False
debug_mode: bool = False

# Drop target state: index = physical drop; False = up, True = down
drop_targets_down = [False, False, False]

# Debouncing
last_hit: float = 0.0
last_bumper_hit: dict = {1: 0.0, 2: 0.0}

# Track previous state of the drain switch to detect edges
ball_drain_last_state: bool = False

# Track previous state of each drop-target switch (edge detection like Arduino s1/s1_last)
target1_last_state: bool = False
target2_last_state: bool = False
target3_last_state: bool = False

# For uptime / status display
program_start_time = time.time()


# ============================================================
# RENDER HELPERS
# ============================================================


def _blit_centered(surface: pygame.Surface, source: pygame.Surface, y: int) -> None:
    """Blit source onto surface horizontally centered at the given y."""
    x = SCREEN_WIDTH // 2 - source.get_width() // 2
    surface.blit(source, (x, y))


def draw_dot_text(
    surface: pygame.Surface,
    text: str,
    x: int,
    y: int,
    color: tuple = (255, 255, 255),
    scale: int = 2,
    spacing: int = 3,
) -> None:
    """Render text as a dot-matrix style using a mask."""
    font = pygame.font.SysFont("Courier New", 48, bold=True)
    base = font.render(text, True, (255, 255, 255))
    base = pygame.transform.scale(
        base,
        (base.get_width() * scale, base.get_height() * scale),
    )
    mask = pygame.mask.from_surface(base)

    for px in range(mask.get_size()[0]):
        for py in range(mask.get_size()[1]):
            if (
                mask.get_at((px, py))
                and (px % spacing == 0)
                and (py % spacing == 0)
            ):
                pygame.draw.circle(surface, color, (x + px, y + py), 2)


def draw_pioneer(
    surface: pygame.Surface, x: int, y: int, collected_count: int
) -> None:
    """Draw PIONEER letters as bulbs on the jumbotron."""
    for i, letter in enumerate(PIONEER_LETTERS):
        if i < collected_count:
            # Lit letter
            draw_dot_text(surface, letter, x + i * 70, y, (255, 215, 60), scale=2)
        else:
            # Dim placeholder dot
            draw_dot_text(surface, "•", x + i * 70, y, (120, 120, 60), scale=2)


def draw_layout() -> None:
    """Draw the full rink, jumbotron, score, PIONEER progress, and HUD."""
    SCREEN.blit(rink_img, (0, 0))
    SCREEN.blit(jumbo_img, (jumbo_x, jumbo_y))

    score_text = str(score)
    font = pygame.font.SysFont("Courier New", 48, bold=True)
    base = font.render(score_text, True, (255, 255, 255))
    base = pygame.transform.scale(
        base,
        (base.get_width() * 3, base.get_height() * 3),
    )
    mask = pygame.mask.from_surface(base)
    text_width = mask.get_size()[0]
    draw_dot_text(
        SCREEN,
        score_text,
        cutout_rect.centerx - text_width // 2,
        cutout_rect.y + 200,
        (255, 255, 255),
        scale=3,
    )

    hs_surface = small_font.render(f"HIGH SCORE: {high_score}", True, (255, 215, 0))
    SCREEN.blit(hs_surface, (SCREEN_WIDTH - hs_surface.get_width() - 20, 20))

    draw_pioneer(
        SCREEN,
        cutout_rect.x,
        cutout_rect.y + cutout_rect.height + 258,
        collected,
    )

    balls_surface = small_font.render(f"Balls: {balls_left}", True, (255, 255, 255))
    SCREEN.blit(balls_surface, (40, SCREEN_HEIGHT - 50))

    if mega_jackpot:
        mj = medium_font.render("MEGA JACKPOT!!", True, (206, 17, 65))
        _blit_centered(SCREEN, mj, SCREEN_HEIGHT - 80)

    # Debug overlay (jumbotron grid)
    if debug_mode:
        pygame.draw.rect(SCREEN, (255, 0, 0), cutout_rect, 2)
        step_x = cutout_rect.width // 10
        step_y = cutout_rect.height // 5
        for gx in range(cutout_rect.x, cutout_rect.right, step_x):
            pygame.draw.line(
                SCREEN, (255, 0, 0),
                (gx, cutout_rect.y),
                (gx, cutout_rect.bottom),
                1,
            )
        for gy in range(cutout_rect.y, cutout_rect.bottom, step_y):
            pygame.draw.line(
                SCREEN, (255, 0, 0),
                (cutout_rect.x, gy),
                (cutout_rect.right, gy),
                1,
            )


# ============================================================
# GAME LOGIC / EVENT HANDLERS
# ============================================================

def on_target_hit() -> None:
    """Strike plate hit: award points with cooldown."""
    global last_hit, score
    now = time.time()
    if now - last_hit >= HIT_COOLDOWN:
        score += POINTS_TARGET_HIT
        update_high_score()
        last_hit = now
        play_sound("hit")


def on_bumper_hit(bumper_id: int) -> None:
    """Bumper hit: score, sound, and fire the corresponding gate."""
    global last_bumper_hit, score
    now = time.time()
    if now - last_bumper_hit[bumper_id] >= BUMPER_COOLDOWN:
        score += POINTS_BUMPER
        update_high_score()
        last_bumper_hit[bumper_id] = now
        play_sound("bumper")
        gate = gate1 if bumper_id == 1 else gate2
        threading.Thread(
            target=pulse_solenoid,
            args=(gate, SOLENOID_PULSE_TIME),
            daemon=True,
        ).start()


def on_goal_scored() -> None:
    """Goal sensor: award points, advance PIONEER letters, possibly trigger mega jackpot."""
    global collected, score, mega_jackpot
    score += POINTS_GOAL
    update_high_score()

    if collected < len(PIONEER_LETTERS):
        collected += 1

    play_sound("jackpot")

    if collected == len(PIONEER_LETTERS):
        mega_jackpot = True
        score += POINTS_MEGA_JACKPOT
        update_high_score()
        play_sound("jackpot")
        collected = 0
        mega_jackpot = False


def on_drop_target_hit() -> None:
    """Scan the 3 drop targets; on edge-down mark target down; when all down, fire reset."""
    global drop_targets_down, target1_last_state, target2_last_state, target3_last_state

    switches = [target1, target2, target3]
    last_states = [target1_last_state, target2_last_state, target3_last_state]

    for i, (btn, last) in enumerate(zip(switches, last_states)):
        if btn.is_pressed and not last and not drop_targets_down[i]:
            drop_targets_down[i] = True

    target1_last_state = target1.is_pressed
    target2_last_state = target2.is_pressed
    target3_last_state = target3.is_pressed

    if all(drop_targets_down):
        threading.Thread(
            target=pulse_solenoid,
            args=(jackpot_gate, JACKPOT_GATE_PULSE_TIME),
            daemon=True,
        ).start()
        drop_targets_down = [False, False, False]
        time.sleep(DROP_TARGET_RESET_DELAY)


def on_ball_drained() -> None:
    """Ball in trough: decrement balls left."""
    global balls_left
    if balls_left > 0:
        balls_left -= 1


def poll_hardware_inputs() -> None:
    """Read GPIO inputs and dispatch to game handlers."""
    global ball_drain_last_state

    if not USE_GPIO:
        return

    # "Activate" the column each scan (Arduino: digitalWrite(colPin, LOW);)
    col.on()

    # Strike plate / main target (simple level read with a short cooldown inside handler)
    if targets_any.is_pressed:
        on_target_hit()
        time.sleep(0.25)

    # Bumpers (simple reads; cooldown handled in on_bumper_hit)
    if bumper1.is_pressed:
        on_bumper_hit(1)
        time.sleep(0.1)

    if bumper2.is_pressed:
        on_bumper_hit(2)
        time.sleep(0.1)

    # Drop targets: scan & handle all 3 inside on_drop_target_hit()
    on_drop_target_hit()

    # Goal sensor can remain level‑based with a small delay
    if goal_sensor.is_pressed:
        on_goal_scored()
        time.sleep(0.3)

    # --- BALL DRAIN SENSOR ---
    # Detect a new press (ball arriving in trough)
    current_drain_pressed = ball_drain.is_pressed
    if current_drain_pressed and not ball_drain_last_state:
        on_ball_drained()
    ball_drain_last_state = current_drain_pressed


# ============================================================
# SCREENS (START / GAME OVER)
# ============================================================

def show_start_screen() -> SystemMode:
    """Attract screen. Returns GAMEPLAY_MODE to start game, TEST_MODE if service/F9 used."""
    global current_mode
    current_mode = SystemMode.ATTRACT_MODE
    blink = True
    timer = 0.0
    fade_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    fade_surface.fill((0, 0, 0))

    while True:
        SCREEN.blit(rink_img, (0, 0))
        SCREEN.blit(jumbo_img, (jumbo_x, jumbo_y))

        title = medium_font.render("SHU PIONEER PINBALL", True, (255, 255, 255))
        _blit_centered(SCREEN, title, 260)

        hs_txt = small_font.render(f"ALL-TIME HIGH SCORE: {high_score}", True, (255, 215, 0))
        _blit_centered(SCREEN, hs_txt, 300)

        if blink:
            txt = small_font.render("PRESS ENTER TO START", True, (255, 215, 0))
            _blit_centered(SCREEN, txt, 340)

        timer += clock.get_time()
        if timer >= BLINK_INTERVAL_MS:
            blink = not blink
            timer = 0.0

        pygame.display.flip()
        clock.tick(FPS)

        if USE_GPIO and getattr(service_button, "is_pressed", False):
            current_mode = SystemMode.TEST_MODE
            return SystemMode.TEST_MODE

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_RETURN:
                    for alpha in range(0, 180, FADE_STEP_START):
                        fade_surface.set_alpha(alpha)
                        SCREEN.blit(fade_surface, (0, 0))
                        pygame.display.flip()
                        clock.tick(FPS)
                    current_mode = SystemMode.GAMEPLAY_MODE
                    return SystemMode.GAMEPLAY_MODE
                if e.key == pygame.K_F9:
                    current_mode = SystemMode.TEST_MODE
                    return SystemMode.TEST_MODE


def show_game_over_screen() -> None:
    """Fade in Game Over, show score/high score, wait for Enter to restart."""
    fade_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    fade_surface.fill((0, 0, 0))

    for alpha in range(0, 180, FADE_STEP_GAME_OVER):
        fade_surface.set_alpha(alpha)
        SCREEN.blit(rink_img, (0, 0))
        SCREEN.blit(jumbo_img, (jumbo_x, jumbo_y))
        text = medium_font.render("GAME OVER", True, (255, 50, 50))
        _blit_centered(SCREEN, text, 200)
        final_txt = small_font.render(f"FINAL SCORE: {score}", True, (255, 255, 255))
        _blit_centered(SCREEN, final_txt, 260)
        hs_txt = small_font.render(f"ALL-TIME HIGH: {high_score}", True, (255, 215, 0))
        _blit_centered(SCREEN, hs_txt, 295)
        prompt = small_font.render("PRESS ENTER TO RESTART", True, (255, 255, 255))
        _blit_centered(SCREEN, prompt, 340)
        SCREEN.blit(fade_surface, (0, 0))
        pygame.display.flip()
        pygame.time.delay(30)

    while True:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if e.type == pygame.KEYDOWN and e.key == pygame.K_RETURN:
                return


def handle_pygame_events() -> bool:
    """Handle Pygame window + keyboard events.

    Returns False if the user requested to quit, otherwise True.
    """
    global score, balls_left, collected, mega_jackpot, debug_mode

    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            return False

        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_SPACE:
                # Test bumper 2
                on_bumper_hit(2)
            elif e.key == pygame.K_t:
                # Test strike plate
                on_target_hit()
            elif e.key == pygame.K_g:
                if collected < len(PIONEER_LETTERS):
                    collected += 1
                if collected == len(PIONEER_LETTERS):
                    mega_jackpot = True
                    score += POINTS_MEGA_JACKPOT
                    update_high_score()
                    play_sound("jackpot")
                    collected = 0
                    mega_jackpot = False
            elif e.key == pygame.K_b:
                # Manual drain test
                on_ball_drained()
            elif e.key == pygame.K_r:
                score = 0
                balls_left = INITIAL_BALLS
                collected = 0
                mega_jackpot = False
            elif e.key == pygame.K_d:
                # Toggle debug overlay
                debug_mode = not debug_mode

    return True


def handle_keyboard_test_hit() -> None:
    """Keyboard test: Enter triggers strike plate hit."""
    if pygame.key.get_pressed()[pygame.K_RETURN]:
        on_target_hit()
        pygame.time.wait(200)


def check_game_over() -> None:
    """If no balls left, show game over screen then reset game state (keep high score)."""
    global score, balls_left, collected, mega_jackpot
    if balls_left <= 0:
        show_game_over_screen()
        score = 0
        balls_left = INITIAL_BALLS
        collected = 0
        mega_jackpot = False


def render_frame() -> None:
    """Draw current frame and tick clock."""
    draw_layout()
    pygame.display.flip()
    clock.tick(FPS)


def close_hardware() -> None:
    """Release all GPIO/hardware resources."""
    for device in (targets_any, bumper1, bumper2, gate1, gate2, ball_drain, jackpot_gate):
        device.close()


# ============================================================
# MAIN
# ============================================================


def main() -> None:
    """Initialize hardware, run start/test/gameplay flow, then exit cleanly."""
    global current_mode

    initialize_all_gates()
    start_music()
    chosen_mode = show_start_screen()

    if chosen_mode == SystemMode.TEST_MODE:
        current_mode = SystemMode.TEST_MODE
        test_ctx = TestModeContext(
            screen=SCREEN,
            clock=clock,
            width=SCREEN_WIDTH,
            height=SCREEN_HEIGHT,
            rink_img=rink_img,
            jumbo_img=jumbo_img,
            jumbo_x=jumbo_x,
            jumbo_y=jumbo_y,
            small_font=small_font,
            medium_font=medium_font,
            program_start_time=program_start_time,
        )
        run_test_mode(test_ctx)
        current_mode = SystemMode.ATTRACT_MODE
        chosen_mode = show_start_screen()

    current_mode = SystemMode.GAMEPLAY_MODE
    running = True
    while running:
        running = handle_pygame_events()
        poll_hardware_inputs()
        handle_keyboard_test_hit()
        check_game_over()
        render_frame()

    close_hardware()
    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
