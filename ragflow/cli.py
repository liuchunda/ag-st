import logging
import sys
import argparse
import json
from rich import print
from pipeline import RAGFlowPipeline
from config import RAGConfig
from utils import print_answer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s ",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def cmd_ingest(args):
    # 创建RAG主流程编排器的实例
    pipeline = RAGFlowPipeline(RAGConfig.from_env())
    # 调用ingest_file方法入库文件
    chunks = pipeline.ingest_file(args.path)
    print(json.dumps({"file": args.path, chunks: chunks}, ensure_ascii=False, indent=2))


def cmd_query(args):
    pipeline = RAGFlowPipeline(RAGConfig.from_env())
    result = pipeline.ask(args.question)
    print_answer(result)


def build_parser():
    # 创建顶层的parser,设置程序描述与帮助格式化器
    parser = argparse.ArgumentParser(
        # 设置程序用途说明
        description="RAG知识库 文件入库+问答",
        # 指定原始描述帮助格式化器 保留描述中的换行和缩进
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    # 添加子命令解析器，将结果写入args.command且必须指定子命令
    # uv run cli.py ingest --path handbook.md
    # uv run cli.py query --question 公司年假怎么申请？ dest  destination  不是description
    # 子命令的参数会合并到args命名空间中，所有的参数都会在同一个对象里
    sub = parser.add_subparsers(dest="command", required=True)  # type: ignore
    # ingest在RAG/向量数据库意思是数据摄入/注入，指的是把原始的数据经过处理后存入数据库的过程
    # 指的是数据摄入流程，指的是把非结构化的数据(PDF/网页/WORD)经过清理-切块-向量化-存入向量数据库的过程
    # 添加名为ingest的子命令，用于文件入库
    p_ingest = sub.add_parser("ingest", help="入库的文件")
    # 为ingest子命令添加必填的参数 --path,  表示待入库的文件
    p_ingest.add_argument("--path", required=True, help="文件路径")
    # 为ingest子命令指定默认的处理函数 cmd_ingest
    p_ingest.set_defaults(func=cmd_ingest)

    # 添加名为query的子命令，用于用户问答
    p_ingest = sub.add_parser("query", help="问答")
    # 为ingest子命令添加必填的参数 --path,  表示待入库的文件
    p_ingest.add_argument("--question", required=True, help="用户问题")
    # 为ingest子命令指定默认的处理函数 cmd_query
    p_ingest.set_defaults(func=cmd_query)
    return parser


def main():
    # 构建命令行参数解析器
    parser = build_parser()
    # 解析命令行参数，得到命名空间对象args
    args = parser.parse_args()
    # Namespace(command='ingest', path='handbook.md', func=<function cmd_ingest at 0x00000274CCD3E0C0>)
    try:
        args.func(args)
        return 0
    # 捕获用户按下ctrl+c产生的键盘中断异常
    except KeyboardInterrupt:
        print("\n已经中断")
        # 130是标准的键盘中断退出码
        return 130
    except Exception as exc:
        # 记录完整的异常堆栈，提示执行失败
        logger.exception("执行命令失败")
        # 将错误信息输出到标准错误流中
        print(f"[错误]{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    main()
