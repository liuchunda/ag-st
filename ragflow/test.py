# from pathlib import Path
import argparse
# print(Path('./chroma_db/ss').mkdir(parents=True,exist_ok=True))

# path = Path('./chroma_db/chroma.sqlite3').resolve()
# print(path.is_file())


parser = argparse.ArgumentParser(
    # description="RAG知识库 文件入库+问答",
    add_help=False,
    epilog="我是结尾",
    usage="我是使用说明",
    formatter_class=argparse.RawDescriptionHelpFormatter,
)

parser.add_argument("-h", "--help", action="help", help="查看帮助")

parser.add_argument("--path", help="文件路径")  # 显示在该参数那一行

# parser.add_parser("ingest", help="入库文件")  # 子命令列表里显示


def cmd_ingest(args):
    print("入库:", args.path)
    print("名称:", args.name)
    print("xxx:", args.xxx)
def cmd_query(args):
    print("问答:", args.question)

sub = parser.add_subparsers(dest="command")

p1 = sub.add_parser("ingest", help="入库文件")
p1.add_argument("--path", required=True)
p1.add_argument("--name")
p1.add_argument("--mode", choices=["fast", "full"], default="fast")
p1.set_defaults(func=cmd_ingest,xxx=123) #可以配置新参数和默认值，如果参数在命令行中没有提供，则使用默认值



p2 = sub.add_parser("query", help="问答")
p2.add_argument("--question", required=True)
p2.set_defaults(func=cmd_query)


args = parser.parse_args()
print(args.name)
args.func(args)

# args = parser.parse_args()  # 关键：必须有这一行
# print(args.path)
# print(type(args))
