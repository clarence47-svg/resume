import asyncio
from pathlib import Path


async def upload_resume(page, resume_path: str) -> bool:
    path = Path(resume_path)
    if not await asyncio.to_thread(path.exists):
        return False
    inputs = page.locator('input[type="file"]')
    if await inputs.count() == 0:
        return False
    await inputs.first.set_input_files(str(path))
    return True
