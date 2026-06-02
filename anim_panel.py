import pygame

from config import SELECTION_COLOR, get_font
from editor import (
    AnimFrame,
    EditorState,
    anim_adjust_clip_delay,
    anim_adjust_frame_delay,
    anim_move_frame_down,
    anim_move_frame_up,
    anim_remove_clip,
    anim_remove_frame,
    anim_remove_set,
    anim_toggle_loop,
    get_active_clip,
)

_SECTION_H = 32
_ITEM_H = 26
_BTN_H = 28
_MAX_LIST = 4

_CTRL_ROW_H = 24
_CTRL_PAD = 2
# 3 control rows (frame delay, clip delay, loop) + top separator
_EXTRA_CONTROLS_H = 3 * (_CTRL_ROW_H + _CTRL_PAD) + 4

_BG = (30, 30, 30)
_SECTION_BG = (40, 40, 40)
_FG = (200, 200, 200)
_SEL_BG = (50, 70, 100)
_BTN_BG = (60, 60, 60)
_BTN_HOV = (80, 80, 80)
_RED_BG = (100, 40, 40)
_RED_HOV = (140, 60, 60)
_GREEN_BG = (40, 90, 40)
_GREEN_HOV = (60, 130, 60)


def _font(size=15):
    return get_font(size)


def _text(screen, msg, x, y, size=15, color=_FG):
    screen.blit(_font(size).render(msg, True, color), (x, y))


def _btn(screen, label, rect, bg=_BTN_BG, hover=_BTN_HOV, active=False):
    mx, my = pygame.mouse.get_pos()
    c = SELECTION_COLOR if active else (hover if rect.collidepoint(mx, my) else bg)
    pygame.draw.rect(screen, c, rect, border_radius=3)
    pygame.draw.rect(screen, (90, 90, 90), rect, 1, border_radius=3)
    s = _font(14).render(label, True, (255, 255, 255))
    screen.blit(s, (rect.x + (rect.width - s.get_width()) // 2,
                    rect.y + (rect.height - s.get_height()) // 2))


def _section_header(screen, label, rect):
    pygame.draw.rect(screen, _SECTION_BG, rect)
    pygame.draw.line(screen, (70, 70, 70), rect.bottomleft, rect.bottomright)
    _text(screen, label, rect.x + 8, rect.y + (rect.height - 15) // 2, size=16)


def _compute_ctrl_positions(panel_rect, x, w):
    """Returns (ctrl_y, extra_top, bws) for the bottom control area."""
    ctrl_y = panel_rect.bottom - _BTN_H - 6
    extra_top = ctrl_y - _EXTRA_CONTROLS_H
    bws = 26
    return ctrl_y, extra_top, bws


def draw_anim_panel(screen: pygame.Surface, state: EditorState,
                    panel_rect: pygame.Rect) -> None:
    pygame.draw.rect(screen, _BG, panel_rect)
    pygame.draw.line(screen, (70, 70, 70),
                     (panel_rect.x, panel_rect.y), (panel_rect.x, panel_rect.bottom))

    y = panel_rect.y
    x = panel_rect.x
    w = panel_rect.width

    _section_header(screen, "Sets", pygame.Rect(x, y, w, _SECTION_H))
    y += _SECTION_H

    for i, s in enumerate(state.anim_sets[:_MAX_LIST]):
        r = pygame.Rect(x, y, w, _ITEM_H)
        if i == state.active_anim_set:
            pygame.draw.rect(screen, _SEL_BG, r)
        _text(screen, s.name, x + 8, y + 4)
        y += _ITEM_H

    bw = (w - 16) // 2
    _btn(screen, "+ Set", pygame.Rect(x + 4, y + 4, bw, _BTN_H), _GREEN_BG, _GREEN_HOV)
    _btn(screen, "- Set", pygame.Rect(x + 8 + bw, y + 4, bw, _BTN_H), _RED_BG, _RED_HOV)
    y += _BTN_H + 8
    pygame.draw.line(screen, (60, 60, 60), (x + 4, y), (x + w - 4, y))
    y += 4

    _section_header(screen, "Clips", pygame.Rect(x, y, w, _SECTION_H))
    y += _SECTION_H

    active_set = state.anim_sets[state.active_anim_set] if state.anim_sets else None
    clips = active_set.clips if active_set else []

    for i, clip in enumerate(clips[:_MAX_LIST]):
        r = pygame.Rect(x, y, w, _ITEM_H)
        if i == state.active_anim_clip:
            pygame.draw.rect(screen, _SEL_BG, r)
        label = f"{clip.name}  {clip.default_delay_ms}ms"
        if clip.loop:
            label += " ↺"
        _text(screen, label, x + 8, y + 4)
        y += _ITEM_H

    _btn(screen, "+ Clip", pygame.Rect(x + 4, y + 4, bw, _BTN_H), _GREEN_BG, _GREEN_HOV)
    _btn(screen, "- Clip", pygame.Rect(x + 8 + bw, y + 4, bw, _BTN_H), _RED_BG, _RED_HOV)
    y += _BTN_H + 8
    pygame.draw.line(screen, (60, 60, 60), (x + 4, y), (x + w - 4, y))
    y += 4

    _section_header(screen, "Frames", pygame.Rect(x, y, w, _SECTION_H))
    y += _SECTION_H

    clip = get_active_clip(state)

    ctrl_y, extra_top, bws = _compute_ctrl_positions(panel_rect, x, w)
    visible_h = extra_top - y - 4
    visible_n = max(1, visible_h // _ITEM_H)

    if clip:
        for i, frame in enumerate(clip.frames[:visible_n]):
            r = pygame.Rect(x, y, w, _ITEM_H)
            if i == state.active_anim_frame:
                pygame.draw.rect(screen, _SEL_BG, r)
            eff = frame.delay_ms if frame.delay_ms > 0 else clip.default_delay_ms
            _text(screen, f"[{i}]  tile={frame.tile_id}  {eff}ms", x + 8, y + 4)
            y += _ITEM_H

    # --- extra controls (delay + loop) ---
    pygame.draw.line(screen, (60, 60, 60), (x + 4, extra_top), (x + w - 4, extra_top))
    cy = extra_top + 4

    # Row 1: frame delay
    f_minus = pygame.Rect(x + w - bws * 2 - 6, cy, bws, _CTRL_ROW_H)
    f_plus  = pygame.Rect(x + w - bws - 4,     cy, bws, _CTRL_ROW_H)
    if clip and 0 <= state.active_anim_frame < len(clip.frames):
        fdelay = clip.frames[state.active_anim_frame].delay_ms
        fval = f"{fdelay}ms" if fdelay > 0 else "def"
        _text(screen, f"frame: {fval}", x + 4, cy + 5, size=13, color=(160, 160, 160))
    else:
        _text(screen, "frame: —", x + 4, cy + 5, size=13, color=(100, 100, 100))
    _btn(screen, "−", f_minus)
    _btn(screen, "+", f_plus)
    cy += _CTRL_ROW_H + _CTRL_PAD

    # Row 2: clip default delay
    c_minus = pygame.Rect(x + w - bws * 2 - 6, cy, bws, _CTRL_ROW_H)
    c_plus  = pygame.Rect(x + w - bws - 4,     cy, bws, _CTRL_ROW_H)
    if clip:
        _text(screen, f"clip: {clip.default_delay_ms}ms", x + 4, cy + 5, size=13,
              color=(160, 160, 160))
    else:
        _text(screen, "clip: —", x + 4, cy + 5, size=13, color=(100, 100, 100))
    _btn(screen, "−", c_minus)
    _btn(screen, "+", c_plus)
    cy += _CTRL_ROW_H + _CTRL_PAD

    # Row 3: loop toggle
    loop_val = clip.loop if clip else False
    loop_rect = pygame.Rect(x + 4, cy, w - 8, _CTRL_ROW_H)
    _btn(screen, f"loop: {'ON  ↺' if loop_val else 'OFF'}",
         loop_rect, _GREEN_BG if loop_val else _BTN_BG, _GREEN_HOV if loop_val else _BTN_HOV)

    # ↑↓✕ buttons
    bw3 = (w - 20) // 3
    _btn(screen, "↑", pygame.Rect(x + 4, ctrl_y, bw3, _BTN_H))
    _btn(screen, "↓", pygame.Rect(x + 8 + bw3, ctrl_y, bw3, _BTN_H))
    _btn(screen, "✕", pygame.Rect(x + 12 + bw3 * 2, ctrl_y, bw3, _BTN_H), _RED_BG, _RED_HOV)


def handle_anim_panel_click(state: EditorState, mx: int, my: int,
                             panel_rect: pygame.Rect) -> str | None:
    y = panel_rect.y
    x = panel_rect.x
    w = panel_rect.width

    y += _SECTION_H
    for i in range(min(len(state.anim_sets), _MAX_LIST)):
        if pygame.Rect(x, y, w, _ITEM_H).collidepoint(mx, my):
            state.active_anim_set = i
            state.active_anim_clip = 0
            state.active_anim_frame = 0
            return None
        y += _ITEM_H

    bw = (w - 16) // 2
    if pygame.Rect(x + 4, y + 4, bw, _BTN_H).collidepoint(mx, my):
        return "add_set"
    if pygame.Rect(x + 8 + bw, y + 4, bw, _BTN_H).collidepoint(mx, my):
        anim_remove_set(state)
        return None
    y += _BTN_H + 12

    y += _SECTION_H
    active_set = state.anim_sets[state.active_anim_set] if state.anim_sets else None
    clips = active_set.clips if active_set else []

    for i in range(min(len(clips), _MAX_LIST)):
        if pygame.Rect(x, y, w, _ITEM_H).collidepoint(mx, my):
            state.active_anim_clip = i
            state.active_anim_frame = 0
            return None
        y += _ITEM_H

    if pygame.Rect(x + 4, y + 4, bw, _BTN_H).collidepoint(mx, my):
        return "add_clip"
    if pygame.Rect(x + 8 + bw, y + 4, bw, _BTN_H).collidepoint(mx, my):
        anim_remove_clip(state)
        return None
    y += _BTN_H + 12

    y += _SECTION_H
    clip = get_active_clip(state)

    ctrl_y, extra_top, bws = _compute_ctrl_positions(panel_rect, x, w)
    visible_h = extra_top - y - 4
    visible_n = max(1, visible_h // _ITEM_H)

    if clip:
        for i in range(min(len(clip.frames), visible_n)):
            if pygame.Rect(x, y, w, _ITEM_H).collidepoint(mx, my):
                state.active_anim_frame = i
                return None
            y += _ITEM_H

    # extra controls
    cy = extra_top + 4

    f_minus = pygame.Rect(x + w - bws * 2 - 6, cy, bws, _CTRL_ROW_H)
    f_plus  = pygame.Rect(x + w - bws - 4,     cy, bws, _CTRL_ROW_H)
    if f_minus.collidepoint(mx, my):
        anim_adjust_frame_delay(state, state.active_anim_frame, -10)
        return None
    if f_plus.collidepoint(mx, my):
        anim_adjust_frame_delay(state, state.active_anim_frame, +10)
        return None
    cy += _CTRL_ROW_H + _CTRL_PAD

    c_minus = pygame.Rect(x + w - bws * 2 - 6, cy, bws, _CTRL_ROW_H)
    c_plus  = pygame.Rect(x + w - bws - 4,     cy, bws, _CTRL_ROW_H)
    if c_minus.collidepoint(mx, my):
        anim_adjust_clip_delay(state, -10)
        return None
    if c_plus.collidepoint(mx, my):
        anim_adjust_clip_delay(state, +10)
        return None
    cy += _CTRL_ROW_H + _CTRL_PAD

    loop_rect = pygame.Rect(x + 4, cy, w - 8, _CTRL_ROW_H)
    if loop_rect.collidepoint(mx, my):
        anim_toggle_loop(state)
        return None

    # ↑↓✕ buttons
    bw3 = (w - 20) // 3
    if pygame.Rect(x + 4, ctrl_y, bw3, _BTN_H).collidepoint(mx, my):
        anim_move_frame_up(state, state.active_anim_frame)
    elif pygame.Rect(x + 8 + bw3, ctrl_y, bw3, _BTN_H).collidepoint(mx, my):
        anim_move_frame_down(state, state.active_anim_frame)
    elif pygame.Rect(x + 12 + bw3 * 2, ctrl_y, bw3, _BTN_H).collidepoint(mx, my):
        anim_remove_frame(state, state.active_anim_frame)

    return None
