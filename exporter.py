import os
import re
from datetime import datetime
from editor import EditorState, tile_index
from anim_exporter import export_animations


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


def _asm_label_part(value: str) -> str:
    label = re.sub(r"[^0-9A-Za-z_]+", "_", value.strip().upper())
    label = re.sub(r"_+", "_", label).strip("_")
    if not label:
        return "ENTITY"
    if label[0].isdigit():
        return f"ENTITY_{label}"
    return label


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
    for et in state.entity_types:
        lines.append(f".eqv {label_prefix}_ENTITY_TYPE_{_asm_label_part(et.name)} {et.id}\n")

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

    row_order = list(
        range(state.map_rows) if y_axis == "down" else range(state.map_rows - 1, -1, -1)
    )
    for i, row in enumerate(row_order):
        row_vals = [
            state.collision_layer[tile_index(col, row, state.map_cols)]
            for col in range(state.map_cols)
        ]
        if pack_mode == "nibble":
            row_vals = pack_nibble(row_vals)
        elif pack_mode == "2bit":
            row_vals = pack_2bit(row_vals)
        vals_str = ", ".join(str(v) for v in row_vals)
        sep = "" if i == len(row_order) - 1 else ","
        lines.append(f"    {vals_str}{sep}   # row {row}\n")

    path = os.path.join(output_dir, f"{label_prefix}_colisao.s")
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    return path


def export_visual(
    state: EditorState, output_dir: str, label_prefix: str, y_axis: str = "down"
) -> str:
    use_half = (state.tileset_cols * state.tileset_rows) > 255
    directive = ".half" if use_half else ".byte"

    row_order = list(
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
            sep = "" if row_i == len(row_order) - 1 else ","
            f.write(f"    {vals_str}{sep}   # row {row_i}\n")
    return path


def export_entities(state: EditorState, output_dir: str, label_prefix: str) -> str:
    use_half = state.map_cols > 255 or state.map_rows > 255
    directive = ".half" if use_half else ".byte"

    entity_types = sorted(state.entity_types, key=lambda et: et.id)
    entities_by_type = {
        et.id: sorted(
            (entity for entity in state.entities if entity.type_id == et.id),
            key=lambda entity: (entity.row, entity.col),
        )
        for et in entity_types
    }
    entity_labels = {
        et.id: f"{label_prefix}_{_asm_label_part(et.name)}" for et in entity_types
    }

    lines = [_header(state, label_prefix)]
    lines.append(f".eqv {label_prefix}_ENTITY_POSITION_SIZE_BYTES 2\n")
    lines.append(
        f".eqv {label_prefix}_NUM_ENTIDADES  "
        f"{sum(len(entities) for entities in entities_by_type.values())}\n\n"
    )

    for et in entity_types:
        label = entity_labels[et.id]
        lines.append(f".eqv {label}_COUNT {len(entities_by_type[et.id])}\n")
    if entity_types:
        lines.append("\n")

    lines.append(f"# .include \"{label_prefix}_defs.s\"\n\n")

    lines.append(
        f"# Cada tabela abaixo guarda pares col,row para um tipo de entidade.\n"
        f"# Iteração típica:\n"
        f"#   la   t1, {label_prefix}_NOME_DA_ENTIDADE\n"
        f"#   li   t2, {label_prefix}_NOME_DA_ENTIDADE_COUNT\n"
        f"# loop_ent:\n"
        f"#   beqz t2, done_ent\n"
        f"#   lbu  t3, 0(t1)  # col\n"
        f"#   lbu  t4, 1(t1)  # row\n"
        f"#   addi t1, t1, {label_prefix}_ENTITY_POSITION_SIZE_BYTES\n"
        f"#   addi t2, t2, -1\n"
        f"#   j    loop_ent\n"
        f"# done_ent:\n\n"
    )

    if entity_types:
        for type_i, et in enumerate(entity_types):
            label = entity_labels[et.id]
            entities = entities_by_type[et.id]
            if entities:
                lines.append(f"{label}: {directive}\n")
                for i, ent in enumerate(entities):
                    sep = "" if i == len(entities) - 1 else ","
                    lines.append(f"    {ent.col}, {ent.row}{sep}\n")
            else:
                lines.append(f"# {label}: (nenhuma entidade definida)\n")
            if type_i != len(entity_types) - 1:
                lines.append("\n")
    else:
        lines.append(f"# Nenhum tipo de entidade definido.\n")

    path = os.path.join(output_dir, f"{label_prefix}_entidades.s")
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    return path


def export_entities_flat(state: EditorState, output_dir: str, label_prefix: str) -> str:
    use_half = state.map_cols > 255 or state.map_rows > 255
    directive = ".half" if use_half else ".byte"
    sorted_entities = sorted(state.entities, key=lambda entity: (entity.row, entity.col))
    entity_type_names = {
        entity_type.id: _asm_label_part(entity_type.name)
        for entity_type in state.entity_types
    }

    lines = [_header(state, label_prefix)]
    lines.append(f".eqv {label_prefix}_FLAT_ENTITY_SIZE_BYTES 3\n")
    lines.append(f".eqv {label_prefix}_FLAT_NUM_ENTIDADES  {len(sorted_entities)}\n")
    lines.append(f".eqv {label_prefix}_FLAT_ENTITY_FIELD_TYPE 0\n")
    lines.append(f".eqv {label_prefix}_FLAT_ENTITY_FIELD_COL  1\n")
    lines.append(f".eqv {label_prefix}_FLAT_ENTITY_FIELD_ROW  2\n\n")

    lines.append(f"# .include \"{label_prefix}_defs.s\"\n\n")
    lines.append(
        f"# Formato flat: cada entidade ocupa type,col,row.\n"
        f"# Iteração típica:\n"
        f"#   la   t1, {label_prefix}_ENTIDADES_FLAT\n"
        f"#   li   t2, {label_prefix}_FLAT_NUM_ENTIDADES\n"
        f"# loop_ent:\n"
        f"#   beqz t2, done_ent\n"
        f"#   lbu  t3, {label_prefix}_FLAT_ENTITY_FIELD_TYPE(t1)\n"
        f"#   lbu  t4, {label_prefix}_FLAT_ENTITY_FIELD_COL(t1)\n"
        f"#   lbu  t5, {label_prefix}_FLAT_ENTITY_FIELD_ROW(t1)\n"
        f"#   addi t1, t1, {label_prefix}_FLAT_ENTITY_SIZE_BYTES\n"
        f"#   addi t2, t2, -1\n"
        f"#   j    loop_ent\n"
        f"# done_ent:\n\n"
    )

    if sorted_entities:
        lines.append(f"{label_prefix}_ENTIDADES_FLAT: {directive}\n")
        for i, ent in enumerate(sorted_entities):
            sep = "" if i == len(sorted_entities) - 1 else ","
            type_name = entity_type_names.get(ent.type_id)
            type_value = (
                f"{label_prefix}_ENTITY_TYPE_{type_name}" if type_name else str(ent.type_id)
            )
            lines.append(f"    {type_value}, {ent.col}, {ent.row}{sep}\n")
    else:
        lines.append(f"# {label_prefix}_ENTIDADES_FLAT: (nenhuma entidade definida)\n")

    path = os.path.join(output_dir, f"{label_prefix}_entidades_flat.s")
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    return path


def export_tileset_offsets(
    state: EditorState,
    output_dir: str,
    label_prefix: str,
) -> str:
    tileset_w_px = state.tileset_cols * state.tile_w
    num_tiles = state.tileset_cols * state.tileset_rows

    lines = [_header(state, label_prefix)]
    lines.append(
        f"# Offset (em bytes) do pixel superior-esquerdo de cada tile dentro\n"
        f"# da imagem do tileset ({tileset_w_px}px de largura, 1 byte/pixel).\n"
        f"# offset[i] = (i / {label_prefix}_TILESET_COLS) * {tileset_w_px} * {label_prefix}_TILE_H\n"
        f"#           + (i % {label_prefix}_TILESET_COLS) * {label_prefix}_TILE_W\n"
        f"#\n"
        f"# Lookup:\n"
        f"#   la   t1, {label_prefix}_TILESET_OFFSETS\n"
        f"#   slli t2, a0, 2          # a0 = tile_id\n"
        f"#   add  t1, t1, t2\n"
        f"#   lw   t1, 0(t1)          # offset em bytes no tileset\n\n"
    )
    lines.append(f".eqv {label_prefix}_TILESET_COLS {state.tileset_cols}\n")
    lines.append(f".eqv {label_prefix}_TILESET_ROWS {state.tileset_rows}\n")
    lines.append(f".eqv {label_prefix}_NUM_TILES    {num_tiles}\n\n")

    lines.append(f"{label_prefix}_TILESET_OFFSETS: .word\n")
    per_line = 8
    for start in range(0, num_tiles, per_line):
        chunk = []
        for i in range(start, min(start + per_line, num_tiles)):
            col = i % state.tileset_cols
            row = i // state.tileset_cols
            chunk.append(row * tileset_w_px * state.tile_h + col * state.tile_w)
        vals_str = ", ".join(str(v) for v in chunk)
        sep = "" if start + per_line >= num_tiles else ","
        lines.append(f"    {vals_str}{sep}\n")

    path = os.path.join(output_dir, f"{label_prefix}_tileset_offsets.s")
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
    paths.append(export_entities_flat(state, output_dir, label_prefix))
    paths.append(export_tileset_offsets(state, output_dir, label_prefix))
    if state.anim_sets:
        paths.append(export_animations(state, output_dir, label_prefix))
    return paths
