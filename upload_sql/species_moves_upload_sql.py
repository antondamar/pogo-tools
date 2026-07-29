import json
import re
from psycopg2.extras import execute_values
from db_access import get_db_connection

PATTERN_POKEMON = r"^V(?P<pokedex_num>\d{4})_POKEMON_(?P<name>[A-Z0-9]+)(?:_(?P<form>[A-Z0-9_]+))?$"

def extract_species_moves_raw(game_master: list, N: int) -> list:
    """
    Extracts raw species-to-move mappings from the JSON file.
    Returns dictionaries containing:
    { "species_id": int, "species_form": str, "move_name": str, "is_elite_move": bool }
    """
    seen_relations = set()
    raw_records = []

    for item in game_master:
        template_id = item.get("templateId", "")
        match = re.match(PATTERN_POKEMON, template_id)

        if not match:
            continue

        pokedex_num = int(match.group("pokedex_num"))
        if pokedex_num > N:
            continue

        pokemon_form = match.group("form") if match.group("form") else "NORMAL"
        
        data = item.get("data", {})
        pokemon_settings = data.get("pokemonSettings", {})

        # 1. Grab base moves
        quick_moves = pokemon_settings.get("quickMoves", [])
        cinematic_moves = pokemon_settings.get("cinematicMoves", [])
        elite_quick_moves = pokemon_settings.get("eliteQuickMove", [])
        elite_cinematic_moves = pokemon_settings.get("eliteCinematicMove", [])

        # 2. Extract Signature Moves from form changes (Purely in-memory)
        form_changes = pokemon_settings.get("formChange", [])
        for form in form_changes:
            move_reassignment = form.get("moveReassignment", {})
            
            # Extract existing Fast Moves tied to this specific form
            for q in move_reassignment.get("quickMoves", []):
                existing_q = q.get("existingMoves", [])
                quick_moves.extend(existing_q)
                
            # Extract existing Charged Moves tied to this specific form (e.g., Behemoth Blade)
            for c in move_reassignment.get("cinematicMoves", []):
                existing_c = c.get("existingMoves", [])
                cinematic_moves.extend(existing_c)

        # 3. Group and format
        move_groups = [
            (quick_moves, False),
            (cinematic_moves, False),
            (elite_quick_moves, True),
            (elite_cinematic_moves, True),
        ]

        for moves, is_elite in move_groups:
            if not moves or not isinstance(moves, list):
                continue
            
            for move_raw in moves:
                # Strip _FAST to match the moves table naming convention
                move_name = str(move_raw).replace("_FAST", "")
    
                # Deduplication check
                relation_key = (pokedex_num, pokemon_form, move_name)
                if relation_key in seen_relations:
                    continue
                seen_relations.add(relation_key)

                raw_records.append({
                    "species_id": pokedex_num,
                    "species_form": pokemon_form,
                    "move_name": move_name,
                    "is_elite_move": is_elite
                })

    return raw_records


def populate_species_moves(raw_records: list):
    """
    Looks up move_id from the 'moves' table and inserts into 'species_moves'.
    """

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                print("Fetching move IDs from Neon...")
                cursor.execute("SELECT id, name FROM moves;")
                move_map = {name: move_id for move_id, name in cursor.fetchall()}
                tuples_to_insert = []
                missing_moves = set()

                for r in raw_records:
                    move_name = r["move_name"]
                    if move_name in move_map:
                        tuples_to_insert.append((
                            r["species_id"],
                            r["species_form"],
                            move_map[move_name],
                            r["is_elite_move"]
                        ))
                    else:
                        missing_moves.add(move_name)

                if missing_moves:
                    print(f"Warning: {len(missing_moves)} moves in species data were not found in 'moves' table.")

                insert_query = """
                    INSERT INTO species_moves (species_id, species_form, move_id, is_elite_move)
                    VALUES %s
                    ON CONFLICT (species_id, species_form, move_id) DO UPDATE SET
                        is_elite_move = EXCLUDED.is_elite_move;
                """

                print(f"Uploading {len(tuples_to_insert)} relations to 'species_moves'...")
                execute_values(cursor, insert_query, tuples_to_insert)
            conn.commit()

        print(f"Successfully connected {len(tuples_to_insert)} species-move pairs in PostgreSQL!")

    except Exception as e:
        print(f"Database Error: {e}")


if __name__ == "__main__":
    with open('../latest.json', 'r', encoding='utf-8') as file:
        game_master = json.load(file)

    raw_species_moves = extract_species_moves_raw(game_master, 1025)
    populate_species_moves(raw_species_moves)