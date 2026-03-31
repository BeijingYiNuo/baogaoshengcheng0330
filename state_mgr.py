from __future__ import annotations
from abc import ABC
import os
from typing import Any
import datetime


class StateManager(ABC):
    def __init__(self, report_path: str):
        pass

    def update(self, idx: int, progress: float, msg: str = "") -> None:
        pass

    def start(self) -> FileInfo:
        pass

    def abort(self, idx: int) -> None:
        pass

    def done(self, idx: int) -> None:
        pass


class FileInfo:
    def __init__(self, file_name: str):
        file_name = file_name.split(".")[:-1]
        self.idx, self.gen_time = file_name.split("_")

    @staticmethod
    def from_info(idx: int, gen_time: str = None, postfix: str = ".docx") -> FileInfo:
        if gen_time is None:
            gen_time = datetime.now().strftime("%Y-%m-%d-%H-%M")
        return __class__(f"{idx}_{gen_time}{postfix}")

    def filename(self, postfix: str = ".docx") -> str:
        return self.idx + "_" + self.gen_time + postfix


class FileState:
    info: FileInfo
    done: bool = False
    progress: float = 0
    msg: str = ""

    def __init__(self, info: FileInfo):
        self.info = info


class SimpleStateManager(StateManager):
    idx_counter: int = None
    state_container: dict[int, FileState] = None

    def __init__(self, report_path):
        self.report_path = report_path
        os.makedirs(report_path, exist_ok=True)
        self.idx_counter = self.next_id()
        self.state_container = dict[int, Any]()

    def list_files(self) -> list[str]:
        return os.listdir(self.report_path)

    def file_name_to_info(self, file_name: str) -> FileInfo:
        return FileInfo(file_name)

    def next_id(self) -> int:
        if self.idx_counter is None:
            self.idx_counter = max(
                *[self.file_name_to_info(fn).idx for fn in self.list_files()]
            )
        self.idx_counter += 1
        return self.idx_counter

    def del_file(self, file_name: str) -> None:
        try:
            os.remove(self.report_path + "/" + file_name)
        except:
            pass

    def start(self) -> FileInfo:
        info = FileInfo.from_info(self.next_id())
        if info.idx in self.state_container:
            raise KeyError(f"idx {info.idx} already started")
        self.state_container[info.idx] = FileState(info)

    def abort(self, idx: int) -> None:
        if idx in self.state_container:
            self.del_file(self.state_container[idx].info.filename())
            del self.state_container[idx]

    def update(self, idx: int, progress: float, msg: str = "") -> None:
        if idx not in self.state_container:
            pass
        self.state_container[idx].progress = progress
        self.state_container[idx].msg = msg

    def done(self, idx: int) -> None:
        if idx not in self.state_container:
            pass
        self.state_container[idx].done = True
        self.state_container[idx].progress = 1
