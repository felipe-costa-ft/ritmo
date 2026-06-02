import pygame
from canvas import draw_entity_icon
from config import EMPTY_TILE_BG, MIN_ZOOM, MAX_ZOOM, SELECTION_COLOR, ZOOM_STEP
from editor import EditorState, Mode, get_entity_at, tile_index

HEADER_H = 32
ITEM_H = 28
TILE_PREVIEW = 32
PANEL_BG = (30, 30, 30)
PANEL_FG = (200, 200, 200)
BUTTON_BG = (60, 60, 60)
BUTTON_HOVER = (80, 80, 80)
ACTIVE_TAB = (70, 120, 180)


def _font(size: int = 16) -> pygame.font.Font:
    return pygame.font.SysFont(None, size)


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

    for label in ("Novo", "Abrir", "Salvar", "Exportar"):
        _button(screen, label, pygame.Rect(x, by, bw, bh))
        x += bw + 6

    x += 12
    pygame.draw.line(screen, (80, 80, 80), (x, by), (x, by + bh))
    x += 12

    for label, mode in (
        ("Visual", Mode.VISUAL),
        ("Colisão", Mode.COLLISION),
        ("Entidades", Mode.ENTITY),
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
    """Retorna string de ação ('new','open','save','export') ou None."""
    bw, bh = 72, 30
    by = toolbar_rect.y + (toolbar_rect.height - bh) // 2
    x = toolbar_rect.x + 8

    for action in ("new", "open", "save", "export"):
        if pygame.Rect(x, by, bw, bh).collidepoint(mx, my):
            return action
        x += bw + 6

    x += 24
    for mode in (Mode.VISUAL, Mode.COLLISION, Mode.ENTITY):
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
    return False


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

    cols = max(1, content_rect.width // TILE_PREVIEW)
    for i, surf in enumerate(state.tile_surfaces):
        c = i % cols
        r = i // cols
        x = content_rect.x + c * TILE_PREVIEW
        y = content_rect.y + r * TILE_PREVIEW
        if y + TILE_PREVIEW > content_rect.bottom:
            break
        if i == 0:
            pygame.draw.rect(screen, EMPTY_TILE_BG, (x, y, TILE_PREVIEW, TILE_PREVIEW))
        scaled = pygame.transform.scale(surf, (TILE_PREVIEW, TILE_PREVIEW))
        screen.blit(scaled, (x, y))
        if i == state.selected_visual_tile:
            pygame.draw.rect(
                screen, SELECTION_COLOR, (x, y, TILE_PREVIEW, TILE_PREVIEW), 2
            )


def _handle_tileset_click(
    state: EditorState, mx: int, my: int, content_rect: pygame.Rect
) -> bool:
    if not state.tile_surfaces:
        return False
    cols = max(1, content_rect.width // TILE_PREVIEW)
    c = (mx - content_rect.x) // TILE_PREVIEW
    r = (my - content_rect.y) // TILE_PREVIEW
    idx = r * cols + c
    if 0 <= idx < len(state.tile_surfaces):
        state.selected_visual_tile = idx
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

    _text(
        screen,
        " | ".join(parts),
        statusbar_rect.x + 8,
        statusbar_rect.y + (statusbar_rect.height - 14) // 2,
        size=14,
    )
