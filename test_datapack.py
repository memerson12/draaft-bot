import asyncio
from datapack_generator import DatapackGenerator
from items import pools, DraftItem


async def main():
    # Get all items from all pools
    all_draft_items = []
    for pool in pools:
        # pool[2] contains the list of DraftItems
        all_draft_items.extend(pool[2])

    # Create the datapack generator with all items
    generator = DatapackGenerator("test_all_items", all_draft_items)

    try:
        # Generate and save the datapack
        output_path = await generator.save_datapack()
        print(f"Successfully generated datapack at: {output_path}")
        print(f"Total items included: {len(all_draft_items)}")

        # Print a summary of included items by category
        print("\nItems included by category:")
        for pool in pools:
            category_name = pool[1]
            items_in_category = [item for item in all_draft_items if item.pretty_name in [
                i.pretty_name for i in pool[2]]]
            print(f"{category_name}: {len(items_in_category)} items")

    except Exception as e:
        print(f"Error generating datapack: {e}")

if __name__ == "__main__":
    asyncio.run(main())
