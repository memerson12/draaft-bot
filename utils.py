import discord
from typing import Optional, List, Dict, Any
from datetime import datetime


def create_draft_embed(title: str, description: str, color: discord.Color = discord.Color.blue()) -> discord.Embed:
    """Create a standardized embed for draft-related messages."""
    embed = discord.Embed(title=title, description=description, color=color)
    embed.set_thumbnail(
        url="https://cdn.icon-icons.com/icons2/2072/PNG/512/minecraft_logo_icon_128449.png")
    return embed


def format_draft_status(draft_state: Dict[str, Any], guild: discord.Guild) -> tuple[str, str]:
    """Format the draft status for display in an embed."""
    draft_id = draft_state['draft_id']

    if draft_state['status'] != 'active':
        description = f"🎉 Draft ID: {draft_id} - Status: {draft_state['status'].capitalize()}! 🎉"
        if draft_state.get('drafted_items_by_player'):
            description += f" View final picks with `/draftstatus draft_id={draft_id}`."
        title = f"🏆 Minecraft Item Draft - Final State (ID: {draft_id}) 🏆"
        return title, description

    # Active draft formatting
    player_slot_index = draft_state['draft_order_player_indices'][draft_state['current_pick_global_index']]
    current_player_id = None
    current_player_name = "Next Player"

    for p_id, p_name in draft_state['players']:
        if draft_state['players'].index((p_id, p_name)) == player_slot_index:
            current_player_id = p_id
            current_player_name = p_name
            break

    member = guild.get_member(current_player_id) if current_player_id else None
    current_player_mention = member.mention if member else current_player_name

    total_picks_allotted = draft_state.get(
        'total_picks_allotted_per_player', 'N/A')
    picks_made_by_player_total = 0
    if current_player_id in draft_state['drafted_items_by_player']:
        for cat_items in draft_state['drafted_items_by_player'][current_player_id].values():
            picks_made_by_player_total += len(cat_items)

    description = (
        f"**Global Pick {draft_state['current_pick_global_index'] + 1} of {draft_state['total_picks_to_make']}**\n"
        f"It's **{current_player_mention}**'s turn.\n"
        f"{current_player_mention} has picked {picks_made_by_player_total}/{total_picks_allotted} items total.\n"
        f"Pick Limit per Category: {draft_state['picks_allowed_per_player_per_category']}"
    )
    title = f"🏆 Minecraft Item Draft (ID: {draft_id}) 🏆"

    return title, description


def format_category_field(category_name: str, master_list: List[str], available_items: List[str]) -> tuple[str, str]:
    """Format a category field for the draft board."""
    available_count = len(available_items)
    display_items = []

    for item in master_list:
        if item in available_items:
            display_items.append(item)
        else:
            display_items.append(f"~~{item}~~")

    value = ", ".join(display_items) if display_items else "No items defined."
    if len(value) > 1020:
        value = value[:1020] + "..."

    return f"🎁 {category_name} ({available_count} available)", value


def format_pick_order(draft_state: Dict[str, Any], current_index: int) -> str:
    """Format the pick order display for the draft board."""
    pick_order_display = []
    start_idx = max(0, current_index - 2)
    end_idx = min(
        len(draft_state['draft_order_player_indices']), current_index + 3)

    if start_idx > 0:
        pick_order_display.append("...")

    for i in range(start_idx, end_idx):
        player_list_idx = draft_state['draft_order_player_indices'][i]
        p_name_from_slot = "Unknown"
        for p_id_slot, p_name_slot in draft_state['players']:
            if draft_state['players'].index((p_id_slot, p_name_slot)) == player_list_idx:
                p_name_from_slot = p_name_slot
                break

        if i == current_index:
            pick_order_display.append(f"**> {p_name_from_slot} <**")
        else:
            pick_order_display.append(p_name_from_slot)

    if end_idx < len(draft_state['draft_order_player_indices']):
        pick_order_display.append("...")

    return " -> ".join(pick_order_display)


def get_player_draft_summary(draft_state: Dict[str, Any], player_id: int) -> tuple[int, List[str]]:
    """Get a summary of a player's drafted items."""
    player_draft = draft_state['drafted_items_by_player'].get(player_id, {})
    total_items = 0
    category_lines = []

    for category_name in draft_state['categories_order']:
        items_in_category = player_draft.get(category_name, [])
        if items_in_category:
            category_lines.append(
                f"**{category_name}**: {', '.join(items_in_category)} ({len(items_in_category)})")
            total_items += len(items_in_category)

    return total_items, category_lines
