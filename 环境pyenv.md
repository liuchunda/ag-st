是管理python版本的，包括安装，切换

# 安装某个版本
pyenv install 3.12.13

# 本机默认用这个版本
pyenv global 3.12.13

# 只对当前项目用这个版本（写 .python-version）文件里边记录着python版本
pyenv local 3.12.13

# 查看已安装 会查看  如果安装了pyenv，查看版本时会查看.python-version这个文件
pyenv versions