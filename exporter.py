import os
from datetime import datetime
from editor import EditorState, tile_index


def pack_nibble(values: list[int]) -> list[int]:
    result = []
    for i in range(0, len(values), 2):
        lo = values[i] & 0xF
        hi = (values[i + 1] & 0xF) if i + 1 < len(values) else 0
        result.append(lo | (hi << 4))
    return result


def pack_2bit(values: list[int]) -> list[int]:
    result = []
    for i in range(0, len(values), 4):
        byte = 0
        for j in range(4):
            if i + j < len(values):
                byte |= (values[i + j] & 0x3) << (j * 2)
        result.append(byte)
    return result


def _header(state: EditorState, label_prefix: str) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    return (
        f"# Gerado automaticamente pelo RITMO em {now}\n"
        f"# Mapa: {state.map_cols} colunas x {state.map_rows} linhas, "
        f"tile {state.tile_w}x{state.tile_h} pixels\n"
        f"# Prefixo: {label_prefix}\n\n"
    )


def export_defs(
    state: EditorState,
    output_dir: str,
    label_prefix: str,
) -> str:
    lines = [_header(state, label_prefix)]
    lines.append(f".eqv {label_prefix}_MAP_COLS  {state.map_cols}\n")
    lines.append(f".eqv {label_prefix}_MAP_ROWS  {state.map_rows}\n")
    lines.append(f".eqv {label_prefix}_TILE_W    {state.tile_w}\n")
    lines.append(f".eqv {label_prefix}_TILE_H    {state.tile_h}\n")

    lines.append(f"\n# Tipos de colisão:\n")
    for ct in state.collision_types:
        lines.append(f"#   {ct.id} = {ct.name}\n")

    lines.append(f"\n# Tipos de entidade:\n")
    for et in state.entity_types:
        lines.append(f"#   {et.id} = {et.name}\n")

    path = os.path.join(output_dir, f"{label_prefix}_defs.s")
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    return path


def export_collision(
    state: EditorState,
    output_dir: str,
    label_prefix: str,
    pack_mode: str = "byte",
    y_axis: str = "down",
) -> str:
    lines = [_header(state, label_prefix)]
    lines.append(f"# .include \"{label_prefix}_defs.s\"\n\n")

    if pack_mode == "byte":
        lines.append(
            f"# Lookup (1 byte/tile):\n"
            f"#   # t0 = row * {label_prefix}_MAP_COLS + col\n"
            f"#   la  t1, {label_prefix}_COLISAO\n"
            f"#   add t1, t1, t0\n"
            f"#   lbu t1, 0(t1)\n\n"
        )
    elif pack_mode == "nibble":
        lines.append(
            f"# Lookup (nibble/tile):\n"
            f"#   t0 = row * {label_prefix}_MAP_COLS + col\n"
            f"#   srli t1, t0, 1          # byte_index\n"
            f"#   andi t2, t0, 1           # nibble_pos (0=low,1=high)\n"
            f"#   la   t3, {label_prefix}_COLISAO\n"
            f"#   add  t1, t1, t3\n"
            f"#   lbu  t1, 0(t1)\n"
            f"#   beqz t2, done\n"
            f"#   srli t1, t1, 4\n"
            f"# done:\n"
            f"#   andi t1, t1, 0xF\n\n"
        )
    else:  # 2bit
        lines.append(
            f"# Lookup (2 bits/tile):\n"
            f"#   t0 = row * {label_prefix}_MAP_COLS + col\n"
            f"#   srli t1, t0, 2           # byte_index\n"
            f"#   andi t2, t0, 3            # posição no byte\n"
            f"#   slli t2, t2, 1            # bit_shift\n"
            f"#   la   t3, {label_prefix}_COLISAO\n"
            f"#   add  t1, t1, t3\n"
            f"#   lbu  t1, 0(t1)\n"
            f"#   srl  t1, t1, t2\n"
            f"#   andi t1, t1, 0x3\n\n"
        )

    lines.append(f"{label_prefix}_COLISAO: .byte\n")

    row_order = (
        range(state.map_rows) if y_axis == "down" else range(state.map_rows - 1, -1, -1)
    )
    for row in row_order:
        row_vals = [
            state.collision_layer[tile_index(col, row, state.map_cols)]
            for col in range(state.map_cols)
        ]
        if pack_mode == "nibble":
            row_vals = pack_nibble(row_vals)
        elif pack_mode == "2bit":
            row_vals = pack_2bit(row_vals)
        vals_str = ", ".join(str(v) for v in row_vals)
        lines.append(f"    {vals_str}   # row {row}\n")

    path = os.path.join(output_dir, f"{label_prefix}_colisao.s")
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    return path


def export_visual(
    state: EditorState, output_dir: str, label_prefix: str, y_axis: str = "down"
) -> str:
    use_half = (state.tileset_cols * state.tileset_rows) > 255
    directive = ".half" if use_half else ".byte"

    row_order = (
        range(state.map_rows) if y_axis == "down" else range(state.map_rows - 1, -1, -1)
    )

    path = os.path.join(output_dir, f"{label_prefix}_visual.s")
    with open(path, "w", encoding="utf-8") as f:
        f.write(_header(state, label_prefix))
        f.write(f"# .include \"{label_prefix}_defs.s\"\n\n")
        f.write(f"{label_prefix}_VISUAL: {directive}\n")
        for row_i, row in enumerate(row_order):
            row_vals = [
                state.visual_layer[tile_index(col, row, state.map_cols)]
                for col in range(state.map_cols)
            ]
            vals_str = ", ".join(str(v) for v in row_vals)
            f.write(f"    {vals_str}   # row {row_i}\n")
    return path


def export_entities(state: EditorState, output_dir: str, label_prefix: str) -> str:
    use_half = state.map_cols > 255 or state.map_rows > 255
    stride = 5 if use_half else 3
    directive = ".half" if use_half else ".byte"

    sorted_entities = sorted(state.entities, key=lambda e: (e.row, e.col))

    lines = [_header(state, label_prefix)]
    lines.append(f".eqv {label_prefix}_NUM_ENTIDADES  {len(sorted_entities)}\n")
    lines.append(f".eqv {label_prefix}_ENTIDADE_STRIDE {stride}\n\n")

    lines.append(f"# .include \"{label_prefix}_defs.s\"\n\n")

    lines.append(
        f"# Loop de iteração:\n"
        f"#   li   t0, 0\n"
        f"#   li   t5, {label_prefix}_NUM_ENTIDADES\n"
        f"# loop_ent:\n"
        f"#   bge  t0, t5, done_ent\n"
        f"#   la   t1, {label_prefix}_ENTIDADES\n"
        f"#   li   t2, {label_prefix}_ENTIDADE_STRIDE\n"
        f"#   mul  t3, t0, t2\n"
        f"#   add  t1, t1, t3\n"
        f"#   lbu  t4, 0(t1)  # type_id\n"
        f"#   lbu  t5, 1(t1)  # col\n"
        f"#   lbu  t6, 2(t1)  # row\n"
        f"#   addi t0, t0, 1\n"
        f"#   j    loop_ent\n"
        f"# done_ent:\n\n"
    )

    if sorted_entities:
        lines.append(f"{label_prefix}_ENTIDADES: {directive}\n")
        for ent in sorted_entities:
            lines.append(f"    {ent.type_id}, {ent.col}, {ent.row}\n")
    else:
        lines.append(f"# {label_prefix}_ENTIDADES: (nenhuma entidade definida)\n")

    path = os.path.join(output_dir, f"{label_prefix}_entidades.s")
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    return path


def export_all(
    state: EditorState,
    output_dir: str,
    label_prefix: str,
    pack_mode: str = "byte",
    y_axis: str = "down",
) -> list[str]:
    os.makedirs(output_dir, exist_ok=True)
    paths = []
    paths.append(export_defs(state, output_dir, label_prefix))
    paths.append(export_collision(state, output_dir, label_prefix, pack_mode, y_axis))
    paths.append(export_visual(state, output_dir, label_prefix, y_axis))
    paths.append(export_entities(state, output_dir, label_prefix))
    return paths
