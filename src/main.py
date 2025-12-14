from data_loader import load_type_chart, effectiveness, load_moves, load_pokemon
from inference import forward_chain
from kb import rules


def ask_types(label: str):
    """
    Pide los tipos de un Pokémon a mano (plan B si no se encuentra en la base).
    """
    t1 = input(f"Tipo 1 de {label} (ej: fire, water, grass): ").strip().lower()
    t2 = input(f"Tipo 2 de {label} (vacío si no tiene): ").strip().lower()
    tipos = [t1] if t1 else []
    if t2:
        tipos.append(t2)
    return tipos


def ask_pokemon(label: str, pokemon_db):
    """
    Pregunta el nombre del Pokémon y, si está en la base de datos veekun,
    obtiene automáticamente sus tipos. Si no, pide los tipos manualmente.
    """
    raw_name = input(f"Nombre de {label} (ej: pikachu, charizard): ").strip().lower()
    identifier = raw_name.replace(" ", "-")  # 'mr mime' -> 'mr-mime' (formato veekun)

    info = pokemon_db.get(identifier)
    if info:
        types = info["types"]
        print(f"  -> Encontrado en la base: tipos = {types}")
        return identifier, types
    else:
        print("  -> No se ha encontrado en la base, introduce los tipos manualmente.")
        types = ask_types(label)
        return identifier, types


def has_type_advantage(attacking_types, defending_types, chart) -> bool:
    """
    Devuelve True si alguno de tus tipos hace más de x1 contra la combinación del rival.
    """
    best = 1.0
    for t in attacking_types:
        eff = effectiveness(t, defending_types, chart)
        if eff > best:
            best = eff
    return best > 1.0   # ventaja si hay algún ataque > x1


def ask_moves(moves_db, my_types, enemy_types, chart):
    """
    Pregunta hasta 4 movimientos.
    - Intenta buscarlos en la base veekun por identifier (con guiones).
    - Si no los encuentra, pide tipo y poder manualmente.
    Calcula y añade: tipo, poder, efectividad y score.
    """
    my_moves = []
    print("\nIntroduce hasta 4 movimientos. Ejemplos de nombres válidos (formato veekun):")
    print("  water gun -> water-gun")
    print("  flamethrower -> flamethrower")
    print("  vine whip -> vine-whip")
    print("Deja vacío el nombre para terminar.\n")

    for i in range(4):
        raw_name = input(f"Nombre del movimiento {i+1}: ").strip()
        if not raw_name:
            break

        key = raw_name.lower().replace(" ", "-")
        db_mv = moves_db.get(key)

        if db_mv:
            mv_type = db_mv["type"]
            power = db_mv["power"] if db_mv["power"] is not None else 60
            print(f"  -> Encontrado en base: tipo={mv_type}, poder={power}")
        else:
            print("  -> No encontrado en la base. Te pido datos manuales.")
            mv_type = input("     Tipo del movimiento: ").strip().lower()
            power = float(input("     Poder aproximado (ej 40, 60, 90): "))

        eff = effectiveness(mv_type, enemy_types, chart)
        score = eff * power
        if mv_type in my_types:
            score *= 1.2  # pequeño bonus por STAB

        my_moves.append({
            "name": raw_name,      # nombre tal cual lo escribe el usuario
            "identifier": key,     # nombre en formato veekun (con guiones)
            "type": mv_type,
            "power": power,
            "eff": eff,
            "score": score,
        })

    return my_moves


def main():
    # Cargar bases de datos
    chart = load_type_chart()
    moves_db = load_moves()
    pokemon_db = load_pokemon()

    print("=== Sistema Experto Pokémon (v0.4) ===\n")

    # Datos básicos: nombres + tipos automáticos
    my_name, my_types = ask_pokemon("TU Pokémon", pokemon_db)
    enemy_name, enemy_types = ask_pokemon("POKÉMON ENEMIGO", pokemon_db)

    my_hp_pct = float(input("Tu vida actual (%) 0-100: "))
    enemy_hp_pct = float(input("Vida actual del enemigo (%) 0-100: "))

    # Movimientos
    my_moves = ask_moves(moves_db, my_types, enemy_types, chart)

    # Hechos adicionales: prioridad, defensa y velocidad
    has_priority_move = input(
        "\n¿Tienes algún movimiento de prioridad (ej: quick attack, extremespeed)? (s/n): "
    ).strip().lower() == "s"

    has_defensive_move = input(
        "¿Tienes movimiento defensivo / de curación útil este turno? (s/n): "
    ).strip().lower() == "s"

    speed_info = input(
        "En general, ¿tu Pokémon es más rápido que el rival? (rapido/lento/no se): "
    ).strip().lower()
    is_faster = speed_info == "rapido"
    is_slower = speed_info == "lento"

    # Ventaja aproximada de tipos
    my_advantage = has_type_advantage(my_types, enemy_types, chart)
    enemy_advantage = has_type_advantage(enemy_types, my_types, chart)

    # Base de hechos
    facts = {
        "my_pokemon": my_name,
        "enemy_pokemon": enemy_name,
        "my_types": my_types,
        "enemy_types": enemy_types,
        "my_hp_pct": my_hp_pct,
        "enemy_hp_pct": enemy_hp_pct,
        "my_advantage": my_advantage,
        "enemy_advantage": enemy_advantage,
        "my_moves": my_moves,
        "has_priority_move": has_priority_move,
        "has_defensive_move": has_defensive_move,
        "is_faster": is_faster,
        "is_slower": is_slower,
    }

    # Motor de inferencia
    result = forward_chain(facts, rules())

    # Recomendaciones ordenadas por prioridad
    recos = sorted(result.facts.get("recommendations", []),
                   key=lambda r: -r["priority"])

    print("\n=== RECOMENDACIONES DEL SISTEMA EXPERTO ===")
    if not recos:
        print("No se ha generado ninguna recomendación (todavía pocas reglas).")
    else:
        for r in recos:
            print(f"- [{r['priority']}] {r['text']}")

    print("\n=== EXPLICACIÓN (TRAZA DE REGLAS DISPARADAS) ===")
    if not result.trace:
        print("Ninguna regla se ha activado.")
    else:
        for line in result.trace:
            print(line)


if __name__ == "__main__":
    main()
