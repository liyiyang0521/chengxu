"""
管理器 Agent - 任务协调与流程控制
"""

from typing import Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import asyncio
import uuid
import logging

from .base import BaseAgent
from .message import Message, MessageType, MessageQueue
from .config import AgentConfig


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"           # 待处理
    RESEARCHING = "researching"   # 研究中
    WRITING = "writing"           # 写作中
    EDITING = "editing"           # 编辑中
    PUBLISHING = "publishing"     # 发布中
    COMPLETED = "completed"       # 已完成
    FAILED = "failed"            # 失败


class WorkflowStage(Enum):
    """工作流阶段"""
    INIT = "init"
    RESEARCH = "research"
    WRITE = "write"
    EDIT = "edit"
    PUBLISH = "publish"
    DONE = "done"


@dataclass
class Task:
    """运营任务"""
    task_id: str
    topic: str
    requirements: dict = field(default_factory=dict)
    
    # 工作流状态
    status: TaskStatus = TaskStatus.PENDING
    current_stage: WorkflowStage = WorkflowStage.INIT
    stages_completed: list[str] = field(default_factory=list)
    
    # 各阶段数据
    research_data: dict = field(default_factory=dict)
    article_data: dict = field(default_factory=dict)
    edited_article: dict = field(default_factory=dict)
    
    # 元信息
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    
    # 配置
    platforms: list[str] = field(default_factory=lambda: ["zhihu", "juejin"])
    scheduled_time: Optional[datetime] = None
    
    # 错误处理
    error_message: Optional[str] = None
    retry_count: int = 0
    
    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "topic": self.topic,
            "status": self.status.value,
            "current_stage": self.current_stage.value,
            "stages_completed": self.stages_completed,
            "platforms": self.platforms,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message
        }


class ManagerAgent(BaseAgent):
    """管理器 Agent - 协调所有其他 Agent"""
    
    def __init__(self, config: AgentConfig, message_queue: MessageQueue):
        super().__init__(config, message_queue)
        
        # Agent 引用
        self.agents: dict[str, BaseAgent] = {}
        
        # 任务管理
        self.tasks: dict[str, Task] = {}
        self.active_task: Optional[str] = None
        
        # 工作流配置
        self.workflow_config = {
            "auto_research": True,
            "auto_write": True,
            "auto_edit": True,
            "auto_publish": True,
            "parallel_write": False  # 是否并行写作
        }
        
        # 回调
        self.status_callbacks: list[Callable] = []
        self.completion_callbacks: list[Callable] = []
    
    def register_agent(self, name: str, agent: BaseAgent) -> None:
        """注册 Agent"""
        self.agents[name] = agent
        self.logger.info(f"Registered agent: {name}")
    
    def _get_default_system_prompt(self) -> str:
        return """你是内容运营系统的协调者，负责管理整个内容创作到发布的工作流程。

你的职责：
1. 接收并解析用户的内容需求
2. 协调研究员、写手、编辑、发布者等 Agent
3. 监控工作流进度，处理异常
4. 确保内容质量和发布时效

工作原则：
- 以任务完成为导向
- 合理分配资源
- 及时汇报进度
- 优雅处理失败"""
    
    async def _on_initialize(self) -> None:
        """初始化"""
        # 订阅消息
        self.message_queue.subscribe(self.name, self._on_message_received)
    
    async def _on_shutdown(self) -> None:
        """关闭"""
        self.message_queue.unsubscribe(self.name, self._on_message_received)
    
    async def _on_message_received(self, message: Message) -> None:
        """消息接收"""
        await self.receive_message(message)
    
    async def _handle_message(self, message: Message) -> None:
        """处理消息"""
        content = message.content
        action = content.get("action", "")
        
        # 根据来源和类型处理
        if message.sender in self.agents:
            await self._handle_agent_response(message)
        elif message.msg_type == MessageType.TASK_REQUEST:
            if action == "create_content_task":
                await self._create_content_task(content)
            elif action == "get_task_status":
                await self._get_task_status(content)
            elif action == "cancel_task":
                await self._cancel_task(content)
    
    async def _handle_agent_response(self, message: Message) -> None:
        """处理 Agent 响应"""
        content = message.content
        sender = message.sender
        task_id = content.get("task_id", self.active_task)
        
        task = self.tasks.get(task_id)
        if not task:
            return
        
        # 根据发送者和动作处理
        if sender == "Researcher":
            await self._handle_researcher_response(task, content)
        elif sender == "Writer":
            await self._handle_writer_response(task, content)
        elif sender == "Editor":
            await self._handle_editor_response(task, content)
        elif sender == "Publisher":
            await self._handle_publisher_response(task, content)
    
    async def _handle_researcher_response(self, task: Task, content: dict) -> None:
        """处理研究员响应"""
        action = content.get("action", "")
        
        if action == "research_complete":
            task.research_data = content.get("result", {})
            task.stages_completed.append("research")
            
            self.logger.info(f"Research completed for task {task.task_id}")
            
            # 通知所有回调
            self._notify_status_callbacks(task, "research_completed")
            
            # 进入下一阶段：写作
            if self.workflow_config["auto_write"]:
                await self._start_writing_stage(task)
        
        elif action == "research_failed":
            task.error_message = content.get("error", "Research failed")
            task.status = TaskStatus.FAILED
            self._notify_status_callbacks(task, "failed")
    
    async def _handle_writer_response(self, task: Task, content: dict) -> None:
        """处理写作者响应"""
        action = content.get("action", "")
        
        if action == "article_written":
            task.article_data = content.get("article", {})
            task.stages_completed.append("writing")
            
            self.logger.info(f"Writing completed for task {task.task_id}")
            self._notify_status_callbacks(task, "writing_completed")
            
            # 进入下一阶段：编辑
            if self.workflow_config["auto_edit"]:
                await self._start_editing_stage(task)
        
        elif action == "writing_failed":
            task.error_message = content.get("error", "Writing failed")
            task.status = TaskStatus.FAILED
            self._notify_status_callbacks(task, "failed")
    
    async def _handle_editor_response(self, task: Task, content: dict) -> None:
        """处理编辑响应"""
        action = content.get("action", "")
        
        if action == "article_edited":
            task.edited_article = content.get("edited_article", {})
            task.stages_completed.append("editing")
            
            self.logger.info(f"Editing completed for task {task.task_id}")
            self._notify_status_callbacks(task, "editing_completed")
            
            # 进入下一阶段：发布
            if self.workflow_config["auto_publish"]:
                await self._start_publishing_stage(task)
        
        elif action == "editing_failed":
            task.error_message = content.get("error", "Editing failed")
            task.status = TaskStatus.FAILED
            self._notify_status_callbacks(task, "failed")
    
    async def _handle_publisher_response(self, task: Task, content: dict) -> None:
        """处理发布者响应"""
        action = content.get("action", "")
        
        if action == "publish_complete":
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            
            self.logger.info(f"Task {task.task_id} completed!")
            self._notify_status_callbacks(task, "completed")
            self._notify_completion_callbacks(task)
            
            # 触发完成回调
            for callback in self.completion_callbacks:
                try:
                    await callback(task)
                except Exception as e:
                    self.logger.error(f"Completion callback error: {e}")
        
        elif action == "publish_failed":
            task.error_message = content.get("error", "Publishing failed")
            task.status = TaskStatus.FAILED
            self._notify_status_callbacks(task, "failed")
    
    async def _create_content_task(self, content: dict) -> None:
        """创建内容任务"""
        topic = content.get("topic", "")
        platforms = content.get("platforms", ["zhihu", "juejin"])
        requirements = content.get("requirements", {})
        
        task = Task(
            task_id=str(uuid.uuid4())[:8],
            topic=topic,
            requirements=requirements,
            platforms=platforms,
            scheduled_time=content.get("scheduled_time")
        )
        
        self.tasks[task.task_id] = task
        self.active_task = task.task_id
        
        self.logger.info(f"Created task {task.task_id}: {topic}")
        
        # 发送确认
        await self.broadcast({
            "action": "task_created",
            "task": task.to_dict()
        })
        
        # 自动开始研究阶段
        if self.workflow_config["auto_research"]:
            await self._start_research_stage(task)
    
    async def _start_research_stage(self, task: Task) -> None:
        """开始研究阶段"""
        task.status = TaskStatus.RESEARCHING
        task.current_stage = WorkflowStage.RESEARCH
        
        self.logger.info(f"Starting research for task {task.task_id}")
        self._notify_status_callbacks(task, "research_started")
        
        researcher = self.agents.get("Researcher")
        if researcher:
            await researcher.send_message(
                researcher.name,
                {
                    "action": "research_trending",
                    "task_id": task.task_id,
                    "keywords": [task.topic] + task.requirements.get("keywords", []),
                    "competitors": task.requirements.get("competitors", [])
                },
                MessageType.TASK_REQUEST,
                task.task_id
            )
        else:
            # 没有研究员，使用默认数据
            task.research_data = self._get_default_research_data(task.topic)
            task.stages_completed.append("research")
            if self.workflow_config["auto_write"]:
                await self._start_writing_stage(task)
    
    async def _start_writing_stage(self, task: Task) -> None:
        """开始写作阶段"""
        task.status = TaskStatus.WRITING
        task.current_stage = WorkflowStage.WRITE
        
        self.logger.info(f"Starting writing for task {task.task_id}")
        self._notify_status_callbacks(task, "writing_started")
        
        writer = self.agents.get("Writer")
        if writer:
            await writer.send_message(
                writer.name,
                {
                    "action": "write_article",
                    "task_id": task.task_id,
                    "topic": task.topic,
                    "research_data": task.research_data,
                    "style": task.requirements.get("style", "tutorial"),
                    "platform": task.platforms[0] if task.platforms else "通用",
                    "word_count": task.requirements.get("word_count", 2000)
                },
                MessageType.TASK_REQUEST,
                task.task_id
            )
        else:
            # 没有写作者，模拟生成
            task.article_data = self._get_default_article(task.topic)
            task.stages_completed.append("writing")
            if self.workflow_config["auto_edit"]:
                await self._start_editing_stage(task)
    
    async def _start_editing_stage(self, task: Task) -> None:
        """开始编辑阶段"""
        task.status = TaskStatus.EDITING
        task.current_stage = WorkflowStage.EDIT
        
        self.logger.info(f"Starting editing for task {task.task_id}")
        self._notify_status_callbacks(task, "editing_started")
        
        editor = self.agents.get("Editor")
        if editor:
            await editor.send_message(
                editor.name,
                {
                    "action": "edit_article",
                    "task_id": task.task_id,
                    "article": task.article_data or task.edited_article,
                    "platform": task.platforms[0] if task.platforms else "通用"
                },
                MessageType.TASK_REQUEST,
                task.task_id
            )
        else:
            # 没有编辑者，直接进入发布
            task.edited_article = task.article_data
            task.stages_completed.append("editing")
            if self.workflow_config["auto_publish"]:
                await self._start_publishing_stage(task)
    
    async def _start_publishing_stage(self, task: Task) -> None:
        """开始发布阶段"""
        task.status = TaskStatus.PUBLISHING
        task.current_stage = WorkflowStage.PUBLISH
        
        self.logger.info(f"Starting publishing for task {task.task_id}")
        self._notify_status_callbacks(task, "publishing_started")
        
        publisher = self.agents.get("Publisher")
        if publisher:
            publish_content = task.edited_article or task.article_data
            
            if task.scheduled_time:
                await publisher.send_message(
                    publisher.name,
                    {
                        "action": "schedule",
                        "article": publish_content,
                        "platforms": task.platforms,
                        "scheduled_time": task.scheduled_time.isoformat()
                    },
                    MessageType.TASK_REQUEST,
                    task.task_id
                )
            else:
                await publisher.send_message(
                    publisher.name,
                    {
                        "action": "publish",
                        "task_id": task.task_id,
                        "article": publish_content,
                        "platforms": task.platforms
                    },
                    MessageType.TASK_REQUEST,
                    task.task_id
                )
    
    async def _get_task_status(self, content: dict) -> None:
        """获取任务状态"""
        task_id = content.get("task_id", self.active_task)
        task = self.tasks.get(task_id)
        
        if task:
            await self.broadcast({
                "action": "task_status",
                "task": task.to_dict()
            })
    
    async def _cancel_task(self, content: dict) -> None:
        """取消任务"""
        task_id = content.get("task_id")
        
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task.status = TaskStatus.FAILED
            task.error_message = "Cancelled by user"
            
            self.logger.info(f"Task {task_id} cancelled")
    
    def _get_default_research_data(self, topic: str) -> dict:
        """获取默认研究数据"""
        return {
            "trending_topics": [
                {"name": topic, "heat": 8000, "trend": "up"}
            ],
            "recommended_angles": [
                f"{topic}的核心原理",
                f"{topic}的实战应用",
                f"如何快速上手{topic}"
            ],
            "keyword_trends": [
                {"keyword": topic, "search_volume": 50000}
            ]
        }
    
    def _get_default_article(self, topic: str) -> dict:
        """获取默认文章"""
        return {
            "title": f"深入理解{topic}",
            "subtitle": "从入门到精通",
            "sections": [
                {
                    "title": "概述",
                    "content": f"本文将详细介绍{topic}的相关知识，帮助你快速入门并掌握核心技能。"
                },
                {
                    "title": "核心概念",
                    "content": f"关于{topic}的核心概念解析，让你从根本上理解这一技术。"
                },
                {
                    "title": "实战案例",
                    "content": "通过实际案例演示如何在项目中应用。"
                },
                {
                    "title": "总结",
                    "content": f"以上就是关于{topic}的全部内容，希望对你有所帮助。"
                }
            ],
            "tags": ["AI", "技术", topic],
            "keywords": [topic]
        }
    
    def _notify_status_callbacks(self, task: Task, event: str) -> None:
        """通知状态回调"""
        for callback in self.status_callbacks:
            try:
                callback(task, event)
            except Exception as e:
                self.logger.error(f"Status callback error: {e}")
    
    def _notify_completion_callbacks(self, task: Task) -> None:
        """通知完成回调"""
        for callback in self.completion_callbacks:
            try:
                callback(task)
            except Exception as e:
                self.logger.error(f"Completion callback error: {e}")
    
    def on_status_change(self, callback: Callable) -> None:
        """注册状态变更回调"""
        self.status_callbacks.append(callback)
    
    def on_completion(self, callback: Callable) -> None:
        """注册完成回调"""
        self.completion_callbacks.append(callback)
    
    async def create_task(self, topic: str, **kwargs) -> str:
        """创建任务 - 外部调用接口"""
        platforms = kwargs.get("platforms", ["zhihu", "juejin"])
        requirements = kwargs.get("requirements", {})
        scheduled_time = kwargs.get("scheduled_time")
        
        task = Task(
            task_id=str(uuid.uuid4())[:8],
            topic=topic,
            requirements=requirements,
            platforms=platforms,
            scheduled_time=scheduled_time
        )
        
        self.tasks[task.task_id] = task
        self.active_task = task.task_id
        
        self.logger.info(f"Created task {task.task_id}: {topic}")
        
        # 自动开始研究阶段
        if self.workflow_config["auto_research"]:
            await self._start_research_stage(task)
        
        return task.task_id
