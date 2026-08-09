

如果你不加这句话，让它用CMD，它会先使用linux bash命令先尝试，失败了以后才会换到CMD命令


# 输出为什么要加限制，不可以无限输出吗？
因为技术和成本双重原因，不可能无限输出，必须限制
1. 算力成本 每个token都需要计算，无限输出=无限的GPU的无限消耗，成本失控
2. 工程的稳定性 模型可能会陷入死循环，或者胡说八道
3. 另在技术成本 LLm内部用是transformer架构，生成的自回归的 一个字一个字往外蹦，长度越长计算量呈平方级增加，越来效果越差


# harness engineering 驾驭工程
指的是AI智能体设计和构建约束机制、反馈回路，工作流程控制，以及持续改进循环的系统工程实践



# del /q tmp\\*
del  windows的删除文件的命令 等同于linux rm 
/q 静默模式 quiet  不提示确认，直接删除
tmp/* 删除tmp目录下面的所有的文件


请帮我读取a.txt、b.txt、c.txt三个文件的内容并输出结果
a和c成功了，b失败了
然后你把这个结果 反馈给AI大模型

#claude code中的/bwt指令是不是也是类似的原理，开启一个子进程，用主Agent的上下文发起临时查询？\

正确，核心机制也是类似于临时子任务的思路，但是细节不太一样

/btw 指令  不是开启独立子进程，而在当前会话中创建一个轻量级的临时链，复用主会话的上下文和提示词缓存，但是
回答后的结果不会写入主对话历史，实现零污染并行回答


# encoding 指定字符编码 通常为utf-8
# errors="replace" 指定解码失败的时候的处理策略，replace替换，指的是用 乱码符号�替换无法解码的字节，防止程序崩溃
# errors 有几个可选策略
  - strict 严格格式 如果遇到解码失败就会抛出UnicodeDecodeError错误
  - replace 容忍乱码，确保程序不中断，用�替换掉坏的字节
  - ignore 跳过坏字节，丢弃异常数据
  - backslashreplace 用\xXX转义  如果遇到解码失败显示成原始字节


skill中 scripts/目录用于存放可执行脚本，可以帮助skill实现功能的复杂核心执行
- my-skill
  - SKILL.md 指令文件 加载到上下文中去
  - scripts
    - extract.py 提取pdf文档的内容
    - process.h  shell脚本
    - data
      - config.json 辅助数据

- 执行方式 calude 通过bash工具调用脚本，不加载源码到上下文中
- 触发时机  skill.md文件加载后，claude会根据指令 决定什么时候执行哪个脚本，获取什么结果
- 输入输出 通过命令行参数传递输入参数，通过stdout/stderr返回结果

常用脚本类型
python 可以处理复杂逻辑 pDF解析 文件格式转式
shell/bash 系统操作相关的命令 配置环境变量
node.js  前端相关脚本 可以实现打包构建 npm run build 解析AST语法


_  - 中划线和下划线并没有固定硬性要求
目录名 用中划线  tool-results 这是个linux惯例
变量名 下划线  tool_result
域名   my-site
字段名  tool_result
CSS类名  my-home

messages = [
 user,
 assistant, tool_call.id
 tool,
 user,
 assistant(两个tool call ids) 开始要求新的一轮工具调用，要求之前的tool call都要已经有了对应的tool
 tool,
 tool
]

messags = [
  {"role":"user"},
  {"role":"assistant","tool_calls":[{"id":"call_ids"},{}]}
]


# prompt cache
定义: LLM API 对重复输入前缀(比如说系统提示词)进行缓存复用，跳过重复计算，仅处理增量内容- 
- 降低成本 缓存命中后费用降低50%-90%  DeepSeep  缓存的成本只有原来1%
- 提速 首token延迟降低50%-50
- 适合场景  长系统提示词 RAG上下文  多轮对话历史

# 工作原理
- 首次请求需要计算完整的输入 ，缓存中间的Key-Value状态
- 后续请求检测到相同的前缀， 复用Key-Value缓存，仅计算新的内容 

# 注意事项
-  一定要精确前缀匹配 空格 换行 差异都会导致缓存失效 
- 缓存的时间一般是5-10分钟

client.messags.create(
  messages=[{"role":"user","content"："1+1=?"}]
)
client.messags.create(
  messages=[{"role":"user","content"："1+1=?"},{"role":"user","content"："2+2=?"}]
)
斐波那契序列
从第3项开始 ，每项=前两项之和
F(0)=0,F(1)=1
F(n)=F(n-1)+F(n-2)

F(3)
F(4)

F(5)=F(4)+F(3)
# prompt cache  使用了 前缀缓存 和 kv 缓存 是吧
Prompt Cache核心是使用了前缀缓存和KV缓存的结合
前缀缓存(Prefix Cache)  缓存的是输入文本的前缀(字符串)，匹配相同开头的请求，复用计算结果
KV缓存(Key Value Cache) transformer中间状态 跳过重复部分的模型计算

第一次请求  "你是谁？"
大模型  计算完整的KV  - 缓存前缀 和所有的KV层
你  v1
你是 v2
你是谁 v3 
你是谁？ v4

第二次请求 "你是谁？今天天气怎么样?"
前缀匹配你是谁？直接复用v4 ，仅计算后面的今天天气怎么样?就可以了



# 整个messages都是提示词
messages = [
  #不变放前面
  {"role":"system","content":"你是一个Agent"},
  {"role":"user"}
  ...
  # 有可能变化的放在后面

]

# kebab-case
#定义 使用 连字符(-)连接小写单词的命名方式，所有的字符都是小写的
分隔符用连字符- user-profile
大小写 全小写
长度一般比较短，2到4个词

camelCase userProfile js常用
PascalCase UserProfile  类名常用
snake_case user_profile python变量名常用
kebab-case user-profile  HTML类名 文件名文件目录名比较常用
SCREAMING_SNAKRE USER_PROFILE 常用比较常用


#  rounds_since_todo
1. 不管有没有使用todowrite,不管现在有没有当前尚未完成的任务，都会每3轮一次。
2. 现在这个提醒放在了messages里面，会污染上下文


执行任务，计算1+1=？和2+2=？和3+3=？和4+4=？和5+5=？（先列出5个步骤再执行）

有些Agent会给记忆添加一个半衰期的概念
每个记忆文件有记录的时间

指的是记忆的重要性/权重会随着时间而指数衰减，越久远的记忆影响越小
新的权重 =原始权重x(0.5)^(时间差/半衰期)

# 比如codex, 记忆和自定义指令冲突时，以哪个为准
在codex里，当记忆memories和自定义指令 AGENTS.md冲突的时候，以正定义指令为准

AutoDream

# max_tokens
API参数，限制模型输出的最大Token数
截断truncation  输出达到max_tokens限制时会强行切断
首次恢复策略  增大max_tokens并重新请求，不添加任何合成续写消息

方法A
response = "这是一段被截断的"
如果这个时候让它续写
人工拼接 或请继续
final = response +"..." 污染原始输出

方法B 直接增加预算并重试
首次请求max_tokens = 8000 截断
再次请求max_tokens=64000 得到完整输出

# 429 529是返回的异常码吗？
429 Too Many Requests 请求过多 客户端错误
520 Site is Overloaded 站点过载 服务器端错误

# 有向无环图（DAG）
定义  一种有方向，但无环的图结构 ，由节点和有向边组成，不能从栽个节点出发沿方向回到自身
有方向 可以表示任务依赖关系
无环 a-b-c-dxa 避免死循环
排序  可排序为线性序列 前置任务在前


你写一首中文诗歌，然后再把它翻译成英文，你可以创建两个任务


完成某个任务后，（更新其他依赖任务的状态），llm 如何感知其他任务的状态改变了，然后规划其他任务的执行的？

完成某个任务后，并没有更新其它依赖的任务状态
只是给大模型说，有哪些任务可以被认领执行了

#with background_lock是怎么加锁的？
with background_lock 是一个上下文管理器(Context Manger),自动获取和释放锁
等同于以下写法

background_lock.acquire() # 加锁
执行线程安全的操作
background_lock.release() #解锁 释放锁


安排一个每 5 分钟在控制台打印helloworld的持久化任务

# 现在的问题是每子线程与大模型的对话执行完就重置了current_agent ，销毁退出了，你给他发的消息，它也没有机会读，current_agent.name 重置，也拿不到


1. 队长让队友提交一个工作计划
2. 队友向队长提交这个工作计划，要求审批
3. 队长看完这个工作计划，认为可能，审批通过
4. 队友看到审批结果执行工作计划
5. 队友执行完成工作计划后把执行结果发给队长
6. 队长看完认为工作成功完成


派 bob 创建一张用户表的schema.sql，request_plan 让他 submit_plan，批准后 review_plan 通过


1. spawn_teammate {"name": "bob", "role": "数据库开发工程师", "prompt": "你的任务是根据要求创建 user.sql 文件}
2. [总线] lead->bob [message]:请提交计划:创建 user.sql 文件，基于项目已有的 schema.sql 中 users 表
3. [总线] bob->lead [plan_approval_request]:## 计划：创建 user.sql 文件
   req_id=req_672791 status="pending"  type="plan_approval" 
4. 队长review_plan {"request_id": "req_672791", "approve": true, "feedback": "计划清晰合理，批准执行"} 
   req_id=req_672791 status="approved"
5. lead->bob [plan_approval_response]:计划清晰合理， 协议 计划 √ req_672791
6. bob 在空闲的收到1条消息 lead->bob [plan_approval_response]:计划清晰合理开始执行创建文件的任务
7. 文件创建成功之后 [总线] bob->lead [result]:✅ **`user.sql已经成功创建
8. Idle bob 超时 120秒，自动关闭 [队友]bob已经结束



1.在这个案例中 派 bob 创建一张用户表的schema.sql，request_plan 让他 submit_plan，批准后 review_plan 通过
ProtocolState实例是在哪里创建的？
队长处理后会调用run_review_plan ，用LLM给的值去修改 state.status = "approved" if approve else "rejected"



spawn bob 和 carol 两个队友，再 create_task 三条互不依赖的小任务，观察谁自动认领了哪条。


创建三个任务，计算1+1=？（完成计算后暂停1秒后再返回），计算2+2=?（完成计算后暂停1秒后再返回）,计算3+3=？（完成计算后暂停1秒后再返回）。然后派生bob 和 alice 两个队友,观察谁自动认领了哪条。


创建隔离的git worktree及独立分支

创建一个分支login，并且再创建一个 worktree,把login分支检出到此worktree里

创建两个任务，第一个任务是在README.md里添加一首诗，第二个任务是个任务在README.md里添加一道数学题，为这二个任务分别创建 worktree（用 task_id 绑定）。启动 alice 和 bob。观察他们自动认领任务，并在各自隔离的目录中工作。
