"""
Agent 配置管理
"""

from dataclasses import dataclass, field
from typing import Any
import yaml
from pathlib import Path


@dataclass
class LLMConfig:
    """大语言模型配置"""
    provider: str = "openai"  # openai / anthropic / local
    model: str = "gpt-4"
    api_key: str = ""
    base_url: str = "https://api.openai.com/v1"
    temperature: float = 0.7
    max_tokens: int = 2000
    timeout: int = 60


@dataclass
class PlatformConfig:
    """发布平台配置"""
    name: str
    enabled: bool = True
    api_key: str = ""
    api_secret: str = ""
    channel_id: str = ""
    webhook_url: str = ""


@dataclass
class AgentConfig:
    """Agent 配置"""
    name: str
    role: str
    description: str
    llm: LLMConfig = field(default_factory=LLMConfig)
    system_prompt: str = ""
    max_retries: int = 3
    timeout: int = 300
    
    # 平台配置
    platforms: list[PlatformConfig] = field(default_factory=list)


@dataclass 
class SystemConfig:
    """系统配置"""
    project_name: str = "多Agent协同运营系统"
    log_level: str = "INFO"
    data_dir: str = "./data"
    
    # Agent 配置
    manager: AgentConfig = field(default_factory=lambda: AgentConfig(
        name="Manager",
        role="manager",
        description="任务协调者"
    ))
    
    researcher: AgentConfig = field(default_factory=lambda: AgentConfig(
        name="Researcher",
        role="researcher", 
        description="热点研究员"
    ))
    
    writer: AgentConfig = field(default_factory=lambda: AgentConfig(
        name="Writer",
        role="writer",
        description="内容写作者"
    ))
    
    editor: AgentConfig = field(default_factory=lambda: AgentConfig(
        name="Editor",
        role="editor",
        description="文字编辑"
    ))
    
    publisher: AgentConfig = field(default_factory=lambda: AgentConfig(
        name="Publisher",
        role="publisher",
        description="多平台发布"
    ))
    
    @classmethod
    def from_yaml(cls, path: str) -> "SystemConfig":
        """从 YAML 文件加载配置"""
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return cls(**data)
    
    def to_yaml(self, path: str) -> None:
        """保存配置到 YAML 文件"""
        with open(path, 'w', encoding='utf-8') as f:
            yaml.dump(self._to_dict(), f, allow_unicode=True, default_flow_style=False)
    
    def _to_dict(self) -> dict:
        """转换为字典"""
        return {
            "project_name": self.project_name,
            "log_level": self.log_level,
            "data_dir": self.data_dir,
        }


def load_default_config() -> SystemConfig:
    """加载默认配置"""
    return SystemConfig()


def load_config(path: str = "config.yaml") -> SystemConfig:
    """加载配置文件"""
    if Path(path).exists():
        return SystemConfig.from_yaml(path)
    return load_default_config()
