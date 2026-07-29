import json
import re
from psycopg2.extras import execute_values
from db_access import get_db_connection

# Pattern matches both PvE (V0247_MOVE_FOCUS_BLAST) and PvP (COMBAT_V0247_MOVE_FOCUS_BLAST)
PATTERN_MOVE = r"^(?:COMBAT_)?V\d{4}_MOVE_(?P<move_name>[A-Z0-9_]+)$"

def extract_move_records(game_master: list) -> list:
    """Extract and parse all PvE and PvP combat moves, merging them by name."""
    moves_dict = {}

    for item in game_master:
        template_id = item.get("templateId", "")
        match = re.match(PATTERN_MOVE, template_id)

        if not match:
            continue

        raw_name = match.group("move_name")
        move_name = raw_name.replace("_FAST", "")
        
        # Initialize the move in the dictionary if we haven't seen it yet
        if move_name not in moves_dict:
            moves_dict[move_name] = {
                "name": move_name,
                "type": "NORMAL",
                "is_fast_move": raw_name.endswith("_FAST"),
                "pve_power": 0.0,
                "pve_energy_delta": 0,
                "duration_ms": 0,
                "damage_window_start_ms": 0,
                "damage_window_end_ms": 0,
                "pvp_power": 0.0,
                "pvp_energy_delta": 0
            }

        data = item.get("data", {})

        # 1. Parse PvE Data (moveSettings)
        if "moveSettings" in data:
            move_settings = data["moveSettings"]
            
            raw_type = move_settings.get("pokemonType", "")
            if raw_type:
                moves_dict[move_name]["type"] = raw_type.replace("POKEMON_TYPE_", "")
            
            moves_dict[move_name]["pve_power"] = move_settings.get("power", 0.0)
            moves_dict[move_name]["pve_energy_delta"] = move_settings.get("energyDelta", 0)
            moves_dict[move_name]["duration_ms"] = move_settings.get("durationMs", 0)
            moves_dict[move_name]["damage_window_start_ms"] = move_settings.get("damageWindowStartMs", 0)
            moves_dict[move_name]["damage_window_end_ms"] = move_settings.get("damageWindowEndMs", 0)
            
            # Fallback fast move check (fast moves generate energy)
            if move_settings.get("energyDelta", 0) > 0:
                moves_dict[move_name]["is_fast_move"] = True

        # 2. Parse PvP Data (combatMove)
        elif "combatMove" in data:
            combat_move = data["combatMove"]
            
            raw_type = combat_move.get("type", "")
            if raw_type:
                moves_dict[move_name]["type"] = raw_type.replace("POKEMON_TYPE_", "")
                
            moves_dict[move_name]["pvp_power"] = combat_move.get("power", 0.0)
            moves_dict[move_name]["pvp_energy_delta"] = combat_move.get("energyDelta", 0)
            
            # Fallback fast move check
            if combat_move.get("energyDelta", 0) > 0:
                moves_dict[move_name]["is_fast_move"] = True

    # Convert dictionary values back to a list of records
    return list(moves_dict.values())


def populate_moves_database(records: list):
    """Upsert moves into the PostgreSQL database."""

    insert_query = """
        INSERT INTO moves (
            name, type, is_fast_move, 
            pve_power, pve_energy_delta, duration_ms, damage_window_start_ms, damage_window_end_ms, 
            pvp_power, pvp_energy_delta
        )
        VALUES %s
        ON CONFLICT (name) DO UPDATE SET
            type = EXCLUDED.type,
            is_fast_move = EXCLUDED.is_fast_move,
            pve_power = EXCLUDED.pve_power, 
            pve_energy_delta = EXCLUDED.pve_energy_delta,
            duration_ms = EXCLUDED.duration_ms,
            damage_window_start_ms = EXCLUDED.damage_window_start_ms,
            damage_window_end_ms = EXCLUDED.damage_window_end_ms,
            pvp_power = EXCLUDED.pvp_power,
            pvp_energy_delta = EXCLUDED.pvp_energy_delta;
    """

    tuples_to_insert = [
        (
            r["name"],
            r["type"],
            r["is_fast_move"],
            r["pve_power"],
            r["pve_energy_delta"],
            r["duration_ms"],
            r["damage_window_start_ms"],
            r["damage_window_end_ms"],
            r["pvp_power"],
            r["pvp_energy_delta"]
        )
        for r in records
    ]

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                execute_values(cursor, insert_query, tuples_to_insert)
            conn.commit()
        print(f"Successfully inserted/updated {len(records)} moves into PostgreSQL!")

    except Exception as e:
        print(f"Database Error: {e}")


if __name__ == "__main__":
    with open('../latest.json', 'r', encoding='utf-8') as file:
        game_master = json.load(file)

    move_records = extract_move_records(game_master)
    populate_moves_database(move_records)