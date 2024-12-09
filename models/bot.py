from typing import Literal, TypedDict


ModuleType = Literal["register", "bind_twitter", "farm"]


class OperationResult(TypedDict):
    identifier: str
    data: str
    status: bool


