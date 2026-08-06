
Anaconda 公司出品
虚拟环境、Python 版本、各种包（含非纯 Python 的二进制库）
需要 NumPy / PyTorch / CUDA（NVIDIA 驱动；有时还要 CUDA Toolkit） 等，希望少踩编译坑的人

# macOS 用 Homebrew 示例
brew install --cask miniconda

# 按提示初始化（zsh）
conda init zsh
# 重开终端后可用
conda --version


# 创建带指定 Python 的环境
conda create -n myenv python=3.12

# 激活 / 退出
conda activate myenv

<!-- 导出配置文件，别人打开项目依赖这个配置文件 -->
<!-- 
文件示例
name: myenv
channels:
  - conda-forge
dependencies:
  - python=3.12
  - numpy
  - pip
  - pip:
    - fastapi
 -->
conda env export --from-history > environment.yml

conda deactivate

# 装包
conda install numpy
# 或
pip install fastapi

# 看环境列表
conda env list



# 别人维护
# 已装好 conda / miniforge 后，在项目根目录
# 创建 + 安装全部依赖
conda env create -f environment.yml 
conda activate myenv

# 你这边改完依赖后重新导出，或手改 environment.yml
conda env update -f environment.yml --prune