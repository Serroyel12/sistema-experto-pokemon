from pathlib import Path
from typing import Dict, List, Any
import csv

# Ruta base del proyecto y carpeta data/
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"


def load_types() -> Dict[int, str]:
    """
    Lee types.csv y devuelve un diccionario:
    id_tipo (int) -> nombre_tipo (str), por ejemplo: 10 -> 'fire'
    """
    types_path = DATA_DIR / "types.csv"
    id_to_name: Dict[int, str] = {}

    with types_path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            type_id = int(row["id"])
            identifier = row["identifier"].lower()
            id_to_name[type_id] = identifier

    return id_to_name


def load_type_chart() -> Dict[str, Dict[str, float]]:
    """
    Lee type_efficacy.csv y construye:
    chart[attacking_type][defending_type] = multiplicador (0, 0.5, 1, 2, 4, ...)
    """
    types_by_id = load_types()
    chart: Dict[str, Dict[str, float]] = {}

    efficacy_path = DATA_DIR / "type_efficacy.csv"
    with efficacy_path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            atk_id = int(row["damage_type_id"])
            def_id = int(row["target_type_id"])
            factor = int(row["damage_factor"])  # 0, 50, 100, 200, etc.

            atk_name = types_by_id.get(atk_id)
            def_name = types_by_id.get(def_id)
            if atk_name is None or def_name is None:
                continue

            multiplier = factor / 100.0  # 200 -> 2.0, 50 -> 0.5, 0 -> 0.0
            chart.setdefault(atk_name, {})[def_name] = multiplier

    return chart


def effectiveness(attacking: str, defending_types: List[str], chart: Dict[str, Dict[str, float]]) -> float:
    """
    Devuelve el multiplicador total de un ataque de tipo `attacking`
    contra un Pokémon con tipos `defending_types` (1 o 2 tipos).
    """
    attacking = attacking.lower()
    total = 1.0

    for dt in defending_types:
        dt = dt.lower()
        mul = chart.get(attacking, {}).get(dt, 1.0)  # por defecto 1.0 si no hay dato
        total *= mul

    return total


def load_moves() -> Dict[str, Dict[str, Any]]:
    """
    Lee moves.csv y devuelve:
    moves[identifier] = {"name": identifier, "type": tipo_nombre, "power": power_int_o_None}
    identifier es el nombre 'oficial' en minúsculas y con guiones, ej: 'water-gun'.
    """
    types_by_id = load_types()
    moves_path = DATA_DIR / "moves.csv"
    moves: Dict[str, Dict[str, Any]] = {}

    with moves_path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            identifier = row["identifier"].lower()  # ej: 'water-gun'
            type_id = int(row["type_id"])
            power_raw = row["power"]

            if power_raw in ("", "0", None):
                power = None
            else:
                power = int(power_raw)

            move_type = types_by_id.get(type_id)
            moves[identifier] = {
                "name": identifier,
                "type": move_type,
                "power": power,
            }

    return moves

def load_pokemon() -> Dict[str, Dict[str, Any]]:
    """
    Carga la información básica de los Pokémon:
    pokemon['charizard'] -> {'id': 6, 'name': 'charizard', 'types': ['fire', 'flying']}
    """
    types_by_id = load_types()

    # Primero: mapa pokemon_id -> lista de type_id (desde pokemon_types.csv)
    ptypes_path = DATA_DIR / "pokemon_types.csv"
    pokemon_types_ids: Dict[int, List[int]] = {}

    with ptypes_path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pid = int(row["pokemon_id"])
            tid = int(row["type_id"])
            pokemon_types_ids.setdefault(pid, []).append(tid)

    # Segundo: leemos pokemon.csv y armamos el diccionario final
    pokemon_path = DATA_DIR / "pokemon.csv"
    pokemon_db: Dict[str, Dict[str, Any]] = {}

    with pokemon_path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pid = int(row["id"])
            identifier = row["identifier"].lower()  # ej: 'charizard'
            type_ids = sorted(pokemon_types_ids.get(pid, []))
            type_names = [types_by_id[tid] for tid in type_ids if tid in types_by_id]

            pokemon_db[identifier] = {
                "id": pid,
                "name": identifier,
                "types": type_names,
            }

    return pokemon_db
