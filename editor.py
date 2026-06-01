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
