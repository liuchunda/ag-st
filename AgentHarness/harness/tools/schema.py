# 用于定义工具的函数，接收函数名称、函数描述、属性和必填的字段,返回一个字典
def _fn_tool(
    name: str, description: str, properties: dict, requried: list[str]
) -> dict:
    return {
        "type": "function",  # 类型是函数
        "function": {  # 函数的具体内容
            "name": name,  # 函数名称
            "description": description,  # 函数描述
            "parameters": {  # 参数设置，是一个对象，包含属性和必需字段
                "type": "object",
                "properties": properties,
                "requried": requried,
            },
        },
    }


# 子代理的工具
BASE_TOOLS = [
    _fn_tool(
        "bash",
        "执行一条shell命令，耗时操作可设置 run_in_background=true在后台运行",
        {
            "command": {"type": "string"},
            "run_in_background": {"type": "boolean", "default": False},
        },
        ["command"],
    ),
    _fn_tool(
        "read_file",
        "读取文件内容",
        {"path": {"type": "string"}, "limit": {"type": "integer"}},
        ["path"],
    ),
    _fn_tool(
        "write_file",
        "将内容写入文件",
        {"path": {"type": "string"}, "content": {"type": "string"}},
        ["path", "content"],
    ),
    _fn_tool(
        "edit_file",
        "在文件中精确替换一段文件(仅替换一次)",
        {
            "path": {"type": "string"},
            "old_text": {"type": "string"},
            "new_text": {"type": "string"},
        },
        ["path", "old_text", "new_text"],
    ),
    _fn_tool(
        "glob",
        "按glob模式查找文件",
        {"pattern": {"type": "string"}},
        ["pattern"],
    ),
    #   _fn_tool(
    #       "todo_write",  # 名称
    #       "创建并管理当前编码会话的任务列表。",  # 描述
    #       {
    #           "todos": {
    #               "type": "array",
    #               "items": {
    #                   "type": "object",
    #                   "properties": {
    #                       "content": {"type": "string"},  # 子任务的内容
    #                       "status": {  # 子任务的状态
    #                           "type": "string",
    #                           "enum": [
    #                               "pending",  # 待执行
    #                               "in_progress",  # 进行中
    #                               "completed",  # 已完成
    #                           ],
    #                       },
    #                   },
    #                   "required": ["content", "status"],
    #               },
    #           }
    #       },
    #       ["todos"],
    #   ),
    _fn_tool(
        "create_task",
        "创建新任务，可选blockedBy依赖",
        {
            "subject": {"type": "string"},
            "description": {"type": "string"},
            "blockedBy": {"type": "array", "items": {"type": "string"}},
        },
        ["subject"],
    ),
    _fn_tool(
        "list_tasks",
        "列出所有的任务的状态、负责人与依赖",
        {},
        [],
    ),
    _fn_tool(
        "get_task",
        "按任务ID获取任务完整详情",
        {"task_id": {"type": "string"}},
        ["task_id"],
    ),
    _fn_tool(
        "claim_task",
        "认领pending状态的任务，设置owner并把状态改为in_progress",
        {"task_id": {"type": "string"}},
        ["task_id"],
    ),
    _fn_tool(
        "complete_task",
        "完成状态为in_progress的任务，并报告下游解阻任务",
        {"task_id": {"type": "string"}},
        ["task_id"],
    ),
    _fn_tool(
        "delete_task",
        "删除已完成的任务",
        {"task_id": {"type": "string"}},
        ["task_id"],
    ),
    _fn_tool(
        "schedule_cron",
        "调度cron任务，cron为5段： 分 时 日 月 周",
        {
            "cron": {"type": "string", "description": "5段cron表达式"},
            "prompt": {"type": "string", "description": "触发时要注入的消息"},
            "recurring": {"type": "boolean", "description": "True=循环，False=单次"},
            "durable": {"type": "boolean", "description": "True=持久化到磁盘"},
        },
        ["cron", "prompt"],
    ),
    _fn_tool(
        "list_crons",
        "列出已经注册的Cron任务",
        {},
        [],
    ),
    _fn_tool(
        "cancel_cron",
        "按ID取消cron任务",
        {"job_id": {"type": "string", "description": "任务ID"}},
        ["job_id"],
    ),
    _fn_tool(
        "spawn_teammate",
        "启动自主队友 Agent。（idle轮询任务看板，自动认领任务）",
        {
            "name": {"type": "string", "description": "队友的名字"},
            "role": {"type": "string", "description": "队友的角色"},
            "prompt": {"type": "string"},
        },
        ["name", "role", "prompt"],
    ),
    _fn_tool(
        "send_message",
        "通过MessageBUS发送消息，发送方固定为当前的Agent身份，不可伪造",
        {"to": {"type": "string"}, "content": {"type": "string"}},
        ["to", "content"],
    ),
    _fn_tool(
        "check_inbox",
        "检查自己的收件箱(队友回信)",
        {},
        [],
    ),
    _fn_tool(
        "request_shutdown",
        "请求队友优雅关闭",
        {"teammate": {"type": "string"}},
        ["teammate"],
    ),
    _fn_tool(
        "request_plan",
        "要求队友提交计划供审核",
        {
            "teammate": {"type": "string"},  # 队友的名字
            "task": {"type": "string"},  # 计划是关于什么的计划
        },
        ["teammate", "task"],
    ),
    _fn_tool(
        "submit_plan",
        "向Lead提交计划待审核",
        {
            "from_name": {"type": "string"},  # 谁提交的
            "plan": {"type": "string"},  # 计划本身
        },
        ["from_name", "plan"],  #
    ),
    _fn_tool(
        "review_plan",
        "按request_id批准或拒绝已经提交的计划",
        {
            "request_id": {"type": "string"},  # 请求ID
            "approve": {"type": "boolean"},  # 是否审批通过
            "feedback": {
                "type": "string"
            },  # 失败的反馈，如果没审核通过，在这里告知拒绝的原因
        },
        ["request_id", "approve"],
    ),
    _fn_tool(
        "await_teammates",
        "阻塞等待队友完成并发送result,可指定names;默认等待全部待回收队友，派工后、向用户汇报前调用",
        {
            "names": {
                "type": "array",
                "items": {"type": "string"},
                "description": "要等待的队友名列表，省略则等待全部pending的队友",
            },  # 请求ID
            "timeout": {
                "type": "number",
                "description": "最长等待秒数",
            },
        },
        [],
    ),
    _fn_tool(
        "create_worktree",
        "创建隔离的git worktree及独立分支 wt/{name}。可选task_id绑定任务(不改任务状态)",
        {
            "name": {"type": "string", "description": "worktree名称，仅[A-Za-z0-9._-]"},
            "task_id": {"type": "string", "description": "可选，绑定到该任务"},
        },
        ["name"],
    ),
    _fn_tool(
        "remove_worktree",
        "删除worktree。有未提交变更时拒绝，除非 discard_change=True",
        {
            "name": {"type": "string", "description": "worktree名称"},
            "discard_change": {
                "type": "boolean",
                "description": "强制丢弃未提交的改动",
            },
        },
        ["name"],
    ),
    _fn_tool(
        "keep_worktree",
        "保留worktree。供人工审查(不删除目录与分支)",
        {
            "name": {
                "type": "string",
            },
        },
        ["name"],
    ),
    _fn_tool(
        "connect_mcp",
        "连接MCP服务器并发现外部工具，可用: docs、deploy。连接后工具名前缀为mcp__",
        {
            "name": {
                "type": "string",
                "description": "MCP服务器的名称，如docs或deploy",
            },
        },
        ["name"],
    ),
]
# 主代理的工具
TOOLS = [
    *BASE_TOOLS,
    _fn_tool(
        "spawn_subagent",
        "启动子Agent处理复杂子任务，仅返回最终结论",
        {
            "description": {"type": "string"},
        },
        ["description"],
    ),
    _fn_tool(
        "load_skill",
        "按名称加载技能的完整内容",
        {
            "name": {"type": "string"},
        },
        ["name"],
    ),
    _fn_tool(
        "compact",
        "摘要较早的对话以释放上下文的空间",
        {
            "focus": {"type": "string"},
        },
        [],
    ),
]
