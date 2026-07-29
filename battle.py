import math
from db import get_db_connection
from constants import TYPE_CHART
from pokemon_utils import (
    calculate_move_damage,
    expand_pokemon_variants,
    format_mega_label
)

# Super Effective = 1.6
# Neutral = 1.0
# Not Very Effective = 0.625
# Double Resistance = 0.390625

def get_type_effectiveness(attack_type: str, defender_type1: str, defender_type2: str = None) -> float:
    if not attack_type:
        return 1.0

    attack_type = attack_type.upper()
    mult1 = TYPE_CHART.get(attack_type, {}).get(defender_type1.upper(), 1.0) if defender_type1 else 1.0
    mult2 = TYPE_CHART.get(attack_type, {}).get(defender_type2.upper(), 1.0) if defender_type2 else 1.0

    return mult1 * mult2

def _score_pokemon_variant(p: dict, def_type1: str, def_type2: str | None, def_defense: float, is_pvp: bool) -> dict:
    is_shadow = bool(p.get("is_shadow"))

    def calculate_damage(m_type, m_power, p_type1, p_type2):
        if not m_type or m_power is None or float(m_power) <= 0:
            return 0.0
        return calculate_move_damage(
            p, m_type, float(m_power), def_type1, def_type2, def_defense, attacker_is_shadow=is_shadow,
        )

    f_power = p["fast_pvp_power"] if is_pvp else p["fast_pve_power"]
    f_energy = abs(p["fast_pvp_energy"] or 0) if is_pvp else abs(p["fast_pve_energy"] or 0)
    f_dur = (p["fast_duration"] or 1000) / 1000.0

    fast_dmg = calculate_damage(p["fast_type"], f_power, p["type_1"], p["type_2"])
    fast_dps = fast_dmg / f_dur if f_dur > 0 else 0.0

    def score_charged_move(c_prefix):
        c_type = p[f"{c_prefix}_type"]
        c_power = p[f"{c_prefix}_pvp_power"] if is_pvp else p[f"{c_prefix}_pve_power"]
        c_energy = abs(p[f"{c_prefix}_pvp_energy"] or 0) if is_pvp else abs(p[f"{c_prefix}_pve_energy"] or 0)
        c_dur = (p[f"{c_prefix}_duration"] or 2000) / 1000.0

        if not c_type or c_power is None:
            return "None", 0.0

        c_dmg = calculate_damage(c_type, c_power, p["type_1"], p["type_2"])
        fasts_needed = math.ceil(c_energy / f_energy) if f_energy > 0 else 0
        total_cycle_time = c_dur + (fasts_needed * f_dur)
        total_cycle_damage = c_dmg + (fasts_needed * fast_dmg)
        effective_dps = total_cycle_damage / total_cycle_time if total_cycle_time > 0 else 0.0
        move_str = f"{c_dmg} dmg, {round(effective_dps, 1)} DPS"
        return move_str, effective_dps

    c1_str, c1_eff_dps = score_charged_move("c1")
    c2_str, c2_eff_dps = score_charged_move("c2")
    best_charge_dps = max(c1_eff_dps, c2_eff_dps)
    total_score = fast_dps + (1.5 * best_charge_dps)

    base_name = p["nickname"]
    species = (p["species_name"] + '_' + ("" if p["form"] == "NORMAL" else p["form"])).replace('_', ' ').title()
    shadow_tag = " (Shadow)" if is_shadow else ""
    mega_form = p.get("form")
    mega_tag = f" ({format_mega_label(mega_form)})" if mega_form else ""
    display_name = f"{base_name}{mega_tag}{shadow_tag}"
    eff_f = get_type_effectiveness(p["fast_type"], def_type1, def_type2)
    eff_c1 = get_type_effectiveness(p["c1_type"], def_type1, def_type2)
    eff_c2 = get_type_effectiveness(p["c2_type"], def_type1, def_type2) if p["c2_id"] is not None else None

    return {
        "inv_id": p["inv_id"],
        "nickname": display_name,
        "species": species,
        "cp": p["cp"],
        "fast_move": f"{fast_dmg} dmg, {round(fast_dps, 1)} DPS" if p["fast_name"] else "None",
        "charge_1": c1_str,
        "charge_2": c2_str,
        "best_charge": f"{round(best_charge_dps, 1)} DPS",
        "score": round(total_score, 2),
        "eff_f": eff_f,
        "eff_c1": eff_c1,
        "eff_c2": eff_c2,
        "pokemon": p
    }


def get_battle_recommendations(inventory, include_mega, is_pvp, def_species_id: int, def_form: str = "NORMAL"):
    """
    Fetches defender types, calculates offensive effectiveness score for each Pokémon 
    in user's inventory based on CP, Power, STAB, and Type Effectiveness.
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT name, type_1, type_2, base_defense FROM species WHERE id = %s AND form = %s;",
                    (def_species_id, def_form.upper())
                )
                defender = cursor.fetchone()
                def_name = defender['name']
                def_type1 = defender['type_1']
                def_type2 = defender['type_2']
                def_defense = defender['base_defense']

                MEGA_FORMS_QUERY = """
                    SELECT form, type_1, type_2, base_attack, base_defense, base_stamina
                    FROM species
                    WHERE id = %s AND (form LIKE 'MEGA%%' OR form = 'PRIMAL')
                    ORDER BY form ASC;
                """

                mega_cache: dict[int, list[dict]] = {}
                scored_pokemon = []

                for p in inventory:
                    species_id = p["species_id"]
                    if species_id not in mega_cache:
                        cursor.execute(MEGA_FORMS_QUERY, (species_id,))
                        mega_cache[species_id] = cursor.fetchall()

                    for variant in expand_pokemon_variants(p, mega_cache[species_id], include_mega):
                        scored_pokemon.append(_score_pokemon_variant(variant, def_type1, def_type2, def_defense, is_pvp))

                scored_pokemon.sort(key=lambda p: p['score'], reverse=True)

                return scored_pokemon

    except Exception as e:
        print(f"Error generating battle recommendation: {e}")

