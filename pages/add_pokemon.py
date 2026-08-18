import streamlit as st
from pathlib import Path

from tools.inventory import delete_pokemon, select_move, upload_add_new_pokemon, upload_update_existing_pokemon
from tools.pokemon_utils import calculate_level_from_cp, get_all_species, get_form_name_img
from tools.constants import mega_pokedex_ids, mega_xy_pokedex_ids, primal_pokedex_ids

import base64

def format_pokemon(p):
    form = " ".join(p['form'].split('_'))
    form = form if form != "NORMAL" else ""
    return f"{p['id']:04d} - {p['name']} {form}"


def format_moves(m):
    elite_move_label = " (Elite TM)" if m["is_elite_move"] else ""
    name = m["name"].replace('_', ' ').title()
    return f"{name}{elite_move_label}"


def move_index(moves: list[dict], move_id: int | None) -> int | None:
    if move_id is None:
        return None
    for i, m in enumerate(moves):
        if m["id"] == move_id:
            return i
    return None


def close_add_pokemon_dialog() -> None:
    st.session_state["show_add_pokemon_dialog"] = False


def close_update_pokemon_dialog() -> None:
    st.session_state["show_update_pokemon_dialog"] = False
    st.session_state.pop("update_pokemon_inv_id", None)


def close_delete_pokemon_dialog() -> None:
    st.session_state["show_delete_pokemon_dialog"] = False
    st.session_state.pop("delete_pokemon_inv_id", None)


def selectbox_pokemon(prompt, include_mega):
    if include_mega:
        species = [s for s in get_all_species()]
    else:
        species = [
            s for s in get_all_species()
            if "PRIMAL" not in (s["form"] or "") and "MEGA" not in (s["form"] or "")
        ]
    selected_poke = st.selectbox(
        prompt,
        options=species,
        index=None,
        format_func=format_pokemon,
        filter_mode="contains"
    )
    return selected_poke


def insert_pokemon_data(selected_poke, is_adding):
    species_id = selected_poke["id"] if is_adding else selected_poke["species_id"]
    species_form = selected_poke["form"] if is_adding else selected_poke["form"]

    form = get_form_name_img(species_form)
    poke_img_filename = f"{species_id:04d}{form}.png"
    poke_img_filepath = Path(__file__).parent.parent / "assets" / "images" / poke_img_filename

    moves = select_move(species_id, species_form)
    fm = [
        m for m in moves
        if m["is_fast_move"]
    ]
    cm = [
        m for m in moves
        if not m["is_fast_move"]
    ]

    form_key = (
        f"add_pokemon_{species_id}_{species_form}"
        if is_adding
        else f"update_pokemon_{selected_poke['inv_id']}"
    )
    with st.form(form_key):
        with open(poke_img_filepath, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()

        st.markdown(
            f'<div style="text-align: center; padding-bottom: 16px;"><img src="data:image/png;base64,{b64}" width="200"></div>',
            unsafe_allow_html=True,
        )
        p = {
            "user_id": st.session_state["user"]["id"], "species_id": species_id, "form": species_form,
            "fm_id": None, "cm1_id": None, "cm2_id": None, "mega_1": False, "mega_2": False
        }
        default_nickname = selected_poke["name"].replace('_', ' ').title() if is_adding else selected_poke["nickname"]
        p["nickname"] = st.text_input("Nickname", value=default_nickname)
        default_cp = selected_poke["cp"] if not is_adding else None
        p["cp"] = st.number_input("Combat Power (CP)*", min_value=10, max_value=6000, step=1, format="%d", value=default_cp)
        with st.container(horizontal=True):
            default_atk_iv = selected_poke["atk_iv"] if not is_adding else None
            p["atk_iv"] = st.number_input("Attack IV*", min_value=0, max_value=15, step=1, format="%d", value=default_atk_iv)
            default_def_iv = selected_poke["def_iv"] if not is_adding else None
            p["def_iv"] = st.number_input("Defense IV*", min_value=0, max_value=15, step=1, format="%d", value=default_def_iv)
            default_sta_iv = selected_poke["sta_iv"] if not is_adding else None
            p["sta_iv"] = st.number_input("Stamina IV*", min_value=0, max_value=15, step=1, format="%d", value=default_sta_iv)
        if None not in [p["cp"], p["atk_iv"], p["def_iv"], p["sta_iv"]]:
            p["level"] = calculate_level_from_cp(
                p["cp"], selected_poke["base_attack"], selected_poke["base_defense"], selected_poke["base_stamina"],
                p["atk_iv"], p["def_iv"], p["sta_iv"],
            )
        if species_id in mega_xy_pokedex_ids:
            with st.container(horizontal=True):
                default_mega_1 = selected_poke["is_mega_1"] if not is_adding else False
                p["mega_1"] = st.checkbox("Mega Evolution X unlocked", value=default_mega_1)
                default_mega_2 = selected_poke["is_mega_2"] if not is_adding else False
                p["mega_2"] = st.checkbox("Mega Evolution Y unlocked", value=default_mega_2)
        elif species_id in mega_pokedex_ids:
            default_mega_1 = selected_poke["is_mega_1"] if not is_adding else False
            p["mega_1"] = st.checkbox("Mega Evolution unlocked", value=default_mega_1)
        elif species_id in primal_pokedex_ids:
            default_mega_1 = selected_poke["is_mega_1"] if not is_adding else False
            p["mega_1"] = st.checkbox("Primal Evolution unlocked", value=default_mega_1)
        default_shadow = selected_poke["is_shadow"] if not is_adding else False
        p["shadow"] = st.checkbox("Shadow", value=default_shadow)
        default_shiny = selected_poke["is_shiny"] if not is_adding else False
        p["shiny"] = st.checkbox("Shiny", value=default_shiny)
        fm = st.selectbox(
            "Enter or select fast move*",
            options=fm,
            index=None if is_adding else move_index(fm, selected_poke["fast_id"]),
            format_func=format_moves,
            filter_mode="contains",
        )
        cm1 = st.selectbox(
            "Enter or select charged move 1*",
            options=cm,
            index=None if is_adding else move_index(cm, selected_poke["c1_id"]),
            format_func=format_moves,
            filter_mode="contains"
        )
        cm2 = st.selectbox(
            "Enter or select charged move 2",
            options=cm,
            index=None if is_adding else move_index(cm, selected_poke["c2_id"]),
            format_func=format_moves,
            filter_mode="contains"
        )

        with st.container(horizontal=True, horizontal_alignment="center"):
            add_btn = st.form_submit_button("Add", type="primary") if is_adding else st.form_submit_button("Update", type="primary")

        if add_btn:
            if None in (p["cp"], p["atk_iv"], p["def_iv"], p["sta_iv"]) or not fm or not cm1:
                st.warning("All * fields are required.")
            elif cm1 and cm2 and cm1["id"] == cm2["id"]:
                st.warning("Charged move 1 and 2 cannot be equal.")
            else:
                p["level"] = calculate_level_from_cp(
                    p["cp"], selected_poke["base_attack"], selected_poke["base_defense"], selected_poke["base_stamina"],
                    p["atk_iv"], p["def_iv"], p["sta_iv"],
                )
                p["fm_id"] = fm["id"]
                p["cm1_id"] = cm1["id"]
                p["cm2_id"] = cm2["id"] if cm2 else None
                if is_adding:
                    upload_add_new_pokemon(p)
                    st.session_state["add_pokemon_success"] = p["nickname"]
                    close_add_pokemon_dialog()
                else:
                    p["inv_id"] = selected_poke["inv_id"]
                    upload_update_existing_pokemon(p)
                    st.session_state["update_pokemon_success"] = p["nickname"]
                    close_update_pokemon_dialog()
                st.rerun()


@st.dialog("Add New Pokémon", on_dismiss=close_add_pokemon_dialog)
def render_add_new_pokemon():
    selected_poke = selectbox_pokemon("Enter Pokédex # or Pokémon name", include_mega=False)
    
    if selected_poke:
        insert_pokemon_data(selected_poke, True)


@st.dialog("Update Pokémon", on_dismiss=close_update_pokemon_dialog)
def render_update_existing_pokemon(p):
    insert_pokemon_data(p, False)


@st.dialog("Delete Pokémon", on_dismiss=close_delete_pokemon_dialog)
def render_delete_existing_pokemon(user_id, inv_id, poke_nickname):
    st.write(f"Transfer **{poke_nickname}** to the Professor? This cannot be undone.")
    with st.container(horizontal=True, horizontal_alignment="center"):
        cancel_btn = st.button("Cancel")
        confirm_btn = st.button("Delete", type="primary")

    if cancel_btn:
        close_delete_pokemon_dialog()
        st.session_state["show_pokemon_details_dialog"] = True
        st.session_state["pokemon_details_id"] = inv_id
        st.rerun()

    if confirm_btn:
        delete_pokemon(user_id, inv_id)
        st.session_state["delete_pokemon_success"] = poke_nickname
        close_delete_pokemon_dialog()
        st.rerun()