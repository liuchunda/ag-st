import json
import sys
import argparse


# python scripts/format.py  --pretty "{\"name\":\"zhangsan\",\"age\":\"18\"}"
def main():
    parser = argparse.ArgumentParser(description="处理JSON数据")
    parser.add_argument("--pretty", help="美化输出")
    args = parser.parse_args()
    print(args)
    try:
        data = json.loads(args.pretty)
        print(data)
        print(json.dumps(data, indent=2, ensure_ascii=False))
    except json.JSONDecodeError as e:
        print(f"JSON语法错误:{e}")
        sys.exit(1)


if __name__ == "__main__":
    main()


# windows的缺陷 windows 的CMD和powershell不支持单引号，只认双引号，且内部双引号需要转义
