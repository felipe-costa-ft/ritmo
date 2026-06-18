import pygame

from canvas import (bresenham_line, draw_anim_canvas, draw_canvas,
                    pixel_to_sheet_tile, screen_to_tile, tile_to_screen)
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
    get_font,
)
from dialogs import (
    _open_file_dialog,
    dialog_new_anim_clip,
    dialog_new_anim_set,
    dialog_new_collision_type,
    dialog_new_entity_type,
    dialog_new_project,
    dialog_resize_map,
)
from editor import (
    EditorState,
    Mode,
    anim_add_clip,
    anim_add_frame,
    anim_add_set,
    copy_region,
    create_empty_state,
    fill_rect,
    flood_fill,
    load_tileset,
    paint_collision,
    paint_visual,
    paste_at,
    place_entity,
    push_undo,
    redo,
    remove_entity,
    resize_map,
    stamp_brush,
    take_snapshot,
    undo,
    update_anim_preview,
)
from exporter import export_all
from importer import load_project, save_project
from panels import (
    draw_panel,
    draw_statusbar,
    draw_toolbar,
    handle_panel_click,
    handle_toolbar_click,
    try_scrollbar_drag,
    update_brush_drag,
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
        case pygame.K_c if ctrl:
            copy_region(state)
        case pygame.K_v if ctrl:
            if state.clipboard_visual is not None:
                state.paste_mode = True
        case pygame.K_s if ctrl:
            pass
        case pygame.K_e if ctrl:
            pass
        case pygame.K_ESCAPE:
            state.paste_mode = False
            state.selection = None
        case pygame.K_TAB:
            modes = list(Mode)
            current = modes.index(state.active_mode)
            state.active_mode = modes[(current + 1) % len(modes)]


def paint_tile(state: EditorState, col: int, row: int, erase: bool) -> None:
    match state.active_mode:
        case Mode.VISUAL:
            if erase:
                paint_visual(state, col, row, 0)
            elif state.brush_cols == 1 and state.brush_rows == 1:
                paint_visual(state, col, row, state.selected_visual_tile)
            else:
                stamp_brush(state, col, row)
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
    screen: pygame.Surface,
) -> str | None:
    """Retorna ação de toolbar ('new','open','save','export') ou None."""
    mx, my = event.pos

    if canvas_rect.collidepoint(mx, my):
        if state.active_mode == Mode.ANIMATION:
            if event.button == 1:
                idx = pixel_to_sheet_tile(mx, my, state, canvas_rect)
                if idx is not None:
                    anim_add_frame(state, idx)
                else:
                    from canvas import _draw_anim_preview
                    pw, ph = 160, 160
                    btn = pygame.Rect(
                        canvas_rect.right - pw // 2 - 30 - 8,
                        canvas_rect.bottom - ph - 8 + ph - 22,
                        60, 18,
                    )
                    if btn.collidepoint(mx, my):
                        state.anim_preview_playing = not state.anim_preview_playing
                        state.anim_preview_t = 0.0
                        if state.anim_preview_playing:
                            state.anim_preview_frame = 0
            elif event.button == 4:
                state.anim_sheet_scroll = max(0, state.anim_sheet_scroll - 1)
            elif event.button == 5:
                state.anim_sheet_scroll += 1
            return None

        if event.button == 2:
            mouse_state["panning"] = True
            mouse_state["pan_last"] = (mx, my)
        elif event.button in (1, 3):
            mods = pygame.key.get_mods()
            col, row = screen_to_tile(mx, my, state, canvas_rect)
            erase = event.button == 3

            if state.paste_mode and event.button == 1:
                snapshot = take_snapshot(state)
                paste_at(state, col, row)
                push_undo(state, snapshot)
                state.paste_mode = False
                state.selection = None

            elif mods & pygame.KMOD_ALT and event.button == 1:
                mouse_state["sel_start"] = (col, row)

            elif mods & pygame.KMOD_CTRL and not erase and state.active_mode != Mode.ENTITY:
                state.selection = None
                snapshot = take_snapshot(state)
                tile_id = (state.selected_visual_tile if state.active_mode == Mode.VISUAL
                           else state.selected_collision_id)
                flood_fill(state, col, row, tile_id)
                push_undo(state, snapshot)

            elif mods & pygame.KMOD_SHIFT and state.active_mode != Mode.ENTITY:
                state.selection = None
                mouse_state["rect_start"] = (col, row)
                mouse_state["snapshot_before"] = take_snapshot(state)

            else:
                state.selection = None
                mouse_state["down"] = True
                mouse_state["snapshot_before"] = take_snapshot(state)
                paint_tile(state, col, row, erase)
                mouse_state["prev_tile"] = (col, row)

    elif panel_rect.collidepoint(mx, my):
        drag = try_scrollbar_drag(state, mx, my, panel_rect)
        if drag is not None:
            mouse_state["scrollbar_drag"] = drag
            return None
        action = handle_panel_click(state, mx, my, panel_rect)
        if action == "add_set":
            name = dialog_new_anim_set(screen)
            if name:
                anim_add_set(state, name)
        elif action == "add_clip":
            result = dialog_new_anim_clip(screen)
            if result:
                anim_add_clip(state, result[0], result[1], result[2])
        elif action:
            if state.active_mode == Mode.COLLISION:
                existing = {ct.id for ct in state.collision_types}
                new_ct = dialog_new_collision_type(screen, existing)
                if new_ct:
                    state.collision_types.append(new_ct)
            elif state.active_mode == Mode.ENTITY:
                existing = {et.id for et in state.entity_types}
                new_et = dialog_new_entity_type(screen, existing)
                if new_et:
                    state.entity_types.append(new_et)

    elif toolbar_rect.collidepoint(mx, my):
        return handle_toolbar_click(state, mx, my, toolbar_rect)

    return None


def check_mousebuttonup(
    event: pygame.event.Event,
    state: EditorState,
    canvas_rect: pygame.Rect,
    mouse_state: dict,
) -> None:
    if event.button == 2:
        mouse_state["panning"] = False
        mouse_state["pan_last"] = None
    elif event.button in (1, 3):
        mouse_state["scrollbar_drag"] = None
        state.brush_drag_start = None

        if mouse_state.get("sel_start") is not None and event.button == 1:
            mx, my = event.pos
            col, row = screen_to_tile(mx, my, state, canvas_rect)
            c0, r0 = mouse_state["sel_start"]
            sc = min(c0, col)
            sr = min(r0, row)
            scols = abs(col - c0) + 1
            srows = abs(row - r0) + 1
            state.selection = (
                max(0, sc), max(0, sr),
                min(scols, state.map_cols - max(0, sc)),
                min(srows, state.map_rows - max(0, sr)),
            )
            mouse_state["sel_start"] = None

        elif mouse_state["rect_start"] is not None:
            mx, my = event.pos
            col, row = screen_to_tile(mx, my, state, canvas_rect)
            c0, r0 = mouse_state["rect_start"]
            erase = event.button == 3
            tile_id = (
                0
                if erase
                else (
                    state.selected_visual_tile
                    if state.active_mode == Mode.VISUAL
                    else state.selected_collision_id
                )
            )
            fill_rect(state, c0, r0, col, row, tile_id)
            push_undo(state, mouse_state["snapshot_before"])
            mouse_state["rect_start"] = None
            mouse_state["snapshot_before"] = None
        elif mouse_state["down"]:
            if mouse_state["snapshot_before"] is not None:
                push_undo(state, mouse_state["snapshot_before"])
            mouse_state["down"] = False
            mouse_state["prev_tile"] = None
            mouse_state["snapshot_before"] = None


def check_mousemotion(
    event: pygame.event.Event,
    state: EditorState,
    canvas_rect: pygame.Rect,
    panel_rect: pygame.Rect,
    mouse_state: dict,
) -> None:
    mx, my = event.pos

    if mouse_state.get("scrollbar_drag") is not None:
        drag = mouse_state["scrollbar_drag"]
        if drag["axis"] == "v":
            delta_px = my - drag["pixel_origin"]
            new_val = drag["scroll_origin"] + int(delta_px / drag["pixels_per_unit"])
            state.panel_scroll = max(0, new_val)
        else:
            delta_px = mx - drag["pixel_origin"]
            new_val = drag["scroll_origin"] + int(delta_px / drag["pixels_per_unit"])
            state.panel_scroll_x = max(0, new_val)
        return

    if mouse_state.get("panning") and mouse_state.get("pan_last"):
        lx, ly = mouse_state["pan_last"]
        state.camera_x -= (mx - lx) / state.zoom
        state.camera_y -= (my - ly) / state.zoom
        mouse_state["pan_last"] = (mx, my)
        return

    if state.brush_drag_start is not None:
        update_brush_drag(state, mx, my, panel_rect)
        return

    if not mouse_state["down"]:
        return
    if state.active_mode == Mode.ENTITY:
        return

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
    panel_rect: pygame.Rect,
) -> None:
    mx, my = pygame.mouse.get_pos()

    if panel_rect.collidepoint(mx, my):
        if state.active_mode == Mode.VISUAL:
            mods = pygame.key.get_mods()
            if mods & pygame.KMOD_SHIFT:
                # Shift + roda → scroll horizontal
                state.panel_scroll_x = max(0, state.panel_scroll_x - event.y)
            else:
                state.panel_scroll = max(0, state.panel_scroll - event.y)
            # Trackpad: evento horizontal (event.x) → sempre scroll horizontal
            if event.x:
                state.panel_scroll_x = max(0, state.panel_scroll_x + event.x)
        else:
            state.panel_scroll = max(0, state.panel_scroll - event.y)
        return

    if not canvas_rect.collidepoint(mx, my):
        return

    world_x = (mx - canvas_rect.x) / state.zoom + state.camera_x
    world_y = (my - canvas_rect.y) / state.zoom + state.camera_y

    new_zoom = state.zoom + event.y * ZOOM_STEP
    new_zoom = max(MIN_ZOOM, min(MAX_ZOOM, new_zoom))
    state.zoom = new_zoom

    state.camera_x = world_x - (mx - canvas_rect.x) / state.zoom
    state.camera_y = world_y - (my - canvas_rect.y) / state.zoom


def _ask_string(screen: pygame.Surface, prompt: str, default: str = "") -> str | None:
    sw, sh = screen.get_size()
    dw, dh = 400, 130
    dx, dy = (sw - dw) // 2, (sh - dh) // 2
    value = default
    clock = pygame.time.Clock()
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return None
                elif event.key == pygame.K_RETURN:
                    return value
                elif event.key == pygame.K_BACKSPACE:
                    value = value[:-1]
                elif event.unicode.isprintable():
                    value += event.unicode

        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        screen.blit(overlay, (0, 0))
        pygame.draw.rect(screen, (45, 45, 45), (dx, dy, dw, dh), border_radius=8)
        pygame.draw.rect(screen, (90, 90, 90), (dx, dy, dw, dh), 1, border_radius=8)

        font = get_font(16)
        screen.blit(font.render(prompt, True, (200, 200, 200)), (dx + 16, dy + 16))

        input_rect = pygame.Rect(dx + 16, dy + 40, dw - 32, 32)
        pygame.draw.rect(screen, (30, 30, 30), input_rect, border_radius=4)
        pygame.draw.rect(screen, (90, 90, 90), input_rect, 1, border_radius=4)
        cursor = "|" if (pygame.time.get_ticks() // 500) % 2 == 0 else ""
        screen.blit(
            font.render(value + cursor, True, (255, 255, 255)),
            (input_rect.x + 6, input_rect.y + 8),
        )

        hint = font.render("Enter confirma • Esc cancela", True, (120, 120, 120))
        screen.blit(hint, (dx + 16, dy + dh - 22))

        pygame.display.flip()
        clock.tick(60)


def _handle_toolbar_action(
    action: str, state: EditorState, screen: pygame.Surface
) -> None:
    if action == "new":
        result = dialog_new_project(screen)
        if result:
            new_state = create_empty_state(
                result["map_cols"],
                result["map_rows"],
                result["tile_w"],
                result["tile_h"],
            )
            if result["tileset_path"]:
                load_tileset(new_state, result["tileset_path"])
            state.__dict__.update(new_state.__dict__)

    elif action == "open":
        path = _open_file_dialog(screen, "Abrir projeto", ext_filter=".json")
        if path:
            try:
                loaded = load_project(path)
                state.__dict__.update(loaded.__dict__)
            except Exception as e:
                print(f"Erro ao abrir projeto: {e}")

    elif action == "save":
        path = _open_file_dialog(
            screen, "Salvar projeto", ext_filter=".json", save=True
        )
        if path:
            if not path.endswith(".json"):
                path += ".json"
            try:
                save_project(state, path)
            except Exception as e:
                print(f"Erro ao salvar projeto: {e}")

    elif action == "resize":
        result = dialog_resize_map(screen, state.map_cols, state.map_rows)
        if result:
            resize_map(state, result["map_cols"], result["map_rows"])

    elif action == "export":
        out_dir = _open_file_dialog(screen, "Diretório de exportação", directory=True)
        if out_dir:
            prefix = _ask_string(
                screen, "Prefixo dos labels assembly (ex: FASE1):", "MAPA"
            )
            if prefix:
                paths = export_all(state, out_dir, prefix.upper())
                print("Exportado:")
                for p in paths:
                    print(" ", p)


def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
    pygame.display.set_caption("RITMO - RISC-V Interactive Tilemap and Map Output")

    editor_state = create_empty_state(20, 15, 16, 16)
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
        "panning": False,
        "pan_last": None,
        "rect_start": None,
        "sel_start": None,
        "scrollbar_drag": None,
    }

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                check_keydown(event, editor_state)
            if event.type == pygame.MOUSEBUTTONDOWN:
                action = check_mousebuttondown(
                    event,
                    editor_state,
                    canvas_rect,
                    panel_rect,
                    toolbar_rect,
                    mouse_state,
                    screen,
                )
                if action:
                    _handle_toolbar_action(action, editor_state, screen)
            if event.type == pygame.MOUSEBUTTONUP:
                check_mousebuttonup(event, editor_state, canvas_rect, mouse_state)
            if event.type == pygame.MOUSEMOTION:
                check_mousemotion(event, editor_state, canvas_rect, panel_rect, mouse_state)
            if event.type == pygame.MOUSEWHEEL:
                check_mousewheel(event, editor_state, canvas_rect, panel_rect)

        # render
        draw_toolbar(screen, editor_state, toolbar_rect)
        if editor_state.active_mode == Mode.ANIMATION:
            draw_anim_canvas(screen, editor_state, canvas_rect)
        else:
            draw_canvas(screen, editor_state, canvas_rect)

        if mouse_state["sel_start"] is not None:
            mx, my = pygame.mouse.get_pos()
            col, row = screen_to_tile(mx, my, editor_state, canvas_rect)
            c0, r0 = mouse_state["sel_start"]
            sx, sy = tile_to_screen(min(c0, col), min(r0, row), editor_state, canvas_rect)
            ex, ey = tile_to_screen(max(c0, col) + 1, max(r0, row) + 1, editor_state, canvas_rect)
            sx, sy, ex, ey = int(sx), int(sy), int(ex), int(ey)
            rw, rh = ex - sx, ey - sy
            if rw > 0 and rh > 0:
                ov = pygame.Surface((rw, rh), pygame.SRCALPHA)
                ov.fill((80, 160, 255, 60))
                screen.blit(ov, (sx, sy))
                pygame.draw.rect(screen, (80, 160, 255), (sx, sy, rw, rh), 2)

        if mouse_state["rect_start"] is not None:
            mx, my = pygame.mouse.get_pos()
            col, row = screen_to_tile(mx, my, editor_state, canvas_rect)
            c0, r0 = mouse_state["rect_start"]
            tw = int(editor_state.tile_w * editor_state.zoom)
            th = int(editor_state.tile_h * editor_state.zoom)
            sx, sy = tile_to_screen(
                min(c0, col), min(r0, row), editor_state, canvas_rect
            )
            ex, ey = tile_to_screen(
                max(c0, col) + 1, max(r0, row) + 1, editor_state, canvas_rect
            )
            sx, sy, ex, ey = int(sx), int(sy), int(ex), int(ey)
            rw, rh = ex - sx, ey - sy
            if rw > 0 and rh > 0:
                overlay = pygame.Surface((rw, rh), pygame.SRCALPHA)
                overlay.fill((255, 200, 0, 60))
                screen.blit(overlay, (sx, sy))
                pygame.draw.rect(screen, (255, 200, 0), (sx, sy, rw, rh), 2)

        draw_panel(screen, editor_state, panel_rect)

        mx, my = pygame.mouse.get_pos()
        mc, mr = screen_to_tile(mx, my, editor_state, canvas_rect)
        draw_statusbar(screen, editor_state, status_rect, mc, mr)

        pygame.display.flip()
        dt = clock.tick(FPS)
        update_anim_preview(editor_state, dt)

    pygame.quit()


if __name__ == "__main__":
    main()
