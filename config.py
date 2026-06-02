import pygame

WINDOW_W = 1280
WINDOW_H = 720
PANEL_W = 320
TOOLBAR_H = 48
STATUS_H = 24

BG_COLOR = (40, 40, 40)
GRID_COLOR = (80, 80, 80, 150)
SELECTION_COLOR = (255, 200, 0)
EMPTY_TILE_BG = (20, 20, 20)

UNDO_STACK_LIMIT = 30
MIN_ZOOM = 0.25
MAX_ZOOM = 8.0
ZOOM_STEP = 0.25

FPS = 60
ANIM_TILE_SIZE = 48

_font_cache: dict[int, pygame.font.Font] = {}

_UNICODE_FONT = "dejavusans"


def get_font(size: int) -> pygame.font.Font:
    if size not in _font_cache:
        f = pygame.font.SysFont(_UNICODE_FONT, size)
        _font_cache[size] = f
    return _font_cache[size]
