from fastapi import Query
skip: int = Query(0, ge=0)
limit: int = Query(..., ge=1, le=100)   # ... 表示必填


# 参数名: 类型 = Query(默认值, 规则1, 规则2, ...)



# 只要可选
# q: Optional[str] = None


# 只要校验（必填，且有规则）
# limit: int = Query(..., ge=1, le=100)   # ... 表示必填


# 既可选，又要校验
# q: Optional[str] = Query(None, max_length=50)