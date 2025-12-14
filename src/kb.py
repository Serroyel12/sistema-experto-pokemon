from typing import Any, Dict, List
from inference import Rule, FactBase


def add_reco(facts: FactBase, text: str, priority: int) -> None:
    """
    Añade una recomendación a la lista de recomendaciones en los hechos.
    Cada recomendación tiene un texto y una prioridad numérica.
    """
    facts.setdefault("recommendations", [])
    facts["recommendations"].append({
        "text": text,
        "priority": priority
    })


def compute_best_move(facts: FactBase) -> Dict[str, Any] | None:
    """
    Elige el mejor movimiento según 'score' (ya calculado al leerlos en main).
    """
    moves = facts.get("my_moves", [])
    if not moves:
        return None
    best = max(moves, key=lambda m: m.get("score", 0.0))
    return best


def rules() -> List[Rule]:
    """
    Devuelve la lista de reglas del sistema experto.
    """
    r: List[Rule] = []

    # BLOQUE A: REGLAS GENERALES DE VIDA / VENTAJA DE TIPOS

    # R1: Si tengo mucha vida y ventaja de tipos -> atacar de forma agresiva
    r.append(Rule(
        name="R1_ATTACK_WITH_TYPE_ADVANTAGE",
        when=lambda f: f["my_hp_pct"] >= 60 and f.get("my_advantage") is True,
        then=lambda f: add_reco(f, "Tienes mucha vida y ventaja de tipos: atacar es una buena opción.", 80),
        explain="Con vida alta y ventaja de tipos, es razonable jugar ofensivo."
    ))

    # R2: Si tengo poca vida y el rival tiene ventaja de tipos -> cambiar
    r.append(Rule(
        name="R2_SWITCH_IF_LOW_HP_AND_ENEMY_ADVANTAGE",
        when=lambda f: f["my_hp_pct"] <= 35 and f.get("enemy_advantage") is True,
        then=lambda f: add_reco(f, "Estás en desventaja de tipos y con poca vida: se recomienda cambiar de Pokémon.", 95),
        explain="En desventaja clara y con poca vida, lo experto es pivotar a otro Pokémon."
    ))

    # R3: Si el rival está muy bajo de vida y tú tienes ventaja -> rematar
    r.append(Rule(
        name="R3_FINISH_ENEMY_IF_LOW_HP",
        when=lambda f: f["enemy_hp_pct"] <= 25 and f.get("my_advantage") is True,
        then=lambda f: add_reco(f, "El rival está muy tocado y tienes ventaja: intenta rematarlo este turno.", 90),
        explain="Con el rival en vida baja y ventaja, conviene buscar el KO."
    ))

    # R4: Si los dos tienen vida alta y nadie tiene ventaja clara -> jugar neutro
    r.append(Rule(
        name="R4_NEUTRAL_PLAY_IF_NO_CLEAR_ADVANTAGE",
        when=lambda f: f["my_hp_pct"] >= 50 and f["enemy_hp_pct"] >= 50
                       and not f.get("my_advantage") and not f.get("enemy_advantage"),
        then=lambda f: add_reco(f, "No hay ventaja clara de tipos: puedes optar por un movimiento seguro o ver qué hace el rival.", 50),
        explain="En emparejamientos neutros se recomienda jugar de forma segura."
    ))

    # R5: Si estoy muy bajo pero el rival también -> decisión arriesgada
    r.append(Rule(
        name="R5_RISKY_PLAY_IF_BOTH_LOW",
        when=lambda f: f["my_hp_pct"] <= 30 and f["enemy_hp_pct"] <= 30,
        then=lambda f: add_reco(f, "Ambos estáis muy bajos de vida: cualquier turno puede decidir el combate.", 70),
        explain="Con ambos Pokémon en vida crítica, cada decisión tiene mucho impacto."
    ))

    # BLOQUE B: REGLAS RELACIONADAS CON LOS MOVIMIENTOS

    # D1: derivada -> calcular mejor movimiento según el 'score'
    r.append(Rule(
        name="D1_COMPUTE_BEST_MOVE",
        when=lambda f: "best_move" not in f and len(f.get("my_moves", [])) > 0,
        then=lambda f: f.__setitem__("best_move", compute_best_move(f)),
        explain="Se calcula el mejor movimiento disponible según efectividad, potencia y STAB."
    ))

    # R6: mejor movimiento es súper eficaz (>= x2) -> recomendarlo claramente
    r.append(Rule(
        name="R6_USE_SUPER_EFFECTIVE",
        when=lambda f: f.get("best_move") is not None and f["best_move"]["eff"] >= 2.0,
        then=lambda f: add_reco(
            f,
            f"Tu mejor opción ofensiva es {f['best_move']['name']} (efectividad x{f['best_move']['eff']}).",
            92
        ),
        explain="Cuando hay un movimiento súper eficaz, se prioriza ese ataque."
    ))

    # R7: no hay súper eficaz pero hay uno neutral decente -> usar el mejor neutral
    r.append(Rule(
        name="R7_USE_NEUTRAL_BEST",
        when=lambda f: f.get("best_move") is not None and 0.5 < f["best_move"]["eff"] < 2.0,
        then=lambda f: add_reco(
            f,
            f"No tienes movimientos súper eficaces. Usa {f['best_move']['name']} como mejor opción neutral.",
            75
        ),
        explain="Cuando no hay ventaja de tipos, se usa el movimiento neutral más fuerte."
    ))

    # R8: todos son resistidos y rival bastante sano -> cambio
    r.append(Rule(
        name="R8_SWITCH_IF_ALL_RESISTED",
        when=lambda f: f.get("best_move") is not None and f["best_move"]["eff"] <= 0.5 and f["enemy_hp_pct"] >= 40,
        then=lambda f: add_reco(
            f,
            "Tus movimientos son poco eficaces contra el rival. Plantéate cambiar de Pokémon.",
            85
        ),
        explain="Si todo lo que tienes es resistido y el rival tiene bastante vida, es preferible cambiar."
    ))

    # BLOQUE C: PRIORIDAD, DEFENSA Y VELOCIDAD

    # R9: estás muy bajo de vida, no hay súper eficaz claro y tienes defensa -> defiéndete
    r.append(Rule(
        name="R9_DEFEND_IF_VERY_LOW_HP_NO_KO",
        when=lambda f: f["my_hp_pct"] <= 25
                       and f.get("has_defensive_move")
                       and (f.get("best_move") is None or f["best_move"]["eff"] < 2.0),
        then=lambda f: add_reco(
            f,
            "Tienes poca vida y no parece que puedas hacer un KO claro: usar un movimiento defensivo/curación es razonable.",
            88
        ),
        explain="Si no hay opción clara de eliminar al rival y estás muy tocado, prioriza sobrevivir."
    ))

    # R10: el rival está muy bajo y tienes prioridad -> remata con prioridad
    r.append(Rule(
        name="R10_FINISH_WITH_PRIORITY",
        when=lambda f: f["enemy_hp_pct"] <= 25 and f.get("has_priority_move"),
        then=lambda f: add_reco(
            f,
            "El rival está muy bajo de vida y tienes un movimiento de prioridad: es buena idea usarlo para asegurar el KO.",
            93
        ),
        explain="La prioridad reduce el riesgo de que el rival te golpee antes en esta situación."
    ))

    # R11: estás bajo de vida, eres más lento y el rival tiene ventaja -> casi obligado a cambiar
    r.append(Rule(
        name="R11_SWITCH_IF_SLOW_AND_WEAK",
        when=lambda f: f["my_hp_pct"] <= 40 and f.get("is_slower") and f.get("enemy_advantage"),
        then=lambda f: add_reco(
            f,
            "Eres más lento, el rival tiene ventaja de tipos y vas justo de vida: la opción más segura es cambiar de Pokémon.",
            97
        ),
        explain="Ser más lento en desventaja de tipos aumenta la probabilidad de caer antes de actuar."
    ))

    # R12: tienes vida aceptable, eres más rápido y el mejor movimiento es al menos neutral -> atacar
    r.append(Rule(
        name="R12_ATTACK_IF_FASTER_AND_OK_HP",
        when=lambda f: f["my_hp_pct"] >= 40
                       and f.get("is_faster")
                       and f.get("best_move") is not None
                       and f["best_move"]["eff"] >= 1.0,
        then=lambda f: add_reco(
            f,
            "Eres más rápido, tienes vida razonable y un movimiento al menos neutral: atacar es una jugada sólida.",
            78
        ),
        explain="Ser más rápido permite presionar al rival antes de que actúe."
    ))

    # R13: ambos con vida media, tú eres más rápido y el mejor movimiento es súper eficaz -> presión fuerte
    r.append(Rule(
        name="R13_STRONG_PRESSURE_IF_FASTER_SUPER_EFFECTIVE",
        when=lambda f: 40 <= f["my_hp_pct"] <= 80
                       and 40 <= f["enemy_hp_pct"] <= 80
                       and f.get("is_faster")
                       and f.get("best_move") is not None
                       and f["best_move"]["eff"] >= 2.0,
        then=lambda f: add_reco(
            f,
            "Tienes un movimiento súper eficaz siendo más rápido y ambos estáis a media vida: presionar fuerte puede darte una gran ventaja.",
            89
        ),
        explain="En situaciones equilibradas, un ataque súper eficaz y rápido suele decantar el combate."
    ))

    # R14: no tienes movimientos decentes (score muy bajo) -> advertencia
    r.append(Rule(
        name="R14_NO_GOOD_MOVES_WARNING",
        when=lambda f: len(f.get("my_moves", [])) > 0
                       and all(m.get("score", 0.0) < 30 for m in f["my_moves"]),
        then=lambda f: add_reco(
            f,
            "Ninguno de tus movimientos parece especialmente bueno (baja potencia o poco eficaz). Plantéate cambiar si es posible.",
            60
        ),
        explain="Si todos los movimientos tienen mala puntuación, quizá otro Pokémon tenga mejores opciones."
    ))

    # R15: no se ha introducido ningún movimiento -> recomendación genérica
    r.append(Rule(
        name="R15_NO_MOVES_INFO",
        when=lambda f: len(f.get("my_moves", [])) == 0,
        then=lambda f: add_reco(
            f,
            "No se han especificado movimientos, solo puedo recomendar de forma general según tipos y vida.",
            40
        ),
        explain="La ausencia de información sobre movimientos limita la precisión de las recomendaciones."
    ))
    # BLOQUE D: REGLAS QUE USAN LOS NOMBRES DE LOS POKÉMON

    # R16: Combate de mismo tipo principal sin ventaja clara
    r.append(Rule(
        name="R16_SAME_MAIN_TYPE_BATTLE",
        when=lambda f: len(f.get("my_types", [])) > 0
                       and len(f.get("enemy_types", [])) > 0
                       and f["my_types"][0] == f["enemy_types"][0]
                       and not f.get("my_advantage")
                       and not f.get("enemy_advantage"),
        then=lambda f: add_reco(
            f,
            f"Tu {f.get('my_pokemon', 'Pokémon')} comparte el mismo tipo principal que "
            f"{f.get('enemy_pokemon', 'el rival')}: los movimientos de cobertura de otros tipos pueden ser decisivos.",
            65
        ),
        explain="En combates de mismo tipo, los movimientos de cobertura suelen marcar la diferencia."
    ))

    # R17: Explicación específica de ventaja de tipos con los nombres
    r.append(Rule(
        name="R17_EXPLAIN_TYPE_ADVANTAGE_WITH_NAMES",
        when=lambda f: f.get("my_pokemon") and f.get("enemy_pokemon") and f.get("my_advantage"),
        then=lambda f: add_reco(
            f,
            f"{f['my_pokemon'].capitalize()} tiene ventaja de tipos sobre "
            f"{f['enemy_pokemon'].capitalize()}: mantener este emparejamiento suele ser beneficioso.",
            55
        ),
        explain="Se ofrece una explicación específica de la ventaja de tipos usando los nombres de los Pokémon."
    ))

    return r


