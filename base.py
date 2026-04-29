"""
Agent 基类
所有 Agent 的父类
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional
import asyncio
import logging

from .message import Message, MessageType, MessageQueue
from .config import AgentConfig, LLMConfig


class BaseAgent(ABC):
    """Agent 基类"""
    
    def __init__(self, config: AgentConfig, message_queue: MessageQueue):
        self.config = config
        self.name = config.name
        self.role = config.role
        self.description = config.description
        self.message_queue = message_queue
        
        # 状态
        self.status = "idle"  # idle / working / waiting / error
        self.current_task: Optional[str] = None
        self.task_history: list[dict] = []
        
        # 日志
        self.logger = logging.getLogger(f"Agent.{self.name}")
        
        # LLM 调用锁
        self._llm_lock = asyncio.Lock()
    
    async def initialize(self) -> None:
        """初始化 Agent"""
        self.logger.info(f"Initializing {self.name}...")
        await self._on_initialize()
        self.logger.info(f"{self.name} initialized successfully")
    
    async def _on_initialize(self) -> None:
        """子类初始化逻辑"""
        pass
    
    async def shutdown(self) -> None:
        """关闭 Agent"""
        self.logger.info(f"Shutting down {self.name}...")
        self.status = "idle"
        await self._on_shutdown()
        self.logger.info(f"{self.name} shut down")
    
    async def _on_shutdown(self) -> None:
        """子类关闭逻辑"""
        pass
    
    async def receive_message(self, message: Message) -> None:
        """接收消息"""
        self.logger.debug(f"Received message from {message.sender}: {message.content}")
        await self._handle_message(message)
    
    @abstractmethod
    async def _handle_message(self, message: Message) -> None:
        """处理消息 - 子类必须实现"""
        pass
    
    async def send_message(
        self,
        recipient: str,
        content: dict,
        msg_type: MessageType = MessageType.QUERY,
        task_id: Optional[str] = None
    ) -> None:
        """发送消息"""
        message = Message(
            sender=self.name,
            recipient=recipient,
            content=content,
            msg_type=msg_type,
            task_id=task_id,
            timestamp=datetime.now()
        )
        self.message_queue.enqueue(message)
        self.logger.debug(f"Sent message to {recipient}: {content}")
    
    async def broadcast(self, content: dict, msg_type: MessageType = MessageType.BROADCAST) -> None:
        """广播消息"""
        await self.send_message("", content, msg_type)
    
    async def call_llm(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """调用大语言模型"""
        async with self._llm_lock:
            try:
                # 这里可以接入实际的 LLM API
                # 目前是模拟实现
                self.logger.info(f"Calling LLM with prompt: {prompt[:50]}...")
                
                # 模拟 LLM 调用
                await asyncio.sleep(0.5)
                
                return await self._generate_response(prompt, system_prompt, **kwargs)
                
            except Exception as e:
                self.logger.error(f"LLM call failed: {e}")
                raise
    
    async def _generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """生成 LLM 响应 - 子类可重写"""
        # 默认实现：返回提示信息
        return f"[模拟响应] {prompt[:100]}..."
    
    def update_status(self, status: str) -> None:
        """更新状态"""
        self.status = status
        self.logger.info(f"Status updated: {status}")
    
    def log_task(self, task_id: str, action: str, result: Any = None) -> None:
        """记录任务日志"""
        self.task_history.append({
            "task_id": task_id,
            "action": action,
            "result": result,
            "timestamp": datetime.now().isoformat()
        })
    
    @property
    def system_prompt(self) -> str:
        """获取系统提示词"""
        return self.config.system_prompt or self._get_default_system_prompt()
    
    @abstractmethod
    def _get_default_system_prompt(self) -> str:
        """获取默认系统提示词 - 子类必须实现"""
        pass
