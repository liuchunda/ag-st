agent teams

队友agent不能派生新的队友agent

messagesbus 文件收信箱 消息总线
spawn_agent
agent发送消息是往messagesbus加一条数据，另一个agent读完删除

主agent开启队友agent，然后往邮箱里派发任务

队友agent的循环，和队友agent循环是独立的
队友agent给领导发送消息是发到lead.json
team_tool
每个agent都有一个.json邮箱
 队友agent完成任务给主agent发送消息，主agent在下轮大模型时接受到消息

子任务会阻塞主agent，队友agent不会阻塞主agent
队友agent可以实现中途双向通信。可以和主agent并行

开发步骤
1.添加系统提示词，如果遇到复杂的问题，可以调用spawn_teamate/send_mesages 派发队友，
添加工具：spawn_teamate name 队友名字，role队友角色，prompt 提示词

添加工具：send_mesages


通过收信箱进行通信，收信箱就是每个agent一个json文件
每一个队友agent都是一个独立的线程

权限冒泡，队友agent发给主agenr，主agent由人审核，结果在返回给队友agent

任务系统是团队共享的

任务的发送
1.主agent通过提示词派发
2.自动认领
3.
利用contextVar维护全局变量，维护currentagent 

主agent循环时每次都会读取信箱