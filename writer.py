"""
写作者 Agent - 内容创作
"""

from typing import Optional
from dataclasses import dataclass
import asyncio
import random

from .base import BaseAgent
from .message import Message, MessageType
from .config import AgentConfig


@dataclass
class ArticleContent:
    """文章内容"""
    title: str = ""
    subtitle: str = ""
    outline: list[str] = None
    sections: list[dict] = None
    tags: list[str] = None
    keywords: list[str] = None
    meta_description: str = ""
    
    def __post_init__(self):
        self.outline = self.outline or []
        self.sections = self.sections or []
        self.tags = self.tags or []
        self.keywords = self.keywords or []
    
    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "subtitle": self.subtitle,
            "outline": self.outline,
            "sections": self.sections,
            "tags": self.tags,
            "keywords": self.keywords,
            "meta_description": self.meta_description,
        }


class WriterAgent(BaseAgent):
    """写作者 Agent"""
    
    def __init__(self, config: AgentConfig, message_queue, llm_adapter=None):
        super().__init__(config, message_queue)
        self.llm = llm_adapter
        self.templates: dict = {}
        self.style_guide: dict = {}
        self._load_templates()
    
    def _get_default_system_prompt(self) -> str:
        return """你是一位专业的内容创作者，精通各类文章写作。

你的核心能力：
1. 撰写高质量技术文章和深度分析
2. 创作吸引人的标题和开场
3. 根据不同平台调整内容风格
4. SEO 友好的内容结构

写作风格：
- 专业但不晦涩
- 逻辑清晰，层次分明
- 善用案例和数据支撑观点
- 结尾要有行动号召或讨论引导"""
    
    def _load_templates(self) -> None:
        """加载内容模板"""
        self.templates = {
            "tutorial": {
                "structure": ["问题背景", "解决方案", "实现步骤", "代码示例", "总结展望"],
                "style": "技术教程"
            },
            "analysis": {
                "structure": ["现象描述", "原因分析", "影响评估", "趋势预测", "应对建议"],
                "style": "深度分析"
            },
            "news": {
                "structure": ["事件概述", "关键信息", "各方反应", "后续发展", "简短点评"],
                "style": "新闻快讯"
            },
            "opinion": {
                "structure": ["观点提出", "论证过程", "案例支撑", "反驳预判", "结论升华"],
                "style": "观点评论"
            }
        }
    
    async def _handle_message(self, message: Message) -> None:
        """处理消息"""
        content = message.content
        
        if message.msg_type == MessageType.TASK_REQUEST:
            action = content.get("action")
            
            if action == "write_article":
                await self._write_article(content)
            elif action == "generate_title":
                await self._generate_titles(content)
            elif action == "rewrite_section":
                await self._rewrite_section(content)
            elif action == "expand_content":
                await self._expand_content(content)
    
    async def _write_article(self, content: dict) -> None:
        """写文章"""
        self.update_status("working")
        task_id = content.get("task_id")
        
        try:
            topic = content.get("topic", "")
            style = content.get("style", "tutorial")
            platform = content.get("platform", "通用")
            word_count = content.get("word_count", 2000)
            
            self.logger.info(f"Writing article: {topic}")
            
            # 1. 生成标题
            title_result = await self._generate_titles_internal(topic, style, count=3)
            
            # 2. 生成大纲
            outline = await self._generate_outline(topic, style, word_count)
            
            # 3. 撰写各章节
            sections = []
            for section_title in outline:
                section_content = await self._write_section(
                    topic, section_title, style, platform
                )
                sections.append({
                    "title": section_title,
                    "content": section_content,
                    "word_count": len(section_content)
                })
            
            # 4. 生成元数据
            article = ArticleContent(
                title=title_result[0],
                subtitle=title_result[1] if len(title_result) > 1 else "",
                outline=outline,
                sections=sections,
                tags=self._extract_tags(topic),
                keywords=self._extract_keywords(topic, outline),
                meta_description=self._generate_meta_description(sections)
            )
            
            # 发送结果
            await self.send_message(
                "Manager",
                {
                    "action": "article_written",
                    "task_id": task_id,
                    "article": article.to_dict(),
                    "total_words": sum(s["word_count"] for s in sections),
                    "writing_time": "2分钟"
                },
                MessageType.TASK_RESPONSE,
                task_id
            )
            
        except Exception as e:
            await self.send_message(
                "Manager",
                {
                    "action": "writing_failed",
                    "task_id": task_id,
                    "error": str(e)
                },
                MessageType.TASK_FAILED,
                task_id
            )
        finally:
            self.update_status("idle")
    
    async def _generate_titles(self, content: dict) -> None:
        """生成标题"""
        topic = content.get("topic", "")
        style = content.get("style", "tutorial")
        count = content.get("count", 5)
        
        titles = await self._generate_titles_internal(topic, style, count)
        
        await self.send_message(
            "Manager",
            {
                "action": "titles_generated",
                "titles": titles
            },
            MessageType.RESPONSE
        )
    
    async def _generate_titles_internal(self, topic: str, style: str, count: int) -> list[str]:
        """内部生成标题方法"""
        if self.llm:
            prompt = f"""为以下主题生成{count}个吸引人的标题：

主题：{topic}
风格：{style}

要求：
1. 标题要吸引人，激发点击欲望
2. 可以使用数字、疑问、对比等技巧
3. 长度适中（15-30字）

直接返回标题列表，每行一个，不要其他内容。"""
            
            result = await self.llm.generate(prompt, system_prompt=self.system_prompt)
            titles = [t.strip() for t in result.split('\n') if t.strip()]
            return titles[:count]
        
        # 模拟标题
        templates = [
            f"深入解析：{topic}的核心原理与实践",
            f"从入门到精通：{topic}完全指南",
            f"{topic}的{count}个关键知识点",
            f"为什么{topic}如此重要？",
            f"关于{topic}，你可能不知道的事",
        ]
        return templates[:count]
    
    async def _generate_outline(self, topic: str, style: str, word_count: int) -> list[str]:
        """生成文章大纲"""
        template = self.templates.get(style, self.templates["tutorial"])
        outline = template["structure"].copy()
        
        # 根据风格调整
        if self.llm:
            prompt = f"""为以下主题生成文章大纲：

主题：{topic}
风格：{style}
目标字数：{word_count}字

请返回大纲结构，用换行分隔。"""
            
            result = await self.llm.generate(prompt, system_prompt=self.system_prompt)
            outline = [line.strip() for line in result.split('\n') if line.strip()]
        
        return outline
    
    async def _write_section(self, topic: str, section_title: str, style: str, platform: str) -> str:
        """撰写章节"""
        # 模拟章节内容
        content_templates = {
            "问题背景": f"""在当今快速发展的技术领域，{topic}已经成为不可忽视的重要趋势。

根据最新数据显示，超过70%的企业已经开始关注并尝试引入相关技术。然而，在实际落地过程中，仍有不少挑战需要克服。

本文将带你深入了解{topic}，从原理到实践，循序渐进地掌握这一技术。""",

            "解决方案": f"""针对{topic}，我们提出了一套完整的解决方案：

**核心思路**：以实际业务需求为导向，循序渐进地推进落地。

**关键步骤**：
1. 需求分析与技术选型
2. 原型设计与快速验证
3. 迭代优化与规模扩展

通过这一方案，我们可以有效降低实施风险，提高项目成功率。""",

            "实现步骤": """**第一步：环境准备**
```python
# 安装必要的依赖
pip install relevant-packages

# 验证安装
python -c "import package; print(package.__version__)"
```

**第二步：基础配置**
```python
# 初始化配置
config = {
    'api_key': 'your-api-key',
    'model': 'gpt-4',
    'temperature': 0.7
}
```

**第三步：核心代码实现**
```python
# 创建 Agent 实例
agent = Agent(config)

# 定义任务
task = {
    'type': 'content_generation',
    'input': '用户需求描述'
}

# 执行任务
result = await agent.run(task)
```""",

            "代码示例": """下面是一个完整的示例代码：

```python
import asyncio
from agent_framework import Agent, Task

async def main():
    # 初始化 Agent
    agent = Agent(
        model="gpt-4",
        tools=["search", "calculator", "code_interpreter"]
    )
    
    # 创建任务
    task = Task(
        description="分析竞品内容策略",
        constraints={"time_limit": 300}
    )
    
    # 执行
    result = await agent.execute(task)
    print(f"Result: {result}")

if __name__ == "__main__":
    asyncio.run(main())
```

运行上述代码，你将得到一个完整的竞品分析报告。""",

            "总结展望": f"""通过本文的介绍，相信你对{topic}已经有了全面的了解。

**核心要点回顾**：
- {topic}的核心价值在于降本增效
- 实施过程中要注意循序渐进
- 持续优化是成功的关键

**未来展望**：
随着技术的不断发展，{topic}将会有更多的应用场景。我们建议企业持续关注这一领域的发展动态，及时调整策略。

如果你有任何问题或想法，欢迎在评论区留言交流！""",

            "总结": """以上就是关于这个主题的详细介绍。希望本文对你有所帮助。

**下一步行动**：
1. 动手实践本文中的代码示例
2. 根据自己的业务场景进行调整
3. 与团队成员分享讨论

如果你觉得本文有价值，欢迎转发给需要的朋友。"""
        }
        
        # 返回匹配的内容或生成默认内容
        for key, content in content_templates.items():
            if key in section_title:
                return content
        
        return f"这一部分将详细讲解{section_title}相关的核心概念和实践方法。\n\n在实际应用中，需要注意以下几点：\n\n1. **理论准备**：充分理解基础概念\n2. **实践验证**：通过小规模实验验证想法\n3. **持续优化**：根据反馈不断改进\n\n接下来，让我们深入探讨。"
    
    async def _rewrite_section(self, content: dict) -> None:
        """重写章节"""
        original = content.get("content", "")
        rewrite_type = content.get("type", "简化")  # 简化/扩展/改写风格
        
        if self.llm:
            prompt = f"""将以下内容进行{rewrite_type}：

{original}

要求：
- 保持核心信息不变
- 调整表达方式
- 优化阅读体验"""
            
            result = await self.llm.generate(prompt, system_prompt=self.system_prompt)
        else:
            result = f"[已{rewrite_type}] {original[:100]}..."
        
        await self.send_message(
            content.get("recipient", "Manager"),
            {
                "action": "section_rewritten",
                "original": original,
                "rewritten": result,
                "type": rewrite_type
            },
            MessageType.RESPONSE
        )
    
    async def _expand_content(self, content: dict) -> None:
        """扩展内容"""
        base_content = content.get("content", "")
        target_words = content.get("target_words", 1000)
        
        expansion = await self._expand_text(base_content, target_words)
        
        await self.send_message(
            "Manager",
            {
                "action": "content_expanded",
                "original": base_content,
                "expanded": expansion,
                "original_words": len(base_content),
                "expanded_words": len(expansion)
            },
            MessageType.RESPONSE
        )
    
    async def _expand_text(self, text: str, target_words: int) -> str:
        """扩展文本"""
        if self.llm:
            prompt = f"""将以下内容扩展至约{target_words}字：

{text}

要求：
- 保持原意
- 增加细节和案例
- 逻辑连贯"""
            
            return await self.llm.generate(prompt, system_prompt=self.system_prompt)
        
        # 模拟扩展
        current_words = len(text)
        expansion_ratio = target_words / current_words if current_words > 0 else 1
        
        if expansion_ratio > 1.5:
            return text + f"\n\n此外，{text[:50]}这一主题还有更多值得深入探讨的方面。通过不断学习和实践，我们可以更好地掌握相关技能，提升专业能力。"
        
        return text
    
    def _extract_tags(self, topic: str) -> list[str]:
        """提取标签"""
        base_tags = ["AI", "Agent", "自动化", "技术"]
        topic_keywords = topic.split("：")[-1].split("、")
        return list(set(base_tags + topic_keywords))[:5]
    
    def _extract_keywords(self, topic: str, outline: list[str]) -> list[str]:
        """提取关键词"""
        keywords = topic.replace("：", " ").replace("、", " ").split()
        for section in outline:
            keywords.extend(section.split("：")[-1].split())
        return list(set(keywords))[:8]
    
    def _generate_meta_description(self, sections: list[dict]) -> str:
        """生成元描述"""
        if sections and sections[0].get("content"):
            first_content = sections[0]["content"]
            return first_content[:150] + "..." if len(first_content) > 150 else first_content
        return "本文深入探讨了相关主题，提供实用的解决方案和实践指南。"
