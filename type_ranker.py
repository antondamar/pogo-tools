import math
from db import get_db_connection
from battle import TYPE_CHART, get_type_effectiveness
from pokemon_utils import (
    calculate_move_damage,
    expand_pokemon_variants,
    format_mega_label,
    MEGA_FORMS_QUERY,
    prompt_include_mega,
)

POKEMON_TYPES = sorted(TYPE_CHART.keys())
REFERENCE_DEFENSE = 150  # Neutral reference for type-only counter rankings

INVENTORY_QUERY = """
    SELECT
        up.id AS inv_id,
        up.species_id,
        up.species_form,
        up.nickname,
        s.name AS species_name,
        s.type_1 AS atk_type_1,
        s.type_2 AS atk_type_2,
        s.base_attack,
        s.base_defense,
        s.base_stamina,
        up.cp,
        up.level,
        up.atk_iv,
        up.def_iv,
        up.sta_iv,
        up.is_shadow,
        up.fast_move_id,
        up.charged_move_1_id,
        up.charged_move_2_id,
        mf.id AS cur_fast_id, mf.name AS cur_fast_name, mf.type AS cur_fast_type,
        mf.pve_power AS cur_fast_pve_power, mf.pvp_power AS cur_fast_pvp_power,
        mf.pve_energy_delta AS cur_fast_pve_energy, mf.pvp_energy_delta AS cur_fast_pvp_energy,
        mf.duration_ms AS cur_fast_duration,
        mc1.id AS cur_c1_id, mc1.name AS cur_c1_name, mc1.type AS cur_c1_type,
        mc1.pve_power AS cur_c1_pve_power, mc1.pvp_power AS cur_c1_pvp_power,
        mc1.pve_energy_delta AS cur_c1_pve_energy, mc1.pvp_energy_delta AS cur_c1_pvp_energy,
        mc1.duration_ms AS cur_c1_duration,
        mc2.id AS cur_c2_id, mc2.name AS cur_c2_name, mc2.type AS cur_c2_type,
        mc2.pve_power AS cur_c2_pve_power, mc2.pvp_power AS cur_c2_pvp_power,
        mc2.pve_energy_delta AS cur_c2_pve_energy, mc2.pvp_energy_delta AS cur_c2_pvp_energy,
        mc2.duration_ms AS cur_c2_duration
    FROM user_pokemon up
    JOIN species s ON up.species_id = s.id AND up.species_form = s.form
    LEFT JOIN moves mf ON up.fast_move_id = mf.id
    LEFT JOIN moves mc1 ON up.charged_move_1_id = mc1.id
    LEFT JOIN moves mc2 ON up.charged_move_2_id = mc2.id
    WHERE up.user_id = %s;
"""

LEGAL_MOVES_QUERY = """
    SELECT
        m.id, m.name, m.type, m.is_fast_move,
        m.pve_power, m.pvp_power,
        m.pve_energy_delta, m.pvp_energy_delta,
        m.duration_ms, sm.is_elite_move
    FROM species_moves sm
    JOIN moves m ON m.id = sm.move_id
    WHERE sm.species_id = %s AND sm.species_form = %s
    ORDER BY m.is_fast_move DESC, m.name ASC;
"""


def _move_power(move: dict, is_pvp: bool) -> float | None:
    key = "pvp_power" if is_pvp else "pve_power"
    val = move.get(key)
    return float(val) if val is not None else None


def _move_energy(move: dict, is_pvp: bool) -> float:
    key = "pvp_energy_delta" if is_pvp else "pve_energy_delta"
    return abs(move.get(key) or 0)


def _move_duration(move: dict, is_fast: bool) -> float:
    default = 1000 if is_fast else 2000
    return (move.get("duration_ms") or default) / 1000.0


def _charged_cycle_dps(fast: dict, charged: dict, pokemon: dict, def_type1, def_type2, def_defense, is_pvp, neutral_target, defender_is_shadow: bool = False) -> float:
    f_power = _move_power(fast, is_pvp)
    c_power = _move_power(charged, is_pvp)
    if f_power is None or c_power is None:
        return 0.0

    f_dur = _move_duration(fast, is_fast=True)
    c_dur = _move_duration(charged, is_fast=False)
    f_energy = _move_energy(fast, is_pvp)
    c_energy = _move_energy(charged, is_pvp)
    is_shadow = bool(pokemon.get("is_shadow"))

    fast_dmg = calculate_move_damage(
        pokemon, fast["type"], f_power, def_type1, def_type2, def_defense, neutral_target,
        attacker_is_shadow=is_shadow, defender_is_shadow=defender_is_shadow,
    )
    fast_dps = fast_dmg / f_dur if f_dur > 0 else 0.0

    c_dmg = calculate_move_damage(
        pokemon, charged["type"], c_power, def_type1, def_type2, def_defense, neutral_target,
        attacker_is_shadow=is_shadow, defender_is_shadow=defender_is_shadow,
    )
    fasts_needed = math.ceil(c_energy / f_energy) if f_energy > 0 else 0
    total_cycle_time = c_dur + (fasts_needed * f_dur)
    total_cycle_damage = c_dmg + (fasts_needed * fast_dmg)

    return total_cycle_damage / total_cycle_time if total_cycle_time > 0 else 0.0


def _compute_moveset_dps(
    fast: dict | None,
    c1: dict | None,
    c2: dict | None,
    pokemon: dict,
    def_type1: str | None,
    def_type2: str | None,
    def_defense: float,
    is_pvp: bool,
    neutral_target: bool,
    defender_is_shadow: bool = False,
) -> tuple[float, float, float]:
    """Returns (fast_edps, c1_edps, c2_edps)."""
    if not fast:
        return 0.0, 0.0, 0.0

    f_power = _move_power(fast, is_pvp)
    if f_power is None:
        return 0.0, 0.0, 0.0

    f_dur = _move_duration(fast, is_fast=True)
    is_shadow = bool(pokemon.get("is_shadow"))
    fast_dmg = calculate_move_damage(
        pokemon, fast["type"], f_power, def_type1, def_type2, def_defense, neutral_target,
        attacker_is_shadow=is_shadow, defender_is_shadow=defender_is_shadow,
    )
    fast_edps = fast_dmg / f_dur if f_dur > 0 else 0.0

    c1_edps = _charged_cycle_dps(fast, c1, pokemon, def_type1, def_type2, def_defense, is_pvp, neutral_target, defender_is_shadow) if c1 else 0.0
    c2_edps = _charged_cycle_dps(fast, c2, pokemon, def_type1, def_type2, def_defense, is_pvp, neutral_target, defender_is_shadow) if c2 else 0.0

    return round(fast_edps, 1), round(c1_edps, 1), round(c2_edps, 1)


def score_moveset(
    fast: dict | None,
    charged_moves: list[dict],
    pokemon: dict,
    def_type1: str | None,
    def_type2: str | None,
    def_defense: float,
    is_pvp: bool,
    neutral_target: bool = False,
    defender_is_shadow: bool = False,
) -> tuple[float, float]:
    """Returns (total_score, best_charge_dps). charged_moves is 0-2 entries."""
    if not fast:
        return 0.0, 0.0

    f_power = _move_power(fast, is_pvp)
    if f_power is None:
        return 0.0, 0.0

    f_dur = _move_duration(fast, is_fast=True)
    is_shadow = bool(pokemon.get("is_shadow"))
    fast_dmg = calculate_move_damage(
        pokemon, fast["type"], f_power, def_type1, def_type2, def_defense, neutral_target,
        attacker_is_shadow=is_shadow, defender_is_shadow=defender_is_shadow,
    )
    fast_dps = fast_dmg / f_dur if f_dur > 0 else 0.0

    charge_dps_values = [
        _charged_cycle_dps(fast, charged, pokemon, def_type1, def_type2, def_defense, is_pvp, neutral_target, defender_is_shadow)
        for charged in charged_moves
    ]
    best_charge_dps = max(charge_dps_values) if charge_dps_values else 0.0
    total_score = fast_dps + (1.5 * best_charge_dps)
    return total_score, best_charge_dps


def _format_move_edps(move: dict | None, edps: float) -> str:
    if not move:
        return "None"
    return f"{move['name']} ({edps} eDPS)"


def _current_moves(pokemon: dict) -> tuple[dict | None, list[dict]]:
    fast = None
    if pokemon.get("cur_fast_id"):
        fast = {
            "id": pokemon["cur_fast_id"],
            "name": pokemon["cur_fast_name"],
            "type": pokemon["cur_fast_type"],
            "pve_power": pokemon["cur_fast_pve_power"],
            "pvp_power": pokemon["cur_fast_pvp_power"],
            "pve_energy_delta": pokemon["cur_fast_pve_energy"],
            "pvp_energy_delta": pokemon["cur_fast_pvp_energy"],
            "duration_ms": pokemon["cur_fast_duration"],
        }

    charges = []
    for key in ("c1", "c2"):
        move_id = pokemon.get(f"cur_{key}_id")
        if move_id:
            charges.append({
                "id": move_id,
                "name": pokemon[f"cur_{key}_name"],
                "type": pokemon[f"cur_{key}_type"],
                "pve_power": pokemon[f"cur_{key}_pve_power"],
                "pvp_power": pokemon[f"cur_{key}_pvp_power"],
                "pve_energy_delta": pokemon[f"cur_{key}_pve_energy"],
                "pvp_energy_delta": pokemon[f"cur_{key}_pvp_energy"],
                "duration_ms": pokemon[f"cur_{key}_duration"],
            })

    return fast, charges


def _find_best_moveset(
    legal_moves: list[dict],
    pokemon: dict,
    def_type1: str | None,
    def_type2: str | None,
    def_defense: float,
    is_pvp: bool,
    neutral_target: bool,
    require_move_type: str | None = None,
) -> tuple[float, dict | None, dict | None, dict | None]:
    """Returns (score, best_fast, best_c1, best_c2)."""
    fast_moves = [m for m in legal_moves if m["is_fast_move"]]
    charged_moves = [m for m in legal_moves if not m["is_fast_move"]]

    if require_move_type:
        type_upper = require_move_type.upper()
        typed_charges = [m for m in charged_moves if m["type"] == type_upper]
        if not typed_charges:
            return 0.0, None, None, None
        charged_pool = typed_charges
    else:
        charged_pool = charged_moves

    if not fast_moves or not charged_pool:
        return 0.0, None, None, None

    best_score = 0.0
    best_fast = None
    best_c1 = None
    best_c2 = None

    charge_pairs = [(c,) for c in charged_pool]
    charge_pairs += [(c1, c2) for c1 in charged_pool for c2 in charged_pool if c1["id"] != c2["id"]]

    for fast in fast_moves:
        for pair in charge_pairs:
            c1 = pair[0]
            c2 = pair[1] if len(pair) > 1 else None
            charges = [c1] if c2 is None else [c1, c2]
            score, _ = score_moveset(fast, charges, pokemon, def_type1, def_type2, def_defense, is_pvp, neutral_target)
            if score > best_score:
                best_score = score
                best_fast = fast
                best_c1 = c1
                best_c2 = c2

    return best_score, best_fast, best_c1, best_c2


def _evaluate_pokemon(
    pokemon: dict,
    legal_moves: list[dict],
    use_best_moves: bool,
    def_type1: str | None,
    def_type2: str | None,
    def_defense: float,
    is_pvp: bool,
    neutral_target: bool,
    require_move_type: str | None = None,
) -> dict | None:
    if use_best_moves:
        score, fast, c1, c2 = _find_best_moveset(
            legal_moves, pokemon, def_type1, def_type2, def_defense, is_pvp, neutral_target, require_move_type
        )
        if score <= 0:
            return None
    else:
        fast, charges = _current_moves(pokemon)
        if require_move_type:
            type_upper = require_move_type.upper()
            if not any(m["type"] == type_upper for m in ([fast] if fast else []) + charges):
                return None
        score, _ = score_moveset(fast, charges, pokemon, def_type1, def_type2, def_defense, is_pvp, neutral_target)
        if score <= 0:
            return None
        c1 = charges[0] if len(charges) > 0 else None
        c2 = charges[1] if len(charges) > 1 else None

    fast_edps, c1_edps, c2_edps = _compute_moveset_dps(
        fast, c1, c2, pokemon, def_type1, def_type2, def_defense, is_pvp, neutral_target
    )

    base_name = pokemon["nickname"] or pokemon["species_name"]
    mega_form = pokemon.get("mega_form")
    if mega_form:
        display_name = f"{base_name} ({format_mega_label(mega_form)})"
    else:
        display_name = base_name

    return {
        "inv_id": pokemon["inv_id"],
        "name": display_name,
        "cp": pokemon["cp"],
        "score": round(score, 2),
        "fast_move": _format_move_edps(fast, fast_edps),
        "charge_1": _format_move_edps(c1, c1_edps),
        "charge_2": _format_move_edps(c2, c2_edps),
    }


def _prompt_type(label: str) -> str | None:
    print(f"\nSelect {label}:")
    for idx, ptype in enumerate(POKEMON_TYPES, start=1):
        print(f"  {idx}. {ptype.title()}")

    while True:
        choice = input(f"Choice (1-{len(POKEMON_TYPES)}): ").strip()
        if choice.isdigit():
            num = int(choice)
            if 1 <= num <= len(POKEMON_TYPES):
                return POKEMON_TYPES[num - 1]
        print("Invalid selection. Choose a number from the list.")


def _prompt_battle_mode() -> bool:
    print("\nSelect Battle Mode:")
    print("1. PvE (Raids & Gyms)")
    print("2. PvP (Trainer Battles & GO Battle League)")
    while True:
        choice = input("Choice (1/2): ").strip()
        if choice == "1":
            return False
        if choice == "2":
            return True
        print("Invalid choice. Enter 1 for PvE or 2 for PvP.")


def _prompt_move_mode() -> bool:
    print("\nMove Selection:")
    print("1. Use current moves")
    print("2. Use best possible move combination")
    while True:
        choice = input("Choice (1/2): ").strip()
        if choice == "1":
            return False
        if choice == "2":
            return True
        print("Invalid choice. Enter 1 or 2.")


def _display_rankings(title: str, rankings: list[dict], mode_label: str, move_mode_label: str):
    if not rankings:
        print("\nNo matching Pokémon found in your inventory.")
        return

    print(f"\n{'=' * 177}")
    print(f" {title}")
    print(f" Battle mode: {mode_label} | Move mode: {move_mode_label}")
    print(f"{'=' * 177}")
    print(
        f"{'RANK':<5} | {'INV':<5} | {'NAME':<15} | {'CP':<6} | {'SCORE':<8} | "
        f"{'FAST MOVE':<35} | {'CHARGE 1':<35} | {'CHARGE 2':<35}"
    )
    print("-" * 177)

    for rank, entry in enumerate(rankings, start=1):
        print(
            f"{rank:<5} | {entry['inv_id']:<5} | {entry['name']:<15} | {entry['cp']:<6} | "
            f"{entry['score']:<8} | {entry['fast_move']:<35} | {entry['charge_1']:<35} | {entry['charge_2']:<35}"
        )


def _rank_inventory(
    cursor,
    inventory: list[dict],
    include_mega: bool,
    use_best_moves: bool,
    def_type1: str | None,
    def_type2: str | None,
    def_defense: float,
    is_pvp: bool,
    neutral_target: bool,
    require_move_type: str | None = None,
) -> list[dict]:
    mega_cache: dict[int, list[dict]] = {}
    rankings = []

    for pokemon in inventory:
        species_id = pokemon["species_id"]
        if species_id not in mega_cache:
            cursor.execute(MEGA_FORMS_QUERY, (species_id,))
            mega_cache[species_id] = cursor.fetchall()

        cursor.execute(LEGAL_MOVES_QUERY, (pokemon["species_id"], pokemon["form"]))
        legal_moves = cursor.fetchall()

        for variant in expand_pokemon_variants(pokemon, mega_cache[species_id], include_mega):
            result = _evaluate_pokemon(
                variant,
                legal_moves,
                use_best_moves,
                def_type1=def_type1,
                def_type2=def_type2,
                def_defense=def_defense,
                is_pvp=is_pvp,
                neutral_target=neutral_target,
                require_move_type=require_move_type,
            )
            if result:
                rankings.append(result)

    rankings.sort(key=lambda x: x["score"], reverse=True)
    return rankings


def rank_type_attackers(user_id: int, attack_type: str, use_best_moves: bool, is_pvp: bool, include_mega: bool = False):
    """Rank inventory Pokémon by best output for a chosen attacking move type (neutral target)."""
    move_mode_label = "Best possible moves" if use_best_moves else "Current moves"
    mode_label = "PvP" if is_pvp else "PvE"

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(INVENTORY_QUERY, (user_id,))
                inventory = cursor.fetchall()
                if not inventory:
                    print("\nYou don't have any Pokémon in your inventory.")
                    return

                rankings = _rank_inventory(
                    cursor,
                    inventory,
                    include_mega,
                    use_best_moves,
                    def_type1=None,
                    def_type2=None,
                    def_defense=REFERENCE_DEFENSE,
                    is_pvp=is_pvp,
                    neutral_target=True,
                    require_move_type=attack_type,
                )
                title = f"BEST {attack_type} ATTACKERS"
                _display_rankings(title, rankings, mode_label, move_mode_label)

    except Exception as e:
        print(f"Error ranking type attackers: {e}")


def rank_type_counters(user_id: int, defender_type: str, use_best_moves: bool, is_pvp: bool, include_mega: bool = False):
    """Rank inventory Pokémon that best counter a chosen defending type."""
    move_mode_label = "Best possible moves" if use_best_moves else "Current moves"
    mode_label = "PvP" if is_pvp else "PvE"

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(INVENTORY_QUERY, (user_id,))
                inventory = cursor.fetchall()
                if not inventory:
                    print("\nYou don't have any Pokémon in your inventory.")
                    return

                rankings = _rank_inventory(
                    cursor,
                    inventory,
                    include_mega,
                    use_best_moves,
                    def_type1=defender_type,
                    def_type2=None,
                    def_defense=REFERENCE_DEFENSE,
                    is_pvp=is_pvp,
                    neutral_target=False,
                    require_move_type=None,
                )
                title = f"BEST COUNTERS VS {defender_type} TYPE"
                _display_rankings(title, rankings, mode_label, move_mode_label)

    except Exception as e:
        print(f"Error ranking type counters: {e}")


def run_type_rankings(user_id: int):
    print("\n--- TYPE RANKINGS ---")
    print("1. Type Attacker Rankings (best users of a move type)")
    print("2. Type Counter Rankings (best counters vs a defending type)")
    print("3. Back")

    while True:
        choice = input("Choice (1-3): ").strip()
        if choice == "3":
            return
        if choice not in ("1", "2"):
            print("Invalid choice. Enter 1, 2, or 3.")
            continue

        is_pvp = _prompt_battle_mode()
        use_best_moves = _prompt_move_mode()
        include_mega = prompt_include_mega()

        if choice == "1":
            attack_type = _prompt_type("Attacking Move Type")
            rank_type_attackers(user_id, attack_type, use_best_moves, is_pvp, include_mega)
        else:
            defender_type = _prompt_type("Defending Pokémon Type")
            rank_type_counters(user_id, defender_type, use_best_moves, is_pvp, include_mega)
        return
