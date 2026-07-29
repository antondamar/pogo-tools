import json
import re
from psycopg2.extras import execute_values
from db_access import get_db_connection

PATTERN = r"^V(?P<pokedex_num>\d{4})_POKEMON_(?P<name>[A-Z0-9]+)(?:_(?P<form>[A-Z0-9_]+))?$"

def extract_pokemon_records(game_master, N: int) -> list:
    """Fetch the pokemons listed on the file."""
    seen_id_form = set()  # Changed list to set for O(1) lookup
    records = []

    for item in game_master:
        template_id = item.get("templateId", "")
        match = re.match(PATTERN, template_id)

        if not match:
            continue

        pokedex_num = int(match.group("pokedex_num"))
        if pokedex_num > N:
            continue

        pokemon_name = match.group("name")
        pokemon_form = match.group("form") if match.group("form") else "NORMAL"

        if (pokedex_num, pokemon_form) in seen_id_form:
            continue
        seen_id_form.add((pokedex_num, pokemon_form))

        data = item.get("data", {})
        pokemon_settings = data.get("pokemonSettings", {})
        stats = pokemon_settings.get("stats", {})

        raw_type1 = pokemon_settings.get("type", None)
        raw_type2 = pokemon_settings.get("type2", None)
        if not raw_type1:
            continue

        type1 = raw_type1.replace("POKEMON_TYPE_", "") if raw_type1 else None
        type2 = raw_type2.replace("POKEMON_TYPE_", "") if raw_type2 else None

        records.append({
            "id": pokedex_num,
            "form": pokemon_form,
            "name": pokemon_name,
            "type_1": type1,
            "type_2": type2,
            "base_attack": stats.get("baseAttack", 0),
            "base_defense": stats.get("baseDefense", 0),
            "base_stamina": stats.get("baseStamina", 0)
        })

        # Process Mega / Temp Evolutions
        temp_evo_overrides = pokemon_settings.get("tempEvoOverrides", [])
        if isinstance(temp_evo_overrides, list):
            for evo in temp_evo_overrides:
                evo_name = evo.get("tempEvoId", "MEGA").replace("TEMP_EVOLUTION_", "")
                evo_stats = evo.get("stats", {})

                if (pokedex_num, evo_name) in seen_id_form:
                    continue
                seen_id_form.add((pokedex_num, evo_name))

                # If override keys exist, use them; otherwise fall back to base form types
                evo_type1_raw = evo.get("typeOverride1", raw_type1)
                evo_type2_raw = evo.get("typeOverride2", raw_type2) if "typeOverride2" in evo else raw_type2

                evo_type1 = evo_type1_raw.replace("POKEMON_TYPE_", "") if evo_type1_raw else None
                evo_type2 = evo_type2_raw.replace("POKEMON_TYPE_", "") if evo_type2_raw else None

                records.append({
                    "id": pokedex_num,
                    "form": evo_name,
                    "name": pokemon_name,
                    "type_1": evo_type1,
                    "type_2": evo_type2,
                    "base_attack": evo_stats.get("baseAttack", 0),
                    "base_defense": evo_stats.get("baseDefense", 0),
                    "base_stamina": evo_stats.get("baseStamina", 0)
                })

    return records


def populate_database(records: list):
    insert_query = """
        INSERT INTO species (id, form, name, type_1, type_2, base_attack, base_defense, base_stamina)
        VALUES %s
        ON CONFLICT (id, form) DO UPDATE SET
            name = EXCLUDED.name,
            type_1 = EXCLUDED.type_1,
            type_2 = EXCLUDED.type_2,
            base_attack = EXCLUDED.base_attack,
            base_defense = EXCLUDED.base_defense,
            base_stamina = EXCLUDED.base_stamina;
    """

    # Format tuples for batch execution
    tuples_to_insert = [
        (
            r["id"],
            r["form"],
            r["name"],
            r["type_1"],
            r["type_2"],
            r["base_attack"],
            r["base_defense"],
            r["base_stamina"]
        )
        for r in records
    ]

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                execute_values(cursor, insert_query, tuples_to_insert)
            conn.commit()
        print(f"Successfully inserted/updated {len(records)} records into PostgreSQL!")

    except Exception as e:
        print(f"Database Error: {e}")


if __name__ == "__main__":
    with open('../latest.json', 'r', encoding='utf-8') as file:
        game_master = json.load(file)

    pokemon_records = extract_pokemon_records(game_master, 1025)
    populate_database(pokemon_records)