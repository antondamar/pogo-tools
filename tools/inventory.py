from tools.db import get_db_connection

def get_pokemon_storage(user_id: int) -> list[dict]:
    STORAGE_QUERY = """
        SELECT 
            up.id AS inv_id,
            up.species_id,
            up.species_form AS form,
            up.nickname,
            up.cp,
            up.level,
            up.atk_iv,
            up.def_iv,
            up.sta_iv,
            up.is_shiny,
            up.is_shadow,
            up.is_mega_1,
            up.is_mega_2,
            s.type_1,
            s.type_2,
            s.name AS species_name,
            s.base_attack,
            s.base_defense,
            s.base_stamina,
            
            mf.id AS fast_id, mf.name AS fast_name, mf.type AS fast_type, 
            mf.pve_power AS fast_pve_power, mf.pvp_power AS fast_pvp_power,
            mf.pve_energy_delta AS fast_pve_energy, mf.pvp_energy_delta AS fast_pvp_energy,
            mf.duration_ms AS fast_duration,

            mc1.id AS c1_id, mc1.name AS c1_name, mc1.type AS c1_type, 
            mc1.pve_power AS c1_pve_power, mc1.pvp_power AS c1_pvp_power,
            mc1.pve_energy_delta AS c1_pve_energy, mc1.pvp_energy_delta AS c1_pvp_energy,
            mc1.duration_ms AS c1_duration,

            mc2.id AS c2_id, mc2.name AS c2_name, mc2.type AS c2_type, 
            mc2.pve_power AS c2_pve_power, mc2.pvp_power AS c2_pvp_power,
            mc2.pve_energy_delta AS c2_pve_energy, mc2.pvp_energy_delta AS c2_pvp_energy,
            mc2.duration_ms AS c2_duration

        FROM user_pokemon up
        JOIN species s ON up.species_id = s.id AND up.species_form = s.form
        LEFT JOIN moves mf ON up.fast_move_id = mf.id
        LEFT JOIN moves mc1 ON up.charged_move_1_id = mc1.id
        LEFT JOIN moves mc2 ON up.charged_move_2_id = mc2.id
        WHERE up.user_id = %s
        ORDER BY up.id ASC;
    """
    
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(STORAGE_QUERY, (user_id,))
            return cursor.fetchall()


def delete_pokemon(user_id, inv_id):
    DELETE_UPLOAD = """
        DELETE FROM user_pokemon 
        WHERE id = %s AND user_id = %s 
    """

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(DELETE_UPLOAD, (inv_id, user_id))
            conn.commit()


def select_move(poke_id, poke_form):
    MOVES_QUERY = """
        SELECT 
            m.id, 
            m.name, 
            m.is_fast_move, 
            sm.is_elite_move
        FROM moves m
        JOIN species_moves sm ON m.id = sm.move_id
        WHERE sm.species_id = %s AND sm.species_form = %s
        ORDER BY m.is_fast_move ASC, m.name ASC;
    """

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(MOVES_QUERY, (poke_id, poke_form))
            return cursor.fetchall()


def upload_add_new_pokemon(p):
    NEW_POKEMON_UPLOAD = """
        INSERT INTO user_pokemon 
        (user_id, species_id, species_form, nickname, cp, level, atk_iv, def_iv, sta_iv, is_shiny, is_shadow, fast_move_id, charged_move_1_id, charged_move_2_id, is_mega_1, is_mega_2)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
    """

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(NEW_POKEMON_UPLOAD, (
                p["user_id"], p["species_id"], p["form"], p["nickname"],
                p["cp"], p["level"], p["atk_iv"], p["def_iv"], p["sta_iv"], p["shiny"],
                p["shadow"], p["fm_id"], p["cm1_id"], p["cm2_id"], p["mega_1"], p["mega_2"]
            ))
            conn.commit()

def upload_update_existing_pokemon(p):
    EXISTING_POKEMON_UPLOAD = """
        UPDATE user_pokemon SET cp = %s, level = %s, nickname = %s, is_shadow = %s, atk_iv = %s, def_iv = %s, sta_iv = %s,
        is_mega_1 = %s, is_mega_2 = %s, fast_move_id = %s, charged_move_1_id = %s, charged_move_2_id = %s
        WHERE id = %s;
    """

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(EXISTING_POKEMON_UPLOAD, (
                p["cp"], p["level"], p["nickname"], p["shadow"], p["atk_iv"], p["def_iv"], p["sta_iv"],
                p["mega_1"], p["mega_2"], p["fm_id"], p["cm1_id"], p["cm2_id"], p["inv_id"]
            ))
            conn.commit()

def get_mega_types(poke_id, poke_form):
    MEGA_TYPES_QUERY = """
        SELECT 
            s.type_1,
            s.type_2
        FROM species s
        WHERE s.id = %s AND s.form = %s
    """
    
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(MEGA_TYPES_QUERY, (poke_id, poke_form))
            return cursor.fetchone()
            