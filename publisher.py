"""
发布 Agent - 多平台发布管理
"""

from typing import Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import asyncio
import hashlib
import json

from .base import BaseAgent
from .message import Message, MessageType
from .config import AgentConfig, PlatformConfig


class PublishStatus(Enum):
    """发布状态"""
    PENDING = "pending"
    PUBLISHING = "publishing"
    SUCCESS = "success"
    FAILED = "failed"
    SCHEDULED = "scheduled"


class Platform(Enum):
    """支持的平台"""
    WECHAT_PUBLIC = "wechat_public"      # 微信公众号
    ZHIHU = "zhihu"                       # 知乎
    JUEJIN = "juejin"                    # 掘金
    XIAOHONGSHU = "xiaohongshu"         # 小红书
    JIANSHU = "jianshu"                 # 简书
    WEIBO = "weibo"                     # 微博
    BILI = "bili"                       # B站
    ZHONG = "zhong"                     # 知识星球
    CUSTOM = "custom"                   # 自定义平台


@dataclass
class PublishTask:
    """发布任务"""
    task_id: str
    article: dict
    platforms: list[str]
    scheduled_time: Optional[datetime] = None
    status: PublishStatus = PublishStatus.PENDING
    results: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "article_title": self.article.get("title", ""),
            "platforms": self.platforms,
            "scheduled_time": self.scheduled_time.isoformat() if self.scheduled_time else None,
            "status": self.status.value,
            "results": self.results,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class PlatformResult:
    """平台发布结果"""
    platform: str
    success: bool
    article_id: Optional[str] = None
    article_url: Optional[str] = None
    publish_time: Optional[datetime] = None
    error: Optional[str] = None
    stats: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "platform": self.platform,
            "success": self.success,
            "article_id": self.article_id,
            "article_url": self.article_url,
            "publish_time": self.publish_time.isoformat() if self.publish_time else None,
            "error": self.error,
            "stats": self.stats
        }


class PublisherAgent(BaseAgent):
    """发布 Agent"""
    
    def __init__(self, config: AgentConfig, message_queue, llm_adapter=None):
        super().__init__(config, message_queue)
        self.llm = llm_adapter
        
        # 发布任务队列
        self.publish_queue: list[PublishTask] = []
        self.scheduled_tasks: dict[str, asyncio.Task] = {}
        
        # 平台适配器
        self.platform_adapters: dict[str, PlatformAdapter] = {}
        self._register_adapters()
        
        # 发布历史
        self.publish_history: list[dict] = []
    
    def _get_default_system_prompt(self) -> str:
        return """你是一位专业的内容发布运营专家，精通多平台内容发布。

你的核心能力：
1. 多平台统一发布
2. 内容格式自动适配
3. 定时发布管理
4. 发布效果追踪

工作原则：
- 内容一致性：确保各平台内容核心一致
- 平台适配：针对不同平台调整格式
- 时机选择：选择最佳发布时机
- 数据追踪：及时获取发布效果数据"""
    
    def _register_adapters(self) -> None:
        """注册平台适配器"""
        self.platform_adapters = {
            Platform.WECHAT_PUBLIC.value: WeChatAdapter(),
            Platform.ZHIHU.value: ZhihuAdapter(),
            Platform.JUEJIN.value: JuejinAdapter(),
            Platform.XIAOHONGSHU.value: XiaohongshuAdapter(),
            Platform.JIANSHU.value: JianshuAdapter(),
            Platform.BILI.value: BiliAdapter(),
        }
    
    async def _handle_message(self, message: Message) -> None:
        """处理消息"""
        content = message.content
        
        if message.msg_type == MessageType.TASK_REQUEST:
            action = content.get("action")
            
            if action == "publish":
                await self._publish_article(content)
            elif action == "schedule":
                await self._schedule_publish(content)
            elif action == "get_status":
                await self._get_publish_status(content)
            elif action == "get_history":
                await self._get_publish_history(content)
    
    async def _publish_article(self, content: dict) -> None:
        """发布文章"""
        self.update_status("working")
        task_id = content.get("task_id")
        article = content.get("article", {})
        platforms = content.get("platforms", ["zhihu"])
        
        task = PublishTask(
            task_id=task_id or self._generate_task_id(article),
            article=article,
            platforms=platforms
        )
        
        self.publish_queue.append(task)
        results = {}
        
        for platform in platforms:
            self.logger.info(f"Publishing to {platform}...")
            
            adapter = self.platform_adapters.get(platform)
            if not adapter:
                results[platform] = PlatformResult(
                    platform=platform,
                    success=False,
                    error=f"Platform adapter not found: {platform}"
                ).to_dict()
                continue
            
            try:
                # 格式转换
                formatted_content = adapter.format_content(article)
                
                # 发布
                result = await adapter.publish(formatted_content, article)
                results[platform] = result.to_dict()
                
                # 记录历史
                self.publish_history.append({
                    "task_id": task.task_id,
                    "article_title": article.get("title", ""),
                    "platform": platform,
                    "success": result.success,
                    "publish_time": datetime.now().isoformat(),
                    "article_url": result.article_url
                })
                
            except Exception as e:
                self.logger.error(f"Failed to publish to {platform}: {e}")
                results[platform] = PlatformResult(
                    platform=platform,
                    success=False,
                    error=str(e)
                ).to_dict()
        
        task.results = results
        task.status = PublishStatus.SUCCESS
        
        await self.send_message(
            "Manager",
            {
                "action": "publish_complete",
                "task_id": task_id,
                "results": results,
                "total_platforms": len(platforms),
                "success_count": sum(1 for r in results.values() if r.get("success")),
                "failed_count": sum(1 for r in results.values() if not r.get("success"))
            },
            MessageType.TASK_RESPONSE,
            task_id
        )
        
        self.update_status("idle")
    
    async def _schedule_publish(self, content: dict) -> None:
        """定时发布"""
        article = content.get("article", {})
        platforms = content.get("platforms", [])
        scheduled_time_str = content.get("scheduled_time")
        
        # 解析时间
        if scheduled_time_str:
            scheduled_time = datetime.fromisoformat(scheduled_time_str)
        else:
            # 默认1小时后
            scheduled_time = datetime.now() + timedelta(hours=1)
        
        task = PublishTask(
            task_id=self._generate_task_id(article),
            article=article,
            platforms=platforms,
            scheduled_time=scheduled_time,
            status=PublishStatus.SCHEDULED
        )
        
        # 计算延迟
        delay = (scheduled_time - datetime.now()).total_seconds()
        
        if delay > 0:
            # 创建定时任务
            timer_task = asyncio.create_task(
                self._delayed_publish(task, delay)
            )
            self.scheduled_tasks[task.task_id] = timer_task
        
        await self.send_message(
            "Manager",
            {
                "action": "schedule_confirmed",
                "task_id": task.task_id,
                "scheduled_time": scheduled_time.isoformat(),
                "platforms": platforms,
                "article_title": article.get("title", "")
            },
            MessageType.RESPONSE
        )
    
    async def _delayed_publish(self, task: PublishTask, delay: float) -> None:
        """延迟发布"""
        await asyncio.sleep(delay)
        
        self.logger.info(f"Executing scheduled publish: {task.task_id}")
        
        await self._publish_article({
            "task_id": task.task_id,
            "article": task.article,
            "platforms": task.platforms
        })
        
        if task.task_id in self.scheduled_tasks:
            del self.scheduled_tasks[task.task_id]
    
    async def _get_publish_status(self, content: dict) -> None:
        """获取发布状态"""
        task_id = content.get("task_id")
        
        status = "not_found"
        results = {}
        
        for task in self.publish_queue:
            if task.task_id == task_id:
                status = task.status.value
                results = task.results
                break
        
        await self.send_message(
            content.get("recipient", "Manager"),
            {
                "action": "publish_status",
                "task_id": task_id,
                "status": status,
                "results": results
            },
            MessageType.RESPONSE
        )
    
    async def _get_publish_history(self, content: dict) -> None:
        """获取发布历史"""
        limit = content.get("limit", 20)
        platform_filter = content.get("platform")
        
        history = self.publish_history[-limit:]
        
        if platform_filter:
            history = [h for h in history if h.get("platform") == platform_filter]
        
        # 统计
        stats = {
            "total": len(self.publish_history),
            "success": sum(1 for h in self.publish_history if h.get("success")),
            "failed": sum(1 for h in self.publish_history if not h.get("success")),
            "by_platform": {}
        }
        
        for h in self.publish_history:
            p = h.get("platform", "unknown")
            if p not in stats["by_platform"]:
                stats["by_platform"][p] = {"success": 0, "failed": 0}
            if h.get("success"):
                stats["by_platform"][p]["success"] += 1
            else:
                stats["by_platform"][p]["failed"] += 1
        
        await self.send_message(
            content.get("recipient", "Manager"),
            {
                "action": "publish_history",
                "history": history,
                "stats": stats
            },
            MessageType.RESPONSE
        )
    
    def _generate_task_id(self, article: dict) -> str:
        """生成任务ID"""
        content = f"{article.get('title', '')}{article.get('created_at', '')}"
        return hashlib.md5(content.encode()).hexdigest()[:12]


class PlatformAdapter:
    """平台适配器基类"""
    
    name: str = "base"
    
    def format_content(self, article: dict) -> dict:
        """格式化内容"""
        return article
    
    async def publish(self, content: dict, article: dict) -> PlatformResult:
        """发布内容"""
        return PlatformResult(
            platform=self.name,
            success=True,
            article_id="mock_id",
            article_url=f"https://{self.name}.com/article/mock"
        )


class WeChatAdapter(PlatformAdapter):
    """微信公众号适配器"""
    
    name = Platform.WECHAT_PUBLIC.value
    
    def format_content(self, article: dict) -> dict:
        """微信公众号格式"""
        sections = article.get("sections", [])
        
        formatted_sections = []
        for section in sections:
            content = section.get("content", "")
            # 微信公众号：双换行，更简洁
            content = content.replace("\n\n\n", "\n\n")
            formatted_sections.append({
                **section,
                "content": content
            })
        
        return {
            **article,
            "sections": formatted_sections,
            "author": article.get("author", "AI运营助手"),
            "digest": article.get("meta_description", "")[:120]
        }
    
    async def publish(self, content: dict, article: dict) -> PlatformResult:
        """发布到微信公众号"""
        await asyncio.sleep(1)  # 模拟API调用
        
        return PlatformResult(
            platform=self.name,
            success=True,
            article_id=f"wx_{datetime.now().strftime('%Y%m%d%H%M')}",
            article_url="https://mp.weixin.qq.com/s/mock_article_id"
        )


class ZhihuAdapter(PlatformAdapter):
    """知乎适配器"""
    
    name = Platform.ZHIHU.value
    
    def format_content(self, article: dict) -> dict:
        """知乎格式"""
        sections = article.get("sections", [])
        
        formatted_sections = []
        for section in sections:
            content = section.get("content", "")
            # 知乎：添加"#"标签
            section_title = section.get("title", "")
            if section_title and not section_title.startswith("#"):
                formatted_sections.append({
                    **section,
                    "display_title": f"## {section_title}"
                })
            formatted_sections.append({**section, "content": content})
        
        return {
            **article,
            "sections": formatted_sections,
            "topics": article.get("tags", ["AI", "科技"])[:5],
            "is_anonymous": False
        }
    
    async def publish(self, content: dict, article: dict) -> PlatformResult:
        """发布到知乎"""
        await asyncio.sleep(0.8)
        
        return PlatformResult(
            platform=self.name,
            success=True,
            article_id=f"zh_{hashlib.md5(article.get('title','').encode()).hexdigest()[:8]}",
            article_url="https://zhihu.com/p/mock_article_id"
        )


class JuejinAdapter(PlatformAdapter):
    """掘金适配器"""
    
    name = Platform.JUEJIN.value
    
    def format_content(self, article: dict) -> dict:
        """掘金格式"""
        return {
            **article,
            "tags": article.get("tags", []),
            "category": "前端" if any(t in str(article) for t in ["React", "Vue", "JavaScript"]) else "后端",
            "is_original": True
        }
    
    async def publish(self, content: dict, article: dict) -> PlatformResult:
        """发布到掘金"""
        await asyncio.sleep(0.6)
        
        return PlatformResult(
            platform=self.name,
            success=True,
            article_id=f"jj_{datetime.now().timestamp():.0f}",
            article_url="https://juejin.cn/post/mock_article_id"
        )


class XiaohongshuAdapter(PlatformAdapter):
    """小红书适配器"""
    
    name = Platform.XIAOHONGSHU.value
    
    def format_content(self, article: dict) -> dict:
        """小红书格式"""
        # 小红书：短文本，突出重点
        combined_content = "\n\n".join([
            f"💡 {s.get('title', '')}\n{s.get('content', '')[:300]}"
            for s in article.get("sections", [])[:3]
        ])
        
        return {
            **article,
            "short_content": combined_content,
            "cover_image_prompt": f"Beautiful tech illustration for: {article.get('title', '')}",
            "hashtags": [f"#{t}" for t in article.get("tags", ["AI", "科技"])[:10]]
        }
    
    async def publish(self, content: dict, article: dict) -> PlatformResult:
        """发布到小红书"""
        await asyncio.sleep(0.5)
        
        return PlatformResult(
            platform=self.name,
            success=True,
            article_id=f"xhs_{datetime.now().timestamp():.0f}",
            article_url="https://xiaohongshu.com/explore/mock_article_id"
        )


class JianshuAdapter(PlatformAdapter):
    """简书适配器"""
    
    name = Platform.JIANSHU.value
    
    def format_content(self, article: dict) -> dict:
        """简书格式"""
        return {
            **article,
            "public": True,
            "paid": False,
            "rewardable": False
        }
    
    async def publish(self, content: dict, article: dict) -> PlatformResult:
        """发布到简书"""
        await asyncio.sleep(0.7)
        
        return PlatformResult(
            platform=self.name,
            success=True,
            article_id=f"js_{datetime.now().timestamp():.0f}",
            article_url="https://www.jianshu.com/p/mock_article_id"
        )


class BiliAdapter(PlatformAdapter):
    """B站适配器"""
    
    name = Platform.BILI.value
    
    def format_content(self, article: dict) -> dict:
        """B站格式"""
        return {
            **article,
            "category": "数码",
            "tags": article.get("tags", []),
            "is_original": True
        }
    
    async def publish(self, content: dict, article: dict) -> PlatformResult:
        """发布到B站"""
        await asyncio.sleep(0.9)
        
        return PlatformResult(
            platform=self.name,
            success=True,
            article_id=f"bili_{datetime.now().timestamp():.0f}",
            article_url="https://www.bilibili.com/read/cvmock_article_id"
        )
