import aiohttp
import asyncio
import zipfile
from io import BytesIO
from datetime import datetime
from typing import List, Dict, Any, Optional
import os
from items import DraftItem


class DatapackGenerator:
    def __init__(self, draft_name: str, drafted_items: List[DraftItem]):
        self.draft_name = draft_name
        self.drafted_items = drafted_items
        self.base_url = "https://disrespec.tech"

    async def download_file(self, session: aiohttp.ClientSession, url: str) -> bytes:
        """Download a file from the given URL."""
        async with session.get(url) as response:
            if response.status == 200:
                return await response.read()
            raise Exception(
                f"Failed to download {url}: HTTP {response.status}")

    async def download_mcfunction(self, session: aiohttp.ClientSession, url: str, filename: str) -> bytes:
        """Download and process an mcfunction file."""
        content = await self.download_file(session, url)
        return self.update_file(content.decode('utf-8'), filename)

    def update_file(self, content: str, filename: str) -> bytes:
        """Update the content of an mcfunction file based on drafted items."""
        for item in self.drafted_items:
            if filename == "on_load.mcfunction":
                if item.file_query is None:
                    content = item.datapack_modifier(content)
            elif item.file_query is not None and item.file_query in filename:
                content = item.datapack_modifier(content)

        return content.encode('utf-8')

    async def generate_datapack(self) -> bytes:
        """Generate the datapack ZIP file."""
        async with aiohttp.ClientSession() as session:
            # Get the index file
            index_url = f"{self.base_url}/assets/draaft/index.txt"
            async with session.get(index_url) as response:
                if response.status != 200:
                    raise Exception(
                        f"Failed to download index: HTTP {response.status}")
                index_content = await response.text()

            # Process all files from the index
            all_files = []
            for line in index_content.split('\n'):
                if not line.strip():
                    continue

                file_url = f"{self.base_url}/assets/draaft/{line}"
                filename = line[line.find('/') + 1:] if '/' in line else line

                if filename.endswith('.mcfunction'):
                    content = await self.download_mcfunction(session, file_url, filename)
                else:
                    content = await self.download_file(session, file_url)

                all_files.append({
                    'name': filename,
                    'last_modified': datetime.now(),
                    'content': content
                })

            # Add files for drafted items
            for item in self.drafted_items:
                if item.file_query and item.file_query.startswith('draaftpack/'):
                    filename = item.file_query[item.file_query.find('/') + 1:]
                    content = item.datapack_modifier('').encode('utf-8')
                    all_files.append({
                        'name': filename,
                        'last_modified': datetime.now(),
                        'content': content
                    })

            # Create ZIP file in memory
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for file_data in all_files:
                    zip_file.writestr(file_data['name'], file_data['content'])

            return zip_buffer.getvalue()

    async def save_datapack(self, output_dir: str = '.') -> str:
        """Generate and save the datapack to a file."""
        zip_data = await self.generate_datapack()
        output_filename = f"draaft_{self.draft_name}.zip"
        output_path = os.path.join(output_dir, output_filename)

        with open(output_path, 'wb') as f:
            f.write(zip_data)

        return output_path

# Example usage:
# generator = DatapackGenerator("my_draft", [draft_item1, draft_item2, draft_item3])
# output_path = await generator.save_datapack()
