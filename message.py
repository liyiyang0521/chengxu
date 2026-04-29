"""
Agent 间通信消息定义
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
import uuid


class MessageType(Enum):
    """消息类型"""
    # 任务相关
    TASK_REQUEST = "task_request"      # 任务请求
    TASK_RESPONSE = "task_response"    # 任务响应
    TASK_COMPLETE = "task_complete"    # 任务完成
    TASK_FAILED = "task_failed"        # 任务失败
    
    # 协作相关
    QUERY = "query"                    # 查询
    RESPONSE = "response"              # 响应
    BROADCAST = "broadcast"            # 广播
    APPROVAL = "approval"              # 审批
    REJECTION = "rejection"            # 拒绝
    
    # 状态相关
    STATUS_UPDATE = "status_update"    # 状态更新
    HEARTBEAT = "heartbeat"            # 心跳


class Priority(Enum):
    """消息优先级"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass
class Message:
    """Agent 间通信消息"""
    
    # 基础信息
    msg_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    msg_type: MessageType = MessageType.QUERY
    priority: Priority = Priority.NORMAL
    
    # 发送者与接收者
    sender: str = ""
    recipient: str = ""  # 空字符串表示广播
    
    # 消息内容
    content: dict = field(default_factory=dict)
    
    # 时间戳
    timestamp: datetime = field(default_factory=datetime.now)
    
    # 关联追踪
    task_id: Optional[str] = None
    correlation_id: Optional[str] = None
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "msg_id": self.msg_id,
            "msg_type": self.msg_type.value,
            "priority": self.priority.value,
            "sender": self.sender,
            "recipient": self.recipient,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "task_id": self.task_id,
            "correlation_id": self.correlation_id,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Message":
        """从字典创建"""
        return cls(
            msg_id=data.get("msg_id", ""),
            msg_type=MessageType(data.get("msg_type", "normal")),
            priority=Priority(data.get("priority", 2)),
            sender=data.get("sender", ""),
            recipient=data.get("recipient", ""),
            content=data.get("content", {}),
            task_id=data.get("task_id"),
            correlation_id=data.get("correlation_id"),
        )
    
    def add_content(self, key: str, value: Any) -> "Message":
        """链式添加内容"""
        self.content[key] = value
        return self
    
    def get_content(self, key: str, default: Any = None) -> Any:
        """获取内容"""
        return self.content.get(key, default)


class MessageQueue:
    """消息队列"""
    
    def __init__(self):
        self._queue: list[Message] = []
        self._subscribers: dict[str, list] = {}
    
    def enqueue(self, message: Message) -> None:
        """入队"""
        self._queue.append(message)
        # 通知订阅者
        if message.recipient in self._subscribers:
            for callback in self._subscribers[message.recipient]:
                callback(message)
        # 广播通知
        if not message.recipient and "" in self._subscribers:
            for callback in self._subscribers[""]:
                callback(message)
    
    def dequeue(self, recipient: str = "") -> Optional[Message]:
        """出队"""
        for i, msg in enumerate(self._queue):
            if msg.recipient == recipient or not msg.recipient:
                return self._queue.pop(i)
        return None
    
    def peek(self, recipient: str = "") -> Optional[Message]:
        """查看但不出队"""
        for msg in self._queue:
            if msg.recipient == recipient or not msg.recipient:
                return msg
        return None
    
    def subscribe(self, recipient: str, callback) -> None:
        """订阅消息"""
        if recipient not in self._subscribers:
            self._subscribers[recipient] = []
        self._subscribers[recipient].append(callback)
    
    def unsubscribe(self, recipient: str, callback) -> None:
        """取消订阅"""
        if recipient in self._subscribers:
            self._subscribers[recipient].remove(callback)
    
    def size(self) -> int:
        """队列大小"""
        return len(self._queue)
    
    def clear(self) -> None:
        """清空队列"""
        self._queue.clear()
