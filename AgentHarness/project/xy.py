#!/usr/bin/env python3
"""XY 坐标工具模块。"""


class Point:
	"""表示二维平面上的一个点。"""

	def __init__(self, x: float = 0, y: float = 0):
		"""初始化坐标点。

		Args:
			x: X 轴坐标
			y: Y 轴坐标
		"""
		self.x = x
		self.y = y

	def distance_to(self, other: "Point") -> float:
		"""计算到另一个点的欧几里得距离。"""
		return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5

	def move(self, dx: float = 0, dy: float = 0):
		"""平移坐标。

		Args:
			dx: X 方向位移
			dy: Y 方向位移
		"""
		self.x += dx
		self.y += dy

	def __repr__(self) -> str:
		"""字符串表示。"""
		return f"Point({self.x}, {self.y})"


def main():
	"""演示用法。"""
	p1 = Point(0, 0)
	p2 = Point(3, 4)
	print(f"p1: {p1}")
	print(f"p2: {p2}")
	print(f"距离: {p1.distance_to(p2)}")
	p1.move(1, 2)
	print(f"p1 移动后: {p1}")


if __name__ == "__main__":
	main()
