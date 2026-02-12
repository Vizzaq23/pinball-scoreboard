# audio.py - Sound effects and ambient music for the pinball scoreboard.

import pygame

from assets import load_sound

# ---------------------------------------------------------------------------
# Mixer
# ---------------------------------------------------------------------------

pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

# ---------------------------------------------------------------------------
# Sound effects (name -> Sound)
# ---------------------------------------------------------------------------

SOUNDS: dict[str, pygame.mixer.Sound | None] = {
    "hit": load_sound("hit.wav", volume=0.7),
    "bumper": load_sound("bumper.wav", volume=0.7),
    "jackpot": load_sound("jackpot.wav", volume=0.7),
}


def play_sound(name: str) -> None:
    """Play a loaded sound by name. No-op if name unknown or sound failed to load."""
    sound = SOUNDS.get(name)
    if sound:
        sound.play()


# ---------------------------------------------------------------------------
# Ambient music
# ---------------------------------------------------------------------------

crowd_loop = load_sound("hockey_theme.wav", volume=0.6)
organ_loop = load_sound("hockey_theme1.wav", volume=0.3)
crowd_channel = pygame.mixer.Channel(0)
organ_channel = pygame.mixer.Channel(1)
music_on = True


def start_music() -> None:
    """Start crowd and organ loops. Safe to call if files failed to load."""
    if crowd_loop:
        crowd_channel.play(crowd_loop, loops=-1)
    if organ_loop:
        organ_channel.play(organ_loop, loops=-1)


def toggle_music() -> None:
    """Toggle ambient music on/off."""
    global music_on
    music_on = not music_on
    if music_on:
        crowd_channel.unpause()
        organ_channel.unpause()
    else:
        crowd_channel.pause()
        organ_channel.pause()
