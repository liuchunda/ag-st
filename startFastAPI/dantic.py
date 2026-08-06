# 导入 BaseModel
from pydantic import BaseModel,Field
from typing import Annotated


# 定义用户模型：继承 BaseModel
class User(BaseModel):
    # 必填字段：id 为整数，name 为字符串
    id: int
    name: str
    # 可选字段：age 默认为 18
    age: int = 18

# # 创建实例时自动验证类型
# user = User(id=1, name="Alice")
# # 打印模型（会显示所有字段）
# print(user)
# # 访问属性
# print(user.name)
# # age 使用默认值
# print(user.age)

# 故意传入错误类型：id 应该是 int，却传了字符串
# try:
#     User(id="不是数字", name="Bob")
# except Exception as e:
#     # 打印验证错误信息
#     print(2626,e,2626)




# 定义商品模型
# class Product(BaseModel):
#     # ... 表示必填；min_length、max_length 限制字符串长度
#     name: str = Field(..., min_length=1, max_length=50)
#     # gt=0 表示大于 0，le=10000 表示小于等于 10000
#     price: float = Field(..., gt=0, le=10000)
#     # 可选，最大长度 200
#     description: str = Field(default="", max_length=200)

# # 正常创建
# p = Product(name="手机", price=2999)
# print(p)

# # 价格超范围会报错
# try:
#     Product(name="电脑", price=99999)
# except Exception as e:
#     print("验证失败:", e)


# 用 Annotated 把类型和约束写在一起
# class Product(BaseModel):
#     name: Annotated[str, Field(min_length=1, max_length=50)]
#     price: Annotated[float, Field(gt=0, le=10000)]

# # 创建实例
# p = Product(name="键盘", price=199)
# print(p)


user = User(id=1, name="Alice", age=18)
print(user.name)
user_dict = user.model_dump()
print(user_dict['name'])



# 从字典解析（会自动验证）
data = {"id": 2, "name": "Bob",'city':'北京'}
user1 = User.model_validate(data)
print(user1)

# 从 JSON 字符串解析
json_str = '{"id": 3, "name": "Charlie", "age": 25}'
user2 = User.model_validate_json(json_str)
print(user2)