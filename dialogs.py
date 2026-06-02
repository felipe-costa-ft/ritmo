import os

import pygame
from editor import CollisionType, EntityType

DIALOG_BG = (45, 45, 45)
DIALOG_BORDER = (90, 90, 90)
INPUT_BG = (30, 30, 30)
INPUT_ACTIVE = (50, 70, 110)
FG = (210, 210, 210)
BTN_OK = (50, 120, 50)
BTN_CANCEL = (100, 50, 50)
BTN_HOVER_OK = (70, 160, 70)
BTN_HOVER_CANCEL = (140, 70, 70)

PRESET_COLORS = [
    (255, 255, 255),
    (180, 180, 180),
    (100, 100, 100),
    (30, 30, 30),
    (220, 60, 60),
    (220, 130, 60),
    (220, 220, 60),
    (60, 200, 60),
    (60, 200, 200),
    (60, 100, 220),
    (130, 60, 220),
    (220, 60, 180),
    (255, 160, 120),
    (120, 255, 160),
    (120, 160, 255),
    (255, 255, 120),
]


def _font(size: int = 16) -> pygame.font.Font:
    return pygame.font.SysFont(None, size)


def _text(screen, msg, x, y, size=16, color=FG):
    screen.blit(_font(size).render(msg, True, color), (x, y))


def _draw_button(screen, label, rect, bg, hover_bg):
    mx, my = pygame.mouse.get_pos()
    c = hover_bg if rect.collidepoint(mx, my) else bg
    pygame.draw.rect(screen, c, rect, border_radius=5)
    pygame.draw.rect(screen, (150, 150, 150), rect, 1, border_radius=5)
    surf = _font(16).render(label, True, (255, 255, 255))
    screen.blit(
        surf,
        (
            rect.x + (rect.width - surf.get_width()) // 2,
            rect.y + (rect.height - surf.get_height()) // 2,
        ),
    )


def _draw_input(screen, label, value, rect, active):
    bg = INPUT_ACTIVE if active else INPUT_BG
    pygame.draw.rect(screen, bg, rect, border_radius=4)
    pygame.draw.rect(screen, DIALOG_BORDER, rect, 1, border_radius=4)
    _text(screen, label, rect.x, rect.y - 18, size=14, color=(160, 160, 160))
    cursor = "|" if active and (pygame.time.get_ticks() // 500) % 2 == 0 else ""
    _text(screen, value + cursor, rect.x + 6, rect.y + (rect.height - 16) // 2)


def _draw_color_picker(screen, x, y, selected_color):
    rects = []
    sw = 24
    for i, c in enumerate(PRESET_COLORS):
        col = i % 4
        row = i // 4
        r = pygame.Rect(x + col * (sw + 4), y + row * (sw + 4), sw, sw)
        pygame.draw.rect(screen, c, r)
        if c[:3] == selected_color[:3]:
            pygame.draw.rect(screen, (255, 255, 0), r, 2)
        else:
            pygame.draw.rect(screen, (80, 80, 80), r, 1)
        rects.append((r, c))
    return rects


def _open_file_dialog(
    screen: pygame.Surface,
    title: str = "Selecionar",
    ext_filter: str = "",
    save: bool = False,
    directory: bool = False,
) -> str:
    sw, sh = screen.get_size()
    dw, dh = 560, 440
    dx, dy = (sw - dw) // 2, (sh - dh) // 2

    cwd = os.path.expanduser("~")
    entries: list[tuple[str, bool]] = []
    scroll = 0
    selected = ""
    filename_buf = ""
    ITEM_H = 26
    VISIBLE = (dh - 130) // ITEM_H

    def load_dir(path: str) -> list[tuple[str, bool]]:
        try:
            items = os.listdir(path)
        except PermissionError:
            return []
        dirs = sorted(
            n
            for n in items
            if os.path.isdir(os.path.join(path, n)) and not n.startswith(".")
        )
        files = sorted(n for n in items if not os.path.isdir(os.path.join(path, n)))
        if ext_filter:
            files = [f for f in files if f.lower().endswith(ext_filter.lower())]
        result = (
            [("..", True)] + [(d, True) for d in dirs] + [(f, False) for f in files]
        )
        return result

    entries = load_dir(cwd)
    clock = pygame.time.Clock()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return ""
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return ""
                elif event.key == pygame.K_RETURN:
                    if directory:
                        return cwd
                    if selected and not os.path.isdir(os.path.join(cwd, selected)):
                        return os.path.join(cwd, selected)
                    if save and filename_buf:
                        return os.path.join(cwd, filename_buf)
                elif save and event.key == pygame.K_BACKSPACE:
                    filename_buf = filename_buf[:-1]
                elif save and event.unicode.isprintable():
                    filename_buf += event.unicode
            if event.type == pygame.MOUSEWHEEL:
                scroll = max(0, min(len(entries) - VISIBLE, scroll - event.y))
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                list_y = dy + 62
                for i, (name, is_dir) in enumerate(entries[scroll : scroll + VISIBLE]):
                    iy = list_y + i * ITEM_H
                    if pygame.Rect(dx + 8, iy, dw - 16, ITEM_H).collidepoint(mx, my):
                        full = os.path.join(cwd, name)
                        if is_dir:
                            cwd = os.path.normpath(full)
                            entries = load_dir(cwd)
                            scroll = 0
                            selected = ""
                        else:
                            selected = name
                            if save:
                                filename_buf = name
                        break

                ok_r = pygame.Rect(dx + dw - 100, dy + dh - 44, 88, 32)
                if ok_r.collidepoint(mx, my):
                    if directory:
                        return cwd
                    if save and filename_buf:
                        return os.path.join(cwd, filename_buf)
                    if selected and not os.path.isdir(os.path.join(cwd, selected)):
                        return os.path.join(cwd, selected)
                cancel_r = pygame.Rect(dx + dw - 200, dy + dh - 44, 88, 32)
                if cancel_r.collidepoint(mx, my):
                    return ""

        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        screen.blit(overlay, (0, 0))

        pygame.draw.rect(screen, DIALOG_BG, (dx, dy, dw, dh), border_radius=8)
        pygame.draw.rect(screen, DIALOG_BORDER, (dx, dy, dw, dh), 1, border_radius=8)
        _text(screen, title, dx + 12, dy + 12, size=18)

        path_surf = pygame.font.SysFont(None, 14).render(cwd, True, (140, 140, 140))
        screen.blit(path_surf, (dx + 12, dy + 38))
        pygame.draw.line(
            screen, DIALOG_BORDER, (dx + 8, dy + 58), (dx + dw - 8, dy + 58)
        )

        list_y = dy + 62
        list_rect = pygame.Rect(dx + 6, list_y, dw - 12, VISIBLE * ITEM_H)
        pygame.draw.rect(screen, (25, 25, 25), list_rect)

        for i, (name, is_dir) in enumerate(entries[scroll : scroll + VISIBLE]):
            iy = list_y + i * ITEM_H
            row_r = pygame.Rect(dx + 8, iy, dw - 16, ITEM_H)
            if name == selected:
                pygame.draw.rect(screen, (50, 80, 120), row_r)
            elif row_r.collidepoint(*pygame.mouse.get_pos()):
                pygame.draw.rect(screen, (50, 50, 60), row_r)
            prefix = "📁 " if is_dir else "   "
            color = (180, 210, 255) if is_dir else FG
            _text(screen, prefix + name, dx + 12, iy + 4, size=15, color=color)

        if save:
            fn_rect = pygame.Rect(dx + 8, dy + dh - 88, dw - 16, 28)
            _draw_input(screen, "Nome do arquivo:", filename_buf, fn_rect, True)

        cancel_r = pygame.Rect(dx + dw - 200, dy + dh - 44, 88, 32)
        ok_r = pygame.Rect(dx + dw - 100, dy + dh - 44, 88, 32)
        _draw_button(screen, "Cancelar", cancel_r, (100, 50, 50), (140, 70, 70))
        ok_label = "Selecionar" if directory else "Abrir" if not save else "Salvar"
        _draw_button(screen, ok_label, ok_r, (50, 100, 50), (70, 140, 70))

        pygame.display.flip()
        clock.tick(60)


def dialog_new_project(screen: pygame.Surface) -> dict | None:
    sw, sh = screen.get_size()
    dw, dh = 420, 360
    dx, dy = (sw - dw) // 2, (sh - dh) // 2

    fields = {
        "map_cols": "20",
        "map_rows": "15",
        "tile_w": "16",
        "tile_h": "16",
    }
    field_order = ["map_cols", "map_rows", "tile_w", "tile_h"]
    labels = {
        "map_cols": "Colunas do mapa",
        "map_rows": "Linhas do mapa",
        "tile_w": "Largura do tile (px)",
        "tile_h": "Altura do tile (px)",
    }
    active_field = field_order[0]
    tileset_path = ""
    error = ""

    clock = pygame.time.Clock()
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return None
                elif event.key == pygame.K_TAB:
                    idx = field_order.index(active_field)
                    active_field = field_order[(idx + 1) % len(field_order)]
                elif event.key == pygame.K_RETURN:
                    pass
                elif event.key == pygame.K_BACKSPACE:
                    fields[active_field] = fields[active_field][:-1]
                else:
                    if event.unicode.isdigit():
                        fields[active_field] += event.unicode
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos

                for i, key in enumerate(field_order):
                    irect = pygame.Rect(dx + 20, dy + 60 + i * 54, dw - 40, 30)
                    if irect.collidepoint(mx, my):
                        active_field = key

                ts_btn = pygame.Rect(
                    dx + 20, dy + 60 + len(field_order) * 54, dw - 40, 30
                )
                if ts_btn.collidepoint(mx, my):
                    tileset_path = _open_file_dialog(
                        screen, "Selecionar tileset PNG", ext_filter=".png"
                    )

                ok_rect = pygame.Rect(dx + dw - 110, dy + dh - 50, 90, 34)
                if ok_rect.collidepoint(mx, my):
                    try:
                        result = {k: int(v) for k, v in fields.items()}
                        if any(v <= 0 for v in result.values()):
                            raise ValueError
                        result["tileset_path"] = tileset_path
                        return result
                    except ValueError:
                        error = "Todos os campos devem ser inteiros positivos"

                cancel_rect = pygame.Rect(dx + 10, dy + dh - 50, 90, 34)
                if cancel_rect.collidepoint(mx, my):
                    return None

        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        screen.blit(overlay, (0, 0))

        pygame.draw.rect(screen, DIALOG_BG, (dx, dy, dw, dh), border_radius=8)
        pygame.draw.rect(screen, DIALOG_BORDER, (dx, dy, dw, dh), 1, border_radius=8)
        _text(screen, "Novo Projeto", dx + 20, dy + 16, size=20)

        for i, key in enumerate(field_order):
            irect = pygame.Rect(dx + 20, dy + 60 + i * 54, dw - 40, 30)
            _draw_input(screen, labels[key], fields[key], irect, active_field == key)

        ts_btn = pygame.Rect(dx + 20, dy + 60 + len(field_order) * 54, dw - 40, 30)
        ts_label = (
            os.path.basename(tileset_path)
            if tileset_path
            else "Selecionar tileset PNG…"
        )
        _draw_button(screen, ts_label, ts_btn, (60, 60, 80), (80, 80, 110))

        if error:
            _text(screen, error, dx + 20, dy + dh - 80, size=14, color=(220, 80, 80))

        _draw_button(
            screen,
            "Cancelar",
            pygame.Rect(dx + 10, dy + dh - 50, 90, 34),
            BTN_CANCEL,
            BTN_HOVER_CANCEL,
        )
        _draw_button(
            screen,
            "Criar",
            pygame.Rect(dx + dw - 110, dy + dh - 50, 90, 34),
            BTN_OK,
            BTN_HOVER_OK,
        )

        pygame.display.flip()
        clock.tick(60)

    return None


def dialog_new_collision_type(
    screen: pygame.Surface, existing_ids: set[int]
) -> CollisionType | None:
    sw, sh = screen.get_size()
    dw, dh = 380, 320
    dx, dy = (sw - dw) // 2, (sh - dh) // 2

    id_str = ""
    name_str = ""
    alpha_str = "150"
    active_field = "id"
    selected_color = (255, 255, 255)
    error = ""

    clock = pygame.time.Clock()
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return None
                elif event.key == pygame.K_TAB:
                    active_field = {"id": "name", "name": "alpha", "alpha": "id"}[
                        active_field
                    ]
                elif event.key == pygame.K_BACKSPACE:
                    if active_field == "id":
                        id_str = id_str[:-1]
                    elif active_field == "name":
                        name_str = name_str[:-1]
                    else:
                        alpha_str = alpha_str[:-1]
                else:
                    ch = event.unicode
                    if active_field == "id" and ch.isdigit():
                        id_str += ch
                    elif active_field == "name" and ch.isprintable():
                        name_str += ch
                    elif active_field == "alpha" and ch.isdigit():
                        alpha_str += ch

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                for field, irect in [
                    ("id", pygame.Rect(dx + 20, dy + 60, 120, 30)),
                    ("name", pygame.Rect(dx + 20, dy + 114, 240, 30)),
                    ("alpha", pygame.Rect(dx + 280, dy + 60, 80, 30)),
                ]:
                    if irect.collidepoint(mx, my):
                        active_field = field

                color_rects = _draw_color_picker(
                    screen, dx + 20, dy + 170, selected_color
                )
                for r, c in color_rects:
                    if r.collidepoint(mx, my):
                        selected_color = c

                ok_rect = pygame.Rect(dx + dw - 110, dy + dh - 50, 90, 34)
                if ok_rect.collidepoint(mx, my):
                    try:
                        cid = int(id_str)
                        if not name_str:
                            raise ValueError("Nome vazio")
                        if cid in existing_ids:
                            error = f"ID {cid} já existe"
                        else:
                            alpha = max(0, min(255, int(alpha_str or "150")))
                            return CollisionType(
                                id=cid,
                                name=name_str,
                                color=(*selected_color[:3], alpha),
                            )
                    except ValueError as e:
                        error = (
                            str(e)
                            if str(e) != "invalid literal for int() with base 10: ''"
                            else "ID inválido"
                        )

                cancel_rect = pygame.Rect(dx + 10, dy + dh - 50, 90, 34)
                if cancel_rect.collidepoint(mx, my):
                    return None

        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        screen.blit(overlay, (0, 0))

        pygame.draw.rect(screen, DIALOG_BG, (dx, dy, dw, dh), border_radius=8)
        pygame.draw.rect(screen, DIALOG_BORDER, (dx, dy, dw, dh), 1, border_radius=8)
        _text(screen, "Novo Tipo de Colisão", dx + 20, dy + 16, size=20)

        _draw_input(
            screen,
            "ID",
            id_str,
            pygame.Rect(dx + 20, dy + 60, 120, 30),
            active_field == "id",
        )
        _draw_input(
            screen,
            "Opacidade (0-255)",
            alpha_str,
            pygame.Rect(dx + 280, dy + 60, 80, 30),
            active_field == "alpha",
        )
        _draw_input(
            screen,
            "Nome",
            name_str,
            pygame.Rect(dx + 20, dy + 114, 240, 30),
            active_field == "name",
        )

        _text(screen, "Cor:", dx + 20, dy + 152, size=14, color=(160, 160, 160))
        _draw_color_picker(screen, dx + 20, dy + 170, selected_color)

        preview_rect = pygame.Rect(dx + dw - 60, dy + 170, 40, 40)
        alpha = max(0, min(255, int(alpha_str or "150")))
        pygame.draw.rect(screen, (*selected_color[:3], alpha), preview_rect)
        pygame.draw.rect(screen, DIALOG_BORDER, preview_rect, 1)

        if error:
            _text(screen, error, dx + 20, dy + dh - 80, size=14, color=(220, 80, 80))

        _draw_button(
            screen,
            "Cancelar",
            pygame.Rect(dx + 10, dy + dh - 50, 90, 34),
            BTN_CANCEL,
            BTN_HOVER_CANCEL,
        )
        _draw_button(
            screen,
            "Criar",
            pygame.Rect(dx + dw - 110, dy + dh - 50, 90, 34),
            BTN_OK,
            BTN_HOVER_OK,
        )

        pygame.display.flip()
        pygame.time.Clock().tick(60)


def dialog_new_entity_type(
    screen: pygame.Surface, existing_ids: set[int]
) -> EntityType | None:
    sw, sh = screen.get_size()
    dw, dh = 380, 340
    dx, dy = (sw - dw) // 2, (sh - dh) // 2

    id_str = ""
    name_str = ""
    active_field = "id"
    selected_color = (255, 128, 0)
    sprite_path = ""
    sprite_surface = None
    error = ""

    clock = pygame.time.Clock()
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return None
                elif event.key == pygame.K_TAB:
                    active_field = "name" if active_field == "id" else "id"
                elif event.key == pygame.K_BACKSPACE:
                    if active_field == "id":
                        id_str = id_str[:-1]
                    else:
                        name_str = name_str[:-1]
                else:
                    ch = event.unicode
                    if active_field == "id" and ch.isdigit():
                        id_str += ch
                    elif active_field == "name" and ch.isprintable():
                        name_str += ch

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos

                for field, irect in [
                    ("id", pygame.Rect(dx + 20, dy + 60, 120, 30)),
                    ("name", pygame.Rect(dx + 20, dy + 114, 240, 30)),
                ]:
                    if irect.collidepoint(mx, my):
                        active_field = field

                color_rects = _draw_color_picker(
                    screen, dx + 20, dy + 170, selected_color
                )
                for r, c in color_rects:
                    if r.collidepoint(mx, my):
                        selected_color = c

                sprite_btn = pygame.Rect(dx + 20, dy + 280, 200, 26)
                if sprite_btn.collidepoint(mx, my):
                    path = _open_file_dialog("Selecionar sprite PNG")
                    if path:
                        try:
                            from PIL import Image as PILImage

                            img = PILImage.open(path).convert("RGBA")
                            sprite_surface = pygame.image.fromstring(
                                img.tobytes(), img.size, "RGBA"
                            )
                            sprite_path = path
                        except Exception:
                            error = "Erro ao carregar sprite"

                ok_rect = pygame.Rect(dx + dw - 110, dy + dh - 50, 90, 34)
                if ok_rect.collidepoint(mx, my):
                    try:
                        eid = int(id_str)
                        if eid < 1:
                            raise ValueError("ID deve ser ≥ 1")
                        if not name_str:
                            raise ValueError("Nome vazio")
                        if eid in existing_ids:
                            error = f"ID {eid} já existe"
                        else:
                            return EntityType(
                                id=eid,
                                name=name_str,
                                color=(*selected_color[:3], 200),
                                sprite_surface=sprite_surface,
                            )
                    except ValueError as e:
                        error = (
                            str(e) if "invalid literal" not in str(e) else "ID inválido"
                        )

                cancel_rect = pygame.Rect(dx + 10, dy + dh - 50, 90, 34)
                if cancel_rect.collidepoint(mx, my):
                    return None

        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        screen.blit(overlay, (0, 0))

        pygame.draw.rect(screen, DIALOG_BG, (dx, dy, dw, dh), border_radius=8)
        pygame.draw.rect(screen, DIALOG_BORDER, (dx, dy, dw, dh), 1, border_radius=8)
        _text(screen, "Novo Tipo de Entidade", dx + 20, dy + 16, size=20)

        _draw_input(
            screen,
            "ID (≥ 1)",
            id_str,
            pygame.Rect(dx + 20, dy + 60, 120, 30),
            active_field == "id",
        )
        _draw_input(
            screen,
            "Nome",
            name_str,
            pygame.Rect(dx + 20, dy + 114, 240, 30),
            active_field == "name",
        )

        _text(screen, "Cor:", dx + 20, dy + 152, size=14, color=(160, 160, 160))
        _draw_color_picker(screen, dx + 20, dy + 170, selected_color)

        preview_rect = pygame.Rect(dx + dw - 60, dy + 170, 40, 40)
        pygame.draw.rect(screen, (*selected_color[:3], 200), preview_rect)
        pygame.draw.rect(screen, DIALOG_BORDER, preview_rect, 1)

        sp_label = (
            os.path.basename(sprite_path) if sprite_path else "Sprite PNG (opcional)"
        )
        _draw_button(
            screen,
            sp_label,
            pygame.Rect(dx + 20, dy + 280, 200, 26),
            (60, 60, 80),
            (80, 80, 110),
        )

        if error:
            _text(screen, error, dx + 20, dy + dh - 80, size=14, color=(220, 80, 80))

        _draw_button(
            screen,
            "Cancelar",
            pygame.Rect(dx + 10, dy + dh - 50, 90, 34),
            BTN_CANCEL,
            BTN_HOVER_CANCEL,
        )
        _draw_button(
            screen,
            "Criar",
            pygame.Rect(dx + dw - 110, dy + dh - 50, 90, 34),
            BTN_OK,
            BTN_HOVER_OK,
        )

        pygame.display.flip()
        clock.tick(60)
