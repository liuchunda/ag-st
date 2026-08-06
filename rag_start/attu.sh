export PATH="$HOME/.docker/bin:$PATH"

docker run -d \
  --name attu \
  -p 8000:3000 \
  -e MILVUS_URL=host.docker.internal:19530 \
  zilliz/attu:v2.5