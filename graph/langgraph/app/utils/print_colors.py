class Colors:
  RED = '\033[91m'      # 红色
  GREEN = '\033[92m'    # 绿色
  YELLOW = '\033[93m'   # 黄色
  BLUE = '\033[94m'     # 蓝色
  MAGENTA = '\033[95m'  # 洋红/紫色
  CYAN = '\033[96m'     # 青色
  BOLD = '\033[1m'      # 加粗
  END = '\033[0m'       # 重置颜色


def print_red(text):  # 红色
  print(f"{Colors.RED}{text}{Colors.END}")


def print_green(text):  # 绿色
  print(f"{Colors.GREEN}{text}{Colors.END}")


def print_yellow(text):  # 黄色
  print(f"{Colors.YELLOW}{text}{Colors.END}")


def print_blue(text):  # 蓝色
  print(f"{Colors.BLUE}{text}{Colors.END}")


def print_cyan(text):  # 青色
  print(f"{Colors.CYAN}{text}{Colors.END}")


def print_magenta(text):  # 洋红/紫色
  print(f"{Colors.MAGENTA}{text}{Colors.END}")


def print_bold(text):  # 加粗（不单独用，配合其他颜色）
  print(f"{Colors.BOLD}{text}{Colors.END}")