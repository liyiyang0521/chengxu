"""
研究员 Agent - 热点挖掘与竞品分析
"""

from typing import Optional
import asyncio
from datetime import datetime, timedelta
import random

from .base import BaseAgent
from .message import Message, MessageType
from .config import AgentConfig


class ResearchResult:
    """研究结果"""
    
    def __init__(self):
        self.trending_topics: list[dict] = []      # 热点话题
        self.competitor_analysis: list[dict] = [] # 竞品分析
        self.keyword_trends: list[dict] = []      # 关键词趋势
        self.user_insights: list[dict] = []        # 用户洞察
        self.recommended_angles: list[str] = []    # 推荐切入角度
        self.content_calendar: list[dict] = []     # 内容日历建议
    
    def to_dict(self) -> dict:
        return {
            "trending_topics": self.trending_topics,
            "competitor_analysis": self.competitor_analysis,
            "keyword_trends": self.keyword_trends,
            "user_insights": self.user_insights,
            "recommended_angles": self.recommended_angles,
            "content_calendar": self.content_calendar,
        }


class ResearcherAgent(BaseAgent):
    """研究员 Agent"""
    
    def __init__(self, config: AgentConfig, message_queue, llm_adapter=None):
        super().__init__(config, message_queue)
        self.llm = llm_adapter
        self.research_cache: dict = {}
        self.last_research_time: Optional[datetime] = None
    
    def _get_default_system_prompt(self) -> str:
        return """你是一位资深的内容研究员，专注于热点挖掘和竞品分析。

你的核心能力：
1. 敏锐捕捉全网热点话题
2. 分析竞品内容策略
3. 发现用户关注点和痛点
4. 提供有价值的选题切入角度

工作原则：
- 数据驱动，用事实说话
- 多角度分析，避免单一视角
- 注重内容的差异化价值
- 关注时效性，热点要快、准、狠"""
    
    async def _handle_message(self, message: Message) -> None:
        """处理消息"""
        content = message.content
        
        if message.msg_type == MessageType.TASK_REQUEST:
            if content.get("action") == "research_trending":
                await self._research_trending(content)
            elif content.get("action") == "analyze_competitor":
                await self._analyze_competitor(content)
            elif content.get("action") == "generate_topics":
                await self._generate_topics(content)
    
    async def _research_trending(self, content: dict) -> None:
        """研究热点"""
        self.update_status("working")
        self.current_task = content.get("task_id")
        
        try:
            # 模拟热点研究
            trending = await self._fetch_trending_data(content.get("keywords", []))
            
            result = ResearchResult()
            result.trending_topics = trending["topics"]
            result.keyword_trends = trending["keywords"]
            result.user_insights = trending["insights"]
            
            # 使用 LLM 深入分析
            if self.llm:
                analysis_prompt = f"""
基于以下热点数据，分析其内容价值：

{trending}

请提供：
1. 3-5个值得切入的角度
2. 每个角度的潜在受众
3. 推荐的内容形式
"""
                analysis = await self.llm.generate(analysis_prompt, system_prompt=self.system_prompt)
                result.recommended_angles = self._parse_angles(analysis)
            
            # 发送结果给 Manager
            await self.send_message(
                "Manager",
                {
                    "action": "research_complete",
                    "task_id": content.get("task_id"),
                    "result": result.to_dict(),
                    "confidence": 0.85
                },
                MessageType.TASK_RESPONSE,
                content.get("task_id")
            )
            
        except Exception as e:
            await self.send_message(
                "Manager",
                {
                    "action": "research_failed",
                    "task_id": content.get("task_id"),
                    "error": str(e)
                },
                MessageType.TASK_FAILED,
                content.get("task_id")
            )
        finally:
            self.update_status("idle")
    
    async def _analyze_competitor(self, content: dict) -> None:
        """分析竞品"""
        competitors = content.get("competitors", [])
        topics = content.get("topics", [])
        
        analysis = {
            "competitors": competitors,
            "analysis": []
        }
        
        for competitor in competitors:
            # 模拟竞品分析
            competitor_data = {
                "name": competitor,
                "content_types": ["文章", "视频", "图文"],
                "posting_frequency": "日更",
                "engagement_rate": round(random.uniform(2, 8), 2),
                "top_content": [
                    {"title": f"{competitor}相关文章1", "views": random.randint(10000, 100000)},
                    {"title": f"{competitor}相关文章2", "views": random.randint(8000, 80000)},
                ],
                "strengths": ["内容专业", "更新稳定", "互动积极"],
                "weaknesses": ["排版一般", "标题党嫌疑"],
                "opportunities": ["可以借鉴其选题策略"]
            }
            analysis["analysis"].append(competitor_data)
        
        await self.send_message(
            "Manager",
            {
                "action": "competitor_analysis_complete",
                "result": analysis
            },
            MessageType.RESPONSE
        )
    
    async def _generate_topics(self, content: dict) -> None:
        """生成选题"""
        topic_count = content.get("count", 5)
        category = content.get("category", "通用")
        
        # 使用 LLM 生成选题
        if self.llm:
            prompt = f"""为{category}类内容生成{topic_count}个选题，要求：
1. 紧跟当前热点
2. 有差异化角度
3. 适合目标受众
4. 标题吸引人

请以 JSON 格式返回：
{{"topics": [{{"title": "...", "angle": "...", "keywords": [...], "estimated_views": "..."}}]}}"""
            
            result = await self.llm.generate(prompt, system_prompt=self.system_prompt)
            topics = self._parse_topics(result)
        else:
            topics = self._generate_mock_topics(topic_count)
        
        await self.send_message(
            "Manager",
            {
                "action": "topics_generated",
                "topics": topics,
                "category": category
            },
            MessageType.RESPONSE
        )
    
    async def _fetch_trending_data(self, keywords: list) -> dict:
        """获取热点数据"""
        await asyncio.sleep(1)  # 模拟网络请求
        
        return {
            "topics": [
                {"name": "AI Agent", "heat": 9850, "trend": "up", "category": "科技"},
                {"name": "大模型应用", "heat": 8600, "trend": "up", "category": "科技"},
                {"name": "智能客服", "heat": 7200, "trend": "stable", "category": "企业服务"},
                {"name": "自动化运维", "heat": 6500, "trend": "up", "category": "技术"},
                {"name": "RAG技术", "heat": 5800, "trend": "up", "category": "AI"},
            ],
            "keywords": [
                {"keyword": "Agent", "search_volume": 125000, "change": "+15%"},
                {"keyword": "多Agent", "search_volume": 85000, "change": "+28%"},
                {"keyword": "自动化", "search_volume": 250000, "change": "+5%"},
            ],
            "insights": [
                "用户对 AI Agent 的实际落地案例最感兴趣",
                "技术教程类内容完播率最高",
                "对话式内容更容易引发讨论"
            ]
        }
    
    def _parse_angles(self, text: str) -> list[str]:
        """解析切入角度"""
        # 简化解析逻辑
        angles = []
        for line in text.split('\n'):
            if '-' in line or '•' in line:
                angle = line.lstrip('-• ').strip()
                if angle:
                    angles.append(angle)
        return angles[:5]
    
    def _parse_topics(self, text: str) -> list[dict]:
        """解析选题"""
        import json
        try:
            # 尝试提取 JSON
            import re
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                data = json.loads(match.group())
                return data.get("topics", [])
        except:
            pass
        return self._generate_mock_topics(5)
    
    def _generate_mock_topics(self, count: int) -> list[dict]:
        """生成模拟选题"""
        return [
            {
                "title": f"AI Agent 实战案例 #{i+1}",
                "angle": f"从{i+1}个真实企业场景看 Agent 落地",
                "keywords": ["Agent", "自动化", "企业应用"],
                "estimated_views": f"{random.randint(5, 50)}万"
            }
            for i in range(count)
        ]


class LLMAdapter:
    """LLM 适配器 - 对接各种 LLM API"""
    
    def __init__(self, provider: str = "openai", api_key: str = "", base_url: str = ""):
        self.provider = provider
        self.api_key = api_key
        self.base_url = base_url or "https://api.openai.com/v1"
        self.model = "gpt-4"
    
    async def generate(self, prompt: str, system_prompt: str = "", **kwargs) -> str:
        """生成文本"""
        # 这里可以接入实际的 API
        # 暂时返回模拟结果
        return f"[LLM 模拟响应] 基于提示词: {prompt[:50]}..."
    
    async def generate_json(self, prompt: str, schema: dict, **kwargs) -> dict:
        """生成 JSON 结构化数据"""
        # 实际实现可以调用支持 JSON mode 的 API
        response = await self.generate(prompt, **kwargs)
        import json
        try:
            import re
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                return json.loads(match.group())
        except:
            pass
        return {}
