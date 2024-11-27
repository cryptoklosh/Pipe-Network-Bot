import asyncio
import aiofiles

from pathlib import Path
from models import ModuleType, OperationResult



class FileOperations:
    def __init__(self, base_path: str = "./results"):
        self.base_path = Path(base_path)
        self.lock = asyncio.Lock()
        self.module_paths: dict[ModuleType, dict[str, Path]] = {
            "register": {
                "success": self.base_path / "registration_success.txt",
                "failed": self.base_path / "registration_failed.txt",
            }
        }

    async def setup_files(self):
        self.base_path.mkdir(exist_ok=True)
        for module_paths in self.module_paths.values():
            for path in module_paths.values():
                path.touch(exist_ok=True)

    async def export_result(self, result: OperationResult, module: ModuleType):
        if module not in self.module_paths:
            raise ValueError(f"Unknown module: {module}")

        file_path = self.module_paths[module][
            "success" if result["status"] else "failed"
        ]
        async with self.lock:
            try:
                async with aiofiles.open(file_path, "a") as file:
                    await file.write(f"{result['identifier']}:{result['data']}\n")
            except IOError as e:
                print(f"Error writing to file: {e}")
