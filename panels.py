import pygame
from anim_panel import draw_anim_panel, handle_anim_panel_click
from canvas import draw_entity_icon
from config import EMPTY_TILE_BG, MIN_ZOOM, MAX_ZOOM, SELECTION_COLOR, ZOOM_STEP, get_font
from editor import EditorState, Mode, get_active_clip, get_entity_at, set_brush, tile_index

HEADER_H = 32
ITEM_H = 28
TILE_PREVIEW = 32
SCROLLBAR_SIZE = 8
PANEL_BG = (30, 30, 30)
PANEL_FG = (200, 200, 200)
BUTTON_BG = (60, 60, 60)
BUTTON_HOVER = (80, 80, 80)
ACTIVE_TAB = (70, 120, 180)


def _font(size: int = 16) -> pygame.font.Font:
    return get_font(size)


def _text(
    screen: pygame.Surface,
    msg: str,
    x: int,
    y: int,
    size: int = 16,
    color: tuple = PANEL_FG,
) -> None:
    screen.blit(_font(size).render(msg, True, color), (x, y))


def _button(
    screen: pygame.Surface, label: str, rect: pygame.Rect, active: bool = False
) -> None:
    color = ACTIVE_TAB if active else BUTTON_BG
    mx, my = pygame.mouse.get_pos()
    if not active and rect.collidepoint(mx, my):
        color = BUTTON_HOVER
    pygame.draw.rect(screen, color, rect, border_radius=4)
    pygame.draw.rect(screen, (100, 100, 100), rect, 1, border_radius=4)
    surf = _font(15).render(label, True, (255, 255, 255))
    screen.blit(
        surf,
        (
            rect.x + (rect.width - surf.get_width()) // 2,
            rect.y + (rect.height - surf.get_height()) // 2,
        ),
    )


def draw_toolbar(
    screen: pygame.Surface, state: EditorState, toolbar_rect: pygame.Rect
) -> None:
    pygame.draw.rect(screen, (50, 50, 50), toolbar_rect)
    pygame.draw.line(
        screen,
        (70, 70, 70),
        (toolbar_rect.x, toolbar_rect.bottom - 1),
        (toolbar_rect.right, toolbar_rect.bottom - 1),
    )

    bw, bh = 72, 30
    by = toolbar_rect.y + (toolbar_rect.height - bh) // 2
    x = toolbar_rect.x + 8

    for label, w in (
        ("Novo", bw),
        ("Abrir", bw),
        ("Salvar", bw),
        ("Exportar", bw),
        ("Redimensionar", 110),
    ):
        _button(screen, label, pygame.Rect(x, by, w, bh))
        x += w + 6

    x += 12
    pygame.draw.line(screen, (80, 80, 80), (x, by), (x, by + bh))
    x += 12

    for label, mode in (
        ("Visual", Mode.VISUAL),
        ("Colisão", Mode.COLLISION),
        ("Entidades", Mode.ENTITY),
        ("Animações", Mode.ANIMATION),
    ):
        _button(
            screen,
            label,
            pygame.Rect(x, by, 80, bh),
            active=(state.active_mode == mode),
        )
        x += 86

    x += 12
    pygame.draw.line(screen, (80, 80, 80), (x, by), (x, by + bh))
    x += 12

    _button(screen, "-", pygame.Rect(x, by, 28, bh))
    x += 32
    zoom_surf = _font(16).render(f"{state.zoom:.2f}x", True, PANEL_FG)
    screen.blit(zoom_surf, (x, by + (bh - zoom_surf.get_height()) // 2))
    x += 48
    _button(screen, "+", pygame.Rect(x, by, 28, bh))


def handle_toolbar_click(
    state: EditorState, mx: int, my: int, toolbar_rect: pygame.Rect
) -> str | None:
    """Retorna string de ação ('new','open','save','export','resize') ou None."""
    bw, bh = 72, 30
    by = toolbar_rect.y + (toolbar_rect.height - bh) // 2
    x = toolbar_rect.x + 8

    for action, w in (
        ("new", bw),
        ("open", bw),
        ("save", bw),
        ("export", bw),
        ("resize", 110),
    ):
        if pygame.Rect(x, by, w, bh).collidepoint(mx, my):
            return action
        x += w + 6

    x += 24
    for mode in (Mode.VISUAL, Mode.COLLISION, Mode.ENTITY, Mode.ANIMATION):
        if pygame.Rect(x, by, 80, bh).collidepoint(mx, my):
            state.active_mode = mode
            return None
        x += 86

    x += 24
    if pygame.Rect(x, by, 28, bh).collidepoint(mx, my):
        state.zoom = max(MIN_ZOOM, state.zoom - ZOOM_STEP)
    x += 32 + 48
    if pygame.Rect(x, by, 28, bh).collidepoint(mx, my):
        state.zoom = min(MAX_ZOOM, state.zoom + ZOOM_STEP)

    return None


def draw_panel(
    screen: pygame.Surface, state: EditorState, panel_rect: pygame.Rect
) -> None:
    pygame.draw.rect(screen, PANEL_BG, panel_rect)
    pygame.draw.line(
        screen,
        (70, 70, 70),
        (panel_rect.x, panel_rect.y),
        (panel_rect.x, panel_rect.bottom),
    )

    header = pygame.Rect(panel_rect.x, panel_rect.y, panel_rect.width, HEADER_H)
    pygame.draw.rect(screen, (40, 40, 40), header)
    label = {
        Mode.VISUAL: "Tileset",
        Mode.COLLISION: "Colisão",
        Mode.ENTITY: "Entidades",
        Mode.ANIMATION: "Animações",
    }[state.active_mode]
    _text(
        screen, label, panel_rect.x + 10, panel_rect.y + (HEADER_H - 16) // 2, size=18
    )

    content_rect = pygame.Rect(
        panel_rect.x,
        panel_rect.y + HEADER_H,
        panel_rect.width,
        panel_rect.height - HEADER_H,
    )
    match state.active_mode:
        case Mode.VISUAL:
            draw_tileset_panel(screen, state, content_rect)
        case Mode.COLLISION:
            draw_collision_panel(screen, state, content_rect)
        case Mode.ENTITY:
            draw_entity_panel(screen, state, content_rect)
        case Mode.ANIMATION:
            draw_anim_panel(screen, state, panel_rect)


def handle_panel_click(
    state: EditorState, mx: int, my: int, panel_rect: pygame.Rect
) -> bool:
    """Retorna True se o clique foi no botão '+ Novo tipo'."""
    content_rect = pygame.Rect(
        panel_rect.x,
        panel_rect.y + HEADER_H,
        panel_rect.width,
        panel_rect.height - HEADER_H,
    )
    match state.active_mode:
        case Mode.VISUAL:
            return _handle_tileset_click(state, mx, my, content_rect)
        case Mode.COLLISION:
            return _handle_collision_click(state, mx, my, content_rect)
        case Mode.ENTITY:
            return _handle_entity_click(state, mx, my, content_rect)
        case Mode.ANIMATION:
            action = handle_anim_panel_click(state, mx, my, panel_rect)
            return action
    return False


def _tileset_metrics(state: EditorState, content_rect: pygame.Rect) -> dict:
    """Calcula as dimensões de layout do painel de tileset.

    Preserva o número de colunas original da imagem (state.tileset_cols) e
    determina quais scrollbars são necessárias. Duas passadas para resolver a
    dependência cruzada entre as duas barras (cada uma consome espaço que pode
    tornar a outra necessária).
    """
    ts_cols = max(1, state.tileset_cols)
    ts_rows = max(1, state.tileset_rows)

    # Passada 1: checa cada scrollbar sem considerar a outra
    need_v = ts_rows * TILE_PREVIEW > content_rect.height
    need_h = ts_cols * TILE_PREVIEW > content_rect.width

    # Passada 2: reconfirma com o espaço reduzido pela outra barra
    eff_w = content_rect.width - (SCROLLBAR_SIZE if need_v else 0)
    eff_h = content_rect.height - (SCROLLBAR_SIZE if need_h else 0)
    need_h = ts_cols * TILE_PREVIEW > eff_w
    need_v = ts_rows * TILE_PREVIEW > eff_h

    draw_w = content_rect.width - (SCROLLBAR_SIZE if need_v else 0)
    draw_h = content_rect.height - (SCROLLBAR_SIZE if need_h else 0)
    visible_cols = max(1, draw_w // TILE_PREVIEW)
    visible_rows = max(1, draw_h // TILE_PREVIEW)

    return dict(
        ts_cols=ts_cols,
        ts_rows=ts_rows,
        need_h=need_h,
        need_v=need_v,
        draw_w=draw_w,
        draw_h=draw_h,
        visible_cols=visible_cols,
        visible_rows=visible_rows,
        max_scroll_x=max(0, ts_cols - visible_cols),
        max_scroll_y=max(0, ts_rows - visible_rows),
    )


def draw_tileset_panel(
    screen: pygame.Surface, state: EditorState, content_rect: pygame.Rect
) -> None:
    if not state.tile_surfaces:
        _text(
            screen,
            "Sem tileset carregado",
            content_rect.x + 10,
            content_rect.y + 10,
            color=(120, 120, 120),
        )
        return

    m = _tileset_metrics(state, content_rect)
    ts_cols = m["ts_cols"]

    # Clamp scroll dentro dos limites válidos
    state.panel_scroll = max(0, min(state.panel_scroll, m["max_scroll_y"]))
    state.panel_scroll_x = max(0, min(state.panel_scroll_x, m["max_scroll_x"]))
    scroll_y = state.panel_scroll
    scroll_x = state.panel_scroll_x

    # Pré-calcula highlight do brush usando coordenadas do tileset (não do painel)
    origin = state.selected_visual_tile
    oc = origin % ts_cols
    or_ = origin // ts_cols

    for i, surf in enumerate(state.tile_surfaces):
        tc = i % ts_cols   # coluna real no tileset
        tr = i // ts_cols  # linha real no tileset

        # Posição visível após aplicar scroll
        vc = tc - scroll_x
        vr = tr - scroll_y

        if vc < 0 or vc >= m["visible_cols"]:
            continue
        if vr < 0 or vr >= m["visible_rows"]:
            continue

        x = content_rect.x + vc * TILE_PREVIEW
        y = content_rect.y + vr * TILE_PREVIEW

        if i == 0:
            pygame.draw.rect(screen, EMPTY_TILE_BG, (x, y, TILE_PREVIEW, TILE_PREVIEW))
        scaled = pygame.transform.scale(surf, (TILE_PREVIEW, TILE_PREVIEW))
        screen.blit(scaled, (x, y))

        in_brush = (
            oc <= tc < oc + state.brush_cols
            and or_ <= tr < or_ + state.brush_rows
        )
        if in_brush:
            color = (100, 200, 255) if state.brush_drag_start else SELECTION_COLOR
            pygame.draw.rect(screen, color, (x, y, TILE_PREVIEW, TILE_PREVIEW), 2)

    # Scrollbar vertical
    if m["need_v"]:
        bar_x = content_rect.x + m["draw_w"]
        bar_h = m["draw_h"]
        thumb_h = max(16, bar_h * m["visible_rows"] // m["ts_rows"])
        thumb_y = content_rect.y + (bar_h - thumb_h) * scroll_y // max(1, m["max_scroll_y"])
        pygame.draw.rect(screen, (50, 50, 50), (bar_x, content_rect.y, SCROLLBAR_SIZE, bar_h))
        pygame.draw.rect(screen, (110, 110, 110), (bar_x, thumb_y, SCROLLBAR_SIZE, thumb_h))

    # Scrollbar horizontal
    if m["need_h"]:
        bar_y = content_rect.y + m["draw_h"]
        bar_w = m["draw_w"]
        thumb_w = max(16, bar_w * m["visible_cols"] // m["ts_cols"])
        thumb_x = content_rect.x + (bar_w - thumb_w) * scroll_x // max(1, m["max_scroll_x"])
        pygame.draw.rect(screen, (50, 50, 50), (content_rect.x, bar_y, bar_w, SCROLLBAR_SIZE))
        pygame.draw.rect(screen, (110, 110, 110), (thumb_x, bar_y, thumb_w, SCROLLBAR_SIZE))


def pixel_to_panel_tile(
    state: EditorState, mx: int, my: int, panel_rect: pygame.Rect
) -> tuple[int, int] | None:
    """Converte posição do mouse em (tileset_col, tileset_row), já com scroll aplicado."""
    if not state.tile_surfaces:
        return None
    content_x = panel_rect.x
    content_y = panel_rect.y + HEADER_H
    content_rect = pygame.Rect(
        content_x, content_y, panel_rect.width, panel_rect.bottom - content_y
    )
    m = _tileset_metrics(state, content_rect)

    if not (content_x <= mx < content_x + m["draw_w"]):
        return None
    if not (content_y <= my < content_y + m["draw_h"]):
        return None

    vc = (mx - content_x) // TILE_PREVIEW
    vr = (my - content_y) // TILE_PREVIEW
    tc = vc + state.panel_scroll_x
    tr = vr + state.panel_scroll

    if tc >= m["ts_cols"] or tr >= m["ts_rows"]:
        return None
    if tr * m["ts_cols"] + tc >= len(state.tile_surfaces):
        return None
    return (tc, tr)


def _build_brush_grid(
    state: EditorState, c0: int, r0: int, c1: int, r1: int
) -> list[list[int]]:
    """Constrói grade de tile_ids usando coordenadas reais do tileset."""
    ts_cols = max(1, state.tileset_cols)
    min_c, max_c = min(c0, c1), max(c0, c1)
    min_r, max_r = min(r0, r1), max(r0, r1)
    grid = []
    for r in range(min_r, max_r + 1):
        row = []
        for c in range(min_c, max_c + 1):
            idx = r * ts_cols + c
            row.append(idx if idx < len(state.tile_surfaces) else 0)
        grid.append(row)
    return grid


def update_brush_drag(
    state: EditorState, mx: int, my: int, panel_rect: pygame.Rect
) -> None:
    if state.brush_drag_start is None:
        return
    pos = pixel_to_panel_tile(state, mx, my, panel_rect)
    if pos is None:
        return
    c0, r0 = state.brush_drag_start
    grid = _build_brush_grid(state, c0, r0, pos[0], pos[1])
    set_brush(state, grid)


def try_scrollbar_drag(
    state: EditorState, mx: int, my: int, panel_rect: pygame.Rect
) -> dict | None:
    """Detecta clique em scrollbar do painel de tileset.

    Retorna dict com info de drag, ou None se o clique não foi num scrollbar.
    Só actua no modo VISUAL.
    """
    if state.active_mode != Mode.VISUAL or not state.tile_surfaces:
        return None
    content_rect = pygame.Rect(
        panel_rect.x,
        panel_rect.y + HEADER_H,
        panel_rect.width,
        panel_rect.bottom - (panel_rect.y + HEADER_H),
    )
    m = _tileset_metrics(state, content_rect)

    if m["need_v"]:
        sb = pygame.Rect(content_rect.x + m["draw_w"], content_rect.y, SCROLLBAR_SIZE, m["draw_h"])
        if sb.collidepoint(mx, my):
            thumb_h = max(16, m["draw_h"] * m["visible_rows"] // m["ts_rows"])
            travel = max(1, m["draw_h"] - thumb_h)
            return {
                "axis": "v",
                "scroll_origin": state.panel_scroll,
                "pixel_origin": my,
                "pixels_per_unit": travel / max(1, m["max_scroll_y"]),
            }

    if m["need_h"]:
        sb = pygame.Rect(content_rect.x, content_rect.y + m["draw_h"], m["draw_w"], SCROLLBAR_SIZE)
        if sb.collidepoint(mx, my):
            thumb_w = max(16, m["draw_w"] * m["visible_cols"] // m["ts_cols"])
            travel = max(1, m["draw_w"] - thumb_w)
            return {
                "axis": "h",
                "scroll_origin": state.panel_scroll_x,
                "pixel_origin": mx,
                "pixels_per_unit": travel / max(1, m["max_scroll_x"]),
            }

    return None


def _handle_tileset_click(
    state: EditorState, mx: int, my: int, content_rect: pygame.Rect
) -> bool:
    if not state.tile_surfaces:
        return False
    m = _tileset_metrics(state, content_rect)

    if not (content_rect.x <= mx < content_rect.x + m["draw_w"]):
        return False
    if not (content_rect.y <= my < content_rect.y + m["draw_h"]):
        return False

    vc = (mx - content_rect.x) // TILE_PREVIEW
    vr = (my - content_rect.y) // TILE_PREVIEW
    tc = vc + state.panel_scroll_x
    tr = vr + state.panel_scroll

    if tc >= m["ts_cols"] or tr >= m["ts_rows"]:
        return False

    idx = tr * m["ts_cols"] + tc
    if 0 <= idx < len(state.tile_surfaces):
        state.brush_drag_start = (tc, tr)
        set_brush(state, [[idx]])
    return False


def draw_collision_panel(
    screen: pygame.Surface, state: EditorState, content_rect: pygame.Rect
) -> None:
    y = content_rect.y + 4
    for ct in state.collision_types:
        row_rect = pygame.Rect(content_rect.x, y, content_rect.width, ITEM_H)
        if ct.id == state.selected_collision_id:
            pygame.draw.rect(screen, (50, 70, 100), row_rect)
        swatch = pygame.Rect(content_rect.x + 6, y + 4, 20, 20)
        pygame.draw.rect(screen, ct.color[:3], swatch)
        pygame.draw.rect(screen, (150, 150, 150), swatch, 1)
        _text(screen, f"{ct.id}: {ct.name}", content_rect.x + 32, y + 6)
        y += ITEM_H

    add_rect = pygame.Rect(content_rect.x + 8, y + 4, content_rect.width - 16, 26)
    _button(screen, "+ Novo tipo", add_rect)


def _handle_collision_click(
    state: EditorState, mx: int, my: int, content_rect: pygame.Rect
) -> bool:
    y = content_rect.y + 4
    for ct in state.collision_types:
        if pygame.Rect(content_rect.x, y, content_rect.width, ITEM_H).collidepoint(
            mx, my
        ):
            state.selected_collision_id = ct.id
            return False
        y += ITEM_H
    add_rect = pygame.Rect(content_rect.x + 8, y + 4, content_rect.width - 16, 26)
    return add_rect.collidepoint(mx, my)


def draw_entity_panel(
    screen: pygame.Surface, state: EditorState, content_rect: pygame.Rect
) -> None:
    y = content_rect.y + 4
    for et in state.entity_types:
        row_rect = pygame.Rect(content_rect.x, y, content_rect.width, ITEM_H)
        if et.id == state.selected_entity_id:
            pygame.draw.rect(screen, (50, 70, 100), row_rect)
        draw_entity_icon(screen, et, content_rect.x + 4, y + 2, 24, 24)
        _text(screen, f"{et.id}: {et.name}", content_rect.x + 32, y + 6)
        y += ITEM_H

    add_rect = pygame.Rect(content_rect.x + 8, y + 4, content_rect.width - 16, 26)
    _button(screen, "+ Novo tipo", add_rect)


def _handle_entity_click(
    state: EditorState, mx: int, my: int, content_rect: pygame.Rect
) -> bool:
    y = content_rect.y + 4
    for et in state.entity_types:
        if pygame.Rect(content_rect.x, y, content_rect.width, ITEM_H).collidepoint(
            mx, my
        ):
            state.selected_entity_id = et.id
            return False
        y += ITEM_H
    add_rect = pygame.Rect(content_rect.x + 8, y + 4, content_rect.width - 16, 26)
    return add_rect.collidepoint(mx, my)


def draw_statusbar(
    screen: pygame.Surface,
    state: EditorState,
    statusbar_rect: pygame.Rect,
    mouse_col: int,
    mouse_row: int,
) -> None:
    pygame.draw.rect(screen, (25, 25, 25), statusbar_rect)
    pygame.draw.line(
        screen,
        (70, 70, 70),
        (statusbar_rect.x, statusbar_rect.y),
        (statusbar_rect.right, statusbar_rect.y),
    )

    if state.active_mode == Mode.ANIMATION:
        parts = []
        if state.anim_sets:
            aset = state.anim_sets[state.active_anim_set]
            parts.append(f"set={aset.name}")
            clip = get_active_clip(state)
            if clip:
                parts.append(f"clip={clip.name}")
                n = len(clip.frames)
                parts.append(f"frame={state.active_anim_frame}/{n}")
                if n > 0 and 0 <= state.active_anim_frame < n:
                    f = clip.frames[state.active_anim_frame]
                    parts.append(f"tile={f.tile_id}")
                    eff = f.delay_ms if f.delay_ms > 0 else clip.default_delay_ms
                    parts.append(f"delay={eff}ms")
        status_text = " | ".join(parts) if parts else "modo animação — crie um set e um clip"
    else:
        parts = [f"col={mouse_col} row={mouse_row}"]

        if 0 <= mouse_col < state.map_cols and 0 <= mouse_row < state.map_rows:
            idx = tile_index(mouse_col, mouse_row, state.map_cols)
            parts.append(f"tile={state.visual_layer[idx]}")

            col_id = state.collision_layer[idx]
            ct = next((c for c in state.collision_types if c.id == col_id), None)
            parts.append(f"colisão={col_id}({ct.name if ct else '?'})")

            ent = get_entity_at(state, mouse_col, mouse_row)
            if ent:
                et = next((e for e in state.entity_types if e.id == ent.type_id), None)
                parts.append(f"entidade={et.name if et else ent.type_id}")
            else:
                parts.append("entidade=—")
        status_text = " | ".join(parts)

    _text(
        screen,
        status_text,
        statusbar_rect.x + 8,
        statusbar_rect.y + (statusbar_rect.height - 14) // 2,
        size=14,
    )
