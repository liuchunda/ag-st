from app.config.env import env

ai_configs = {
  # /*---------------------------------------local-------------------------------------------*/
  "local_glm": {
    "model": "glm-4-9b-0414",
    "url": "http://127.0.0.1:1234/v1/chat/completions",
    "key": env.llm_key_local
  },
  # /*---------------------------------------huoshan-------------------------------------------*/
  'huoshan-doubao': {
    'model': 'doubao-seed-2-1-turbo-260628',
    'url': 'https://ark.cn-beijing.volces.com/api/v3/chat/completions',
    'key': env.llm_key_huoshan,
  },
  # /*---------------------------------------bailian-------------------------------------------*/
  'bailian-qwen3.6-plus': {
    'model': 'qwen3.6-plus',
    'url': 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions',
    'key': env.llm_key_bailian,
  },
  'bailian-embedding': {
    'model': 'text-embedding-v4',
    'url': 'https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings',
    'key': env.llm_key_bailian,
  },
}