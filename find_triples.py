#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from collections import defaultdict

# ============ 配置区域 ============
ROOT_DIR = "."  # 根目录（默认为当前目录）
TARGET_ENTITIES = {
    "concept_city_grenada",
    "concept_sportsleague_mls"
}  # 要统计的目标实体


def search_entities_in_graphs():
    """
    遍历所有子目录中的 graph.txt 文件，统计目标实体出现的频率
    返回结构：{文件夹路径: {实体: 出现次数}}
    """
    stats = defaultdict(lambda: defaultdict(int))

    # 遍历根目录下的所有子文件夹
    for root, dirs, files in os.walk(ROOT_DIR):
        # 检查当前目录是否有 graph.txt
        if "graph.txt" not in files:
            continue

        graph_path = os.path.join(root, "graph.txt")
        try:
            with open(graph_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split("\t")
                    if len(parts) < 3:
                        continue
                    h, r, t = parts[0], parts[1], parts[2]

                    # 检查当前三元组是否包含目标实体
                    for entity in TARGET_ENTITIES:
                        if entity in (h, t):
                            stats[root][entity] += 1

        except Exception as e:
            print(f"读取文件 {graph_path} 失败: {e}")
            continue

    return stats


def print_stats(stats):
    """打印统计结果"""
    if not stats:
        print("未找到任何包含目标实体的三元组。")
        return

    print("统计结果：")
    for folder, counts in stats.items():
        print(f"\n文件夹路径: {folder}")
        total = sum(counts.values())
        print(f"总匹配次数: {total}")
        for entity, count in counts.items():
            print(f"  - {entity}: {count} 次")


if __name__ == "__main__":
    stats = search_entities_in_graphs()
    print_stats(stats)