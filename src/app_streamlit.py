import streamlit as st

from data_loader import load_type_chart, effectiveness, load_moves, load_pokemon
from inference import forward_chain
from kb import rules


# ========================
# Carga de datos (cacheada)
# ========================

@st.cache_data
def get_type_chart():
    return load_type_chart()


@st.cache_data
def get_moves_db():
    return load_moves()


@st.cache_data
def get_pokemon_db():
    return load_pokemon()


# ========================
# Funciones auxiliares
# ========================

def normalize_identifier(name: str) -> str:
    """
    Convierte 'Mr Mime' -> 'mr-mime' (formato veekun aproximado).
    """
    return name.strip().lower().replace(" ", "-")


def get_pokemon_types(name: str, pokemon_db):
    """
    Devuelve (identifier, [types]) a partir del nombre.
    Si no se encuentra, devuelve (identifier, []).
    """
    identifier = normalize_identifier(name)
    info = pokemon_db.get(identifier)
    if info:
        return identifier, info["types"]
    else:
        return identifier, []


def has_type_advantage(attacking_types, defending_types, chart) -> bool:
    """
    Devuelve True si alguno de tus tipos hace más de x1 contra la combinación del rival.
    """
    if not attacking_types or not defending_types:
        return False

    best = 1.0
    for t in attacking_types:
        eff = effectiveness(t, defending_types, chart)
        if eff > best:
            best = eff
    return best > 1.0   # ventaja si hay algún ataque > x1


def build_moves(moves_db, my_types, enemy_types, chart):
    """
    Construye la lista de movimientos a partir de los nombres introducidos en Streamlit.
    Requiere que los movimientos existan en la base veekun.
    """
    my_moves = []

    for i in range(1, 5):
        raw_name = st.text_input(
            f"Movimiento {i} (identifier veekun, ej: flamethrower, water-gun, thunderbolt)",
            key=f"mv{i}"
        )
        raw_name = raw_name.strip()
        if not raw_name:
            continue

        key = normalize_identifier(raw_name)
        db_mv = moves_db.get(key)

        if not db_mv:
            st.warning(f"El movimiento '{raw_name}' no se ha encontrado en la base veekun. "
                       f"Revisa el nombre o déjalo vacío si no lo necesitas.")
            continue

        mv_type = db_mv["type"]
        power = db_mv["power"] if db_mv["power"] is not None else 60

        eff = effectiveness(mv_type, enemy_types, chart) if enemy_types else 1.0
        score = eff * power
        if mv_type in my_types:
            score *= 1.2  # bonus por STAB

        my_moves.append({
            "name": raw_name,      # como lo ve el usuario
            "identifier": key,     # formato veekun
            "type": mv_type,
            "power": power,
            "eff": eff,
            "score": score,
        })

    return my_moves


# ========================
# App principal Streamlit
# ========================

def main():
    st.title("⚔️ Sistema Experto Pokémon – Asistente de Combate")
    st.write("Introduce la situación del combate y el sistema experto te recomendará la mejor acción.")

    chart = get_type_chart()
    moves_db = get_moves_db()
    pokemon_db = get_pokemon_db()

    st.header("1️⃣ Datos de los Pokémon")

    col1, col2 = st.columns(2)

    with col1:
        my_raw_name = st.text_input("Nombre de tu Pokémon (ej: charizard, pikachu)", value="charizard")
        my_identifier, my_types = get_pokemon_types(my_raw_name, pokemon_db)
        if my_types:
            st.success(f"{my_identifier} encontrado. Tipos: {my_types}")
        else:
            st.error("Tu Pokémon no se ha encontrado en la base. Algunas reglas pueden no activarse.")

    with col2:
        enemy_raw_name = st.text_input("Nombre del Pokémon enemigo (ej: blastoise, venusaur)", value="blastoise")
        enemy_identifier, enemy_types = get_pokemon_types(enemy_raw_name, pokemon_db)
        if enemy_types:
            st.success(f"{enemy_identifier} encontrado. Tipos: {enemy_types}")
        else:
            st.error("El Pokémon enemigo no se ha encontrado en la base. Algunas reglas pueden no activarse.")

    st.header("2️⃣ Estado del combate")

    my_hp_pct = st.slider("Tu vida actual (%)", min_value=0, max_value=100, value=80, step=5)
    enemy_hp_pct = st.slider("Vida actual del enemigo (%)", min_value=0, max_value=100, value=60, step=5)

    st.header("3️⃣ Movimientos de tu Pokémon")
    st.caption("Usa los nombres en formato veekun. Ejemplos: **flamethrower**, **water-gun**, **vine-whip**, **thunderbolt**.")
    my_moves = build_moves(moves_db, my_types, enemy_types, chart)

    st.header("4️⃣ Otros factores")
    has_priority_move = st.checkbox("Tengo algún movimiento de prioridad (Quick Attack, ExtremeSpeed, etc.)")
    has_defensive_move = st.checkbox("Tengo un movimiento defensivo / de curación útil este turno")

    speed_choice = st.radio(
        "Velocidad relativa",
        options=["No lo sé", "Soy más rápido", "Soy más lento"],
        index=0
    )
    is_faster = (speed_choice == "Soy más rápido")
    is_slower = (speed_choice == "Soy más lento")

    # Botón para lanzar el motor de inferencia
    if st.button("🔍 Calcular recomendación"):
        # Ventaja de tipos aproximada
        my_advantage = has_type_advantage(my_types, enemy_types, chart)
        enemy_advantage = has_type_advantage(enemy_types, my_types, chart)

        # Base de hechos igual que en la versión de consola
        facts = {
            "my_pokemon": my_identifier,
            "enemy_pokemon": enemy_identifier,
            "my_types": my_types,
            "enemy_types": enemy_types,
            "my_hp_pct": float(my_hp_pct),
            "enemy_hp_pct": float(enemy_hp_pct),
            "my_advantage": my_advantage,
            "enemy_advantage": enemy_advantage,
            "my_moves": my_moves,
            "has_priority_move": has_priority_move,
            "has_defensive_move": has_defensive_move,
            "is_faster": is_faster,
            "is_slower": is_slower,
        }

        result = forward_chain(facts, rules())
        recos = sorted(result.facts.get("recommendations", []),
                       key=lambda r: -r["priority"])

        st.subheader("📋 Resumen de la situación")
        st.write(f"**Tu Pokémon:** {my_identifier}  – tipos: {my_types} – vida: {my_hp_pct}%")
        st.write(f"**Enemigo:** {enemy_identifier}  – tipos: {enemy_types} – vida: {enemy_hp_pct}%")
        st.write(f"Ventaja de tipos tuya: `{my_advantage}`  |  Ventaja del rival: `{enemy_advantage}`")

        best = result.facts.get("best_move")
        if best:
            st.subheader("🥊 Mejor movimiento según el sistema")
            st.write(
                f"- **{best['name']}** (tipo `{best['type']}`, poder {best['power']}, "
                f"efectividad x{best['eff']}, score={best['score']:.1f})"
            )

        st.subheader("✅ Recomendaciones del sistema experto")
        if not recos:
            st.info("No se ha generado ninguna recomendación (puede que falte información de tipos o movimientos).")
        else:
            for r in recos:
                st.markdown(f"- **[{r['priority']}]** {r['text']}")

        st.subheader("🧠 Explicación (reglas disparadas)")
        if not result.trace:
            st.info("Ninguna regla se ha activado.")
        else:
            for line in result.trace:
                st.code(line)


if __name__ == "__main__":
    main()
