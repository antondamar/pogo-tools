import math
from pathlib import Path
import streamlit as st
from datetime import datetime
import base64

from tools.battle import get_battle_recommendations
from tools.inventory import get_mega_types, get_pokemon_storage
from tools.pokemon_utils import calculate_cp_from_level, get_form_name_img, get_mega_stats
from tools.constants import mega_pokedex_ids, mega_xy_pokedex_ids, primal_pokedex_ids

from pages.add_pokemon import render_add_new_pokemon, render_delete_existing_pokemon, render_update_existing_pokemon, selectbox_pokemon


def iv_color(iv: int) -> str:
    if iv == 100:
        return "#FFB74D"
    if iv > 90:
        return "#BF00FF"
    if iv > 80:
        return "#0066FF"
    if iv > 60:
        return "#2AD117"
    return "#000000"


def get_display_cp(p, qry_prm=None):
    if not qry_prm:
        return p["cp"]

    inv_id, poke_mega, poke_level = qry_prm.split(":")
    if int(inv_id) != p["inv_id"]:
        return p["cp"]

    poke_mega = int(poke_mega)
    poke_level = float(poke_level)
    mega_types = get_mega_stats(p["species_id"])
    
    for mega_type in mega_types:
        if p["species_id"] in mega_xy_pokedex_ids and poke_mega == 1 and mega_type["form"] == "MEGA_X":
            return calculate_cp_from_level(poke_level, mega_type["base_attack"], mega_type["base_defense"], mega_type["base_stamina"], p["atk_iv"], p["def_iv"], p["sta_iv"])
        if p["species_id"] in mega_xy_pokedex_ids and poke_mega == 2 and mega_type["form"] == "MEGA_Y":
            return calculate_cp_from_level(poke_level, mega_type["base_attack"], mega_type["base_defense"], mega_type["base_stamina"], p["atk_iv"], p["def_iv"], p["sta_iv"])
        if poke_mega == 3 and (mega_type["form"] == "MEGA" or mega_type["form"] == "PRIMAL"):
            return calculate_cp_from_level(poke_level, mega_type["base_attack"], mega_type["base_defense"], mega_type["base_stamina"], p["atk_iv"], p["def_iv"], p["sta_iv"])

    return p["cp"]


def close_pokemon_details_dialog() -> None:
    st.session_state["show_pokemon_details_dialog"] = False
    st.session_state.pop("pokemon_details_id", None)


def get_pokemon_card_assets(p):
    form = get_form_name_img(p["form"])

    IVs = f"{p["atk_iv"]}/{p["def_iv"]}/{p["sta_iv"]}"

    poke_type1, poke_type_2 = p["type_1"], p["type_2"]
    poke_type1_filepath = Path(__file__).parent.parent / "assets" / "types" / f"{poke_type1}.png"
    poke_type2_filepath = (
        Path(__file__).parent.parent / "assets" / "types" / f"{poke_type_2}.png"
        if poke_type_2
        else None
    )

    qry_prm = st.query_params.get("mega")
    if qry_prm and int(qry_prm.split(":")[0]) == p["inv_id"]:
        poke_mega = int(qry_prm.split(":")[1])
        if p["species_id"] in mega_xy_pokedex_ids and poke_mega == 1:
            poke_img_filename = f"{p["species_id"]:04d}-Mega-X.png"
        elif p["species_id"] in mega_xy_pokedex_ids and poke_mega == 2:
            poke_img_filename = f"{p["species_id"]:04d}-Mega-Y.png"
        else:
            if p["species_id"] not in primal_pokedex_ids:
                poke_img_filename = f"{p["species_id"]:04d}-Mega.png"
            else:
                poke_img_filename = f"{p["species_id"]:04d}-Primal.png"
    else:
        poke_img_filename = f"{p['species_id']:04d}{form}.png"
    poke_img_filepath = Path(__file__).parent.parent / "assets" / "images" / poke_img_filename

    return {
        "form": form,
        "IVs": IVs,
        "poke_type_2": poke_type_2,
        "poke_img_filepath": poke_img_filepath,
        "poke_type1_filepath": poke_type1_filepath,
        "poke_type2_filepath": poke_type2_filepath,
    }


def b64_image(filepath, width):
    with open(filepath, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    st.markdown(
        f'<div style="text-align: center; padding-bottom: 16px;"><img src="data:image/png;base64,{b64}" width="{width}"></div>',
        unsafe_allow_html=True
    )


@st.dialog("Pokémon Details", on_dismiss=close_pokemon_details_dialog)
def show_pokemon_details(p, poke_img_filepath, IVs, poke_type1_filepath, poke_type2_filepath):
    qry_prm = st.query_params.get("mega", None)
    col1, col2 = st.columns(2)
    with col1: 
        if qry_prm and int(qry_prm.split(':')[0]) == p["inv_id"]:
            st.markdown(
                f"""
                <p style="text-align: center; color: #FF0000; font-weight: 500;">
                    CP {p["cp"]} ({IVs})
                </p>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(f"**CP {p["cp"]} ({IVs})**", text_alignment="center")
        IV_total = math.floor(((p["atk_iv"] + p["def_iv"] + p["sta_iv"]) / 45) * 100)
        st.markdown(
            f"""
            <div style="
                border: 1px solid rgba(49, 51, 63, 0.2);
                border-radius: 6px;
                padding: 2px 8px;
                text-align: center;
                width: fit-content;
                margin: 0 auto 8px auto;
                color: {iv_color(IV_total)};
                font-weight: 600;
            ">
                {IV_total}
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.image(poke_img_filepath)
        if poke_type2_filepath:
            col1_1, col1_2 = st.columns(2)
            with col1_1:
                with st.container(horizontal=True, horizontal_alignment="right"):
                    st.image(poke_type1_filepath, width=32)
            with col1_2:
                with st.container(horizontal=True, horizontal_alignment="left"):
                    st.image(poke_type2_filepath, width=32)
        else:
            with st.container(horizontal=True, horizontal_alignment="center"):
                st.image(poke_type1_filepath, width=32)
        
        st.markdown(f"**{p["nickname"]}**", text_alignment="center")
    
    with col2:
        form = " " + p["form"].replace('_', ' ').title() if p["form"] != "NORMAL" else ""
        st.markdown(f"**#{p["species_id"]} {p['species_name'].capitalize()}{form}**")
        
        mega_btn = mega_x_btn = mega_y_btn = False
        if p["species_id"] in mega_xy_pokedex_ids:
            with st.container(horizontal=True):
                mega_x_btn = st.button("Mega X", width="stretch", disabled=not p["is_mega_1"])
                mega_y_btn = st.button("Mega Y", width="stretch", disabled=not p["is_mega_2"])
        elif p["species_id"] in mega_pokedex_ids:
            mega_btn = st.button("Mega", width="stretch", disabled=not p["is_mega_1"])
        elif p["species_id"] in primal_pokedex_ids:
            mega_btn = st.button("Primal", width="stretch", disabled=not p["is_mega_1"])
        
        if qry_prm and int(qry_prm.split(':')[0]) == p["inv_id"]:
            level = float(st.query_params["mega"].split(':')[2])
        else:
            level = p["level"]
        st.write(f"Level: {level}")
        
        with st.container(horizontal=True):
            fm_type_filename = f"{p["fast_type"]}.png"
            fm_type_filepath = Path(__file__).parent.parent / "assets" / "types" / fm_type_filename
            st.image(fm_type_filepath, width=25)
            st.write(p["fast_name"].replace('_', ' ').title())
        with st.container(horizontal=True):
            c1_type_filename = f"{p["c1_type"]}.png"
            c1_type_filepath = Path(__file__).parent.parent / "assets" / "types" / c1_type_filename
            st.image(c1_type_filepath, width=25)
            st.write(p["c1_name"].replace('_', ' ').title())
        if p["c2_type"]:
            with st.container(horizontal=True):
                c2_type_filename = f"{p["c2_type"]}.png"
                c2_type_filepath = Path(__file__).parent.parent / "assets" / "types" / c2_type_filename
                st.image(c2_type_filepath, width=25)
                st.write(p["c2_name"].replace('_', ' ').title())
        
        update_poke_btn = st.button("Update")
        delete_poke_btn = st.button("Delete", type="primary")

        if p["species_id"] in mega_xy_pokedex_ids and mega_x_btn:
            if (
                qry_prm
                and int(qry_prm.split(":")[0]) == p["inv_id"]
                and int(qry_prm.split(":")[1]) == 1
            ):
                del st.query_params["mega"]
            else:
                st.query_params["mega"] = f"{p["inv_id"]}:{1}:{level}"
            st.rerun()
        elif p["species_id"] in mega_xy_pokedex_ids and mega_y_btn:
            if (
                qry_prm
                and int(qry_prm.split(":")[0]) == p["inv_id"]
                and int(qry_prm.split(":")[1]) == 2
            ):
                del st.query_params["mega"]
            else:
                st.query_params["mega"] = f"{p["inv_id"]}:{2}:{level}"
            st.rerun()
        elif p["species_id"] in mega_pokedex_ids and mega_btn:
            if (
                qry_prm
                and int(qry_prm.split(":")[0]) == p["inv_id"]
                and int(qry_prm.split(":")[1]) == 3
            ):
                del st.query_params["mega"]
            else:
                st.query_params["mega"] = f"{p["inv_id"]}:{3}:{level}"
            st.rerun()
        elif p["species_id"] in primal_pokedex_ids and mega_btn:
            if (
                qry_prm
                and int(qry_prm.split(":")[0]) == p["inv_id"]
                and int(qry_prm.split(":")[1]) == 3
            ):
                del st.query_params["mega"]
            else:
                st.query_params["mega"] = f"{p["inv_id"]}:{3}:{level}"
            st.rerun()
        
        if update_poke_btn:
            close_pokemon_details_dialog()
            st.session_state["show_update_pokemon_dialog"] = True
            st.session_state["update_pokemon_inv_id"] = p["inv_id"]
            st.rerun()

        if delete_poke_btn:
            close_pokemon_details_dialog()
            st.session_state["show_delete_pokemon_dialog"] = True
            st.session_state["delete_pokemon_inv_id"] = p["inv_id"]
            st.rerun()


def render_pokemon_card(p):
    name = p["nickname"]
    assets = get_pokemon_card_assets(p)
    IVs = assets["IVs"]
    poke_type_2 = assets["poke_type_2"]
    poke_img_filepath = assets["poke_img_filepath"]
    poke_type1_filepath = assets["poke_type1_filepath"]
    poke_type2_filepath = assets["poke_type2_filepath"]

    with st.container(border=True):
        qry_prm = st.query_params.get("mega")
        if qry_prm and int(qry_prm.split(':')[0]) == p["inv_id"]:
            st.markdown(
                f"""
                <p style="text-align: center; color: #FF0000; font-weight: 500;">
                    CP {p["cp"]} ({IVs})
                </p>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(f"**CP {p["cp"]} ({IVs})**", text_alignment="center")
        IV_total = math.floor(((p["atk_iv"] + p["def_iv"] + p["sta_iv"]) / 45) * 100)
        st.markdown(
            f"""
            <div style="
                border: 1px solid rgba(49, 51, 63, 0.2);
                border-radius: 6px;
                padding: 2px 8px;
                text-align: center;
                width: fit-content;
                margin: 0 auto 8px auto;
                color: {iv_color(IV_total)};
                font-weight: 600;
            ">
                {IV_total}
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.image(poke_img_filepath)
        
        with open(poke_type1_filepath, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()

        if poke_type_2:
            col1, col2 = st.columns(2)
            with col1:
                with st.container(horizontal=True, horizontal_alignment="right"):
                    st.markdown(
                        f'<div style="text-align: center; padding-bottom: 16px;"><img src="data:image/png;base64,{b64}" width="32"></div>',
                        unsafe_allow_html=True
                    )
            with col2:
                with open(poke_type2_filepath, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode()
                with st.container(horizontal=True, horizontal_alignment="left"):
                    st.markdown(
                        f'<div style="text-align: center; padding-bottom: 16px;"><img src="data:image/png;base64,{b64}" width="32"></div>',
                        unsafe_allow_html=True
                    )
        else:
            with st.container(horizontal=True, horizontal_alignment="center"):
                st.markdown(
                    f'<div style="text-align: center; padding-bottom: 16px;"><img src="data:image/png;base64,{b64}" width="32"></div>',
                    unsafe_allow_html=True
                )
        st.markdown(f"**{name}**", text_alignment="center")

        if st.button("View details", key=f"view_{p['inv_id']}", width="stretch"):
            st.session_state["show_pokemon_details_dialog"] = True
            st.session_state["pokemon_details_id"] = p["inv_id"]


def render():
    username = st.session_state["user"].get("username", "")
    user_id = st.session_state["user"].get("id", "")
    hour = datetime.now().hour

    if 5 <= hour < 12:
        greeting = "Good morning"
    elif 12 <= hour < 15:
        greeting = "Good afternoon"
    else:
        greeting = "Good evening"

    st.header(f"{greeting}, @{username}")

    if nickname := st.session_state.pop("add_pokemon_success", None):
        st.toast(f"{nickname} successfully added!", icon="🟢")

    if nickname := st.session_state.pop("update_pokemon_success", None):
        st.toast(f"{nickname} successfully updated!", icon="🟢")

    if nickname := st.session_state.pop("delete_pokemon_success", None):
        st.toast(f"{nickname} successfully deleted!", icon="🟢")

    if "dashboard_tab" not in st.session_state:
        tab = st.query_params.get("tab", "Storage")
        if tab not in ["Storage", "Battle"]:
            tab = "Storage"
        st.session_state["dashboard_tab"] = tab

    storage_tab, battle_tab = st.tabs(
        ["Storage", "Battle"],
        key="dashboard_tab",
        on_change=sync_tab_to_url,
    )
    
    try: 
        pokemons = get_pokemon_storage(user_id)
    except Exception as e:
        st.error(f"Error fetching inventory: {e}")
        return

    with storage_tab:
        _render_storage_tab(pokemons)

    with battle_tab:
        _render_battle_tab(pokemons)


def sync_tab_to_url():
    st.query_params["tab"] = st.session_state["dashboard_tab"]


def _render_storage_tab(pokemons):
    st.subheader("My Pokémon")
    
    col1, col2, col3 = st.columns(3, vertical_alignment="bottom")
    with col1:
        poke_search = st.text_input("🔍︎ Find Pokémon")
        pokemons_filtered = []
        if poke_search:
            ps = poke_search.strip().upper()
            for p in pokemons:
                poke_nickname = (p["nickname"] or "").upper()
                poke_species = (p["species_name"] or "").upper()
                if poke_nickname.startswith(ps) or poke_species.startswith(ps):
                    pokemons_filtered.append(p)
        else:
            pokemons_filtered = pokemons

    qry_prm = st.query_params.get("mega")
    if qry_prm:
        inv_id, mega_type, _ = qry_prm.split(":")
        mega_type = int(mega_type)
        for p in pokemons_filtered:
            if p["inv_id"] == int(inv_id):
                if mega_type == 1:
                    mega_form = "MEGA_X"
                elif mega_type == 2:
                    mega_form = "MEGA_Y"
                elif p["species_id"] in primal_pokedex_ids:
                    mega_form = "PRIMAL"
                else:
                    mega_form = "MEGA"
                t = get_mega_types(p["species_id"], mega_form)
                # if t:
                p["type_1"], p["type_2"] = t["type_1"], t["type_2"]

    for p in pokemons_filtered:
        p["cp"] = get_display_cp(p, qry_prm)

    with col2:
        add_new_poke_btn = st.button("Add new pokemon", width="stretch")

    with col3:
        sort_by = st.selectbox("Sort by", ["CP (high → low)", "CP (low → high)", "IV (high → low)", "IV (low → high)", "# (high → low)", "# (low → high)"])

    if add_new_poke_btn:
        st.session_state["show_add_pokemon_dialog"] = True

    if sort_by == "CP (high → low)":
        pokemons_filtered.sort(key=lambda p: p["cp"], reverse=True)
    elif sort_by == "CP (low → high)":
        pokemons_filtered.sort(key=lambda p: p["cp"])
    elif sort_by == "IV (high → low)":
        pokemons_filtered.sort(key=lambda p: p["atk_iv"] + p["def_iv"] + p["sta_iv"], reverse=True)
    elif sort_by == "IV (low → high)":
        pokemons_filtered.sort(key=lambda p: p["atk_iv"] + p["def_iv"] + p["sta_iv"])
    elif sort_by == "# (high → low)":
        pokemons_filtered.sort(key=lambda p: p["species_id"], reverse=True)
    else:
        pokemons_filtered.sort(key=lambda p: p["species_id"])

    # with st.container(horizontal=True, horizontal_alignment="center"):
    #     with st.container(width=900):
    cols_per_row = 4
    for i in range(0, len(pokemons_filtered), cols_per_row):
        cols = st.columns(cols_per_row)
        for col, pokemon in zip(cols, pokemons_filtered[i:i + cols_per_row]):
            with col:
                render_pokemon_card(pokemon)
    
    if st.session_state.get("show_add_pokemon_dialog"):
        render_add_new_pokemon()
    
    if not pokemons:
        st.info("You don't have any Pokémon in your storage.")
        return 

    if st.session_state.get("show_update_pokemon_dialog"):
        update_inv_id = st.session_state.get("update_pokemon_inv_id")
        update_poke = next((p for p in pokemons if p["inv_id"] == update_inv_id), None)
        if update_poke:
            render_update_existing_pokemon(update_poke)
        else:
            st.session_state["show_update_pokemon_dialog"] = False
            st.session_state.pop("update_pokemon_inv_id", None)

    if st.session_state.get("show_pokemon_details_dialog"):
        details_id = st.session_state.get("pokemon_details_id")
        details_poke = next((p for p in pokemons if p["inv_id"] == details_id), None)
        if details_poke:
            details_poke = dict(details_poke)
            details_poke["cp"] = get_display_cp(details_poke, st.query_params.get("mega"))
            assets = get_pokemon_card_assets(details_poke)
            show_pokemon_details(
                details_poke,
                assets["poke_img_filepath"],
                assets["IVs"],
                assets["poke_type1_filepath"],
                assets["poke_type2_filepath"],
            )
        else:
            close_pokemon_details_dialog()
    
    if st.session_state.get("show_delete_pokemon_dialog"):
        delete_inv_id = st.session_state.get("delete_pokemon_inv_id")
        delete_poke_nickname = next((p["nickname"] for p in pokemons if p["inv_id"] == delete_inv_id), None)
        if delete_poke_nickname:
            render_delete_existing_pokemon(st.session_state["user"]["id"], delete_inv_id, delete_poke_nickname)
        else:
            st.session_state["show_delete_pokemon_dialog"] = False
            st.session_state.pop("delete_pokemon_inv_id", None)


def _render_battle_tab(pokemons):
    with st.container(border=True):
        selected_mode = st.selectbox("Mode:", ["PvE (Raids & Gyms)", "PvP (Trainer Battles & GO Battle League)"], )
        pve_filename, raid_filename = "pokemon_go_battle.png", "pokemon_go_gym.png"
        pve_filepath, raid__filepath = Path(__file__).parent.parent / "assets" / "battle_logo" / pve_filename, Path(__file__).parent.parent / "assets" / "battle_logo" / raid_filename
        if selected_mode == "PvE (Raids & Gyms)":
            with st.container(horizontal_alignment="center"):
                b64_image(pve_filepath, 400)
        elif selected_mode == "PvP (Trainer Battles & GO Battle League)":
            with st.container(horizontal_alignment="center"):
                b64_image(raid__filepath, 110)
        
        dmg_multipy_filename = "DAMAGE_MULTIPLIER.png"
        dmg_multipy_filepath = Path(__file__).parent.parent / "assets" / "types" / dmg_multipy_filename
        with st.container(horizontal_alignment="center"):
            b64_image(dmg_multipy_filepath, 500)

        selected_poke = selectbox_pokemon("Enter defending Pokédex # or Pokémon name", include_mega=True)
        if selected_poke:
            species_id = selected_poke["id"]
            species_form = selected_poke["form"]
            form = get_form_name_img(species_form)

            poke_img_filename = f"{species_id:04d}{form}.png"
            poke_img_filepath = Path(__file__).parent.parent / "assets" / "images" / poke_img_filename
            poke_type1_filepath = Path(__file__).parent.parent / "assets" / "types" / f"{selected_poke["type_1"]}.png"
            poke_type2_filepath = (
                Path(__file__).parent.parent / "assets" / "types" / f"{selected_poke["type_2"]}.png"
                if selected_poke["type_2"]
                else None
            )
            b64_image(poke_img_filepath, 200)

            if poke_type2_filepath:
                col1, col2 = st.columns(2)
                with col1:
                    with st.container(horizontal=True, horizontal_alignment="right"):
                        b64_image(poke_type1_filepath, 32)
                with col2:
                    with st.container(horizontal=True, horizontal_alignment="left"):
                        b64_image(poke_type2_filepath, 32)
            else:
                with st.container(horizontal=True, horizontal_alignment="center"):
                    b64_image(poke_type1_filepath, 32)

            with st.container(horizontal=True, horizontal_alignment="center"):
                generate_deck_btn = st.button("Generate Deck", type="primary")

            is_pvp = True if selected_mode == "PvP (Trainer Battles & GO Battle League)" else False
            if generate_deck_btn:
                st.session_state["deck_results"] = get_battle_recommendations(pokemons, 1, is_pvp, species_id, species_form)

            deck_key = (species_id, species_form, is_pvp)
            if st.session_state.get("deck_key") != deck_key:
                st.session_state.pop("deck_results", None)
                st.session_state.pop("cnt_deck_show", None)
                st.session_state["deck_key"] = deck_key   

    

    if "deck_results" in st.session_state:
        sf = st.selectbox("Filter", ["None", "Exclude Mega Evolution", "Include top 1 only Mega Evolution", "Include top 5 only Mega Evolution"], key="deck_filter")
        selected_filter = 1 if sf == "None" else 2 if sf == "Exclude Mega Evolution" else 3 if sf == "Include top 1 only Mega Evolution" else 4
        result_filtered = filter_result(st.session_state["deck_results"], selected_filter)
        # st.dataframe(result_filtered)
        # print(result_filtered)

        if "cnt_deck_show" not in st.session_state:
            st.session_state["cnt_deck_show"] = 15
        max_render = min(st.session_state.get("cnt_deck_show", 0), len(result_filtered))
        
        cols_per_row = 2
        cnt = 1
        for i in range(0, max_render, cols_per_row):
            cols = st.columns(cols_per_row)
            for col, pokemon in zip(cols, result_filtered[i:min(i + cols_per_row, max_render)]):
                with col:
                    render_deck_card(pokemon, cnt)
                    cnt += 1
        
        if st.session_state["cnt_deck_show"] < len(result_filtered):
            with st.container(horizontal_alignment="center"):
                load_more = st.button("Load more")
    
            if load_more:
                st.session_state["cnt_deck_show"] += 15
                st.rerun()

        


def render_deck_card(p, rank):
    IVs = f"{p["atk_iv"]}/{p["def_iv"]}/{p["sta_iv"]}"
    form = get_form_name_img(p["form"])

    poke_type1, poke_type_2 = p["type_1"], p["type_2"]
    poke_type1_filepath = Path(__file__).parent.parent / "assets" / "types" / f"{poke_type1}.png"
    poke_type2_filepath = (
        Path(__file__).parent.parent / "assets" / "types" / f"{poke_type_2}.png"
        if poke_type_2
        else None
    )
    # print(p["species_name"], p["form"], p["cp"])

    if p["species_id"] in mega_xy_pokedex_ids and p["form"] == "MEGA_X":
        poke_img_filename = f"{p["species_id"]:04d}-Mega-X.png"
    elif p["species_id"] in mega_xy_pokedex_ids and p["form"] == "MEGA_Y":
        poke_img_filename = f"{p["species_id"]:04d}-Mega-Y.png"
    elif p["species_id"] in mega_pokedex_ids and p["form"] == "MEGA":
        poke_img_filename = f"{p["species_id"]:04d}-Mega.png"
    elif p["species_id"] in primal_pokedex_ids and p["form"] == "PRIMAL":
        poke_img_filename = f"{p["species_id"]:04d}-Primal.png"
    else:
        poke_img_filename = f"{p['species_id']:04d}{form}.png"
    poke_img_filepath = Path(__file__).parent.parent / "assets" / "images" / poke_img_filename

    with st.container(border=True):
        st.markdown(
            f"""
            <div style="
                text-align: center;
                font-weight: 700;
                font-size: 0.95rem;
                padding: 4px 0 8px 0;
                border-bottom: 1px solid rgba(49, 51, 63, 0.15);
                margin-bottom: 8px;
            ">
                #{rank} ({p["score"]})
            </div>
            """,
            unsafe_allow_html=True,
        )

        col1, col2 = st.columns([1.3, 2])
        with col1:
            if _is_mega_or_primal(p):
                st.markdown(
                    f"""
                    <p style="text-align: center; color: #FF0000; font-weight: 500;">
                        CP {p["cp"]} ({IVs})
                    </p>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(f"**CP {p["cp"]} ({IVs})**", text_alignment="center")
            IV_total = math.floor(((p["atk_iv"] + p["def_iv"] + p["sta_iv"]) / 45) * 100)
            st.markdown(
                f"""
                <div style="
                    border: 1px solid rgba(49, 51, 63, 0.2);
                    border-radius: 6px;
                    padding: 2px 8px;
                    text-align: center;
                    width: fit-content;
                    margin: 0 auto 8px auto;
                    color: {iv_color(IV_total)};
                    font-weight: 600;
                ">
                    {IV_total}
                </div>
                """,
                unsafe_allow_html=True,
            )

            # b64_image(poke_img_filepath, 100)
            st.image(poke_img_filepath)

            if poke_type2_filepath:
                left, right = st.columns(2)
                with left:
                    with st.container(horizontal=True, horizontal_alignment="right"):
                        b64_image(poke_type1_filepath, 32)
                with right:
                    with st.container(horizontal=True, horizontal_alignment="left"):
                        b64_image(poke_type2_filepath, 32)
            else:
                with st.container(horizontal=True, horizontal_alignment="center"):
                    b64_image(poke_type1_filepath, 32)
            st.markdown(f"**{p["nickname"]}**", text_alignment="center")

        with col2:
            form = " " + p["form"].replace('_', ' ').title() if p["form"] != "NORMAL" else ""
            st.markdown(f"**#{p["species_id"]} {p['species_name'].capitalize()}{form}**")

            level = p["level"]
            st.write(f"Level: {level}")

            with st.container(horizontal=True):
                fm_type_filename = f"{p["fast_type"]}.png"
                fm_type_filepath = Path(__file__).parent.parent / "assets" / "types" / fm_type_filename
                b64_image(fm_type_filepath, 25)
                st.write((p["fast_name"] + _format_effectiveness(p["eff_f"])).replace('_', ' ').title())
            st.write(f"{p["fast_move"]}")
            with st.container(horizontal=True):
                c1_type_filename = f"{p["c1_type"]}.png"
                c1_type_filepath = Path(__file__).parent.parent / "assets" / "types" / c1_type_filename
                b64_image(c1_type_filepath, 25)
                st.write((p["c1_name"] + _format_effectiveness(p["eff_c1"])).replace('_', ' ').title())
            st.write(f"{p["charge_1"]}")
            if p["c2_type"]:
                with st.container(horizontal=True):
                    c2_type_filename = f"{p["c2_type"]}.png"
                    c2_type_filepath = Path(__file__).parent.parent / "assets" / "types" / c2_type_filename
                    b64_image(c2_type_filepath, 25)
                    st.write((p["c2_name"] + _format_effectiveness(p["eff_c2"])).replace('_', ' ').title())
                st.write(f"{p["charge_2"]}")
            

def _format_effectiveness(score):
    if math.isclose(score, 2.56):
        return " 🟣"
    elif math.isclose(score, 1.6):
        return " 🔴"
    elif math.isclose(score, 1.0):
        return " 🟦"
    elif math.isclose(score, 0.625):
        return " 🟨"
    elif math.isclose(score, 0.390625):
        return " ⚫"
    else:
        return " 🟦"


def _is_mega_or_primal(p) -> bool:
    name = p.get("form") or ""
    return "MEGA" in name or "PRIMAL" in name


def filter_result(res, cond):
    result = []
    if cond == 1:
        result = res
    elif cond == 2:
        for p in res:
            if _is_mega_or_primal(p):
                continue
            result.append(p)
    elif cond == 3:
        cnt = 0
        for p in res:
            if _is_mega_or_primal(p):
                if cnt >= 1:
                    continue
                else:
                    result.append(p)
                    cnt += 1
            else:
                result.append(p)
    elif cond == 4:
        cnt = 0
        for p in res:
            if _is_mega_or_primal(p):
                if cnt >= 5:
                    continue
                else:
                    result.append(p)
                    cnt += 1
            else:
                result.append(p)
    return result
