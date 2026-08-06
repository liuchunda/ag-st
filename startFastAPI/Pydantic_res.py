from typing import Annotated

from fastapi import FastAPI, HTTPException
from pydantic import AfterValidator, BaseModel, Field
from typing import Optional


app = FastAPI()


def price_must_gt_zero(v: float) -> float:
    if v <= 0:
        raise ValueError("价格必须大于 0")
    return v


class Item(BaseModel):
    name: str
    # description 仍只用于 OpenAPI 文档；msg 由上面的 ValueError 决定
    price: Annotated[
        float,
        # AfterValidator 是 Pydantic v2 提供的一种自定义校验钩子：在类型转换完成后，再跑你自己的函数。
        AfterValidator(price_must_gt_zero),
        Field(description="The price must be greater than zero"),
    ]
    is_offer: bool = False
    # Optional[int] = None：可以不传，也可以传 null
    id: int|None = None

class ItemOut(BaseModel):
    name: str
    price: float
    id: int|None = None

@app.post("/items/",status_code=201)
async def create_item(item: Item):
    if(item.id is None):
        raise HTTPException(status_code=404, detail="商品不存在")
    saved = ItemOut(name=item.name, price=item.price, id=item.id)
    return saved

if __name__ == "__main__":
    import uvicorn
    uvicorn.run('Pydantic_res:app', host="0.0.0.0", port=8000,reload=True)