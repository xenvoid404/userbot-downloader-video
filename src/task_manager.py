import asyncio
from dataclasses import dataclass
from typing import Optional
from src.utils import TaskType


@dataclass
class Task:
    """Task tracking data structure"""

    task_id: int
    task_type: TaskType
    filename: str
    task_obj: asyncio.Task


class TaskManager:
    """Manages active tasks with semaphore for concurrency control"""

    def __init__(self, max_downloads: int = 3, max_uploads: int = 2):
        self._tasks: dict[int, Task] = {}
        self._counter: int = 0
        self._lock = asyncio.Lock()

        # Semaphore untuk membatasi concurrent tasks
        self.download_semaphore = asyncio.Semaphore(max_downloads)
        self.upload_semaphore = asyncio.Semaphore(max_uploads)

        print(  # Placeholder for logging
            f"TaskManager initialized: max_downloads={max_downloads}, max_uploads={max_uploads}"
        )

    async def reserve_next_task_id(self) -> int:
        """Reserve and return next task ID"""
        async with self._lock:
            self._counter += 1
            return self._counter

    async def register_task(
        self, task_id: int, task_type: TaskType, filename: str, coro
    ) -> asyncio.Task:
        """Create and register task with reserved ID"""
        async with self._lock:
            task_obj = asyncio.create_task(coro)
            self._tasks[task_id] = Task(task_id, task_type, filename, task_obj)
            print(  # Placeholder for logging
                f"Task {task_id:3} | {task_type.value.upper():8} | Registered: {filename}"
            )
            return task_obj

    async def remove_task(self, task_id: int) -> None:
        """Remove task from tracking"""
        async with self._lock:
            if task_id in self._tasks:
                task = self._tasks.pop(task_id)
                print(  # Placeholder for logging
                    f"Task {task_id:3} | {task.task_type.value.upper():8} | "
                    f"Completed: {task.filename} | Active: {len(self._tasks)}"
                )

    def get_tasks_by_type(self, task_type: TaskType) -> list[Task]:
        """Get all tasks of specific type"""
        return [t for t in self._tasks.values() if t.task_type == task_type]

    def get_task_count(self) -> int:
        """Get active task count"""
        return len(self._tasks)

    def get_all_tasks(self) -> list[Task]:
        """Get all active tasks"""
        return list(self._tasks.values())
