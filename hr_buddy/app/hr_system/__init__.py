from functools import lru_cache

from hr_buddy.app.hr_system.store import HRSystem, HRSystemError


@lru_cache(maxsize=1)
def get_hr_system() -> HRSystem:
    return HRSystem()


__all__ = ["HRSystem", "HRSystemError", "get_hr_system"]
