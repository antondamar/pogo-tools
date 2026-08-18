-- Empty app schema. Seed CSVs fill species / moves / species_moves.
-- User accounts and inventory stay empty until someone uses the app.

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS species (
    id INTEGER NOT NULL,
    form VARCHAR(50) NOT NULL,
    name VARCHAR(50) NOT NULL,
    type_1 VARCHAR(30) NOT NULL,
    type_2 VARCHAR(30),
    base_attack INTEGER NOT NULL,
    base_defense INTEGER NOT NULL,
    base_stamina INTEGER NOT NULL,
    PRIMARY KEY (id, form)
);

CREATE TABLE IF NOT EXISTS moves (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    type VARCHAR(30) NOT NULL,
    is_fast_move BOOLEAN NOT NULL,
    pve_power NUMERIC,
    pve_energy_delta INTEGER DEFAULT 0,
    duration_ms INTEGER DEFAULT 0,
    damage_window_start_ms INTEGER DEFAULT 0,
    damage_window_end_ms INTEGER DEFAULT 0,
    pvp_power DOUBLE PRECISION DEFAULT 0,
    pvp_energy_delta INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS species_moves (
    species_id INTEGER NOT NULL,
    species_form VARCHAR(50) NOT NULL,
    move_id INTEGER NOT NULL REFERENCES moves (id),
    is_elite_move BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (species_id, species_form, move_id),
    FOREIGN KEY (species_id, species_form) REFERENCES species (id, form)
);

CREATE TABLE IF NOT EXISTS user_pokemon (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users (id),
    species_id INTEGER NOT NULL,
    species_form VARCHAR(50) NOT NULL,
    atk_iv INTEGER NOT NULL,
    def_iv INTEGER NOT NULL,
    sta_iv INTEGER NOT NULL,
    cp INTEGER NOT NULL,
    level NUMERIC NOT NULL,
    fast_move_id INTEGER REFERENCES moves (id),
    charged_move_1_id INTEGER REFERENCES moves (id),
    charged_move_2_id INTEGER REFERENCES moves (id),
    nickname VARCHAR(50),
    is_shiny BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_mega_1 BOOLEAN DEFAULT FALSE,
    is_mega_2 BOOLEAN DEFAULT FALSE,
    is_shadow BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (species_id, species_form) REFERENCES species (id, form)
);
