
# 查看有哪些镜像。
# 镜像存放位置/Users/lcd/Library/Containers/com.docker.docker/Data/vms/0/data/Docker.raw
docker images      




# 启动的名字
docker run -d \
  --name attu \
  ...

# 查看现在启动的容器
docker ps

docker stop attu

docker start attu

# 删除某个容器
docker rm attu

# 强制删除
docker rm -f attu


docker ps              # 正在运行的
docker ps -a           # 全部（含已停止）
docker ps -a --filter name=attu   # 只看 attu