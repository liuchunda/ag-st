import re


# 定义MCPCLient类，在MCP服务器上发现和调用工具
class MCPClient:
    def __init__(self, name) -> None:
        self.name = name
        self.tools = []
        self._handlers = {}

    # 注册方法，注册工具定义和对应在处理函数
    def register(self, tool_defs, handlers):
        self.tools = tool_defs
        self._handlers = handlers

    def call_tool(self, tool_name, args):
        handler = self._handlers.get(tool_name)
        if not handler:
            return f"MCP错误，未知工具{tool_name}"
        try:
            return str(handler(**args))
        except Exception as e:
            return f"MCP工具调用错误:{str(e)}"


# 存放已经连接的MCP客户端的集合，键为字符串，值为MCPClient实例

# 定义非法字符的正则表达式（非 a-zA-Z0-9_-），用于名称标准化
_DISALLOWED_CHARS = re.compile(r"[^a-zA-Z0-9_-]")

mcp_clients = {}


# 构造 mock "docs" 服务器，返回对应 MCPClient
def _mock_server_docs() -> MCPClient:
    # 创建 MCPClient 实例，名称为 'docs'
    client = MCPClient("docs")
    # 注册工具定义及处理函数
    client.register(
        tool_defs=[
            {
                "name": "search",
                "description": "搜索文档。（只读）",
                "inputSchema": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
            },
            {
                "name": "get_version",
                "description": "获取 API 版本。（只读）",
                "inputSchema": {"type": "object", "properties": {}, "required": []},
            },
        ],
        handlers={
            "search": lambda query: f"[docs] 找到 3 条与 '{query}' 相关的结果",
            "get_version": lambda: "[docs] API v2.1.0",
        },
    )
    # 返回 mock 的 client 实例
    return client


# 构造 mock "deploy" 服务器，返回对应 MCPClient
def _mock_server_deploy() -> MCPClient:
    # 创建 MCPClient 实例，名称为 'deploy'
    client = MCPClient("deploy")
    # 注册工具定义及处理函数
    client.register(
        tool_defs=[
            {
                "name": "trigger",
                "description": "触发部署。",
                "inputSchema": {
                    "type": "object",
                    "properties": {"service": {"type": "string"}},
                    "required": ["service"],
                },
            },
            {
                "name": "status",
                "description": "查询部署状态。（只读）",
                "inputSchema": {
                    "type": "object",
                    "properties": {"service": {"type": "string"}},
                    "required": ["service"],
                },
            },
        ],
        handlers={
            "trigger": lambda service: f"[deploy] 已触发: {service}",
            "status": lambda service: f"[deploy] {service}: 运行中 (v1.4.2)",
        },
    )
    # 返回 mock 的 client 实例
    return client


# MOCK_SERVERS 字典，服务器名到工厂函数的映射
MOCK_SERVERS = {
    "docs": _mock_server_docs,
    "deploy": _mock_server_deploy,
}


def connect_mcp(name):
    if name in mcp_clients:
        return f"MCP服务器{name}已经连接"
    factory = MOCK_SERVERS.get(name)
    if not factory:
        avaliable = ",".join(MOCK_SERVERS.keys())
        return f"未知的服务器{name},可用的服务器{avaliable}"
    mcp_client = factory()
    mcp_clients[name] = mcp_client
    tool_names = [t["name"] for t in mcp_client.tools]
    print(f"\x1b[33m  已经连接上了MCP服务器：{name} -> {tool_names}\x1b[0m")
    return (
        f"已经连接到了MCP服务器:{name}"
        f"发现了{len(mcp_client.tools)}个工具：{','.join(tool_names)}"
    )


# 连接指定名秒的MCP服务器
def run_connect_mcp(name: str):
    return connect_mcp(name)


def normalize_mcp_name(name):
    return _DISALLOWED_CHARS.sub("_", name)


def _mcp_tool_to_openai(prefixed: str, tool_def: dict):
    from tools.schema import _fn_tool

    schema = tool_def.get("inputSchema", {})
    return _fn_tool(
        prefixed,  # 工具名称
        tool_def.get("description", ""),  # 工具描述
        schema.get("properties", {}),  # 工具参数的说明
        schema.get("required", []),  # 必填参数
    )


# 合并builtin工具和所有已经连接的MCP工具，返回统一的工具池和处理函数字典
def assemble_tool_pool():
    from tools.schema import TOOLS
    from tools.handlers import TOOL_HANDLERS

    tools = list(TOOLS)
    handlers = dict(TOOL_HANDLERS)
    for server_name, mcp_client in mcp_clients.items():
        safe_server = normalize_mcp_name(server_name)
        for tool_def in mcp_client.tools:
            safe_tool = normalize_mcp_name(tool_def["name"])
            prefixed = f"mcp__{safe_server}__{safe_tool}"
            tools.append(_mcp_tool_to_openai(prefixed, tool_def))

            def _make_handler(client: MCPClient, tname: str):
                def _handler(**kwargs):
                    return client.call_tool(tname, kwargs)

                return _handler

            handlers[prefixed] = _make_handler(mcp_client, tool_def["name"])
    return tools, handlers


def connected_mcp_summary():
    """供system_prompt追加：当前已经连接的MCP及带前缀的工具名"""
    if not mcp_clients:
        return ""
    lines = ["已经连接MCP服务器(工具名带mcp_server_tool前缀):"]
    for server_name, mcp_client in mcp_clients.items():
        safe_server = normalize_mcp_name(server_name)
        for tool_def in mcp_client.tools:
            safe_tool = normalize_mcp_name(tool_def["name"])
            prefixed = f"mcp__{safe_server}__{safe_tool}"
            description = tool_def.get("description", "")
            lines.append(f"- {prefixed}:{description}")
    return "\n".join(lines)
