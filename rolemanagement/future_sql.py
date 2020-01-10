# Below is planned schema for SQLite handling and expansion of functionality.
"""
CREATE TABLE IF NOT EXISTS roles (
    role_id INTEGER PRIMARY KEY NOT NULL,
    self_role BOOLEAN DEFAULT FALSE,
    sticky BOOLEAN DEFAULT FALSE,
    self_removable BOOLEAN DEFAULT FALSE,
    -- useful for preventing pre 10 minute bypass
    -- and just for keeping it to people who have been around a bit
    minimum_join_time INTEGER DEFAULT 0,
    cost INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS groups (
    uid INTEGER AUTOINCREMENT,
    name TEXT,
    minimum INTEGER DEFAULT 0,
    maximum INTEGER DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS exclusions (
    role_id INTEGER REFERENCES roles(role_id) ON DELETE CASCADE,
    blocks_role_id INTEGER REFERENCES roles(role_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS requires (
    role_id INTEGER REFERENCES roles(role_id) ON DELETE CASCADE,
    requires_role_id INTEGER REFERENCES roles(role_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS actions (
    message_id INTEGER NOT NULL,
    reaction TEXT NOT NULL  -- unicode emoji or str(discord.Emoji.id),
    channel_id INTEGER NOT NULL,
    guild_id INTEGER NOT NULL,
    reaction_id INTEGER REFERENCES reactions(uid) ON DELETE CASCADE,
    action_type INTEGER, -- handle as enum from python
    role_id INTEGER REFERENCES roles(role_id)
);

CREATE TABLE IF NOT EXISTS members (
    member_id INTEGER NOT NULL,
    guild_id INTEGER NOT NULL,
    kaizo_locked BOOLEAN DEFAULT FALSE,
    kaizo_kicked BOOLEAN DEFAULT FALSE,
    kaizo_banned BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS sticky_roles (
    member_id INTEGER NOT NULL,  -- intentional no ref
    role_id INTEGER REFERENCES roles(role_id) ON DELETE CASCADE,
    is_stickied BOOLEAN DEFAULT FALSE
);
"""


# Below are some action types
import enum


class ActionType(enum.IntEnum):
    TOGGLE = 1
    ADD = 2
    REMOVE = 3
    INVERTED_TOGGLE = 4
    # anti auto react bot measures
    # A subset of spam bots appear to be attempting to auto react
    # to things which appear to be verification channels
    # (As of at least September 2019)
    KAIZO_LOCK = 5
    KAIZO_KICK = 6
    KAIZO_BAN = 7
