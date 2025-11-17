# game.py
import pygame, sys, time, threading

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
    pulse_solenoid,
)
from assets import load_image, load_font

# --- INITIALIZE PYGAME ---
pygame.init()
WIDTH, HEIGHT = 1600, 1000
SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("SHU PIONEER ARENA")

# --- LOAD IMAGES ---
rink_img = load_image("icerink.png", scale=(WIDTH, HEIGHT))
jumbo_img = load_image("jumboT.png", scale=(800, 600))

jumbo_x = WIDTH // 2 - jumbo_img.get_width() // 2
jumbo_y = 50
cutout_width, cutout_height = 460, 140
cutout_x = jumbo_x + (jumbo_img.get_width() - cutout_width) // 2
cutout_y = jumbo_y + 60
cutout_rect = pygame.Rect(cutout_x, cutout_y, cutout_width, cutout_height)

# --- FONTS ---
small_font = load_font(28, bold=True)
medium_font = load_font(48, bold=True)

# --- GAME STATE ---
score = 0
balls_left = 2
collected = 0  # PIONEER progress (0–7)
mega_jackpot = False
debug_mode = False
clock = pygame.time.Clock()

# Drop target state: each index = one physical drop
# False = up, True = down
drop_targets_down = [False, False, False, False]

# --- DOT MATRIX RENDERER ---
def draw_dot_text(surface, text, x, y, color=(255, 255, 255), scale=2, spacing=3):
    font = pygame.font.SysFont("Courier New", 48, bold=True)
    base = font.render(text, True, (255, 255, 255))
    base = pygame.transform.scale(
        base, (base.get_width() * scale, base.get_height() * scale)
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


# --- PIONEER BULBS ---
def draw_pioneer(surface, x, y, collected_count):
    word = "PIONEER"
    for i, letter in enumerate(word):
        if i < collected_count:
            draw_dot_text(surface, letter, x + i * 70, y, (255, 215, 60), scale=2)
        else:
            draw_dot_text(surface, "•", x + i * 70, y, (120, 120, 60), scale=2)


# --- DRAW EVERYTHING ---
def draw_layout():
    SCREEN.blit(rink_img, (0, 0))
    SCREEN.blit(jumbo_img, (jumbo_x, jumbo_y))

    # Score text as big dot-matrix
    score_text = str(score)
    font = pygame.font.SysFont("Courier New", 48, bold=True)
    base = font.render(score_text, True, (255, 255, 255))
    base = pygame.transform.scale(
        base, (base.get_width() * 3, base.get_height() * 3)
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

    # PIONEER letters
    draw_pioneer(
        SCREEN,
        cutout_rect.x,
        cutout_rect.y + cutout_rect.height + 258,
        collected,
    )

    # Balls left
    SCREEN.blit(
        small_font.render(f"Balls: {balls_left}", True, (255, 255, 255)),
        (40, HEIGHT - 50),
    )

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
                SCREEN,
                (255, 0, 0),
                (gx, cutout_rect.y),
                (gx, cutout_rect.bottom),
                1,
            )
        for gy in range(cutout_rect.y, cutout_rect.bottom, step_y):
            pygame.draw.line(
                SCREEN,
                (255, 0, 0),
                (cutout_rect.x, gy),
                (cutout_rect.right, gy),
                1,
            )


# --- SCORING LOGIC ---
last_hit = 0
HIT_COOLDOWN = 0.4


def on_target_hit():
    global last_hit, score
    now = time.time()
    if now - last_hit >= HIT_COOLDOWN:
        score += 500
        last_hit = now
        print("🎯 Target hit! +500")
        play_sound("hit")


last_bumper_hit = {1: 0, 2: 0}
BUMPER_COOLDOWN = 0.3
PULSE_TIME = 0.1


def on_bumper_hit(bumper_id):
    global last_bumper_hit, score
    now = time.time()
    if now - last_bumper_hit[bumper_id] >= BUMPER_COOLDOWN:
        score += 100
        last_bumper_hit[bumper_id] = now
        print(f" Bumper {bumper_id} hit! +100")
        play_sound("bumper")
        gate = gate1 if bumper_id == 1 else gate2
        threading.Thread(
            target=pulse_solenoid, args=(gate, PULSE_TIME), daemon=True
        ).start()


def on_goal_scored():
    global collected, score, mega_jackpot
    score += 2000  # goals are big points
    if collected < len("PIONEER"):
        collected += 1

    print(f"🥅 GOAL SCORED! Letters: {collected}/{len('PIONEER')}")
    play_sound("jackpot")

    # Check jackpot condition
    if collected == len("PIONEER"):
        mega_jackpot = True
        score += 10000
        print("💥 MEGA JACKPOT!")
        play_sound("jackpot")
        # Reset letters & jackpot flag so player can re-earn
        collected = 0
        mega_jackpot = False


def on_drop_target_hit(target_num):
    global drop_targets_down

    idx = target_num - 1
    if not drop_targets_down[idx]:
        drop_targets_down[idx] = True
        print(f"🔽 Drop Target {target_num} DOWN!")

    # If all 4 targets are down -> fire reset solenoid and reset state
    if all(drop_targets_down):
        print("🔄 All drop targets down! Resetting bank...")
        threading.Thread(
            target=pulse_solenoid, args=(jackpot_gate, 0.25), daemon=True
        ).start()
        # Reset for next cycle
        drop_targets_down = [False, False, False, False]
        time.sleep(0.2)

def show_start_screen():
    blink = True
    timer = 0
    fade_surface = pygame.Surface((WIDTH, HEIGHT))
    fade_surface.fill((0, 0, 0))

    while True:
        SCREEN.blit(rink_img, (0, 0))
        SCREEN.blit(jumbo_img, (jumbo_x, jumbo_y))

        # TITLE
        title = medium_font.render("SHU PIONEER PINBALL", True, (255, 255, 255))
        SCREEN.blit(title, (WIDTH//2 - title.get_width()//2, 260))

        # BLINKING PRESS START
        if blink:
            txt = small_font.render("PRESS ENTER TO START", True, (255, 215, 0))
            SCREEN.blit(txt, (WIDTH//2 - txt.get_width()//2, 300))

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
    fade_surface = pygame.Surface((WIDTH, HEIGHT))
    fade_surface.fill((0, 0, 0))

    # Fade-in effect
    for alpha in range(0, 180, 5):
        fade_surface.set_alpha(alpha)
        SCREEN.blit(rink_img, (0, 0))
        SCREEN.blit(jumbo_img, (jumbo_x, jumbo_y))

        # GAME OVER text
        text = medium_font.render("GAME OVER", True, (255, 50, 50))
        SCREEN.blit(
            text, (WIDTH // 2 - text.get_width() // 2, 200)
        )

        # Press Enter prompt
        prompt = small_font.render(
            "PRESS ENTER TO RESTART", True, (255, 255, 255)
        )
        SCREEN.blit(
            prompt, (WIDTH // 2 - prompt.get_width() // 2, 300)
        )

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


# --- START MUSIC ---
start_music()
show_start_screen()

# --- MAIN LOOP ---
running = True
while running:
    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            running = False

        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_SPACE:
                # test bumper 2
                on_bumper_hit(2)
            elif e.key == pygame.K_t:
                # test strike plate
                on_target_hit()
            elif e.key == pygame.K_g:
                # manual letter advance / jackpot test
                if collected < len("PIONEER"):
                    collected += 1
                if collected == len("PIONEER"):
                    mega_jackpot = True
                    score += 10000
                    play_sound("jackpot")
                    collected = 0
                    mega_jackpot = False
            elif e.key == pygame.K_b:
                balls_left -= 1
                print(f"Ball drained, balls_left = {balls_left}")
            elif e.key == pygame.K_r:
                score, balls_left, collected, mega_jackpot = 0, 2, 0, False
            elif e.key == pygame.K_d:
                debug_mode = not debug_mode

    # --- PHYSICAL INPUTS (GPIO) ---
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

    # --- OPTIONAL: Keyboard test for hit using ENTER ---
    keys = pygame.key.get_pressed()
    if keys[pygame.K_RETURN]:
        on_target_hit()
        pygame.time.wait(200)

    # --- GAME OVER CHECK ---
    if balls_left <= 0:
        print("💀 GAME OVER — resetting")
        show_game_over_screen()

        # Reset full game state AFTER screen
        score = 0
        balls_left = 2
        collected = 0
        mega_jackpot = False

    draw_layout()
    pygame.display.flip()
    clock.tick(60)

# --- CLEAN EXIT ---
targets_any.close()
bumper1.close()
bumper2.close()
gate1.close()
gate2.close()
pygame.quit()
sys.exit()
