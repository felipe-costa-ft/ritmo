import json
import os
from editor import (
    AnimClip, AnimFrame, AnimSet,
    CollisionType, Entity, EntityType, EditorState,
    create_empty_state, load_tileset,
)


def save_project(state: EditorState, filepath: str) -> None:
    base_dir = os.path.dirname(os.path.abspath(filepath))
    tileset_rel = (
        os.path.relpath(state.tileset_path, base_dir)
        if state.tileset_path else ""
    )

    data = {
        "version": 3,
        "map_cols": state.map_cols,
        "map_rows": state.map_rows,
        "tile_w": state.tile_w,
        "tile_h": state.tile_h,
        "tileset_path": tileset_rel,
        "collision_types": [
            {"id": ct.id, "name": ct.name, "color": list(ct.color)}
            for ct in state.collision_types
        ],
        "entity_types": [
            {"id": et.id, "name": et.name, "color": list(et.color)}
            for et in state.entity_types
        ],
        "visual_layer": state.visual_layer,
        "collision_layer": state.collision_layer,
        "entities": [[e.type_id, e.col, e.row] for e in state.entities],
        "anim_sets": [
            {
                "name": s.name,
                "clips": [
                    {
                        "name": c.name,
                        "default_delay_ms": c.default_delay_ms,
                        "loop": c.loop,
                        "frames": [
                            {"tile_id": f.tile_id, "delay_ms": f.delay_ms}
                            for f in c.frames
                        ],
                    }
                    for c in s.clips
                ],
            }
            for s in state.anim_sets
        ],
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_project(filepath: str) -> EditorState:
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    version = data.get("version", 1)
    base_dir = os.path.dirname(os.path.abspath(filepath))

    map_cols = data["map_cols"]
    map_rows = data["map_rows"]
    tile_w = data["tile_w"]
    tile_h = data["tile_h"]

    state = create_empty_state(map_cols, map_rows, tile_w, tile_h)

    vl = data["visual_layer"]
    cl = data["collision_layer"]
    expected = map_cols * map_rows
    if len(vl) != expected or len(cl) != expected:
        raise ValueError(
            f"Layers com tamanho incorreto: esperado {expected}, "
            f"visual={len(vl)}, colisão={len(cl)}"
        )
    state.visual_layer = vl
    state.collision_layer = cl

    state.collision_types = [
        CollisionType(id=ct["id"], name=ct["name"], color=tuple(ct["color"]))
        for ct in data["collision_types"]
    ]

    if version >= 2:
        state.entity_types = [
            EntityType(id=et["id"], name=et["name"], color=tuple(et["color"]),
                       sprite_surface=None)
            for et in data.get("entity_types", [])
        ]
        valid_ids = {et.id for et in state.entity_types}
        state.entities = []
        for e in data.get("entities", []):
            type_id, col, row = e
            if type_id not in valid_ids:
                print(f"Aviso: entidade type_id={type_id} sem tipo — ignorada")
                continue
            state.entities.append(Entity(type_id=type_id, col=col, row=row))

    if version >= 3:
        state.anim_sets = [
            AnimSet(
                name=s["name"],
                clips=[
                    AnimClip(
                        name=c["name"],
                        default_delay_ms=c["default_delay_ms"],
                        loop=c["loop"],
                        frames=[
                            AnimFrame(tile_id=f["tile_id"], delay_ms=f["delay_ms"])
                            for f in c["frames"]
                        ],
                    )
                    for c in s["clips"]
                ],
            )
            for s in data.get("anim_sets", [])
        ]

    tileset_rel = data.get("tileset_path", "")
    if tileset_rel:
        tileset_abs = os.path.normpath(os.path.join(base_dir, tileset_rel))
        if os.path.isfile(tileset_abs):
            load_tileset(state, tileset_abs)
        else:
            print(f"Aviso: tileset não encontrado em {tileset_abs}")

    return state
