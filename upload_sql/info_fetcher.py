import json
import re

PATTERN = r"^V(?P<pokedex_num>\d{4})_POKEMON_(?P<name>[A-Z0-9]+)(?:_(?P<form>[A-Z0-9_]+))?$"
POKEMONSETTINGS_TEMPLATE = {"pokemonId": "-", "stats": {"baseStamina": -1, "baseAttack": -1, "baseDefense": -1}}
STATS_TEMPLATE = {"baseStamina": -1, "baseAttack": -1, "baseDefense": -1}

def top_n_pokemon(game_master, N: int) -> list:
    """Fetch the top <count> pokemon listed on the file.
    """
    result = []
    for item in game_master:
        templateId = item.get("templateId", "")
        match = re.match(PATTERN, templateId)
        if not match:
            continue
        pokedex_num = match.group("pokedex_num")
        if int(pokedex_num) > N:
            return result

        data = item.get("data", {})
        data_pokemonSettings = data.get("pokemonSettings", POKEMONSETTINGS_TEMPLATE)

        pokemon = match.groupdict()
        pokemon.update(data_pokemonSettings.get("stats", STATS_TEMPLATE))
        pokemon["type"] = data_pokemonSettings.get("type", "-")
        pokemon["type2"] = data_pokemonSettings.get("type2", "-")
        result.append(pokemon)
    return result


if __name__ == "__main__":
    with open('../latest.json') as file:
        game_master = json.load(file)

    while True:
        user_input = input("Please insert your N (1 - 1025): ")
        try:
            N = int(user_input)
            if 1 <= N:
                break
            else:
                print("Out of range! Please enter a positive number.")
        except ValueError:
            print("Invalid input! That is not a valid integer.")

    top_n_result = top_n_pokemon(game_master, N)
    print(top_n_result)
    cnt = 1
    for i in top_n_result:
        print(f"#{cnt}: {i["name"]} {i["form"]} has stats {i["baseAttack"]}/{i["baseDefense"]}/{i["baseStamina"]}\n")
        cnt += 1