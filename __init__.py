"""
多Agent协同运营自动化系统
Multi-Agent Collaborative Operations Automation System
"""

__version__ = "1.0.0"
__author__ = "WorkBuddy"

from .manager import ManagerAgent
from .researcher import ResearcherAgent
from .writer import WriterAgent
from .editor import EditorAgent
from .publisher import PublisherAgent
from .message import Message, MessageType
from .config import AgentConfig

__all__ = [
    "ManagerAgent",
    "ResearcherAgent",
    "WriterAgent",
    "EditorAgent",
    "PublisherAgent",
    "Message",
    "MessageType",
    "AgentConfig",
]
