import asyncio
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Coroutine, Any

from src.utils import TaskType


@dataclass
class Task:
    """Task metadata"""

    task_id: int
    task_type: TaskType
    filename: str
    task_obj: asyncio.Task


class TaskManager:
    """Manages concurrent tasks with semaphore-based rate limiting"""

    def __init__(
        self,
        max_downloads: int,
        max_uploads: int,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize task manager

        Args:
            max_downloads: Maximum concurrent downloads
            max_uploads: Maximum concurrent uploads
            logger: Optional logger instance
        """
        self._tasks: Dict[int, Task] = {}
        self._counter: int = 0
        self._lock = asyncio.Lock()

        # Semaphores for concurrency control
        self.download_sem = asyncio.Semaphore(max_downloads)
        self.upload_sem = asyncio.Semaphore(max_uploads)

        self.logger = logger or logging.getLogger(__name__)
        self.logger.info(
            f"TaskManager initialized: downloads={max_downloads}, uploads={max_uploads}"
        )

    async def reserve_task_id(self) -> int:
        """Reserve and return next task ID"""
        async with self._lock:
            self._counter += 1
            return self._counter

    async def register_task(
        self,
        task_id: int,
        task_type: TaskType,
        filename: str,
        coro: Coroutine[Any, Any, None],
    ) -> asyncio.Task:
        """
        Register and start a new task

        Args:
            task_id: Unique task identifier
            task_type: Type of task (DOWNLOAD/UPLOAD)
            filename: Associated filename
            coro: Coroutine to execute

        Returns:
            Created asyncio.Task object
        """
        async with self._lock:
            task_obj = asyncio.create_task(coro)
            self._tasks[task_id] = Task(task_id, task_type, filename, task_obj)
            self.logger.info(
                f"Task {task_id:3} | {task_type.value.upper():8} | "
                f"Registered: {filename}"
            )
            return task_obj

    async def remove_task(self, task_id: int) -> None:
        """Remove completed task from tracking"""
        async with self._lock:
            if task := self._tasks.pop(task_id, None):
                self.logger.info(
                    f"Task {task_id:3} | {task.task_type.value.upper():8} | "
                    f"Removed: {task.filename} | Active: {len(self._tasks)}"
                )

    def get_tasks_by_type(self, task_type: TaskType) -> List[Task]:
        """Get all tasks of a specific type"""
        return [t for t in self._tasks.values() if t.task_type == task_type]

    def get_task_count(self) -> int:
        """Get total active task count"""
        return len(self._tasks)

    def get_all_tasks(self) -> List[Task]:
        """Get all active tasks"""
        return list(self._tasks.values())

    def get_semaphore(self, task_type: TaskType) -> asyncio.Semaphore:
        """Get appropriate semaphore for task type"""
        return self.download_sem if task_type == TaskType.DOWNLOAD else self.upload_sem
