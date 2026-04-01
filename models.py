from pydantic import BaseModel
from typing import Literal


class SessionMeta(BaseModel):
    type: Literal['session_meta'] = 'session_meta'
    title: str
    description: str
    agent: str
    source: str


class Message(BaseModel):
    type: Literal['message'] = 'message'
    role: Literal['user', 'assistant', 'system', 'header']
    content: str
    is_navigable: bool = False
    is_write_file: bool = False
