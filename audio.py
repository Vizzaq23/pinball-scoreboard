# audio.py
import pygame
from assets import load_sound

# --- MIXER INIT ---
pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

# ----------------------------------------------------
# LOAD SOUND EFFECTS
# ----------------------------------------------------
hit_sound = load_sound("hit.wav", volume=0.7)
bumper_sound = load_sound("bumper.wav", volume=0.7)
jackpot_sound = load_sound("jackpot.wav", volume=0.7)

def play_sound(name):
    if name == "hit" and hit_sound:
        hit_sound.play()
    elif name == "bumper" and bumper_sound:
        bumper_sound.play()
    elif name == "jackpot" and jackpot_sound:
        jackpot_sound.play()

# ----------------------------------------------------
# AMBIENT MUSIC
# ----------------------------------------------------
crowd_loop = load_sound("hockey_theme.wav", volume=0.6)
organ_loop = load_sound("hockey_theme1.wav", volume=0.3)

crowd_channel = pygame.mixer.Channel(0)
organ_channel = pygame.mixer.Channel(1)

music_on = True

def start_music():
    if crowd_loop:
        crowd_channel.play(crowd_loop, loops=-1)
        print("🎧 Crowd ambience started.")
    if organ_loop:
        organ_channel.play(organ_loop, loops=-1)
        print("🎹 Organ music started.")

def toggle_music():
    global music_on
    music_on = not music_on

    if music_on:
        crowd_channel.unpause()
        organ_channel.unpause()
        print("🎵 Music ON")
    else:
        crowd_channel.pause()
        organ_channel.pause()
        print("🔇 Music OFF")
        
print("hit_sound =", hit_sound)
print("bumper_sound =", bumper_sound)
print("jackpot_sound =", jackpot_sound)

