def generate_graph_png(graph, path):
  # 生成图片并保存为文件
  file_name = f"{path}_graph.png"
  print(f"正在生成图：", file_name)
  with open(file_name, "wb") as f:
    f.write(graph.get_graph().draw_mermaid_png())
    print(f"文件已经生成：{file_name}")