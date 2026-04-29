#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
使用示例
Usage Examples for Multi-Agent System
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from multi_agent_system.message import MessageQueue
from multi_agent_system.config import SystemConfig
from multi_agent_system.manager import ManagerAgent
from multi_agent_system.researcher import ResearcherAgent, LLMAdapter
from multi_agent_system.writer import WriterAgent
from multi_agent_system.editor import EditorAgent
from multi_agent_system.publisher import PublisherAgent


async def example_basic():
    """基础使用示例"""
    print("\n" + "=" * 60)
    print("示例1: 基础使用")
    print("=" * 60)
    
    # 1. 创建消息队列
    message_queue = MessageQueue()
    
    # 2. 创建 Agent
    llm = LLMAdapter(provider="mock")
    
    manager = ManagerAgent(
        AgentConfig(name="Manager", role="manager", description="协调者"),
        message_queue
    )
    
    researcher = ResearcherAgent(
        AgentConfig(name="Researcher", role="researcher", description="研究员"),
        message_queue,
        llm
    )
    
    writer = WriterAgent(
        AgentConfig(name="Writer", role="writer", description="写作者"),
        message_queue,
        llm
    )
    
    # 3. 注册 Agent
    manager.register_agent("Researcher", researcher)
    manager.register_agent("Writer", writer)
    
    # 4. 初始化
    await manager.initialize()
    await researcher.initialize()
    await writer.initialize()
    
    # 5. 创建任务
    task_id = await manager.create_task(
        topic="AI Agent 技术发展趋势",
        platforms=["zhihu", "juejin"]
    )
    
    print(f"任务已创建: {task_id}")
    
    # 6. 等待完成
    await asyncio.sleep(10)
    
    # 7. 查看结果
    task = manager.tasks.get(task_id)
    if task:
        print(f"任务状态: {task.status.value}")
        if task.article_data:
            print(f"文章标题: {task.article_data.get('title')}")
    
    # 8. 关闭
    await manager.shutdown()


async def example_with_callbacks():
    """带回调的示例"""
    print("\n" + "=" * 60)
    print("示例2: 带回调的使用")
    print("=" * 60)
    
    message_queue = MessageQueue()
    
    def on_status_change(task, event):
        print(f"[回调] 任务 {task.task_id} 状态变更: {event}")
    
    def on_completion(task):
        print(f"[回调] 任务 {task.task_id} 已完成!")
        print(f"       标题: {task.article_data.get('title', 'N/A')}")
    
    manager = ManagerAgent(
        AgentConfig(name="Manager", role="manager", description="协调者"),
        message_queue
    )
    
    # 注册回调
    manager.on_status_change(on_status_change)
    manager.on_completion(on_completion)
    
    await manager.initialize()
    
    # 创建任务
    task_id = await manager.create_task(
        topic="大模型应用开发指南",
        platforms=["zhihu"]
    )
    
    print(f"任务已创建: {task_id}")
    print("等待任务完成...\n")
    
    # 等待完成
    await asyncio.sleep(15)


async def example_single_agent():
    """单独使用某个 Agent"""
    print("\n" + "=" * 60)
    print("示例3: 单独使用 Writer Agent")
    print("=" * 60)
    
    message_queue = MessageQueue()
    llm = LLMAdapter(provider="mock")
    
    writer = WriterAgent(
        AgentConfig(name="Writer", role="writer", description="写作者"),
        message_queue,
        llm
    )
    
    await writer.initialize()
    
    # 直接调用写作者
    await writer.send_message(
        writer.name,
        {
            "action": "write_article",
            "task_id": "demo_001",
            "topic": "Python 异步编程实战",
            "style": "tutorial",
            "word_count": 1500
        }
    )
    
    print("文章撰写请求已发送")
    
    # 等待响应
    await asyncio.sleep(3)
    
    # 获取结果
    while message_queue.size() > 0:
        msg = message_queue.dequeue("Manager")
        if msg and msg.content.get("action") == "article_written":
            article = msg.content.get("article", {})
            print(f"\n文章已生成:")
            print(f"  标题: {article.get('title')}")
            print(f"  字数: {article.get('sections', [{}])[0].get('word_count', 0) * len(article.get('sections', []))}")
    
    await writer.shutdown()


def example_api_usage():
    """API 使用示例"""
    print("\n" + "=" * 60)
    print("示例4: API 调用")
    print("=" * 60)
    
    import requests
    
    base_url = "http://localhost:5000/api"
    
    # 1. 健康检查
    resp = requests.get(f"{base_url}/health")
    print(f"健康检查: {resp.json()}")
    
    # 2. 创建任务
    resp = requests.post(
        f"{base_url}/tasks",
        json={
            "topic": "AI Agent 实战案例",
            "platforms": ["zhihu", "juejin"],
            "requirements": {
                "style": "tutorial",
                "word_count": 2000
            }
        }
    )
    task_data = resp.json()
    print(f"\n任务创建: {task_data}")
    
    task_id = task_data.get("task_id")
    
    # 3. 查询状态
    if task_id:
        resp = requests.get(f"{base_url}/tasks/{task_id}")
        print(f"任务状态: {resp.json()}")
    
    # 4. 列出所有任务
    resp = requests.get(f"{base_url}/tasks")
    print(f"所有任务: {resp.json()}")


# Agent 配置类
from multi_agent_system.config import AgentConfig


async def main():
    """运行所有示例"""
    print("\n" + "#" * 60)
    print("# 多Agent协同运营系统 - 使用示例")
    print("#" * 60)
    
    try:
        await example_basic()
    except Exception as e:
        print(f"示例1执行出错: {e}")
    
    try:
        await example_with_callbacks()
    except Exception as e:
        print(f"示例2执行出错: {e}")
    
    try:
        await example_single_agent()
    except Exception as e:
        print(f"示例3执行出错: {e}")
    
    # API 示例需要先启动服务器
    # example_api_usage()
    
    print("\n" + "#" * 60)
    print("# 示例执行完成")
    print("#" * 60)


if __name__ == "__main__":
    asyncio.run(main())
