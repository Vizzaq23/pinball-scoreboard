# assets.py - Load images, sounds, and fonts from the assets directory.

import os
from typing import Optional

import pygame

ASSET_DIR = "assets"


def load_image(
    filename: str,
    scale: Optional[tuple[int, int]] = None,
    background: Optional[tuple[int, int, int]] = None,
) -> Optional[pygame.Surface]:
    """
    Load an image from ASSET_DIR. Uses convert_alpha() for PNGs with
    transparency (unless flattened — see background).

    If ``background`` is an RGB triplet, the (possibly scaled) image is
    composited onto that color and returned as a solid surface. Use this for
    full-screen backdrops like the rink so transparent pixels never pick up
    the display backbuffer (e.g. a white flash after flip).
    """
    path = os.path.join(ASSET_DIR, filename)
    try:
        img = pygame.image.load(path)
    except Exception as e:
        print(f"⚠️ Failed to load image '{path}': {e}")
        return None

    has_alpha = False
    if filename.lower().endswith(".png"):
        try:
            if img.get_alpha() is not None or (img.get_flags() & pygame.SRCALPHA):
                has_alpha = True
        except Exception:
            pass

    img = img.convert_alpha() if has_alpha else img.convert()
    if scale:
        img = pygame.transform.smoothscale(img, scale)
    if background is not None:
        base = pygame.Surface(img.get_size())
        base.fill(background)
        base.blit(img, (0, 0))
        img = base.convert()
    return img


def load_sound(filename: str, volume: float = 1.0) -> Optional[pygame.mixer.Sound]:
    """Load a sound from ASSET_DIR and set volume. Returns None on failure."""
    path = os.path.join(ASSET_DIR, filename)
    try:
        sound = pygame.mixer.Sound(path)
        sound.set_volume(volume)
        return sound
    except Exception as e:
        print(f"⚠️ Failed to load sound '{path}': {e}")
        return None


def load_font(size: int, bold: bool = False) -> pygame.font.Font:
    """Return Courier New system font at given size."""
    return pygame.font.SysFont("Courier New", size, bold=bold)
