# game.py
import os
import sys
import time
import threading

import pygame

from audio import start_music, play_sound
from hardware import (
    targets_any,
    bumper1,
    bumper2,
    gate1,
    gate2,
    target1,
    target2,
    target3,
    target4,
    goal_sensor,
    jackpot_gate,
    USE_GPIO,
    ball_drain,
    pulse_solenoid,
)
from assets import load_image, load_font

# ============================================================
# HIGH SCORE STORAGE
# ============================================================

HIGH_SCORE_FILE = "pinball_highscore.txt"


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
WIDTH, HEIGHT = 1024, 768
SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("SHU PIONEER ARENA")

# Images
rink_img = load_image("icerink.png", scale=(WIDTH, HEIGHT))
jumbo_img = load_image("jumboT.png", scale=(800, 600))

# Jumbotron positioning & score cutout area
jumbo_x = WIDTH // 2 - jumbo_img.get_width() // 2
jumbo_y = 50
cutout_width, cutout_height = 460, 140
cutout_x = jumbo_x + (jumbo_img.get_width() - cutout_width) // 2
cutout_y = jumbo_y + 60
cutout_rect = pygame.Rect(cutout_x, cutout_y, cutout_width, cutout_height)

# Fonts
small_font = load_font(28, bold=True)
medium_font = load_font(48, bold=True)

clock = pygame.time.Clock()

# ============================================================
# GAME STATE
# ============================================================

score: int = 0
high_score: int = load_high_score()  # all-time saved high score
balls_left: int = 2
collected: int = 0  # PIONEER progress (0–7)
mega_jackpot: bool = False
debug_mode: bool = False

# Drop target state: each index = one physical drop
# False = up, True = down
drop_targets_down = [False, False, False, False]

# For debouncing / cooldowns
last_hit = 0.0
HIT_COOLDOWN = 0.4

last_bumper_hit = {1: 0.0, 2: 0.0}
BUMPER_COOLDOWN = 0.3
PULSE_TIME = 0.1

# Track previous state of the drain switch to detect edges
ball_drain_last_state: bool = False


# ============================================================
# RENDER HELPERS
# ============================================================

def draw_dot_text(surface, text, x, y, color=(255, 255, 255), scale=2, spacing=3):
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


def draw_pioneer(surface, x, y, collected_count):
    """Draw PIONEER letters as bulbs on the jumbotron."""
    word = "PIONEER"
    for i, letter in enumerate(word):
        if i < collected_count:
            # Lit letter
            draw_dot_text(surface, letter, x + i * 70, y, (255, 215, 60), scale=2)
        else:
            # Dim placeholder dot
            draw_dot_text(surface, "•", x + i * 70, y, (120, 120, 60), scale=2)


def draw_layout():
    """Draw the full rink, jumbotron, score, PIONEER progress, etc."""
    SCREEN.blit(rink_img, (0, 0))
    SCREEN.blit(jumbo_img, (jumbo_x, jumbo_y))

    # Score text as big dot-matrix
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

    # High score (top right corner)
    hs_text = f"HIGH SCORE: {high_score}"
    hs_surface = small_font.render(hs_text, True, (255, 215, 0))

    # Position 20px from right/top
    hs_x = WIDTH - hs_surface.get_width() - 20
    hs_y = 20
    SCREEN.blit(hs_surface, (hs_x, hs_y))

    # PIONEER letters
    draw_pioneer(
        SCREEN,
        cutout_rect.x,
        cutout_rect.y + cutout_rect.height + 258,
        collected,
    )

    # Balls left
    balls_surface = small_font.render(f"Balls: {balls_left}", True, (255, 255, 255))
    SCREEN.blit(balls_surface, (40, HEIGHT - 50))

    # Jackpot banner
    if mega_jackpot:
        mj = medium_font.render("MEGA JACKPOT!!", True, (206, 17, 65))
        SCREEN.blit(mj, (WIDTH // 2 - mj.get_width() // 2, HEIGHT - 80))

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

def on_target_hit():
    """Strike plate hit → award points with cooldown."""
    global last_hit, score
    now = time.time()
    if now - last_hit >= HIT_COOLDOWN:
        score += 500
        update_high_score()
        last_hit = now
        print("🎯 Target hit! +500")
        play_sound("hit")


def on_bumper_hit(bumper_id: int):
    """Bumper hit → score, sound, and fire the corresponding gate."""
    global last_bumper_hit, score
    now = time.time()
    if now - last_bumper_hit[bumper_id] >= BUMPER_COOLDOWN:
        score += 100
        update_high_score()
        last_bumper_hit[bumper_id] = now
        print(f"🎳 Bumper {bumper_id} hit! +100")
        play_sound("bumper")

        gate = gate1 if bumper_id == 1 else gate2
        threading.Thread(
            target=pulse_solenoid,
            args=(gate, PULSE_TIME),
            daemon=True,
        ).start()


def on_goal_scored():
    """Puck/ball goes through goal sensor → letters and possible jackpot."""
    global collected, score, mega_jackpot
    score += 2000  # goals are big points
    update_high_score()

    if collected < len("PIONEER"):
        collected += 1

    print(f"🥅 GOAL SCORED! Letters: {collected}/{len('PIONEER')}")
    play_sound("jackpot")

    # Check jackpot condition
    if collected == len("PIONEER"):
        mega_jackpot = True
        score += 10000
        update_high_score()
        print("💥 MEGA JACKPOT!")
        play_sound("jackpot")

        # Reset letters & jackpot flag so player can re-earn
        collected = 0
        mega_jackpot = False


def on_drop_target_hit(target_num: int):
    """Handle one of the 4 drop targets being hit."""
    global drop_targets_down

    idx = target_num - 1
    if not drop_targets_down[idx]:
        drop_targets_down[idx] = True
        print(f"🔽 Drop Target {target_num} DOWN!")

    # If all 4 targets are down -> fire reset solenoid and reset state
    if all(drop_targets_down):
        print("🔄 All drop targets down! Resetting bank...")
        threading.Thread(
            target=pulse_solenoid,
            args=(jackpot_gate, 0.25),
            daemon=True,
        ).start()
        # Reset for next cycle
        drop_targets_down = [False, False, False, False]
        time.sleep(0.2)


def on_ball_drained():
    """Ball drains to trough → decrement balls_left."""
    global balls_left
    if balls_left > 0:
        balls_left -= 1
    print(f"🎱 Ball drained (hardware), balls_left = {balls_left}")
    # Optional: if you add a "drain" sound:
    # play_sound("drain")


# ============================================================
# SCREENS (START / GAME OVER)
# ============================================================

def show_start_screen():
    """Start screen loop with blinking 'Press Enter'."""
    blink = True
    timer = 0
    fade_surface = pygame.Surface((WIDTH, HEIGHT))
    fade_surface.fill((0, 0, 0))

    while True:
        SCREEN.blit(rink_img, (0, 0))
        SCREEN.blit(jumbo_img, (jumbo_x, jumbo_y))

        # Title
        title = medium_font.render("SHU PIONEER PINBALL", True, (255, 255, 255))
        SCREEN.blit(title, (WIDTH // 2 - title.get_width() // 2, 260))

        # Show current all-time high score on start screen
        hs_txt = small_font.render(
            f"ALL-TIME HIGH SCORE: {high_score}", True, (255, 215, 0)
        )
        SCREEN.blit(hs_txt, (WIDTH // 2 - hs_txt.get_width() // 2, 300))

        # Blinking "Press Enter to Start"
        if blink:
            txt = small_font.render("PRESS ENTER TO START", True, (255, 215, 0))
            SCREEN.blit(txt, (WIDTH // 2 - txt.get_width() // 2, 340))

        # Blink timer
        timer += clock.get_time()
        if timer > 500:  # blink every 0.5s
            blink = not blink
            timer = 0

        pygame.display.flip()
        clock.tick(60)

        # Input handling
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if e.type == pygame.KEYDOWN and e.key == pygame.K_RETURN:
                # Fade out
                for alpha in range(0, 180, 6):
                    fade_surface.set_alpha(alpha)
                    SCREEN.blit(fade_surface, (0, 0))
                    pygame.display.flip()
                    clock.tick(60)
                return


def show_game_over_screen():
    """Show 'Game Over' screen, then wait for Enter to restart."""
    fade_surface = pygame.Surface((WIDTH, HEIGHT))
    fade_surface.fill((0, 0, 0))

    # Fade-in effect
    for alpha in range(0, 180, 5):
        fade_surface.set_alpha(alpha)
        SCREEN.blit(rink_img, (0, 0))
        SCREEN.blit(jumbo_img, (jumbo_x, jumbo_y))

        # GAME OVER text
        text = medium_font.render("GAME OVER", True, (255, 50, 50))
        SCREEN.blit(text, (WIDTH // 2 - text.get_width() // 2, 200))

        # Show final score and high score
        final_txt = small_font.render(f"FINAL SCORE: {score}", True, (255, 255, 255))
        SCREEN.blit(final_txt, (WIDTH // 2 - final_txt.get_width() // 2, 260))

        hs_txt = small_font.render(f"ALL-TIME HIGH: {high_score}", True, (255, 215, 0))
        SCREEN.blit(hs_txt, (WIDTH // 2 - hs_txt.get_width() // 2, 295))

        # Press Enter prompt
        prompt = small_font.render("PRESS ENTER TO RESTART", True, (255, 255, 255))
        SCREEN.blit(prompt, (WIDTH // 2 - prompt.get_width() // 2, 340))

        SCREEN.blit(fade_surface, (0, 0))
        pygame.display.flip()
        pygame.time.delay(30)

    # Wait for ENTER
    waiting = True
    while waiting:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if e.type == pygame.KEYDOWN and e.key == pygame.K_RETURN:
                waiting = False


# ============================================================
# MAIN GAME LOOP
# ============================================================

# Start background music and show start screen once
start_music()
show_start_screen()

running = True
while running:
    # ----------------------------------------
    # Pygame event handling
    # ----------------------------------------
    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            running = False

        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_SPACE:
                # Test bumper 2
                on_bumper_hit(2)
            elif e.key == pygame.K_t:
                # Test strike plate
                on_target_hit()
            elif e.key == pygame.K_g:
                # Manual letter advance / jackpot test
                if collected < len("PIONEER"):
                    collected += 1
                if collected == len("PIONEER"):
                    mega_jackpot = True
                    score += 10000
                    update_high_score()
                    play_sound("jackpot")
                    collected = 0
                    mega_jackpot = False
            elif e.key == pygame.K_b:
                # Manual drain test
                on_ball_drained()
            elif e.key == pygame.K_r:
                # Reset current game, but keep high score
                score = 0
                balls_left = 2
                collected = 0
                mega_jackpot = False
            elif e.key == pygame.K_d:
                # Toggle debug overlay
                debug_mode = not debug_mode

    # ----------------------------------------
    # PHYSICAL INPUTS (GPIO)
    # ----------------------------------------
    if USE_GPIO:
        if targets_any.is_pressed:
            on_target_hit()
            time.sleep(0.25)

        if bumper1.is_pressed:
            on_bumper_hit(1)
            time.sleep(0.1)

        if bumper2.is_pressed:
            on_bumper_hit(2)
            time.sleep(0.1)

        if target1.is_pressed:
            on_drop_target_hit(1)
            time.sleep(0.1)

        if target2.is_pressed:
            on_drop_target_hit(2)
            time.sleep(0.1)

        if target3.is_pressed:
            on_drop_target_hit(3)
            time.sleep(0.1)

        if target4.is_pressed:
            on_drop_target_hit(4)
            time.sleep(0.1)

        if goal_sensor.is_pressed:
            on_goal_scored()
            time.sleep(0.3)

        # --- BALL DRAIN SENSOR ---
        # Detect a new press (ball arriving in trough)
        current_drain_pressed = ball_drain.is_pressed
        if current_drain_pressed and not ball_drain_last_state:
            on_ball_drained()
        ball_drain_last_state = current_drain_pressed

    # ----------------------------------------
    # OPTIONAL: Keyboard test for hit using ENTER
    # ----------------------------------------
    keys = pygame.key.get_pressed()
    if keys[pygame.K_RETURN]:
        on_target_hit()
        pygame.time.wait(200)

    # ----------------------------------------
    # GAME OVER CHECK
    # ----------------------------------------
    if balls_left <= 0:
        print("GAME OVER — resetting")
        show_game_over_screen()

        # Reset full game state AFTER screen (high_score is kept)
        score = 0
        balls_left = 2
        collected = 0
        mega_jackpot = False

    # ----------------------------------------
    # RENDER FRAME
    # ----------------------------------------
    draw_layout()
    pygame.display.flip()
    clock.tick(60)

# ============================================================
# CLEAN EXIT
# ============================================================

targets_any.close()
bumper1.close()
bumper2.close()
gate1.close()
gate2.close()
ball_drain.close()
jackpot_gate.close()
pygame.quit()
sys.exit()
