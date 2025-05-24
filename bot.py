# bot.py
import discord
from discord.ext import commands
from discord import app_commands
import typing
import os
from dotenv import load_dotenv
import database
import utils

# Load environment variables
load_dotenv()

# Get environment variables
BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
DATABASE_NAME = os.getenv('DATABASE_NAME', 'draft_bot.db')

# --- Bot Configuration ---
MIN_PLAYERS = 2
MAX_PLAYERS = 4
VIEW_TIMEOUT_SECONDS = 300

# --- Intents ---
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.members = True

# Bot setup
bot = commands.Bot(command_prefix=commands.when_mentioned_or(
    "!unusedprefix!"), intents=intents)

# --- Helper Functions ---


def generate_global_draft_order(num_players: int, total_picks_allotted_per_player: int) -> list[int]:
    """Generate the global draft order based on number of players and picks."""
    order_indices = []
    for i in range(total_picks_allotted_per_player):
        current_round_order = list(range(num_players))
        if i % 2 == 1:
            current_round_order.reverse()
        order_indices.extend(current_round_order)
    return order_indices

# --- UI Views ---


class DraftPickView(discord.ui.View):
    def __init__(self, current_player_id: int, draft_id: str):
        super().__init__(timeout=VIEW_TIMEOUT_SECONDS)
        self.current_player_id = current_player_id
        self.draft_id = draft_id

        current_draft_state = database.get_draft_state(
            DATABASE_NAME, self.draft_id)
        if not current_draft_state or not current_draft_state['status'] == 'active':
            for item_ui in self.children:
                item_ui.disabled = True
            print(
                f"Warning: DraftPickView created for inactive/non-existent draft_id {self.draft_id}")
            return

        current_player_name = database.get_player_name_by_id(
            DATABASE_NAME, self.draft_id, self.current_player_id) or "Player"

        player_picks_by_category = {}
        if self.current_player_id in current_draft_state['drafted_items_by_player']:
            player_picks_by_category = {
                cat: len(items) for cat, items in current_draft_state['drafted_items_by_player'][self.current_player_id].items()
            }

        picks_allowed_limit = current_draft_state['picks_allowed_per_player_per_category']
        self._setup_category_selects(
            current_draft_state, player_picks_by_category, picks_allowed_limit, current_player_name)

    def _setup_category_selects(self, draft_state, player_picks_by_category, picks_allowed_limit, current_player_name):
        """Setup the category selection dropdowns."""
        select_count = 0
        for category_name in draft_state['categories_order']:
            items_in_category_master = draft_state['master_item_list'].get(
                category_name, [])
            num_picked_from_this_cat = player_picks_by_category.get(
                category_name, 0)
            can_pick_from_this_cat = num_picked_from_this_cat < picks_allowed_limit

            if items_in_category_master and can_pick_from_this_cat and select_count < 5:
                options = []
                for item_master in items_in_category_master:
                    if item_master in draft_state['available_items'].get(category_name, []):
                        options.append(discord.SelectOption(
                            label=item_master, value=f"{category_name}|{item_master}"))

                if not options:
                    continue

                select = discord.ui.Select(
                    placeholder=f"Pick from {category_name} ({picks_allowed_limit - num_picked_from_this_cat} left for {current_player_name})",
                    options=options[:25],
                    custom_id=f"pick_select_{self.draft_id}_{category_name.replace(' ', '_')}_{select_count}"
                )
                select.callback = self.select_callback
                self.add_item(select)
                select_count += 1
            elif select_count >= 5 and items_in_category_master and can_pick_from_this_cat:
                print(
                    f"Warning: Draft {self.draft_id} - More than 5 eligible categories for player {self.current_player_id}, only showing first 5.")
                break

        if select_count == 0:
            print(
                f"Info: DraftPickView for player {self.current_player_id}, draft {self.draft_id} has no eligible pick options.")

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Check if the interaction is valid."""
        current_draft_state = database.get_draft_state(
            DATABASE_NAME, self.draft_id)
        if not current_draft_state or not current_draft_state['status'] == 'active':
            await interaction.response.send_message("This draft is not active or has been reset.", ephemeral=True)
            for item_ui in self.children:
                item_ui.disabled = True
            if not interaction.response.is_done():
                await interaction.edit_original_response(view=self)
            else:
                try:
                    await interaction.edit_original_response(view=self)
                except:
                    pass
            return False
        if interaction.user.id != self.current_player_id:
            await interaction.response.send_message("It's not your turn to pick for this draft!", ephemeral=True)
            return False
        return True

    async def select_callback(self, interaction: discord.Interaction):
        """Handle the selection of an item."""
        selected_value = interaction.data['values'][0]
        category_name, item_name_actual = selected_value.split('|', 1)

        current_draft_state = database.get_draft_state(
            DATABASE_NAME, self.draft_id)
        if not current_draft_state or not current_draft_state['status'] == 'active':
            await interaction.response.send_message("This draft became inactive.", ephemeral=True)
            return

        if not await self._validate_pick(current_draft_state, category_name, item_name_actual, interaction):
            return

        if not await self._record_pick(category_name, item_name_actual, interaction):
            return

        await self._handle_post_pick(interaction, current_draft_state)

    async def _validate_pick(self, draft_state, category_name, item_name, interaction):
        """Validate if the pick is allowed."""
        player_drafted_items = draft_state['drafted_items_by_player'].get(
            self.current_player_id, {})
        num_picked_from_cat = len(player_drafted_items.get(category_name, []))

        if num_picked_from_cat >= draft_state['picks_allowed_per_player_per_category']:
            await interaction.response.send_message(
                f"You have already picked the maximum items from {category_name} for draft {self.draft_id}.",
                ephemeral=True
            )
            return False

        if item_name not in draft_state['available_items'].get(category_name, []):
            await interaction.response.send_message(
                f"Error: Item '{item_name}' is no longer available. The board may have updated.",
                ephemeral=True
            )
            new_view = DraftPickView(
                current_player_id=self.current_player_id, draft_id=self.draft_id)
            if not interaction.response.is_done():
                await interaction.response.edit_message(view=new_view)
            else:
                try:
                    await interaction.edit_original_response(view=new_view)
                except:
                    pass
            return False

        return True

    async def _record_pick(self, category_name, item_name, interaction):
        """Record the pick in the database."""
        pick_successful = database.record_pick(
            DATABASE_NAME, self.draft_id, self.current_player_id, category_name, item_name)

        if not pick_successful:
            await interaction.response.send_message(
                "Failed to record your pick due to a database error. Please try again or contact an admin.",
                ephemeral=True
            )
            return False

        for child in self.children:
            child.disabled = True
        if not interaction.response.is_done():
            await interaction.response.edit_message(view=self)
        else:
            try:
                await interaction.edit_original_response(view=self)
            except discord.HTTPException as e:
                print(
                    f"Error editing original response in select_callback: {e}")

        await interaction.followup.send(
            f"✅ {interaction.user.display_name} picked **{item_name}** from {category_name} (Draft ID: {self.draft_id})!",
            ephemeral=False
        )
        return True

    async def _handle_post_pick(self, interaction, current_draft_state):
        """Handle post-pick actions."""
        updated_draft_state = database.get_draft_state(
            DATABASE_NAME, self.draft_id)
        if not updated_draft_state:
            return

        if updated_draft_state['current_pick_global_index'] >= updated_draft_state['total_picks_to_make']:
            database.update_draft_status(
                DATABASE_NAME, self.draft_id, 'completed')
            await interaction.channel.send(
                f"🎉🎉 All picks for Draft ID: **{self.draft_id}** have been made! The draft is complete! 🎉🎉"
            )
            await update_draft_message(draft_id=self.draft_id, final_update=True)
            await _draft_status_logic(interaction, self.draft_id, ephemeral_response=False)
        else:
            await update_draft_message(draft_id=self.draft_id)

    async def on_timeout(self):
        """Handle view timeout."""
        current_draft_state = database.get_draft_state(
            DATABASE_NAME, self.draft_id)
        if current_draft_state and current_draft_state['status'] == 'active' and current_draft_state.get('board_message_id'):
            channel = bot.get_channel(current_draft_state['channel_id'])
            if channel:
                try:
                    for item_ui_timeout in self.children:
                        item_ui_timeout.disabled = True

                    msg = await channel.fetch_message(current_draft_state['board_message_id'])
                    player_slot_index = current_draft_state['draft_order_player_indices'][
                        current_draft_state['current_pick_global_index']]

                    current_player_id = None
                    current_player_name = "Player"
                    for p_id, p_name in current_draft_state['players']:
                        if current_draft_state['players'].index((p_id, p_name)) == player_slot_index:
                            current_player_id = p_id
                            current_player_name = p_name
                            break

                    timeout_content = f"⏰ {current_player_name}'s pick timed out for Draft ID: {self.draft_id}! (View disabled)"
                    database.update_last_event_message(
                        DATABASE_NAME, self.draft_id, timeout_content)

                    await msg.edit(content=timeout_content, embed=msg.embeds[0] if msg.embeds else None, view=self)
                except Exception as e:
                    print(
                        f"Error during on_timeout for draft {self.draft_id}: {e}")
        self.stop()


async def update_draft_message(draft_id: str, final_update: bool = False):
    """Update the draft board message."""
    current_draft_state = database.get_draft_state(DATABASE_NAME, draft_id)
    if not current_draft_state:
        print(
            f"update_draft_message called for non-existent draft_id {draft_id}.")
        return

    channel_id = current_draft_state['channel_id']
    guild_id = current_draft_state['guild_id']
    guild = bot.get_guild(guild_id)
    if not guild:
        print(f"Error: Could not find guild {guild_id} for draft {draft_id}.")
        return

    message_content_override = None
    if current_draft_state.get('last_event_message') and not final_update:
        message_content_override = current_draft_state['last_event_message']
    else:
        database.update_last_event_message(DATABASE_NAME, draft_id, None)

    if current_draft_state['status'] != 'active' and not final_update:
        return

    title, description = utils.format_draft_status(current_draft_state, guild)
    embed = utils.create_draft_embed(title, description)

    # Add category fields
    for category_name in current_draft_state['categories_order']:
        master_list = current_draft_state['master_item_list'].get(
            category_name, [])
        available_items = current_draft_state['available_items'].get(
            category_name, [])
        field_name, field_value = utils.format_category_field(
            category_name, master_list, available_items)
        embed.add_field(name=field_name, value=field_value, inline=False)

    # Add pick order if active
    if current_draft_state['status'] == 'active' and not final_update and current_draft_state['draft_order_player_indices']:
        pick_order = utils.format_pick_order(
            current_draft_state, current_draft_state['current_pick_global_index'])
        embed.add_field(
            name=f"🐍 Global Pick Order (Turn {current_draft_state['current_pick_global_index'] + 1})",
            value=pick_order,
            inline=False
        )

    embed.set_footer(
        text=f"Draft ID: {draft_id} | Global Draft with Per-Category Limits")

    # Create view for current player if active
    view_to_send = None
    if current_draft_state['status'] == 'active' and not final_update:
        player_slot_index = current_draft_state['draft_order_player_indices'][
            current_draft_state['current_pick_global_index']]
        current_player_id = None
        for p_id, _ in current_draft_state['players']:
            if current_draft_state['players'].index((p_id, _)) == player_slot_index:
                current_player_id = p_id
                break
        if current_player_id:
            view_to_send = DraftPickView(
                current_player_id=current_player_id, draft_id=draft_id)

    # Update or send message
    channel = bot.get_channel(channel_id)
    if not channel:
        return

    target_message_id = current_draft_state.get('board_message_id')
    try:
        if target_message_id:
            message = await channel.fetch_message(target_message_id)
            await message.edit(content=message_content_override, embed=embed, view=view_to_send)
        else:
            msg = await channel.send(content=message_content_override, embed=embed, view=view_to_send)
            database.update_board_message_id(DATABASE_NAME, draft_id, msg.id)
    except discord.NotFound:
        msg = await channel.send(content=message_content_override, embed=embed, view=view_to_send)
        database.update_board_message_id(DATABASE_NAME, draft_id, msg.id)
    except discord.Forbidden:
        print(f"Error: Bot lacks permissions in channel {channel.id}")
    except Exception as e:
        print(
            f"Error updating/sending draft board message for draft {draft_id}: {e}")

# --- Bot Events ---


@bot.event
async def on_ready():
    """Handle bot ready event."""
    database.initialize_database(DATABASE_NAME)
    print(f'{bot.user.name} has connected to Discord!')
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands.")
    except Exception as e:
        print(f"Failed to sync commands: {e}")
    print("Bot ready.")

# --- Slash Commands ---


@bot.tree.command(name="startdraft", description="Starts a new item draft in this channel.")
@app_commands.describe(
    player1="First player.", player2="Second player.",
    player3="Third player (optional).", player4="Fourth player (optional)."
)
async def start_draft_slash(interaction: discord.Interaction,
                            player1: discord.Member, player2: discord.Member,
                            player3: typing.Optional[discord.Member] = None,
                            player4: typing.Optional[discord.Member] = None):
    """Start a new draft."""
    players_members = [p for p in [
        player1, player2, player3, player4] if p is not None]

    num_actual_players = len(players_members)
    if not (MIN_PLAYERS <= num_actual_players <= MAX_PLAYERS):
        await interaction.response.send_message(
            f"Please provide between {MIN_PLAYERS} and {MAX_PLAYERS} unique players.",
            ephemeral=True
        )
        return

    unique_player_ids = set()
    players_info_for_db = []
    for p_member in players_members:
        if p_member.id not in unique_player_ids:
            unique_player_ids.add(p_member.id)
            players_info_for_db.append((p_member.id, p_member.display_name))
        else:
            await interaction.response.send_message(
                f"Player {p_member.mention} was mentioned more than once. Please use unique players.",
                ephemeral=True
            )
            return

    picks_allowed_per_cat = 2 if num_actual_players == 2 else 1
    num_categories = len(database.INITIAL_ITEMS_BY_CATEGORY)
    total_picks_allotted_player = picks_allowed_per_cat * num_categories

    draft_order_indices = generate_global_draft_order(
        num_actual_players, total_picks_allotted_player)
    total_picks_overall = len(draft_order_indices)

    # Send initial message and get its link
    player_names_str = ", ".join([name for _, name in players_info_for_db])
    start_message = (
        f"🎉 New Draft Started by {interaction.user.mention} with players: {player_names_str}!\n"
        f"**Rules:** {picks_allowed_per_cat} pick(s) per category per player. Total {total_picks_allotted_player} picks per player.\n"
        f"Total picks in draft: {total_picks_overall}."
    )

    await interaction.response.send_message(start_message, ephemeral=False)
    message = await interaction.original_response()
    message_link = message.jump_url

    draft_id = database.create_draft(
        DATABASE_NAME, interaction.guild_id, interaction.channel_id, interaction.user.id,
        players_info_for_db, picks_allowed_per_cat, total_picks_allotted_player,
        draft_order_indices, total_picks_overall, message_link
    )

    if not draft_id:
        await interaction.followup.send(
            "Failed to create the draft due to a database error.",
            ephemeral=True
        )
        return

    # Update the message with the draft ID
    await message.edit(content=start_message + f"\n**Draft ID: `{draft_id}`** (Use this ID for other commands like `/draftboard`, `/mydraft`)")
    await update_draft_message(draft_id=draft_id)


@bot.tree.command(name="listdrafts", description="Lists active drafts in this channel.")
async def listdrafts_slash(interaction: discord.Interaction):
    """List active drafts in the current channel."""
    active_drafts = database.get_active_drafts_in_channel(
        DATABASE_NAME, interaction.channel_id)
    if not active_drafts:
        await interaction.response.send_message("No active drafts in this channel.", ephemeral=True)
        return

    embed = utils.create_draft_embed(
        title=f"Active Drafts in #{interaction.channel.name}",
        description=f"Found {len(active_drafts)} active draft(s) in this channel.",
        color=discord.Color.blurple()
    )

    for draft in active_drafts:
        admin_user = await bot.fetch_user(draft['admin_user_id'])
        admin_name = admin_user.name if admin_user else "Unknown Admin"
        embed.add_field(
            name=f"Draft ID: `{draft['draft_id']}`",
            value=f"Started by: {admin_name}\nPlayers: {draft['num_players']}\nCreated: <t:{draft['created_at_utc']}:R>",
            inline=False
        )
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="draftboard", description="Shows the draft board for a specific draft.")
@app_commands.describe(draft_id="The ID of the draft to display.")
async def draftboard_slash(interaction: discord.Interaction, draft_id: str):
    """Show the draft board for a specific draft."""
    current_draft_state = database.get_draft_state(
        DATABASE_NAME, draft_id.strip())
    if not current_draft_state or current_draft_state['channel_id'] != interaction.channel_id:
        await interaction.response.send_message(
            f"Draft ID `{draft_id}` not found or not active in this channel.",
            ephemeral=True
        )
        return

    database.update_last_event_message(DATABASE_NAME, draft_id, None)
    await interaction.response.defer(ephemeral=True, thinking=True)
    await update_draft_message(draft_id=draft_id)

    # Add link to original message if available
    followup_message = f"Draft board for `{draft_id}` refreshed/shown."
    if current_draft_state.get('message_link'):
        followup_message += f"\n[Jump to Original Draft]({current_draft_state['message_link']})"

    await interaction.followup.send(followup_message, ephemeral=True)


@bot.tree.command(name="mydraft", description="Shows items you drafted for a specific draft.")
@app_commands.describe(draft_id="The ID of the draft.")
async def mydraft_slash(interaction: discord.Interaction, draft_id: str):
    """Show items drafted by the user for a specific draft."""
    draft_id = draft_id.strip()
    current_draft_state = database.get_draft_state(DATABASE_NAME, draft_id)

    if not current_draft_state or current_draft_state['channel_id'] != interaction.channel_id:
        await interaction.response.send_message(
            f"Draft ID `{draft_id}` not found in this channel.",
            ephemeral=True
        )
        return

    player_draft = current_draft_state['drafted_items_by_player'].get(
        interaction.user.id)
    if not player_draft:
        await interaction.response.send_message(
            f"You haven't drafted any items in draft `{draft_id}` or are not part of it.",
            ephemeral=True
        )
        return

    embed = utils.create_draft_embed(
        title=f"📜 Your Drafted Items - {interaction.user.display_name} (Draft ID: {draft_id})",
        color=discord.Color.green()
    )

    total_items, category_lines = utils.get_player_draft_summary(
        current_draft_state, interaction.user.id)

    desc_lines = [
        f"Per-category pick limit: {current_draft_state.get('picks_allowed_per_player_per_category', 'N/A')}"]
    if total_items == 0:
        desc_lines.append("You haven't picked any items yet.")
    else:
        desc_lines.insert(
            0, f"Total items drafted: {total_items} / {current_draft_state.get('total_picks_allotted_per_player', 'N/A')}")

    embed.description = "\n".join(desc_lines)

    for category_name in current_draft_state['categories_order']:
        items_in_category = player_draft.get(category_name, [])
        if items_in_category:
            embed.add_field(
                name=f"🎁 {category_name} ({len(items_in_category)} picked)",
                value=", ".join(items_in_category),
                inline=False
            )

    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="draftstatus", description="Shows all items drafted by players for a specific draft.")
@app_commands.describe(draft_id="The ID of the draft.")
async def _draft_status_logic(interaction: discord.Interaction, draft_id: str, ephemeral_response: bool = False):
    """Show the status of a specific draft."""
    draft_id = draft_id.strip()
    current_draft_state = database.get_draft_state(DATABASE_NAME, draft_id)

    if not current_draft_state or current_draft_state['channel_id'] != interaction.channel_id:
        await interaction.response.send_message(
            f"Draft ID `{draft_id}` not found or not in this channel.",
            ephemeral=True
        )
        return

    embed = utils.create_draft_embed(
        title=f"� Full Draft Status (Draft ID: {draft_id})",
        color=discord.Color.gold()
    )

    embed.description = (
        f"Rules: {current_draft_state.get('picks_allowed_per_player_per_category', 'N/A')} pick(s)/category/player. "
        f"Total: {current_draft_state.get('total_picks_allotted_per_player', 'N/A')} picks/player."
    )

    for p_user_id, p_display_name in current_draft_state['players']:
        total_items, category_lines = utils.get_player_draft_summary(
            current_draft_state, p_user_id)
        value_text = "\n".join(
            category_lines) if category_lines else "No items drafted yet."
        embed.add_field(
            name=f"{p_display_name} ({total_items} / {current_draft_state.get('total_picks_allotted_per_player', 'N/A')})",
            value=value_text,
            inline=False
        )

    if not embed.fields:
        embed.description += "\nNo items drafted by anyone yet."

    if interaction.response.is_done():
        await interaction.followup.send(embed=embed, ephemeral=ephemeral_response)
    else:
        await interaction.response.send_message(embed=embed, ephemeral=ephemeral_response)


@bot.tree.command(name="resetdraft", description="Resets/cancels a specific draft in this channel (starter only).")
@app_commands.describe(draft_id="The ID of the draft to reset.")
async def resetdraft_slash(interaction: discord.Interaction, draft_id: str):
    """Reset a specific draft."""
    draft_id = draft_id.strip()
    current_draft_state = database.get_draft_state(DATABASE_NAME, draft_id)

    if not current_draft_state or current_draft_state['channel_id'] != interaction.channel_id:
        await interaction.response.send_message(
            f"Draft ID `{draft_id}` not found or not active in this channel.",
            ephemeral=True
        )
        return

    if current_draft_state['status'] != 'active':
        await interaction.response.send_message(
            f"Draft `{draft_id}` is not active and cannot be reset.",
            ephemeral=True
        )
        return

    if interaction.user.id != current_draft_state.get('admin_user_id'):
        admin_member = await bot.fetch_user(current_draft_state.get('admin_user_id'))
        starter_name = admin_member.mention if admin_member else "The original starter"
        await interaction.response.send_message(
            f"Only {starter_name} can reset draft `{draft_id}`.",
            ephemeral=True
        )
        return

    board_message_id = current_draft_state.get('board_message_id')

    if database.update_draft_status(DATABASE_NAME, draft_id, 'reset'):
        await interaction.response.send_message(
            f"Draft ID `{draft_id}` has been reset by {interaction.user.mention}.",
            ephemeral=False
        )
        if board_message_id:
            channel = bot.get_channel(current_draft_state['channel_id'])
            if channel:
                try:
                    message = await channel.fetch_message(board_message_id)
                    await message.edit(content=f"*Draft ID `{draft_id}` has been reset.*", embed=None, view=None)
                except Exception as e:
                    print(
                        f"Error clearing board message for reset draft {draft_id}: {e}")
    else:
        await interaction.response.send_message(
            f"Failed to reset draft `{draft_id}` due to a database error.",
            ephemeral=True
        )


@bot.tree.command(name="recentdrafts", description="Shows your recent draft history.")
async def recentdrafts_slash(interaction: discord.Interaction):
    """Show the user's recent draft history."""
    recent_drafts = database.get_user_recent_drafts(
        DATABASE_NAME, interaction.user.id)

    if not recent_drafts:
        await interaction.response.send_message(
            "You haven't participated in any drafts yet.",
            ephemeral=True
        )
        return

    embed = utils.create_draft_embed(
        title=f"📜 Your Recent Drafts - {interaction.user.display_name}",
        description=f"Showing your {len(recent_drafts)} most recent drafts:",
        color=discord.Color.blue()
    )

    for draft in recent_drafts:
        # Get the channel name if possible
        channel = bot.get_channel(draft['channel_id'])
        channel_name = f"#{channel.name}" if channel else f"Channel {draft['channel_id']}"

        # Get admin name
        admin_user = await bot.fetch_user(draft['admin_user_id'])
        admin_name = admin_user.name if admin_user else "Unknown Admin"

        # Format the draft info
        status_emoji = {
            'active': '🟢',
            'completed': '✅',
            'reset': '🔄'
        }.get(draft['status'], '❓')

        value_lines = [
            f"Status: {status_emoji} {draft['status'].capitalize()}",
            f"Started by: {admin_name}",
            f"Channel: {channel_name}",
            f"Players: {draft['num_players']}",
            f"Created: <t:{draft['created_at_utc']}:R>"
        ]

        # Add message link if available
        if draft.get('message_link'):
            value_lines.append(f"[Jump to Draft]({draft['message_link']})")

        embed.add_field(
            name=f"Draft ID: `{draft['draft_id']}`",
            value="\n".join(value_lines),
            inline=False
        )

    await interaction.response.send_message(embed=embed, ephemeral=True)

# --- Run the Bot ---
if __name__ == "__main__":
    if not BOT_TOKEN:
        print("CRITICAL ERROR: DISCORD_BOT_TOKEN environment variable is not set.")
    else:
        try:
            database.initialize_database(DATABASE_NAME)
            bot.run(BOT_TOKEN)
        except discord.LoginFailure:
            print("Login Failure: Invalid bot token.")
        except Exception as e:
            print(f"Bot run error: {e}")
