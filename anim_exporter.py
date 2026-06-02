import os
from datetime import datetime
from editor import EditorState


def export_animations(state: EditorState, output_dir: str, label_prefix: str) -> str:
    lines = [
        f"# Gerado automaticamente pelo RITMO em {datetime.now().strftime('%Y-%m-%d %H:%M')}\n",
        f"# Prefixo: {label_prefix}\n",
        f"#\n",
        f"# Formato de cada descritor:\n",
        f"#   .word N, 0, 0x80000000, tile0, tile1, ..., tileN-1\n",
        f"#   N = numero de frames | campo 2 = frame atual (runtime) | campo 3 = timestamp (runtime)\n",
        f"#   0x80000000 garante que o primeiro frame exibido seja tile0 (mesmo com time=0)\n",
        f"#\n",
        f"# Uso:\n",
        f"#   la  a1, LABEL          # endereco do descritor\n",
        f"#   mv  a2, screen_x\n",
        f"#   mv  a3, screen_y\n",
        f"#   li  a4, LABEL_DELAY    # delay em ms\n",
        f"#   jal DRAW_ANIMATION_TILE\n",
        f"#   # a0 = 1 se completou um ciclo\n\n",
    ]

    for anim_set in state.anim_sets:
        set_prefix = f"{label_prefix}_{anim_set.name.upper()}"
        lines.append(f"# --- {anim_set.name} ---\n\n")

        for clip in anim_set.clips:
            clip_prefix = f"{set_prefix}_{clip.name.upper()}"
            loop_str = "loop" if clip.loop else "one-shot"
            lines.append(f"# {clip.name} ({loop_str})\n")
            lines.append(f".eqv {clip_prefix}_DELAY  {clip.default_delay_ms}\n")

            tile_ids = []
            for frame in clip.frames:
                tile_ids.append(str(frame.tile_id))

            if tile_ids:
                tiles_str = ", ".join(tile_ids)
                lines.append(
                    f"{clip_prefix}: .word {len(clip.frames)}, 0, 0x80000000, {tiles_str}\n\n"
                )
            else:
                lines.append(f"# {clip_prefix}: (sem frames)\n\n")

    path = os.path.join(output_dir, f"{label_prefix}_anim.s")
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    return path
