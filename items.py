from typing import List, Dict, Any, Callable, Optional
import random


class DraftItem:
    def __init__(self, pretty_name: str, description: str, image: str, datapack_modifier: Callable[[str], str]):
        self.pretty_name = pretty_name
        self.description = description
        self.image = image
        self.datapack_modifier = datapack_modifier
        self.file_query = None
        self.simple_name = pretty_name
        self.box_name = pretty_name
        self.small_name = None
        self.id = len(all_items) + 1
        all_items.append(self)

    def set_from(self, item: 'DraftItem', pool: str):
        self.pool = pool
        self.simple_name = item.simple_name
        self.box_name = item.box_name
        self.file_query = item.file_query
        self.small_name = item.small_name


def item_giver(*args) -> Callable[[str], str]:
    """Create a datapack modifier that gives items."""
    def modifier(file: str) -> str:
        for i in range(0, len(args), 2):
            if i + 1 < len(args) and isinstance(args[i + 1], int):
                file += f"\ngive @a minecraft:{args[i]} {args[i + 1]}\n"
            else:
                file += f"\ngive @a minecraft:{args[i]}\n"
        return file
    return modifier


# Initialize the all_items list
all_items: List[DraftItem] = []

# Pool: Biomes
d_mesa = DraftItem("Mesa", "Gives all mesa biomes and cave spider kill", "mesa.png",
                   lambda file: file + """
advancement grant @a only minecraft:adventure/adventuring_time minecraft:badlands
advancement grant @a only minecraft:adventure/adventuring_time minecraft:badlands_plateau
advancement grant @a only minecraft:adventure/adventuring_time minecraft:wooded_badlands_plateau
advancement grant @a only minecraft:adventure/kill_all_mobs minecraft:cave_spider
""")

d_jungle = DraftItem("Jungle", "Gives jungle biomes, cookie, melon, panda, & ocelot", "jungle.png",
                     lambda file: file + """
advancement grant @a only minecraft:adventure/adventuring_time minecraft:bamboo_jungle
advancement grant @a only minecraft:adventure/adventuring_time minecraft:bamboo_jungle_hills
advancement grant @a only minecraft:adventure/adventuring_time minecraft:jungle_hills
advancement grant @a only minecraft:adventure/adventuring_time minecraft:jungle_edge
advancement grant @a only minecraft:adventure/adventuring_time minecraft:jungle
advancement grant @a only minecraft:husbandry/bred_all_animals minecraft:panda
advancement grant @a only minecraft:husbandry/bred_all_animals minecraft:ocelot
advancement grant @a only minecraft:husbandry/balanced_diet melon_slice
advancement grant @a only minecraft:husbandry/balanced_diet cookie
""")

d_snowy = DraftItem("Snowy", "Gives all snowy biomes, stray kill, & zd", "snowy.png",
                    lambda file: file + """
advancement grant @a only minecraft:adventure/adventuring_time minecraft:snowy_tundra
advancement grant @a only minecraft:adventure/adventuring_time minecraft:snowy_taiga
advancement grant @a only minecraft:adventure/adventuring_time minecraft:snowy_taiga_hills
advancement grant @a only minecraft:adventure/adventuring_time minecraft:snowy_mountains
advancement grant @a only minecraft:adventure/adventuring_time minecraft:snowy_beach
advancement grant @a only minecraft:adventure/adventuring_time minecraft:frozen_river
advancement grant @a only minecraft:adventure/kill_all_mobs minecraft:stray
advancement grant @a only minecraft:story/cure_zombie_villager
""")

d_mega_taiga = DraftItem("Mega Taiga", "Gives all mega taiga biomes, sweet berry eat, and fox breed", "taiga.png",
                         lambda file: file + """
advancement grant @a only minecraft:adventure/adventuring_time minecraft:giant_tree_taiga
advancement grant @a only minecraft:adventure/adventuring_time minecraft:giant_tree_taiga_hills
advancement grant @a only minecraft:husbandry/balanced_diet sweet_berries
advancement grant @a only minecraft:husbandry/bred_all_animals minecraft:fox
""")

d_mushroom_island = DraftItem("Mushroom Island", "Gives all mushroom biomes and mooshroom breed", "mooshroom.png",
                              lambda file: file + """
advancement grant @a only minecraft:adventure/adventuring_time minecraft:mushroom_fields
advancement grant @a only minecraft:adventure/adventuring_time minecraft:mushroom_field_shore
advancement grant @a only minecraft:husbandry/bred_all_animals minecraft:mooshroom
""")
d_mushroom_island.simple_name = "Mushroom"
d_mushroom_island.box_name = "Mushroom"

# Pool: Armour
d_helmet = DraftItem("Helmet", "Gives fully enchanted diamond helmet", "helmet.png",
                     lambda file: file + """
give @a minecraft:diamond_helmet{Enchantments:[{id:"minecraft:protection",lvl:5},{id:"minecraft:unbreaking",lvl:3},{id:"minecraft:respiration",lvl:3},{id:"minecraft:aqua_affinity",lvl:1}]}
""")

d_chestplate = DraftItem("Chestplate", "Gives fully enchanted diamond chestplate", "chestplate.png",
                         lambda file: file + """
give @a minecraft:diamond_chestplate{Enchantments:[{id:"minecraft:protection",lvl:5},{id:"minecraft:unbreaking",lvl:3}]}
""")

d_leggings = DraftItem("Leggings", "Gives fully enchanted diamond leggings", "leggings.png",
                       lambda file: file + """
give @a minecraft:diamond_leggings{Enchantments:[{id:"minecraft:protection",lvl:5},{id:"minecraft:unbreaking",lvl:3}]}
""")

d_boots = DraftItem("Boots", "Gives fully enchanted diamond boots", "boots.png",
                    lambda file: file + """
give @a minecraft:diamond_boots{Enchantments:[{id:"minecraft:protection",lvl:5},{id:"minecraft:unbreaking",lvl:3},{id:"minecraft:depth_strider",lvl:3}]}
""")

d_bucket = DraftItem("Bucket", "Gives a fully enchanted, max-tier bucket", "bucket.png",
                     lambda file: file + """
give @a minecraft:bucket{Enchantments:[{}]}
""")

# Pool: Tools
d_sword = DraftItem("Sword", "Gives fully enchanted diamond sword", "sword.png",
                    lambda file: file + """
give @a minecraft:diamond_sword{Enchantments:[{id:"minecraft:smite",lvl:5},{id:"minecraft:looting",lvl:3},{id:"minecraft:unbreaking",lvl:3}]}
""")

d_pickaxe = DraftItem("Pickaxe", "Gives fully enchanted diamond pickaxe", "pickaxe.png",
                      lambda file: file + """
give @a minecraft:diamond_pickaxe{Enchantments:[{id:"minecraft:efficiency",lvl:5},{id:"minecraft:fortune",lvl:3},{id:"minecraft:unbreaking",lvl:3}]}
""")

d_shovel = DraftItem("Shovel", "Gives fully enchanted diamond shovel", "shovel.png",
                     lambda file: file + """
give @a minecraft:diamond_shovel{Enchantments:[{id:"minecraft:efficiency",lvl:5},{id:"minecraft:fortune",lvl:3},{id:"minecraft:unbreaking",lvl:3}]}
""")

d_hoe = DraftItem("Hoe", "Gives fully enchanted netherite hoe", "hoe.png",
                  lambda file: file + """
give @a minecraft:netherite_hoe{Enchantments:[{id:"minecraft:efficiency",lvl:5},{id:"minecraft:silk_touch",lvl:1},{id:"minecraft:unbreaking",lvl:3}]}
""")

d_axe = DraftItem("Axe", "Gives fully enchanted diamond axe", "axe.png",
                  lambda file: file + """
give @a minecraft:diamond_axe{Enchantments:[{id:"minecraft:efficiency",lvl:5},{id:"minecraft:silk_touch",lvl:1},{id:"minecraft:unbreaking",lvl:3}]}
""")

d_trident = DraftItem("Trident", "Gives fully enchanted netherite trident", "trident.png",
                      lambda file: file + """
give @a minecraft:trident{Enchantments:[{id:"minecraft:channeling",lvl:1},{id:"minecraft:loyalty",lvl:3},{id:"minecraft:impaling",lvl:5}]}
""")

# Pool: Big
d_acc = DraftItem("A Complete Catalogue", "Gives a complete catalogue", "acc.png",
                  lambda file: file + """
advancement grant @a only minecraft:husbandry/complete_catalogue
""")
d_acc.box_name = "Catalogue"

d_at = DraftItem("Adventuring Time", "Gives adventuring time", "at.png",
                 lambda file: file + """
advancement grant @a only minecraft:adventure/adventuring_time
""")
d_at.box_name = "Adventuring"
d_at.small_name = "AT"

d_2b2 = DraftItem("Two by Two", "Gives two by two", "2b2.png",
                  lambda file: file + """
advancement grant @a only minecraft:husbandry/bred_all_animals
""")

d_mh = DraftItem("Monsters Hunted", "Gives monsters hunted", "mh.png",
                 lambda file: file + """
advancement grant @a only minecraft:adventure/kill_all_mobs
""")
d_mh.box_name = "Monsters"

d_abd = DraftItem("A Balanced Diet", "Gives a balanced diet", "abd.png",
                  lambda file: file + """
advancement grant @a only minecraft:husbandry/balanced_diet
""")
d_abd.box_name = "Balanced Diet"
d_abd.small_name = "Balanced"

# Pool: Collectors
d_netherite = DraftItem("Netherite", "Gives 4 netherite ingots", "netherite.png",
                        item_giver("netherite_ingot", 4))

d_shells = DraftItem("Shells", "Gives 7 nautilus shells", "shell.png",
                     item_giver("nautilus_shell", 7))

d_skulls = DraftItem("Skulls", "Gives 2 wither skeleton skulls", "skull.png",
                     item_giver("wither_skeleton_skull", 2))

d_breeds = DraftItem("Breeds", "Gives breed for horse, donkey, mule, llama, wolf, fox, & turtle", "breeds.png",
                     lambda file: file + """
advancement grant @a only minecraft:husbandry/bred_all_animals minecraft:horse
advancement grant @a only minecraft:husbandry/bred_all_animals minecraft:donkey
advancement grant @a only minecraft:husbandry/bred_all_animals minecraft:mule
advancement grant @a only minecraft:husbandry/bred_all_animals minecraft:llama
advancement grant @a only minecraft:husbandry/bred_all_animals minecraft:wolf
advancement grant @a only minecraft:husbandry/bred_all_animals minecraft:fox
advancement grant @a only minecraft:husbandry/bred_all_animals minecraft:turtle
""")

d_shulker = DraftItem("Shulker Box", "Gives a shulker box", "shulker.png",
                      item_giver("shulker_box"))
d_shulker.small_name = "Box"

d_bees = DraftItem("Bees", "Gives all bee-related requirements", "bees.png",
                   lambda file: file + """
advancement grant @a only minecraft:husbandry/safely_harvest_honey
advancement grant @a only minecraft:husbandry/silk_touch_nest
advancement grant @a only minecraft:adventure/honey_block_slide
advancement grant @a only minecraft:husbandry/bred_all_animals minecraft:bee
advancement grant @a only minecraft:husbandry/balanced_diet honey_bottle
""")

d_hives = DraftItem("Hives", "Gives the user two 3-bee hives", "hive.png",
                    item_giver('bee_nest{BlockEntityTag:{Bees:[{MinOccupationTicks:600,TicksInHive:500,EntityData:{Brain:{memories:{}},HurtByTimestamp:0,HasStung:0b,Attributes:[],Invulnerable:0b,FallFlying:0b,ForcedAge:0,PortalCooldown:0,AbsorptionAmount:0.0f,FallDistance:0.0f,InLove:0,DeathTime:0s,HandDropChances:[0.085f,0.085f],CannotEnterHiveTicks:0,PersistenceRequired:0b,id:"minecraft:bee",Age:0,TicksSincePollination:0,AngerTime:0,Motion:[0.0d,0.0d,0.0d],Health:10.0f,HasNectar:0b,LeftHanded:0b,Air:300s,OnGround:0b,Rotation:[1.2499212f,0.0f],HandItems:[{},{}],ArmorDropChances:[0.085f,0.085f,0.085f,0.085f],Pos:[0.0d,0.0d,0.0d],Fire:-1s,ArmorItems:[{},{},{},{}],CropsGrownSincePollination:0,CanPickUpLoot:0b,HurtTime:0s}},{MinOccupationTicks:600,TicksInHive:500,EntityData:{Brain:{memories:{}},HurtByTimestamp:0,HasStung:0b,Attributes:[],Invulnerable:0b,FallFlying:0b,ForcedAge:0,PortalCooldown:0,AbsorptionAmount:0.0f,FallDistance:0.0f,InLove:0,DeathTime:0s,HandDropChances:[0.085f,0.085f],CannotEnterHiveTicks:0,PersistenceRequired:0b,id:"minecraft:bee",Age:0,TicksSincePollination:0,AngerTime:0,Motion:[0.0d,0.0d,0.0d],Health:10.0f,HasNectar:0b,LeftHanded:0b,Air:300s,OnGround:0b,Rotation:[1.2499212f,0.0f],HandItems:[{},{}],ArmorDropChances:[0.085f,0.085f,0.085f,0.085f],Pos:[0.0d,0.0d,0.0d],Fire:-1s,ArmorItems:[{},{},{},{}],CropsGrownSincePollination:0,CanPickUpLoot:0b,HurtTime:0s}},{MinOccupationTicks:600,TicksInHive:500,EntityData:{Brain:{memories:{}},HurtByTimestamp:0,HasStung:0b,Attributes:[],Invulnerable:0b,FallFlying:0b,ForcedAge:0,PortalCooldown:0,AbsorptionAmount:0.0f,FallDistance:0.0f,InLove:0,DeathTime:0s,HandDropChances:[0.085f,0.085f],CannotEnterHiveTicks:0,PersistenceRequired:0b,id:"minecraft:bee",Age:0,TicksSincePollination:0,AngerTime:0,Motion:[0.0d,0.0d,0.0d],Health:10.0f,HasNectar:0b,LeftHanded:0b,Air:300s,OnGround:0b,Rotation:[1.2499212f,0.0f],HandItems:[{},{}],ArmorDropChances:[0.085f,0.085f,0.085f,0.085f],Pos:[0.0d,0.0d,0.0d],Fire:-1s,ArmorItems:[{},{},{},{}],CropsGrownSincePollination:0,CanPickUpLoot:0b,HurtTime:0s}}]}}', 2))

# Pool: Misc
d_totem = DraftItem("Totem", "Gives totem of undying and evoker & vex kill credit", "skull.png",
                    lambda file: file + """
give @a minecraft:totem_of_undying
advancement grant @a only minecraft:adventure/kill_all_mobs minecraft:evoker
advancement grant @a only minecraft:adventure/kill_all_mobs minecraft:vex
""")

d_fireworks = DraftItem("Fireworks", "Gives 23 gunpowder / paper", "firework.png",
                        item_giver("gunpowder", 23, "paper", 23))

d_grace = DraftItem("Dolphin's Grace", "Gives dolphin's grace", "firework.png",
                    lambda file: file + """
effect give @a minecraft:dolphins_grace 3600
""")
d_grace.simple_name = "Grace"
d_grace.box_name = "Grace"
d_grace.file_query = "tick.mcfunction"

d_leads = DraftItem("Leads", "Gives 23 leads & slime kill", "leads.png",
                    lambda file: file + """
advancement grant @a only minecraft:adventure/kill_all_mobs minecraft:slime
give @a minecraft:lead 23
""")

d_fire_res = DraftItem("Fire Resistance", "Gives permanent fire resistance.", "fres.png",
                       lambda file: file + """
effect give @a minecraft:fire_resistance 3600
""")
d_fire_res.file_query = "tick.mcfunction"
d_fire_res.box_name = "Fire Res"
d_fire_res.simple_name = "Fire Res"

d_obi = DraftItem("Obsidian", "Gives 10 obsidian.", "obi.png",
                  item_giver("obsidian", 10))

d_logs = DraftItem("Logs", "Gives 64 oak logs.", "logs.png",
                   item_giver("acacia_log", 64))

d_eyes = DraftItem("Eyes", "Gives 2 eyes of ender.", "eyes.png",
                   item_giver("ender_eye", 2))

d_crossbow = DraftItem("Crossbow", "Gives a Piercing IV crossbow.", "crossbow.png",
                       item_giver('crossbow{Enchantments:[{id:"minecraft:piercing",lvl:4s}]}', 1))

SHULKER_COLOUR = random.randint(0, 16)
d_shulker_boat = DraftItem("Shulker", "Grants a boated shulker at your spawn location.", "shulker.png",
                           lambda file: file + f"""
execute at @a run summon minecraft:boat ~ ~2 ~ {{Passengers:[{{id:shulker,Color:{SHULKER_COLOUR}}}]}}
""")

d_rods = DraftItem("Rod Rates", "Blazes never drop 0 rods.", "blaze.png",
                   lambda file: file + """
{
  "type": "minecraft:entity",
  "pools": [
    {
      "rolls": 1,
      "entries": [
        {
          "type": "minecraft:item",
          "functions": [
            {
              "function": "minecraft:set_count",
              "count": {
                "min": 1.0,
                "max": 1.0,
                "type": "minecraft:uniform"
              }
            },
            {
              "function": "minecraft:looting_enchant",
              "count": {
                "min": 0.0,
                "max": 1.0
              }
            }
          ],
          "name": "minecraft:blaze_rod"
        }
      ],
      "conditions": [
        {
          "condition": "minecraft:killed_by_player"
        }
      ]
    }
  ]
}
""")
d_rods.small_name = "Rods"
d_rods.file_query = "draaftpack/data/minecraft/loot_tables/entities/blaze.json"

# Create pools
p_armour = ["armour", "Armour", [
    d_helmet, d_chestplate, d_leggings, d_boots, d_bucket]]
p_tools = ["tools", "Tools", [
    d_sword, d_pickaxe, d_shovel, d_hoe, d_axe, d_trident]]
p_biomes = ["biomes", "Biomes", [d_mesa, d_jungle,
                                 d_snowy, d_mega_taiga, d_mushroom_island]]
p_collectors = ["collectors", "Collectors", [
    d_netherite, d_shells, d_skulls, d_breeds, d_shulker, d_bees]]
p_big = ["big", "Multi-Part Advancements", [d_acc, d_at, d_2b2, d_mh, d_abd]]
p_misc = ["misc", "Misc", [d_leads, d_fire_res,
                           d_breeds, d_hives, d_crossbow, d_shulker_boat]]
p_early = ["early", "Early Game", [d_fireworks,
                                   d_shulker, d_obi, d_logs, d_eyes, d_rods]]

# Define the pools list
pools = [p_biomes, p_armour, p_tools, p_big, p_misc, p_early]


def get_draft_item(item_id: int) -> DraftItem:
    """Get a draft item by its ID."""
    return all_items[item_id - 1]
