#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
多Agent协同运营自动化系统 - 主程序
Multi-Agent Collaborative Operations Automation System
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from multi_agent_system.message import MessageQueue
from multi_agent_system.config import (
    SystemConfig, AgentConfig, LLMConfig,
    load_default_config, load_config
)
from multi_agent_system.manager import ManagerAgent
from multi_agent_system.researcher import ResearcherAgent, LLMAdapter
from multi_agent_system.writer import WriterAgent
from multi_agent_system.editor import EditorAgent
from multi_agent_system.publisher import PublisherAgent


# 配置日志
def setup_logging(level: str = "INFO") -> None:
    """配置日志"""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


class ContentOpsSystem:
    """内容运营系统"""
    
    def __init__(self, config: SystemConfig = None):
        self.config = config or load_default_config()
        self.message_queue = MessageQueue()
        
        # Agent 实例
        self.manager: ManagerAgent = None
        self.researcher: ResearcherAgent = None
        self.writer: WriterAgent = None
        self.editor: EditorAgent = None
        self.publisher: PublisherAgent = None
        
        # LLM 适配器
        self.llm_adapter = None
        
        # 运行状态
        self._running = False
    
    async def initialize(self) -> None:
        """初始化系统"""
        logging.info("=" * 60)
        logging.info("初始化多Agent协同运营系统...")
        logging.info("=" * 60)
        
        # 初始化 LLM 适配器
        llm_config = self.config.manager.llm
        if llm_config.api_key:
            self.llm_adapter = LLMAdapter(
                provider=llm_config.provider,
                api_key=llm_config.api_key,
                base_url=llm_config.base_url
            )
            logging.info(f"LLM 适配器已初始化: {llm_config.provider}/{llm_config.model}")
        else:
            logging.warning("未配置 API Key，将使用模拟模式")
        
        # 创建并注册 Agent
        self.manager = ManagerAgent(self.config.manager, self.message_queue)
        self.researcher = ResearcherAgent(self.config.researcher, self.message_queue, self.llm_adapter)
        self.writer = WriterAgent(self.config.writer, self.message_queue, self.llm_adapter)
        self.editor = EditorAgent(self.config.editor, self.message_queue, self.llm_adapter)
        self.publisher = PublisherAgent(self.config.publisher, self.message_queue, self.llm_adapter)
        
        # 注册 Agent
        self.manager.register_agent("Researcher", self.researcher)
        self.manager.register_agent("Writer", self.writer)
        self.manager.register_agent("Editor", self.editor)
        self.manager.register_agent("Publisher", self.publisher)
        
        # 初始化所有 Agent
        await self.manager.initialize()
        await self.researcher.initialize()
        await self.writer.initialize()
        await self.editor.initialize()
        await self.publisher.initialize()
        
        # 注册回调
        self.manager.on_status_change(self._on_status_change)
        self.manager.on_completion(self._on_task_completion)
        
        logging.info("系统初始化完成！")
        logging.info("=" * 60)
    
    async def shutdown(self) -> None:
        """关闭系统"""
        logging.info("正在关闭系统...")
        
        self._running = False
        
        await self.manager.shutdown()
        await self.researcher.shutdown()
        await self.writer.shutdown()
        await self.editor.shutdown()
        await self.publisher.shutdown()
        
        logging.info("系统已关闭")
    
    async def run_interactive(self) -> None:
        """交互式运行"""
        self._running = True
        
        print("\n" + "=" * 60)
        print("🎯 多Agent协同运营系统 - 交互模式")
        print("=" * 60)
        print("\n可用命令：")
        print("  create <主题>           - 创建内容任务")
        print("  status [任务ID]         - 查看任务状态")
        print("  list                    - 列出所有任务")
        print("  platforms               - 查看支持的平台")
        print("  quit/exit               - 退出系统")
        print("\n" + "-" * 60)
        
        while self._running:
            try:
                user_input = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: input("\n📝 请输入命令: ").strip()
                )
                
                if not user_input:
                    continue
                
                cmd_parts = user_input.split(maxsplit=1)
                cmd = cmd_parts[0].lower()
                args = cmd_parts[1] if len(cmd_parts) > 1 else ""
                
                await self._handle_command(cmd, args)
                
            except KeyboardInterrupt:
                print("\n\n收到退出信号...")
                break
            except Exception as e:
                logging.error(f"命令执行错误: {e}")
        
        await self.shutdown()
    
    async def _handle_command(self, cmd: str, args: str) -> None:
        """处理命令"""
        if cmd in ["quit", "exit", "q"]:
            await self.shutdown()
        
        elif cmd == "create":
            if not args:
                print("❌ 请提供主题，例如: create AI Agent发展趋势分析")
                return
            await self._cmd_create_task(args)
        
        elif cmd == "status":
            await self._cmd_status(args)
        
        elif cmd == "list":
            await self._cmd_list_tasks()
        
        elif cmd == "platforms":
            self._cmd_show_platforms()
        
        elif cmd == "help":
            self._cmd_show_help()
        
        else:
            print(f"❌ 未知命令: {cmd}，输入 help 查看可用命令")
    
    async def _cmd_create_task(self, topic: str) -> None:
        """创建任务命令"""
        print(f"\n📋 正在创建内容任务: {topic}")
        print("-" * 40)
        
        # 解析平台
        platforms = ["zhihu", "juejin"]  # 默认平台
        
        task_id = await self.manager.create_task(
            topic=topic,
            platforms=platforms,
            requirements={
                "style": "tutorial",
                "word_count": 2000,
                "keywords": topic.split()
            }
        )
        
        print(f"✅ 任务已创建！")
        print(f"   任务ID: {task_id}")
        print(f"   主题: {topic}")
        print(f"   平台: {', '.join(platforms)}")
        print("\n⏳ 任务执行中，请稍候...")
    
    async def _cmd_status(self, task_id: str = "") -> None:
        """查看状态命令"""
        if not task_id:
            # 显示最新任务状态
            if self.manager.tasks:
                task = list(self.manager.tasks.values())[-1]
                self._print_task_status(task)
            else:
                print("📭 暂无任务")
        else:
            task = self.manager.tasks.get(task_id)
            if task:
                self._print_task_status(task)
            else:
                print(f"❌ 未找到任务: {task_id}")
    
    async def _cmd_list_tasks(self) -> None:
        """列出任务命令"""
        if not self.manager.tasks:
            print("📭 暂无任务")
            return
        
        print("\n📋 所有任务列表:")
        print("-" * 60)
        print(f"{'任务ID':<10} {'主题':<30} {'状态':<12} {'阶段'}")
        print("-" * 60)
        
        for task in self.manager.tasks.values():
            topic = task.topic[:28] + ".." if len(task.topic) > 30 else task.topic
            print(f"{task.task_id:<10} {topic:<30} {task.status.value:<12} {task.current_stage.value}")
    
    def _cmd_show_platforms(self) -> None:
        """显示支持的平台"""
        platforms = [
            ("wechat_public", "微信公众号"),
            ("zhihu", "知乎"),
            ("juejin", "掘金"),
            ("xiaohongshu", "小红书"),
            ("jianshu", "简书"),
            ("bili", "B站"),
        ]
        
        print("\n📦 支持的发布平台:")
        print("-" * 40)
        for pid, name in platforms:
            print(f"  • {pid:<15} - {name}")
    
    def _cmd_show_help(self) -> None:
        """显示帮助"""
        print("\n🆘 帮助信息")
        print("-" * 40)
        print("create <主题>     - 创建内容任务")
        print("status [任务ID]   - 查看任务状态")
        print("list              - 列出所有任务")
        print("platforms        - 查看支持的平台")
        print("quit/exit         - 退出系统")
    
    def _print_task_status(self, task) -> None:
        """打印任务状态"""
        print(f"\n📊 任务状态 - {task.task_id}")
        print("-" * 40)
        print(f"  主题: {task.topic}")
        print(f"  状态: {task.status.value}")
        print(f"  阶段: {task.current_stage.value}")
        print(f"  已完成: {', '.join(task.stages_completed) if task.stages_completed else '无'}")
        print(f"  平台: {', '.join(task.platforms)}")
        print(f"  创建: {task.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        
        if task.error_message:
            print(f"  ❌ 错误: {task.error_message}")
        elif task.status.value == "completed":
            print(f"  ✅ 已完成: {task.completed_at.strftime('%Y-%m-%d %H:%M:%S')}")
    
    def _on_status_change(self, task, event: str) -> None:
        """状态变更回调"""
        events = {
            "research_started": "🔍 开始研究热点...",
            "research_completed": "✅ 研究完成！",
            "writing_started": "✍️ 开始撰写文章...",
            "writing_completed": "✅ 文章撰写完成！",
            "editing_started": "📝 开始编辑润色...",
            "editing_completed": "✅ 编辑完成！",
            "publishing_started": "📤 开始发布...",
            "completed": "🎉 任务全部完成！",
            "failed": "❌ 任务失败"
        }
        
        msg = events.get(event, f"📌 事件: {event}")
        print(f"\n{msg}")
        print(f"   任务: {task.topic}")
    
    def _on_task_completion(self, task) -> None:
        """任务完成回调"""
        print("\n" + "=" * 60)
        print("🎉 内容运营任务完成报告")
        print("=" * 60)
        print(f"📌 主题: {task.topic}")
        print(f"📋 任务ID: {task.task_id}")
        print(f"✅ 完成阶段: {', '.join(task.stages_completed)}")
        print(f"📦 已发布到: {', '.join(task.platforms)}")
        
        if task.article_data:
            print(f"\n📄 文章信息:")
            print(f"   标题: {task.article_data.get('title', 'N/A')}")
        
        print("=" * 60)
    
    async def run_demo(self) -> None:
        """运行演示"""
        print("\n" + "=" * 60)
        print("🎯 多Agent协同运营系统 - 演示模式")
        print("=" * 60)
        
        # 创建演示任务
        demo_topics = [
            "AI Agent 实战：从入门到精通",
            "多Agent协同系统的设计与实现",
            "大模型在内容运营中的应用"
        ]
        
        for i, topic in enumerate(demo_topics):
            print(f"\n📋 演示任务 {i+1}/{len(demo_topics)}: {topic}")
            print("-" * 40)
            
            await self.manager.create_task(
                topic=topic,
                platforms=["zhihu", "juejin"],
                requirements={
                    "style": "tutorial",
                    "word_count": 1500
                }
            )
            
            # 等待一小段时间
            await asyncio.sleep(2)
        
        print("\n⏳ 等待任务完成...")
        
        # 等待所有任务完成
        max_wait = 60
        waited = 0
        while waited < max_wait:
            await asyncio.sleep(2)
            waited += 2
            
            completed = sum(
                1 for t in self.manager.tasks.values()
                if t.status.value in ["completed", "failed"]
            )
            
            if completed >= len(demo_topics):
                break
            
            print(f"   进度: {completed}/{len(demo_topics)} 任务已完成...")
        
        print("\n" + "=" * 60)
        print("📊 演示完成！")
        print("=" * 60)


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="多Agent协同运营系统")
    parser.add_argument("-c", "--config", default="config.yaml", help="配置文件路径")
    parser.add_argument("-m", "--mode", choices=["interactive", "demo", "api"],
                        default="interactive", help="运行模式")
    parser.add_argument("-v", "--verbose", action="store_true", help="详细输出")
    parser.add_argument("-t", "--topic", help="直接指定主题运行")
    
    args = parser.parse_args()
    
    # 配置日志
    setup_logging("DEBUG" if args.verbose else "INFO")
    
    # 加载配置
    if Path(args.config).exists():
        config = load_config(args.config)
    else:
        config = load_default_config()
        logging.warning(f"配置文件 {args.config} 不存在，使用默认配置")
    
    # 创建系统
    system = ContentOpsSystem(config)
    
    try:
        # 初始化
        await system.initialize()
        
        # 根据模式运行
        if args.topic:
            # 直接执行单个任务
            await system.manager.create_task(
                topic=args.topic,
                platforms=["zhihu", "juejin"]
            )
            await asyncio.sleep(30)  # 等待完成
            
        elif args.mode == "demo":
            await system.run_demo()
            
        elif args.mode == "interactive":
            await system.run_interactive()
            
        elif args.mode == "api":
            # API 模式，保持运行
            logging.info("API 模式已启动，按 Ctrl+C 退出")
            while True:
                await asyncio.sleep(1)
    
    except KeyboardInterrupt:
        logging.info("收到退出信号")
    except Exception as e:
        logging.error(f"系统错误: {e}", exc_info=True)
    finally:
        await system.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
