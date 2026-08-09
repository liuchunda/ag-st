load skill 工具

在agent循环一开始时，添加getsystemprompt，获取提示词，这里会获取整个提示词和skill的提示词
skill.py文件，里边有scanskills方法，用来扫描工作目录下skills目录下的所有skill，提取description字段，提取后，拼接到系统提示词的skill字段

parse_fortmatter提取内容方法
用---分割两次，得到三段内容
parts[1].stip().splitline();
---
name：‘’‘
descripton：‘’‘’
when_to_use：’‘’
--- 