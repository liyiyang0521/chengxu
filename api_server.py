#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
多Agent协同运营系统 - API 服务
Flask API Server for Multi-Agent System
"""

import asyncio
import json
import logging
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# 日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class APIServer:
    """API 服务器"""
    
    def __init__(self, system):
        self.system = system
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
    
    def run_async(self, coro):
        """在线程中运行异步代码"""
        return self.loop.run_until_complete(coro)
    
    async def create_task_api(self, data: dict) -> dict:
        """创建任务 API"""
        topic = data.get("topic", "")
        platforms = data.get("platforms", ["zhihu", "juejin"])
        requirements = data.get("requirements", {})
        
        if not topic:
            return {"success": False, "error": "topic is required"}
        
        task_id = await self.system.manager.create_task(
            topic=topic,
            platforms=platforms,
            requirements=requirements
        )
        
        return {
            "success": True,
            "task_id": task_id,
            "message": "Task created successfully"
        }
    
    async def get_task_status_api(self, task_id: str) -> dict:
        """获取任务状态 API"""
        task = self.system.manager.tasks.get(task_id)
        
        if not task:
            return {"success": False, "error": "Task not found"}
        
        return {
            "success": True,
            "task": task.to_dict()
        }
    
    async def list_tasks_api(self) -> dict:
        """列出任务 API"""
        tasks = [
            task.to_dict() 
            for task in self.system.manager.tasks.values()
        ]
        
        return {
            "success": True,
            "tasks": tasks,
            "count": len(tasks)
        }
    
    async def get_publish_history_api(self, limit: int = 20) -> dict:
        """获取发布历史 API"""
        history = self.system.publisher.publish_history[-limit:]
        
        stats = {
            "total": len(self.system.publisher.publish_history),
            "success": sum(1 for h in self.system.publisher.publish_history if h.get("success")),
            "failed": sum(1 for h in self.system.publisher.publish_history if not h.get("success"))
        }
        
        return {
            "success": True,
            "history": history,
            "stats": stats
        }


# 全局系统实例
_system = None
_api_server = None


def init_system():
    """初始化系统"""
    global _system, _api_server
    
    if _system is None:
        from main import ContentOpsSystem
        from multi_agent_system.config import load_default_config
        
        config = load_default_config()
        _system = ContentOpsSystem(config)
        
        # 初始化
        asyncio.get_event_loop().run_until_complete(_system.initialize())
        
        _api_server = APIServer(_system)
        
        logger.info("System initialized")
    
    return _system, _api_server


@app.route("/api/health", methods=["GET"])
def health_check():
    """健康检查"""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "system": "multi-agent-ops"
    })


@app.route("/api/tasks", methods=["POST"])
def create_task():
    """创建任务"""
    _, api_server = init_system()
    
    data = request.get_json()
    result = api_server.run_async(api_server.create_task_api(data))
    
    return jsonify(result)


@app.route("/api/tasks", methods=["GET"])
def list_tasks():
    """列出任务"""
    _, api_server = init_system()
    
    result = api_server.run_async(api_server.list_tasks_api())
    
    return jsonify(result)


@app.route("/api/tasks/<task_id>", methods=["GET"])
def get_task_status(task_id):
    """获取任务状态"""
    _, api_server = init_system()
    
    result = api_server.run_async(api_server.get_task_status_api(task_id))
    
    return jsonify(result)


@app.route("/api/publish/history", methods=["GET"])
def get_publish_history():
    """获取发布历史"""
    _, api_server = init_system()
    
    limit = request.args.get("limit", 20, type=int)
    result = api_server.run_async(api_server.get_publish_history_api(limit))
    
    return jsonify(result)


@app.route("/api/platforms", methods=["GET"])
def get_platforms():
    """获取支持的平台"""
    return jsonify({
        "success": True,
        "platforms": [
            {"id": "wechat_public", "name": "微信公众号", "enabled": True},
            {"id": "zhihu", "name": "知乎", "enabled": True},
            {"id": "juejin", "name": "掘金", "enabled": True},
            {"id": "xiaohongshu", "name": "小红书", "enabled": False},
            {"id": "jianshu", "name": "简书", "enabled": False},
            {"id": "bili", "name": "B站", "enabled": False},
        ]
    })


if __name__ == "__main__":
    print("=" * 60)
    print("🚀 多Agent协同运营系统 API 服务")
    print("=" * 60)
    print("API 端点:")
    print("  GET  /api/health           - 健康检查")
    print("  POST /api/tasks            - 创建任务")
    print("  GET  /api/tasks            - 列出任务")
    print("  GET  /api/tasks/<id>       - 获取任务状态")
    print("  GET  /api/publish/history  - 发布历史")
    print("  GET  /api/platforms        - 支持的平台")
    print("=" * 60)
    
    app.run(host="0.0.0.0", port=5000, debug=True)