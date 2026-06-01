import pygame

from canvas import bresenham_line, screen_to_tile
from config import (
    FPS,
    MAX_ZOOM,
    MIN_ZOOM,
    PANEL_W,
    STATUS_H,
    TOOLBAR_H,
    WINDOW_H,
    WINDOW_W,
    ZOOM_STEP,
)
from editor import (
    EditorState,
    Mode,
    create_empty_state,
    redo,
    undo,
    paint_visual,
    paint_collision,
    place_entity,
    remove_entity,
    take_snapshot,
    push_undo,
)


def check_keydown(event: pygame.event.Event, state: EditorState) -> None:
    ctrl = pygame.key.get_mods() & pygame.KMOD_CTRL

    match event.key:
        case pygame.K_z if ctrl:
            if pygame.key.get_mods() & pygame.KMOD_SHIFT:
                redo(state)
            else:
                undo(state)
        case pygame.K_y if ctrl:
            redo(state)
        case pygame.K_s if ctrl:
            pass  # salvar — implementar quando importer.py estiver pronto
        case pygame.K_e if ctrl:
            pass  # exportar — implementar quando exporter.py estiver pronto
        case pygame.K_TAB:
            modes = list(Mode)
            current = modes.index(state.active_mode)
            state.active_mode = modes[(current + 1) % len(modes)]


def paint_tile(state: EditorState, col: int, row: int, erase: bool) -> None:
    match state.active_mode:
        case Mode.VISUAL:
            paint_visual(state, col, row, 0 if erase else state.selected_visual_tile)
        case Mode.COLLISION:
            paint_collision(
                state, col, row, 0 if erase else state.selected_collision_id
            )
        case Mode.ENTITY:
            if erase:
                remove_entity(state, col, row)
            else:
                place_entity(state, col, row, state.selected_entity_id)


def check_mousebuttondown(
    event: pygame.event.Event,
    state: EditorState,
    canvas_rect: pygame.Rect,
    panel_rect: pygame.Rect,
    toolbar_rect: pygame.Rect,
    mouse_state: dict,
) -> None:
    mx, my = event.pos

    if canvas_rect.collidepoint(mx, my):
        mouse_state["down"] = True
        mouse_state["snapshot_before"] = take_snapshot(state)
        col, row = screen_to_tile(mx, my, state, canvas_rect)
        erase = event.button == 3
        paint_tile(state, col, row, erase)
        mouse_state["prev_tile"] = (col, row)

    elif panel_rect.collidepoint(mx, my):
        pass  # implementar quando panels.py estiver pronto

    elif toolbar_rect.collidepoint(mx, my):
        pass  # implementar quando panels.py estiver pronto


def check_mousebuttonup(
    event: pygame.event.Event,
    state: EditorState,
    mouse_state: dict,
) -> None:
    if event.button in (1, 3) and mouse_state["down"]:
        if mouse_state["snapshot_before"] is not None:
            push_undo(state, mouse_state["snapshot_before"])
        mouse_state["down"] = False
        mouse_state["prev_tile"] = None
        mouse_state["snapshot_before"] = None


def check_mousemotion(
    event: pygame.event.Event,
    state: EditorState,
    canvas_rect: pygame.Rect,
    mouse_state: dict,
) -> None:
    if not mouse_state["down"]:
        return
    if state.active_mode == Mode.ENTITY:
        return

    mx, my = event.pos
    if not canvas_rect.collidepoint(mx, my):
        return

    col, row = screen_to_tile(mx, my, state, canvas_rect)
    prev = mouse_state["prev_tile"]

    if prev is None or prev == (col, row):
        mouse_state["prev_tile"] = (col, row)
        return

    erase = pygame.mouse.get_pressed()[2]
    for c, r in bresenham_line(prev[0], prev[1], col, row):
        paint_tile(state, c, r, erase)

    mouse_state["prev_tile"] = (col, row)


def check_mousewheel(
    event: pygame.event.Event,
    state: EditorState,
    canvas_rect: pygame.Rect,
) -> None:
    mx, my = pygame.mouse.get_pos()
    if not canvas_rect.collidepoint(mx, my):
        return

    # ponto do mundo sob o cursor antes do zoom
    world_x = (mx - canvas_rect.x) / state.zoom + state.camera_x
    world_y = (my - canvas_rect.y) / state.zoom + state.camera_y

    new_zoom = state.zoom + event.y * ZOOM_STEP
    new_zoom = max(MIN_ZOOM, min(MAX_ZOOM, new_zoom))
    state.zoom = new_zoom

    # reposiciona câmera para manter o ponto sob o cursor
    state.camera_x = world_x - (mx - canvas_rect.x) / state.zoom
    state.camera_y = world_y - (my - canvas_rect.y) / state.zoom


def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
    pygame.display.set_caption("RITMO - RISC-V Interactive Tilemap and Map Output")

    editor_state = create_empty_state(300, 300, 16, 16)
    clock = pygame.time.Clock()

    toolbar_rect = pygame.Rect(0, 0, WINDOW_W, TOOLBAR_H)
    canvas_rect = pygame.Rect(
        0, TOOLBAR_H, WINDOW_W - PANEL_W, WINDOW_H - TOOLBAR_H - STATUS_H
    )
    panel_rect = pygame.Rect(
        WINDOW_W - PANEL_W, TOOLBAR_H, PANEL_W, WINDOW_H - TOOLBAR_H - STATUS_H
    )
    status_rect = pygame.Rect(0, WINDOW_H - STATUS_H, WINDOW_W, STATUS_H)

    mouse_state: dict = {
        "down": False,
        "prev_tile": None,
        "snapshot_before": None,
    }

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                check_keydown(event, editor_state)
            if event.type == pygame.MOUSEBUTTONDOWN:
                check_mousebuttondown(
                    event,
                    editor_state,
                    canvas_rect,
                    panel_rect,
                    toolbar_rect,
                    mouse_state,
                )
            if event.type == pygame.MOUSEBUTTONUP:
                check_mousebuttonup(event, editor_state, mouse_state)
            if event.type == pygame.MOUSEMOTION:
                check_mousemotion(event, editor_state, canvas_rect, mouse_state)
            if event.type == pygame.MOUSEWHEEL:
                check_mousewheel(event, editor_state, canvas_rect)

        clock.tick(FPS)

    pygame.quit()


if __name__ == "__main__":
    main()
