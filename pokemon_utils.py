import math

from constants import CPM_TABLE
from db import get_db_connection

SHADOW_ATTACK_MULTIPLIER = 1.2
SHADOW_DEFENSE_MULTIPLIER = 1.2


def calculate_move_damage(
    pokemon: dict,
    move_type: str,
    move_power: float,
    def_type1: str | None,
    def_type2: str | None,
    def_defense: float,
    neutral_target: bool = False,
    attacker_is_shadow: bool = False,
    defender_is_shadow: bool = False,
) -> float:
    if not move_type or move_power is None or move_power <= 0:
        return 0.0

    from battle import get_type_effectiveness

    if neutral_target:
        effectiveness = 1.0
    else:
        effectiveness = get_type_effectiveness(move_type, def_type1, def_type2)

    stab = 1.2 if move_type in (pokemon["type_1"], pokemon["type_2"]) else 1.0

    nomi = pokemon["cp"] * 10
    denomi = (
        (pokemon["base_attack"] + pokemon["atk_iv"])
        * math.sqrt(pokemon["base_defense"] + pokemon["def_iv"])
        * math.sqrt(pokemon["base_stamina"] + pokemon["sta_iv"])
    )
    cpm = math.sqrt(nomi / denomi)

    total_attack = (pokemon["base_attack"] + pokemon["atk_iv"]) * cpm
    total_defense = float(def_defense) * 0.79

    damage = math.floor(0.5 * move_power * (total_attack / total_defense) * stab * effectiveness) + 1

    if attacker_is_shadow:
        damage = math.floor(damage * SHADOW_ATTACK_MULTIPLIER)
    if defender_is_shadow:
        damage = math.floor(damage * SHADOW_DEFENSE_MULTIPLIER)

    return damage


def calculate_level_from_cp(cp, base_attack, base_defense, base_stamina, atk_iv, def_iv, sta_iv):
    level = 1.0
    for lvl, cpm in CPM_TABLE.items():
        calculated_cp = math.floor(
            0.1 * (base_attack + atk_iv) * math.sqrt(base_defense + def_iv) * math.sqrt(base_stamina + sta_iv) * (cpm ** 2)
        )
        calculated_cp = max(10, calculated_cp)
        
        if calculated_cp == cp:
            level = lvl
            break
    return level


def calculate_cp_from_level(level, base_attack, base_defense, base_stamina, atk_iv, def_iv, sta_iv):
    cpm = CPM_TABLE.get(level)
    if cpm is None:
        cpm = CPM_TABLE[1.0]
    cp = math.floor(
        0.1 * (base_attack + atk_iv) * math.sqrt(base_defense + def_iv) * math.sqrt(base_stamina + sta_iv) * (cpm ** 2)
    )
    return max(10, cp)



def format_mega_label(mega_form: str) -> str:
    if mega_form == "MEGA":
        return "Mega"
    if mega_form.startswith("MEGA_"):
        return "Mega " + mega_form.replace("MEGA_", "").replace("_", " ")
    if mega_form == "PRIMAL":
        return "Primal"
    return mega_form


def build_mega_variant(pokemon: dict, mega_species: dict) -> dict:
    variant = dict(pokemon)
    variant["base_attack"] = mega_species["base_attack"]
    variant["base_defense"] = mega_species["base_defense"]
    variant["base_stamina"] = mega_species["base_stamina"]
    variant["type_1"] = mega_species["type_1"]
    variant["type_2"] = mega_species["type_2"]
    variant["form"] = mega_species["form"]
    level = pokemon.get("level")
    if level is not None:
        variant["cp"] = calculate_cp_from_level(
            level,
            mega_species["base_attack"],
            mega_species["base_defense"],
            mega_species["base_stamina"],
            pokemon["atk_iv"],
            pokemon["def_iv"],
            pokemon["sta_iv"],
        )
    return variant


def expand_pokemon_variants(pokemon: dict, mega_forms: list[dict], include_mega: bool) -> list[dict]:
    variants = [pokemon]
    if include_mega:
        for mega_species in mega_forms:
            variants.append(build_mega_variant(pokemon, mega_species))
    return variants


def get_mega_stats(pokedex_id: int) -> list[dict]:
    MEGA_FORMS_QUERY = """
        SELECT form, type_1, type_2, base_attack, base_defense, base_stamina
        FROM species
        WHERE id = %s AND (form LIKE 'MEGA%%' OR form = 'PRIMAL')
        ORDER BY form ASC;
    """
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(MEGA_FORMS_QUERY, (pokedex_id,))
            return cursor.fetchall()


def get_all_species():
    ALL_SPECIES_QUERY = """
        SELECT 
            s.id,
            s.name,
            s.form,
            s.base_attack,
            s.base_defense,
            s.base_stamina,
            s.type_1,
            s.type_2
        FROM species s
        ORDER BY s.id ASC
    """
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(ALL_SPECIES_QUERY)
            return cursor.fetchall()

def get_form_name_img(raw_form):
    if "MEGA_X" in raw_form:
        form = "-Mega-X"
    elif "MEGA_Y" in raw_form:
        form = "-Mega-Y"
    elif "CROWNED" in raw_form:
        form = "-Crowned"
    elif "DAWN" in raw_form:
        form = "-Dawn"
    elif "DUSK" in raw_form:
        form = "-Dusk"
    elif "ULTRA" in raw_form:
        form = "-Ultra"
    elif "GALARIAN_STANDARD" in raw_form:
        form = "-Galar-Standard"
    elif "GALARIAN_ZEN" in raw_form:
        form = "-Galar-Zen"
    elif "GALAR" in raw_form:
        form = "-Galar"
    elif "HISUI" in raw_form:
        form = "-Hisui"
    elif "PALDEA_AQUA" in raw_form:
        form = "-Paldea-Aqua-Breed"
    elif "PALDEA_BLAZE" in raw_form:
        form = "-Paldea-Blaze-Breed"
    elif "PALDEA_COMBAT" in raw_form:
        form = "-Paldea-Combat-Breed"
    elif "ORIGIN" in raw_form:
        form = "-Origin"
    elif "ALTERED" in raw_form:
        form = ""
    elif "ICE_RIDER" in raw_form:
        form = "-Ice"
    elif "SHADOW_RIDER" in raw_form:
        form = "-Shadow"
    elif "BLACK" in raw_form:
        form = "-Black"
    elif "WHITE" in raw_form:
        form = "-White"
    elif "CONFINED" in raw_form:
        form = ""
    elif "UNBOUND" in raw_form:
        form = "Unbound"
    elif "RAPID_STRIKE" in raw_form:
        form = "-Rapid-Strike"
    elif "SINGLE_STRIKE" in raw_form:
        form = ""
    elif "ETERNAMAX" in raw_form:
        form = "-Eternamax"
    elif "TEN_PERCENT" in raw_form:
        form = "-10"
    elif "FIFTY_PERCENT" in raw_form:
        form = ""
    elif "COMPLETE" in raw_form:
        form = "-Complete"
    elif "APEX" in raw_form:
        form = ""
    elif "ULTIMATE" in raw_form:
        form = ""
    elif "POMPOM" in raw_form:
        form = "-Pom-Pom"
    elif "INCARNATE" in raw_form:
        form = ""
    elif "THERIAN" in raw_form:
        form = "-Therian"
    elif raw_form != "NORMAL":
        form = '-' + raw_form.capitalize()
    else:
        form = ""
    return form
