import pygame
from config import BG_COLOR, EMPTY_TILE_BG, GRID_COLOR, SELECTION_COLOR
from editor import EditorState, Mode, tile_index


def bresenham_line(x0: int, y0: int, x1: int, y1: int) -> list[tuple[int, int]]:
    points = []
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy

    while True:
        points.append((x0, y0))
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy

    return points


def screen_to_tile(
    mouse_x: int, mouse_y: int, state: EditorState, canvas_rect: pygame.Rect
) -> tuple[int, int]:
    world_x = (mouse_x - canvas_rect.x) / state.zoom + state.camera_x
    world_y = (mouse_y - canvas_rect.y) / state.zoom + state.camera_y
    col = int(world_x // state.tile_w)
    row = int(world_y // state.tile_h)
    return (col, row)


def tile_to_screen(
    col: int, row: int, state: EditorState, canvas_rect: pygame.Rect
) -> tuple[float, float]:
    screen_x = (col * state.tile_w - state.camera_x) * state.zoom + canvas_rect.x
    screen_y = (row * state.tile_h - state.camera_y) * state.zoom + canvas_rect.y

    return (screen_x, screen_y)


def get_visible_range(
    state: EditorState, canvas_rect: pygame.Rect
) -> tuple[int, int, int, int]:
    first_col = max(0, int(state.camera_x / state.tile_w))
    last_col = min(
        state.map_cols,
        first_col + int(canvas_rect.width / (state.tile_w * state.zoom)) + 2,
    )
    first_row = max(0, int(state.camera_y / state.tile_h))
    last_row = min(
        state.map_rows,
        first_row + int(canvas_rect.height / (state.tile_h * state.zoom)) + 2,
    )

    return (first_col, last_col, first_row, last_row)


def draw_entity_icon(
    screen: pygame.Surface,
    etype,
    x: int,
    y: int,
    w: int,
    h: int,
) -> None:
    if etype.sprite_surface:
        spr = pygame.transform.scale(etype.sprite_surface, (w, h))
        screen.blit(spr, (x, y))
    else:
        pygame.draw.rect(screen, etype.color[:3], (x, y, w, h))
        font = pygame.font.SysFont(None, max(10, h // 2))
        label = font.render(etype.name[:2].upper(), True, (255, 255, 255))
        screen.blit(label, (x + 2, y + 2))


def draw_canvas(
    screen: pygame.Surface, state: EditorState, canvas_rect: pygame.Rect
) -> None:

    pygame.draw.rect(screen, BG_COLOR, canvas_rect)

    first_col, last_col, first_row, last_row = get_visible_range(state, canvas_rect)

    tile_w_scaled = int(state.tile_w * state.zoom)
    tile_h_scaled = int(state.tile_h * state.zoom)

    for row in range(first_row, last_row):
        for col in range(first_col, last_col):
            screen_x, screen_y = tile_to_screen(col, row, state, canvas_rect)
            screen_x = int(screen_x)
            screen_y = int(screen_y)

            idx = tile_index(col, row, state.map_cols)
            visual_id = state.visual_layer[idx]

            if visual_id == 0 or not state.tile_surfaces:
                pygame.draw.rect(screen, EMPTY_TILE_BG, (screen_x, screen_y, tile_w_scaled, tile_h_scaled))
            else:
                surface = pygame.transform.scale(state.tile_surfaces[visual_id], (tile_w_scaled, tile_h_scaled))
                screen.blit(surface, (screen_x, screen_y))

            if state.active_mode in (Mode.COLLISION, Mode.ENTITY):
                collision_id = state.collision_layer[idx]
                col_type = next((ct for ct in state.collision_types if ct.id == collision_id), None)
                if col_type and col_type.color[3] > 0:
                    overlay = pygame.Surface((tile_w_scaled, tile_h_scaled), pygame.SRCALPHA)
                    overlay.fill(col_type.color)
                    screen.blit(overlay, (screen_x, screen_y))

    # entidades
    for entity in state.entities:
        if first_col <= entity.col < last_col and first_row <= entity.row < last_row:
            ex, ey = tile_to_screen(entity.col, entity.row, state, canvas_rect)
            ex, ey = int(ex), int(ey)
            etype = next((et for et in state.entity_types if et.id == entity.type_id), None)
            if etype:
                draw_entity_icon(screen, etype, ex, ey, tile_w_scaled, tile_h_scaled)

    # grade
    if state.zoom >= 1.5:
        grid_color = GRID_COLOR[:3]
        for c in range(first_col, last_col + 1):
            x = int(tile_to_screen(c, 0, state, canvas_rect)[0])
            top = int(tile_to_screen(0, first_row, state, canvas_rect)[1])
            bot = int(tile_to_screen(0, last_row, state, canvas_rect)[1])
            pygame.draw.line(screen, grid_color, (x, top), (x, bot))
        for r in range(first_row, last_row + 1):
            y = int(tile_to_screen(0, r, state, canvas_rect)[1])
            left  = int(tile_to_screen(first_col, 0, state, canvas_rect)[0])
            right = int(tile_to_screen(last_col,  0, state, canvas_rect)[0])
            pygame.draw.line(screen, grid_color, (left, y), (right, y))

    # highlight do tile sob o cursor
    mx, my = pygame.mouse.get_pos()
    if canvas_rect.collidepoint(mx, my):
        hcol, hrow = screen_to_tile(mx, my, state, canvas_rect)
        if 0 <= hcol < state.map_cols and 0 <= hrow < state.map_rows:
            hx, hy = tile_to_screen(hcol, hrow, state, canvas_rect)
            pygame.draw.rect(screen, SELECTION_COLOR, (int(hx), int(hy), tile_w_scaled, tile_h_scaled), 2)
