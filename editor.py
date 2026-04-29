"""
编辑 Agent - 文字润色与排版优化
"""

from typing import Optional, Callable
from dataclasses import dataclass
import asyncio
import re

from .base import BaseAgent
from .message import Message, MessageType
from .config import AgentConfig


@dataclass
class EditResult:
    """编辑结果"""
    original: str
    edited: str
    changes: list[dict]  # 变更记录
    statistics: dict     # 统计信息
    
    def to_dict(self) -> dict:
        return {
            "original": self.original,
            "edited": self.edited,
            "changes": self.changes,
            "statistics": self.statistics,
        }


class EditorAgent(BaseAgent):
    """编辑 Agent"""
    
    def __init__(self, config: AgentConfig, message_queue, llm_adapter=None):
        super().__init__(config, message_queue)
        self.llm = llm_adapter
        
        # 编辑规则
        self.grammar_rules: list[dict] = []
        self.style_rules: list[dict] = []
        self.seo_rules: list[dict] = []
        self._load_rules()
    
    def _get_default_system_prompt(self) -> str:
        return """你是一位资深的内容编辑，精通各类文字润色和排版优化。

你的核心能力：
1. 语法纠错和表达优化
2. 文章风格统一
3. SEO 友好的内容调整
4. 多平台排版适配

工作原则：
- 尊重原文意图，不改变核心观点
- 润色但不过度修饰
- 注重阅读体验
- 保持专业性和可读性的平衡"""
    
    def _load_rules(self) -> None:
        """加载编辑规则"""
        self.grammar_rules = [
            {"pattern": r"\s+", "replacement": " ", "description": "多空格合并"},
            {"pattern": r"([。！？])(\S)", "replacement": r"\1 \2", "description": "标点后加空格"},
            {"pattern": r"\"([^\"]+)\"", "replacement": r"「\1」", "description": "引号转换"},
        ]
        
        self.style_rules = [
            {"pattern": r"非常", "replacement": "十分/相当", "description": "避免过度使用"},
            {"pattern": r"我觉得", "replacement": "笔者认为", "description": "书面语优化"},
            {"pattern": r"而且", "replacement": "并且", "description": "连接词优化"},
        ]
        
        self.seo_rules = [
            {"keyword_density": 0.02, "description": "关键词密度2%左右"},
            {"first_paragraph_length": 100, "description": "首段不超过100字"},
            {"heading_keywords": True, "description": "小标题包含关键词"},
        ]
    
    async def _handle_message(self, message: Message) -> None:
        """处理消息"""
        content = message.content
        
        if message.msg_type == MessageType.TASK_REQUEST:
            action = content.get("action")
            
            if action == "edit_article":
                await self._edit_article(content)
            elif action == "polish_text":
                await self._polish_text(content)
            elif action == "format_for_platform":
                await self._format_for_platform(content)
            elif action == "add_images_suggestions":
                await self._add_images_suggestions(content)
    
    async def _edit_article(self, content: dict) -> None:
        """编辑整篇文章"""
        self.update_status("working")
        task_id = content.get("task_id")
        
        try:
            article = content.get("article", {})
            sections = article.get("sections", [])
            platform = content.get("platform", "通用")
            
            edited_sections = []
            all_changes = []
            total_original_words = 0
            total_edited_words = 0
            
            for section in sections:
                original_text = section.get("content", "")
                section_title = section.get("title", "")
                
                total_original_words += len(original_text)
                
                # 1. 语法纠错
                edited = await self._fix_grammar(original_text)
                
                # 2. 风格优化
                edited = await self._optimize_style(edited)
                
                # 3. 平台适配
                edited = await self._adapt_platform(edited, platform)
                
                # 4. SEO 优化
                edited = await self._optimize_seo(edited, article.get("keywords", []))
                
                total_edited_words += len(edited)
                
                edited_sections.append({
                    **section,
                    "content": edited,
                    "edited": True
                })
                
                all_changes.append({
                    "section": section_title,
                    "original_length": len(original_text),
                    "edited_length": len(edited),
                    "changes_made": ["语法纠错", "风格优化", "平台适配", "SEO优化"]
                })
            
            # 生成编辑报告
            result = EditResult(
                original="",
                edited="",
                changes=all_changes,
                statistics={
                    "original_words": total_original_words,
                    "edited_words": total_edited_words,
                    "sections_edited": len(sections),
                    "grammar_fixes": len(all_changes),
                    "style_improvements": len(all_changes),
                    "platforms_optimized": [platform]
                }
            )
            
            await self.send_message(
                "Manager",
                {
                    "action": "article_edited",
                    "task_id": task_id,
                    "edited_article": {
                        **article,
                        "sections": edited_sections
                    },
                    "edit_result": result.to_dict()
                },
                MessageType.TASK_RESPONSE,
                task_id
            )
            
        except Exception as e:
            await self.send_message(
                "Manager",
                {
                    "action": "editing_failed",
                    "task_id": task_id,
                    "error": str(e)
                },
                MessageType.TASK_FAILED,
                task_id
            )
        finally:
            self.update_status("idle")
    
    async def _polish_text(self, content: dict) -> None:
        """润色文本"""
        text = content.get("text", "")
        polish_level = content.get("level", "moderate")  # light / moderate / heavy
        
        if self.llm:
            level_instructions = {
                "light": "轻微润色，只修正明显的语法错误和不通顺的表达",
                "moderate": "中等润色，优化表达方式，提升可读性",
                "heavy": "深度润色，全面优化文章质量，可能调整结构"
            }
            
            prompt = f"""对以下文本进行{polish_level}程度的润色：

{text}

要求：{level_instructions.get(polish_level, level_instructions['moderate'])}

直接返回润色后的文本，不要解释。"""
            
            polished = await self.llm.generate(prompt, system_prompt=self.system_prompt)
        else:
            polished = self._apply_rules(text)
        
        await self.send_message(
            content.get("recipient", "Manager"),
            {
                "action": "text_polished",
                "original": text,
                "polished": polished,
                "level": polish_level
            },
            MessageType.RESPONSE
        )
    
    async def _format_for_platform(self, content: dict) -> None:
        """格式化内容以适配平台"""
        article = content.get("article", {})
        platform = content.get("platform", "微信公众号")
        
        platform_formats = {
            "微信公众号": {
                "line_break_style": "double",
                "max_line_length": None,
                "heading_style": "emoji_prefix",
                "code_style": "fenced",
                "image_placeholder": "【图片】"
            },
            "知乎": {
                "line_break_style": "single",
                "max_line_length": None,
                "heading_style": "sharp_prefix",
                "code_style": "fenced",
                "image_placeholder": "![图片说明](图片URL)"
            },
            "掘金": {
                "line_break_style": "single",
                "max_line_length": None,
                "heading_style": "markdown",
                "code_style": "fenced_with_lang",
                "image_placeholder": "![图片说明](图片URL)"
            },
            "小红书": {
                "line_break_style": "emoji_separator",
                "max_line_length": 1000,
                "heading_style": "simple",
                "code_style": "none",
                "image_placeholder": "[图片]"
            }
        }
        
        format_config = platform_formats.get(platform, platform_formats["微信公众号"])
        formatted_sections = []
        
        for section in article.get("sections", []):
            formatted_content = self._apply_format(
                section.get("content", ""),
                format_config
            )
            formatted_sections.append({
                **section,
                "content": formatted_content
            })
        
        await self.send_message(
            "Manager",
            {
                "action": "article_formatted",
                "article": {
                    **article,
                    "sections": formatted_sections
                },
                "platform": platform,
                "format_config": format_config
            },
            MessageType.RESPONSE
        )
    
    async def _add_images_suggestions(self, content: dict) -> None:
        """添加图片建议"""
        article = content.get("article", {})
        platform = content.get("platform", "通用")
        
        suggestions = []
        section_count = len(article.get("sections", []))
        
        for i, section in enumerate(article.get("sections", [])):
            section_title = section.get("title", "")
            
            # 根据内容类型建议图片
            image_type = self._suggest_image_type(section.get("content", ""), section_title)
            
            suggestions.append({
                "position": i,
                "section": section_title,
                "suggested_type": image_type,
                "prompt": self._generate_image_prompt(section.get("content", ""), image_type),
                "alt_text": f"{section_title}配图",
                "caption": f"图{i+1}: {section_title}"
            })
        
        await self.send_message(
            "Manager",
            {
                "action": "images_suggested",
                "suggestions": suggestions,
                "total_images": len(suggestions)
            },
            MessageType.RESPONSE
        )
    
    async def _fix_grammar(self, text: str) -> str:
        """语法纠错"""
        if self.llm:
            prompt = f"""检查并修正以下文本的语法错误：

{text}

直接返回修正后的文本，不要说明修改了什么。"""
            
            return await self.llm.generate(prompt)
        
        return self._apply_rules(text, self.grammar_rules)
    
    async def _optimize_style(self, text: str) -> str:
        """风格优化"""
        if self.llm:
            prompt = f"""优化以下文本的表达方式，使其更加流畅和专业：

{text}

直接返回优化后的文本。"""
            
            return await self.llm.generate(prompt)
        
        return self._apply_rules(text, self.style_rules)
    
    async def _adapt_platform(self, text: str, platform: str) -> str:
        """平台适配"""
        # 根据平台调整
        if platform == "微信公众号":
            # 添加空行，适配微信阅读
            text = re.sub(r"\n\n+", "\n\n", text)
        elif platform == "知乎":
            # 知乎偏好简洁
            text = re.sub(r"\*\*", "**", text)
        elif platform == "小红书":
            # 小红书喜欢 emoji
            text = self._add_emojis(text)
        
        return text
    
    async def _optimize_seo(self, text: str, keywords: list) -> str:
        """SEO 优化"""
        if not keywords:
            return text
        
        # 确保关键词出现在开头
        if keywords and not any(k in text[:100] for k in keywords):
            # 在第一段添加关键词
            first_para_end = text.find("。")
            if first_para_end > 0 and first_para_end < 200:
                insert_pos = first_para_end + 1
                keyword_hint = f"（关键词：{', '.join(keywords[:3])}）"
                text = text[:insert_pos] + keyword_hint + text[insert_pos:]
        
        return text
    
    def _apply_rules(self, text: str, rules: list = None) -> str:
        """应用编辑规则"""
        rules = rules or (self.grammar_rules + self.style_rules)
        
        for rule in rules:
            if "pattern" in rule and "replacement" in rule:
                text = re.sub(
                    rule["pattern"],
                    rule["replacement"],
                    text
                )
        
        return text
    
    def _apply_format(self, text: str, config: dict) -> str:
        """应用格式化配置"""
        line_break_style = config.get("line_break_style", "double")
        
        if line_break_style == "double":
            text = text.replace("\n", "\n\n")
        elif line_break_style == "emoji_separator":
            emojis = ["📌", "💡", "⚡", "🔥", "✨"]
            lines = text.split("\n")
            text = "\n".join(
                f"{emojis[i % len(emojis)]} {line}" if line.strip() else ""
                for i, line in enumerate(lines)
            )
        
        return text
    
    def _suggest_image_type(self, content: str, section_title: str) -> str:
        """建议图片类型"""
        content_lower = content.lower()
        
        if any(k in content_lower for k in ["代码", "code", "python", "javascript"]):
            return "代码截图"
        elif any(k in content_lower for k in ["流程", "步骤", "过程"]):
            return "流程图"
        elif any(k in content_lower for k in ["数据", "统计", "图表"]):
            return "数据图表"
        elif any(k in content_lower for k in ["界面", "效果", "展示"]):
            return "界面截图"
        else:
            return "概念配图"
    
    def _generate_image_prompt(self, content: str, image_type: str) -> str:
        """生成图片提示词"""
        prompts = {
            "代码截图": f"Clean code screenshot with syntax highlighting, {content[:50]}...",
            "流程图": f"Professional flowchart diagram showing {content[:50]}...",
            "数据图表": f"Modern data visualization chart, {content[:50]}...",
            "界面截图": f"Modern UI design mockup, {content[:50]}...",
            "概念配图": f"Abstract tech illustration representing {content[:50]}..."
        }
        return prompts.get(image_type, f"Illustration for: {content[:50]}...")
    
    def _add_emojis(self, text: str) -> str:
        """添加 emoji"""
        # 简单添加 emoji
        text = re.sub(r"^##\s+(.+)$", r"## 💡 \1", text, flags=re.MULTILINE)
        text = re.sub(r"^###\s+(.+)$", r"### ⚡ \1", text, flags=re.MULTILINE)
        return text
