# assets.py
import pygame
import os

ASSET_DIR = "assets"


# -----------------------------
# PNG-SAFE IMAGE LOADER
# -----------------------------
def load_image(filename, scale=None, alpha=True):
    """
    Loads an image and automatically chooses convert_alpha() ONLY if
    the image actually contains transparency.
    This prevents black backgrounds on PNGs like the rink.
    """
    path = os.path.join(ASSET_DIR, filename)

    try:
        img = pygame.image.load(path)
    except Exception as e:
        print(f"⚠️ Failed to load image '{path}': {e}")
        return None

    # Detect if PNG has transparency
    has_alpha = False
    if filename.lower().endswith(".png"):
        try:
            # Check if image has per-pixel alpha
            if img.get_alpha() is not None:
                has_alpha = True
            else:
                # Check if image has a colorkey or palette alpha
                if img.get_flags() & pygame.SRCALPHA:
                    has_alpha = True
        except:
            pass

    # Convert properly
    if has_alpha:
        img = img.convert_alpha()
    else:
        img = img.convert()

    # Scale AFTER conversion
    if scale:
        img = pygame.transform.smoothscale(img, scale)

    return img


# -----------------------------
# SOUND LOADER
# -----------------------------
def load_sound(filename, volume=1.0):
    path = os.path.join(ASSET_DIR, filename)
    try:
        s = pygame.mixer.Sound(path)
        s.set_volume(volume)
        return s
    except Exception as e:
        print(f"⚠️ Failed to load sound '{path}': {e}")
        return None


# -----------------------------
# FONT LOADER
# -----------------------------
def load_font(size, bold=False):
    return pygame.font.SysFont("Courier New", size, bold=bold)