# database.py
import sqlite3
import json  # For storing lists like draft order
import uuid
from typing import List, Tuple, Dict, Optional, Any
import copy  # For deepcopying INITIAL_ITEMS_BY_CATEGORY
from datetime import datetime, timezone

# --- Constants ---
INITIAL_ITEMS_BY_CATEGORY = {
    "Biomes": ["Mesa", "Jungle", "Snowy", "Mega Taiga", "Mushroom"],
    "Armour": ["Helmet", "Chestplate", "Leggings", "Boots", "Bucket"],
    "Tools": ["Sword", "Pickaxe", "Shovel", "Hoe", "Axe", "Trident"],
    "Multi-Part Advancements": ["Catalogue", "Adventuring", "Two by Two", "Monsters", "Balanced Diet"],
    "Misc": ["Leads", "Fire Res", "Breeds", "Hives", "Crossbow", "Shulker"],
    "Early Game": ["Fireworks", "Shulker Box", "Obsidian", "Logs", "Eyes", "Rod Rates"]
}
CATEGORIES_ORDER = list(INITIAL_ITEMS_BY_CATEGORY.keys())


# --- Database Setup ---
def get_db_connection(db_name: str):
    conn = sqlite3.connect(db_name)
    conn.row_factory = sqlite3.Row  # Access columns by name
    return conn


def initialize_database(db_name: str):
    conn = get_db_connection(db_name)
    cursor = conn.cursor()

    # Minecraft Usernames Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS minecraft_usernames (
            discord_id INTEGER NOT NULL,
            minecraft_username TEXT NOT NULL,
            updated_at_utc INTEGER NOT NULL,
            PRIMARY KEY (discord_id)
        )
    ''')

    # Drafts Table: Core information about each draft
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS drafts (
            draft_id TEXT PRIMARY KEY,
            guild_id INTEGER NOT NULL,
            channel_id INTEGER NOT NULL,
            admin_user_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'active', -- 'active', 'completed', 'reset'
            num_players INTEGER NOT NULL,
            picks_allowed_per_player_per_category INTEGER NOT NULL,
            total_picks_allotted_per_player INTEGER NOT NULL,
            current_pick_global_index INTEGER DEFAULT 0,
            total_picks_to_make INTEGER NOT NULL,
            draft_order_player_indices_json TEXT NOT NULL, -- JSON list of player slot indices
            board_message_id INTEGER,
            last_event_message TEXT,
            created_at_utc INTEGER NOT NULL, -- Store as UTC timestamp
            message_link TEXT -- Store the link to the original draft message
        )
    ''')

    # Draft Players Table: Links users to drafts
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS draft_players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            draft_id TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            display_name TEXT NOT NULL,
            player_slot_index INTEGER NOT NULL, -- 0, 1, 2... for their position in the players list
            FOREIGN KEY (draft_id) REFERENCES drafts (draft_id) ON DELETE CASCADE,
            UNIQUE (draft_id, user_id),
            UNIQUE (draft_id, player_slot_index) 
        )
    ''')

    # Draft Items Table: Tracks availability of each item within a draft
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS draft_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            draft_id TEXT NOT NULL,
            category_name TEXT NOT NULL,
            item_name TEXT NOT NULL,
            is_available BOOLEAN DEFAULT 1, -- 1 for true, 0 for false
            FOREIGN KEY (draft_id) REFERENCES drafts (draft_id) ON DELETE CASCADE,
            UNIQUE (draft_id, category_name, item_name)
        )
    ''')

    # Player Picked Items Table: Records which player picked which item
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS player_picked_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            draft_id TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            category_name TEXT NOT NULL,
            item_name TEXT NOT NULL,
            pick_timestamp INTEGER NOT NULL, -- Store as UTC timestamp
            FOREIGN KEY (draft_id) REFERENCES drafts (draft_id) ON DELETE CASCADE
        )
    ''')
    conn.commit()
    conn.close()
    print(f"Database '{db_name}' initialized successfully.")

# --- Draft Creation and Management ---


def create_draft(db_name: str, guild_id: int, channel_id: int, admin_user_id: int,
                 players_info: List[Tuple[int, str]],
                 picks_allowed_per_player_per_category: int,
                 total_picks_allotted_per_player: int,
                 draft_order_player_indices: List[int],
                 total_picks_to_make: int,
                 message_link: Optional[str] = None) -> Optional[str]:
    draft_id = uuid.uuid4().hex[:10]  # Shorter unique ID
    conn = get_db_connection(db_name)
    cursor = conn.cursor()
    try:
        # Get current UTC timestamp
        current_utc_timestamp = int(datetime.now(timezone.utc).timestamp())

        cursor.execute('''
            INSERT INTO drafts (draft_id, guild_id, channel_id, admin_user_id, num_players,
                                picks_allowed_per_player_per_category, total_picks_allotted_per_player,
                                draft_order_player_indices_json, total_picks_to_make, created_at_utc,
                                message_link)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (draft_id, guild_id, channel_id, admin_user_id, len(players_info),
              picks_allowed_per_player_per_category, total_picks_allotted_per_player,
              json.dumps(
                  draft_order_player_indices), total_picks_to_make, current_utc_timestamp,
              message_link))

        for i, (user_id, display_name) in enumerate(players_info):
            cursor.execute('''
                INSERT INTO draft_players (draft_id, user_id, display_name, player_slot_index)
                VALUES (?, ?, ?, ?)
            ''', (draft_id, user_id, display_name, i))

        for category, items in INITIAL_ITEMS_BY_CATEGORY.items():
            for item_name in items:
                cursor.execute('''
                    INSERT INTO draft_items (draft_id, category_name, item_name, is_available)
                    VALUES (?, ?, ?, 1)
                ''', (draft_id, category, item_name))

        conn.commit()
        return draft_id
    except sqlite3.Error as e:
        print(f"Database error creating draft: {e}")
        conn.rollback()
        return None
    finally:
        conn.close()


def get_draft_state(db_name: str, draft_id: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection(db_name)
    cursor = conn.cursor()

    draft_row = cursor.execute(
        "SELECT * FROM drafts WHERE draft_id = ?", (draft_id,)).fetchone()
    if not draft_row:
        conn.close()
        return None

    draft_state = dict(draft_row)
    draft_state['draft_order_player_indices'] = json.loads(
        draft_row['draft_order_player_indices_json'])

    # Fetch players
    players_rows = cursor.execute(
        "SELECT user_id, display_name, player_slot_index FROM draft_players WHERE draft_id = ? ORDER BY player_slot_index", (draft_id,)).fetchall()
    draft_state['players'] = [(row['user_id'], row['display_name'])
                              for row in players_rows]  # Keep order

    # Fetch available items (grouped by category)
    draft_state['available_items'] = copy.deepcopy(
        INITIAL_ITEMS_BY_CATEGORY)  # Start with all
    for cat in draft_state['available_items']:
        draft_state['available_items'][cat] = []  # Clear lists

    available_item_rows = cursor.execute(
        "SELECT category_name, item_name FROM draft_items WHERE draft_id = ? AND is_available = 1", (draft_id,)).fetchall()
    for row in available_item_rows:
        draft_state['available_items'][row['category_name']].append(
            row['item_name'])

    # Fetch drafted items by player
    draft_state['drafted_items_by_player'] = {}
    picked_item_rows = cursor.execute(
        "SELECT user_id, category_name, item_name FROM player_picked_items WHERE draft_id = ?", (draft_id,)).fetchall()
    for row in picked_item_rows:
        player_picks = draft_state['drafted_items_by_player'].setdefault(
            row['user_id'], {})
        category_picks = player_picks.setdefault(row['category_name'], [])
        category_picks.append(row['item_name'])

    draft_state['master_item_list'] = copy.deepcopy(
        INITIAL_ITEMS_BY_CATEGORY)  # For display
    draft_state['categories_order'] = CATEGORIES_ORDER

    conn.close()
    return draft_state


def record_pick(db_name: str, draft_id: str, user_id: int, category_name: str, item_name: str) -> bool:
    conn = get_db_connection(db_name)
    cursor = conn.cursor()
    try:
        # Get current UTC timestamp
        current_utc_timestamp = int(datetime.now(timezone.utc).timestamp())

        # Mark item as unavailable
        cursor.execute('''
            UPDATE draft_items SET is_available = 0
            WHERE draft_id = ? AND category_name = ? AND item_name = ? AND is_available = 1 
        ''', (draft_id, category_name, item_name))

        if cursor.rowcount == 0:  # Item was already unavailable or doesn't exist for this draft
            conn.rollback()
            print(
                f"Failed to mark item as unavailable (draft_id: {draft_id}, item: {item_name})")
            return False

        # Record the pick
        cursor.execute('''
            INSERT INTO player_picked_items (draft_id, user_id, category_name, item_name, pick_timestamp)
            VALUES (?, ?, ?, ?, ?)
        ''', (draft_id, user_id, category_name, item_name, current_utc_timestamp))

        # Advance draft turn
        cursor.execute('''
            UPDATE drafts SET current_pick_global_index = current_pick_global_index + 1, last_event_message = NULL
            WHERE draft_id = ?
        ''', (draft_id,))

        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Database error recording pick: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def update_draft_status(db_name: str, draft_id: str, status: str) -> bool:
    conn = get_db_connection(db_name)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE drafts SET status = ? WHERE draft_id = ?", (status, draft_id))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error updating draft status: {e}")
        return False
    finally:
        conn.close()


def update_board_message_id(db_name: str, draft_id: str, message_id: Optional[int]):
    conn = get_db_connection(db_name)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE drafts SET board_message_id = ? WHERE draft_id = ?", (message_id, draft_id))
        conn.commit()
    except sqlite3.Error as e:
        print(f"DB error updating board message ID: {e}")
    finally:
        conn.close()


def update_last_event_message(db_name: str, draft_id: str, event_message: Optional[str]):
    conn = get_db_connection(db_name)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE drafts SET last_event_message = ? WHERE draft_id = ?", (event_message, draft_id))
        conn.commit()
    except sqlite3.Error as e:
        print(f"DB error updating last event message: {e}")
    finally:
        conn.close()


def get_active_drafts_in_channel(db_name: str, channel_id: int) -> List[Dict[str, Any]]:
    conn = get_db_connection(db_name)
    cursor = conn.cursor()
    draft_rows = cursor.execute(
        "SELECT draft_id, admin_user_id, num_players, created_at_utc FROM drafts WHERE channel_id = ? AND status = 'active' ORDER BY created_at_utc DESC",
        (channel_id,)
    ).fetchall()
    conn.close()
    return [dict(row) for row in draft_rows]


def get_player_name_by_id(db_name: str, draft_id: str, user_id: int) -> Optional[str]:
    """Helper to get a player's display name for a specific draft."""
    conn = get_db_connection(db_name)
    cursor = conn.cursor()
    row = cursor.execute(
        "SELECT display_name FROM draft_players WHERE draft_id = ? AND user_id = ?", (draft_id, user_id)).fetchone()
    conn.close()
    return row['display_name'] if row else None


def get_user_recent_drafts(db_name: str, user_id: int, limit: int = 5) -> List[Dict[str, Any]]:
    """Get a user's recent drafts, ordered by most recent first."""
    conn = get_db_connection(db_name)
    cursor = conn.cursor()

    # Join drafts with draft_players to get drafts where user participated
    cursor.execute('''
        SELECT d.draft_id, d.guild_id, d.channel_id, d.admin_user_id, d.status,
               d.num_players, d.created_at_utc, dp.display_name as player_name
        FROM drafts d
        JOIN draft_players dp ON d.draft_id = dp.draft_id
        WHERE dp.user_id = ?
        ORDER BY d.created_at_utc DESC
        LIMIT ?
    ''', (user_id, limit))

    drafts = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return drafts


def update_message_link(db_name: str, draft_id: str, message_link: Optional[str]) -> bool:
    """Update the message link for a draft."""
    conn = get_db_connection(db_name)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE drafts SET message_link = ? WHERE draft_id = ?",
            (message_link, draft_id)
        )
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        print(f"Database error updating message link: {e}")
        return False
    finally:
        conn.close()


def get_recent_picks(db_name: str, draft_id: str, limit: int = 10) -> list:
    """Get the most recent picks for a draft."""
    conn = get_db_connection(db_name)
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT user_id, category_name, item_name, pick_timestamp
            FROM player_picked_items
            WHERE draft_id = ?
            ORDER BY pick_timestamp DESC
            LIMIT ?
        """, (draft_id, limit))

        picks = []
        for row in cursor.fetchall():
            picks.append({
                'player_id': row['user_id'],
                'category_name': row['category_name'],
                'item_name': row['item_name'],
                'created_at': row['pick_timestamp']
            })
        return picks
    finally:
        conn.close()


def get_minecraft_username(db_name: str, discord_id: int) -> Optional[str]:
    """Get a user's Minecraft username."""
    conn = get_db_connection(db_name)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT minecraft_username FROM minecraft_usernames WHERE discord_id = ?",
            (discord_id,)
        )
        row = cursor.fetchone()
        return row['minecraft_username'] if row else None
    finally:
        conn.close()


def set_minecraft_username(db_name: str, discord_id: int, minecraft_username: Optional[str]) -> bool:
    """Set, update, or remove a user's Minecraft username."""
    conn = get_db_connection(db_name)
    cursor = conn.cursor()
    try:
        if minecraft_username is None:
            # Remove the username
            cursor.execute(
                "DELETE FROM minecraft_usernames WHERE discord_id = ?",
                (discord_id,)
            )
        else:
            # Set or update the username
            current_utc_timestamp = int(datetime.now(timezone.utc).timestamp())
            cursor.execute('''
                INSERT INTO minecraft_usernames (discord_id, minecraft_username, updated_at_utc)
                VALUES (?, ?, ?)
                ON CONFLICT(discord_id) DO UPDATE SET
                    minecraft_username = excluded.minecraft_username,
                    updated_at_utc = excluded.updated_at_utc
            ''', (discord_id, minecraft_username, current_utc_timestamp))
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Database error setting Minecraft username: {e}")
        return False
    finally:
        conn.close()
