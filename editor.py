from dataclasses import dataclass
from enum import Enum
from typing import Optional

from PIL import Image as PILImage
from pygame import Surface

from config import UNDO_STACK_LIMIT


@dataclass
class CollisionType:
    id: int
    name: str
    color: tuple


@dataclass
class EntityType:
    id: int
    name: str
    color: tuple
    sprite_surface: Optional[Surface]


@dataclass
class Entity:
    type_id: int
    col: int
    row: int


class Mode(Enum):
    VISUAL = 1
    COLLISION = 2
    ENTITY = 3
    ANIMATION = 4


@dataclass
class AnimFrame:
    tile_id: int
    delay_ms: int


@dataclass
class AnimClip:
    name: str
    frames: list
    default_delay_ms: int
    loop: bool


@dataclass
class AnimSet:
    name: str
    clips: list


@dataclass
class EditorState:

    map_cols: int
    map_rows: int
    tile_w: int
    tile_h: int
    tileset_path: str

    visual_layer: list[int]
    collision_layer: list[int]

    entities: list[Entity]

    tileset_image: Optional[PILImage.Image]
    tileset_cols: int
    tileset_rows: int
    tile_surfaces: list[Surface]

    collision_types: list[CollisionType]
    entity_types: list[EntityType]

    active_mode: Mode
    selected_visual_tile: int
    selected_collision_id: int
    selected_entity_id: int

    zoom: float
    camera_x: int
    camera_y: int

    panel_scroll: int
    panel_scroll_x: int

    brush: list[list[int]]
    brush_cols: int
    brush_rows: int
    brush_drag_start: Optional[tuple[int, int]]

    selection: Optional[tuple[int, int, int, int]]  # col, row, cols, rows
    clipboard_visual: Optional[list[list[int]]]
    clipboard_collision: Optional[list[list[int]]]
    clipboard_cols: int
    clipboard_rows: int
    paste_mode: bool

    anim_sets: list
    active_anim_set: int
    active_anim_clip: int
    active_anim_frame: int
    anim_preview_playing: bool
    anim_preview_t: float
    anim_preview_frame: int
    anim_sheet_scroll: int

    undo_stack: list[tuple]
    redo_stack: list[tuple]


def create_empty_state(
    map_cols: int, map_rows: int, tile_w: int, tile_h: int
) -> EditorState:
    n = map_cols * map_rows
    return EditorState(
        map_cols=map_cols,
        map_rows=map_rows,
        tile_w=tile_w,
        tile_h=tile_h,
        tileset_path="",
        visual_layer=[0] * n,
        collision_layer=[0] * n,
        entities=[],
        tileset_image=None,
        tileset_cols=0,
        tileset_rows=0,
        tile_surfaces=[],
        collision_types=[CollisionType(id=0, name="vazio", color=(0, 0, 0, 0))],
        entity_types=[],
        active_mode=Mode.VISUAL,
        selected_visual_tile=0,
        selected_collision_id=0,
        selected_entity_id=0,
        zoom=1.0,
        camera_x=0,
        camera_y=0,
        panel_scroll=0,
        panel_scroll_x=0,
        brush=[[0]],
        brush_cols=1,
        brush_rows=1,
        brush_drag_start=None,
        selection=None,
        clipboard_visual=None,
        clipboard_collision=None,
        clipboard_cols=0,
        clipboard_rows=0,
        paste_mode=False,
        anim_sets=[],
        active_anim_set=0,
        active_anim_clip=0,
        active_anim_frame=0,
        anim_preview_playing=False,
        anim_preview_t=0.0,
        anim_preview_frame=0,
        anim_sheet_scroll=0,
        undo_stack=[],
        redo_stack=[],
    )


def load_tileset(state: EditorState, path: str) -> None:
    import pygame

    tile_w = state.tile_w
    tile_h = state.tile_h

    image = PILImage.open(path).convert("RGBA")

    state.tileset_cols = image.width // tile_w
    state.tileset_rows = image.height // tile_h
    state.tileset_image = image
    state.tileset_path = path
    state.tile_surfaces = []
    state.panel_scroll = 0
    state.panel_scroll_x = 0
    state.brush = [[0]]
    state.brush_cols = 1
    state.brush_rows = 1
    state.brush_drag_start = None

    for row in range(state.tileset_rows):
        for col in range(state.tileset_cols):
            left = col * tile_w
            top = row * tile_h
            region = image.crop((left, top, left + tile_w, top + tile_h))
            surface = pygame.image.fromstring(region.tobytes(), region.size, "RGBA")
            state.tile_surfaces.append(surface)


def tile_index(col: int, row: int, map_cols: int) -> int:
    return row * map_cols + col


def paint_visual(state: EditorState, col: int, row: int, tile_id: int) -> None:
    if not (0 <= tile_id < len(state.tile_surfaces)):
        return
    if 0 <= col < state.map_cols and 0 <= row < state.map_rows:
        state.visual_layer[tile_index(col, row, state.map_cols)] = tile_id


def paint_collision(state: EditorState, col: int, row: int, type_id: int) -> None:
    if not any(ct.id == type_id for ct in state.collision_types):
        return
    if 0 <= col < state.map_cols and 0 <= row < state.map_rows:
        state.collision_layer[tile_index(col, row, state.map_cols)] = type_id


def place_entity(state: EditorState, col: int, row: int, type_id: int) -> None:
    if not any(et.id == type_id for et in state.entity_types):
        return
    existing = next((e for e in state.entities if e.col == col and e.row == row), None)
    if existing:
        existing.type_id = type_id
    else:
        state.entities.append(Entity(type_id=type_id, col=col, row=row))


def fill_rect(
    state: EditorState, c0: int, r0: int, c1: int, r1: int, tile_id: int
) -> None:
    """Preenche o retângulo [c0,c1] x [r0,r1] no layer ativo."""
    col_lo, col_hi = min(c0, c1), max(c0, c1)
    row_lo, row_hi = min(r0, r1), max(r0, r1)
    col_lo = max(0, col_lo)
    col_hi = min(state.map_cols - 1, col_hi)
    row_lo = max(0, row_lo)
    row_hi = min(state.map_rows - 1, row_hi)

    match state.active_mode:
        case Mode.VISUAL:
            if not (0 <= tile_id < len(state.tile_surfaces)):
                return
            for r in range(row_lo, row_hi + 1):
                for c in range(col_lo, col_hi + 1):
                    state.visual_layer[tile_index(c, r, state.map_cols)] = tile_id
        case Mode.COLLISION:
            if not any(ct.id == tile_id for ct in state.collision_types):
                return
            for r in range(row_lo, row_hi + 1):
                for c in range(col_lo, col_hi + 1):
                    state.collision_layer[tile_index(c, r, state.map_cols)] = tile_id


def flood_fill(state: EditorState, col: int, row: int, tile_id: int) -> None:
    """BFS flood fill no layer ativo a partir de (col, row)."""
    if not (0 <= col < state.map_cols and 0 <= row < state.map_rows):
        return

    match state.active_mode:
        case Mode.VISUAL:
            if not (0 <= tile_id < len(state.tile_surfaces)):
                return
            layer = state.visual_layer
        case Mode.COLLISION:
            if not any(ct.id == tile_id for ct in state.collision_types):
                return
            layer = state.collision_layer
        case _:
            return

    old_val = layer[tile_index(col, row, state.map_cols)]
    if old_val == tile_id:
        return

    queue = [(col, row)]
    visited = set()
    while queue:
        c, r = queue.pop()
        if (c, r) in visited:
            continue
        if not (0 <= c < state.map_cols and 0 <= r < state.map_rows):
            continue
        idx = tile_index(c, r, state.map_cols)
        if layer[idx] != old_val:
            continue
        visited.add((c, r))
        layer[idx] = tile_id
        queue.extend([(c + 1, r), (c - 1, r), (c, r + 1), (c, r - 1)])


def set_brush(state: EditorState, grid: list[list[int]]) -> None:
    if not grid or not grid[0]:
        return
    state.brush = grid
    state.brush_rows = len(grid)
    state.brush_cols = len(grid[0])
    state.selected_visual_tile = grid[0][0]


def stamp_brush(state: EditorState, col: int, row: int) -> None:
    for r, tile_row in enumerate(state.brush):
        for c, tid in enumerate(tile_row):
            rc, rr = col + c, row + r
            if 0 <= rc < state.map_cols and 0 <= rr < state.map_rows:
                if 0 <= tid < len(state.tile_surfaces):
                    state.visual_layer[tile_index(rc, rr, state.map_cols)] = tid


def copy_region(state: EditorState) -> None:
    if state.selection is None:
        return
    sc, sr, scols, srows = state.selection
    state.clipboard_visual = []
    state.clipboard_collision = []
    for r in range(srows):
        rv, rc = [], []
        for c in range(scols):
            mc, mr = sc + c, sr + r
            if 0 <= mc < state.map_cols and 0 <= mr < state.map_rows:
                idx = tile_index(mc, mr, state.map_cols)
                rv.append(state.visual_layer[idx])
                rc.append(state.collision_layer[idx])
            else:
                rv.append(0)
                rc.append(0)
        state.clipboard_visual.append(rv)
        state.clipboard_collision.append(rc)
    state.clipboard_cols = scols
    state.clipboard_rows = srows


def paste_at(state: EditorState, col: int, row: int) -> None:
    if state.clipboard_visual is None:
        return
    for r in range(state.clipboard_rows):
        for c in range(state.clipboard_cols):
            mc, mr = col + c, row + r
            if 0 <= mc < state.map_cols and 0 <= mr < state.map_rows:
                idx = tile_index(mc, mr, state.map_cols)
                state.visual_layer[idx] = state.clipboard_visual[r][c]
                state.collision_layer[idx] = state.clipboard_collision[r][c]


def remove_entity(state: EditorState, col: int, row: int) -> None:
    state.entities = [e for e in state.entities if not (e.col == col and e.row == row)]


def get_entity_at(state: EditorState, col: int, row: int) -> Optional[Entity]:
    return next((e for e in state.entities if e.col == col and e.row == row), None)


def take_snapshot(state: EditorState) -> tuple:
    return (
        state.visual_layer.copy(),
        state.collision_layer.copy(),
        [Entity(e.type_id, e.col, e.row) for e in state.entities],
    )


def push_undo(
    state: EditorState, snapshot: tuple[list[int], list[int], list[Entity]]
) -> None:
    state.undo_stack.append(snapshot)
    state.redo_stack = []
    if len(state.undo_stack) > UNDO_STACK_LIMIT:
        state.undo_stack.pop(0)


def undo(state: EditorState) -> None:
    if state.undo_stack:
        state.redo_stack.append(take_snapshot(state))
        state.visual_layer, state.collision_layer, state.entities = (
            state.undo_stack.pop()
        )


def redo(state: EditorState) -> None:
    if state.redo_stack:
        state.undo_stack.append(take_snapshot(state))
        state.visual_layer, state.collision_layer, state.entities = (
            state.redo_stack.pop()
        )


def get_active_clip(state: EditorState) -> Optional[AnimClip]:
    if not state.anim_sets:
        return None
    s = state.anim_sets[state.active_anim_set]
    if not s.clips:
        return None
    return s.clips[state.active_anim_clip]


def anim_add_set(state: EditorState, name: str) -> None:
    state.anim_sets.append(AnimSet(name=name, clips=[]))
    state.active_anim_set = len(state.anim_sets) - 1
    state.active_anim_clip = 0


def anim_remove_set(state: EditorState) -> None:
    if not state.anim_sets:
        return
    state.anim_sets.pop(state.active_anim_set)
    state.active_anim_set = max(0, state.active_anim_set - 1)
    state.active_anim_clip = 0
    state.active_anim_frame = 0


def anim_add_clip(state: EditorState, name: str, delay_ms: int, loop: bool) -> None:
    if not state.anim_sets:
        return
    s = state.anim_sets[state.active_anim_set]
    s.clips.append(AnimClip(name=name, frames=[], default_delay_ms=delay_ms, loop=loop))
    state.active_anim_clip = len(s.clips) - 1
    state.active_anim_frame = 0


def anim_remove_clip(state: EditorState) -> None:
    clip = get_active_clip(state)
    if clip is None:
        return
    s = state.anim_sets[state.active_anim_set]
    s.clips.pop(state.active_anim_clip)
    state.active_anim_clip = max(0, state.active_anim_clip - 1)
    state.active_anim_frame = 0


def anim_add_frame(state: EditorState, tile_id: int) -> None:
    clip = get_active_clip(state)
    if clip is None:
        return
    clip.frames.append(AnimFrame(tile_id=tile_id, delay_ms=0))
    state.active_anim_frame = len(clip.frames) - 1


def anim_remove_frame(state: EditorState, idx: int) -> None:
    clip = get_active_clip(state)
    if clip is None or not (0 <= idx < len(clip.frames)):
        return
    clip.frames.pop(idx)
    state.active_anim_frame = max(0, min(state.active_anim_frame, len(clip.frames) - 1))


def anim_move_frame_up(state: EditorState, idx: int) -> None:
    clip = get_active_clip(state)
    if clip is None or idx <= 0 or idx >= len(clip.frames):
        return
    clip.frames[idx - 1], clip.frames[idx] = clip.frames[idx], clip.frames[idx - 1]
    state.active_anim_frame = idx - 1


def anim_move_frame_down(state: EditorState, idx: int) -> None:
    clip = get_active_clip(state)
    if clip is None or idx < 0 or idx >= len(clip.frames) - 1:
        return
    clip.frames[idx], clip.frames[idx + 1] = clip.frames[idx + 1], clip.frames[idx]
    state.active_anim_frame = idx + 1


def anim_adjust_frame_delay(state: EditorState, idx: int, delta: int) -> None:
    clip = get_active_clip(state)
    if clip is None or not (0 <= idx < len(clip.frames)):
        return
    clip.frames[idx].delay_ms = max(0, clip.frames[idx].delay_ms + delta)


def anim_adjust_clip_delay(state: EditorState, delta: int) -> None:
    clip = get_active_clip(state)
    if clip is None:
        return
    clip.default_delay_ms = max(1, clip.default_delay_ms + delta)


def anim_toggle_loop(state: EditorState) -> None:
    clip = get_active_clip(state)
    if clip is None:
        return
    clip.loop = not clip.loop


def update_anim_preview(state: EditorState, delta_ms: float) -> None:
    clip = get_active_clip(state)
    if not state.anim_preview_playing or clip is None or not clip.frames:
        return
    frame = clip.frames[state.anim_preview_frame]
    effective = frame.delay_ms if frame.delay_ms > 0 else clip.default_delay_ms
    effective = max(1, effective)
    state.anim_preview_t += delta_ms
    if state.anim_preview_t >= effective:
        state.anim_preview_t -= effective
        next_f = state.anim_preview_frame + 1
        if next_f >= len(clip.frames):
            if clip.loop:
                state.anim_preview_frame = 0
            else:
                state.anim_preview_playing = False
                state.anim_preview_frame = len(clip.frames) - 1
        else:
            state.anim_preview_frame = next_f
