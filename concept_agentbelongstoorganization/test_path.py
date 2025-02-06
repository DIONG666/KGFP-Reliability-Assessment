#!/usr/bin/env python
# -*- coding: utf-8 -*-

from neo4j import GraphDatabase
import re

# ============ 配置区域 ============
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "neo4jDIONG"
PATH_STATS_FILE = "path_stats-20240124.txt"  # 规则文件
LABEL_FILE = "sort_test.pairs"  # 标签文件


def parse_rule_line(line):
    """解析规则文件中的单行数据，返回关系链"""
    line = line.strip()
    if not line:
        return None
    chain_part = line.split('\t')[0]
    return [rel.strip() for rel in chain_part.split("->")]


def generate_path_query(relation_chain):
    """根据规则链生成路径查询（与rule_matching.py逻辑一致）"""
    nodes = ["a"] + [f"n{i}" for i in range(len(relation_chain) - 1)] + ["b"]
    pattern = []
    for i, rel in enumerate(relation_chain):
        pattern.append(f"({nodes[i]})-[:RELATION {{name: '{rel}'}}]->({nodes[i + 1]})")
    return f"""
    MATCH {', '.join(pattern)}
    WHERE a.name = $h_name AND b.name = $t_name
    RETURN COUNT(*) > 0 AS exists
    """


def validate_positive_pairs():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    # 1. 读取所有规则路径
    with open(PATH_STATS_FILE, "r", encoding="utf-8") as f:
        rules = [parse_rule_line(l) for l in f if parse_rule_line(l)]

    # 2. 读取标签中的正例实体对
    positive_pairs = set()
    with open(LABEL_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or ': -' in line:  # 仅处理正例标签
                continue
            try:
                pair_part, _ = line.split(":", 1)
                left, right = pair_part.split(",", 1)
                h = left.split("$")[1].strip()
                t = right.split("$")[1].strip()
                positive_pairs.add((h, t))
            except Exception as e:
                print(f"解析失败: {line} | 错误: {e}")

    print(f"共发现正例实体对数量: {len(positive_pairs)}")

    # 3. 对每个正例实体对，检查是否存在至少一条规则路径
    matched = 0
    unmatched = []

    with driver.session() as session:
        for idx, (h, t) in enumerate(positive_pairs):
            found = False
            # 遍历所有规则路径
            for rule_chain in rules:
                cypher = generate_path_query(rule_chain)
                result = session.run(cypher, h_name=h, t_name=t)
                exists = result.single()["exists"]
                if exists:
                    found = True
                    break  # 找到一条路径即可
            if found:
                matched += 1
            else:
                unmatched.append((h, t))

            if (idx + 1) % 10 == 0:
                print(f"已检查 {idx + 1}/{len(positive_pairs)} 对，当前匹配率: {matched / (idx + 1):.2%}")

    # 4. 输出统计结果
    print("\n验证结果：")
    print(f"正例总数: {len(positive_pairs)}")
    print(f"匹配规则路径的正例数: {matched} (占比: {matched / len(positive_pairs):.2%})")
    print(f"未匹配的实体对示例（最多20个）:")
    for h, t in unmatched[:20]:
        print(f"  [{h} → {t}]")

    driver.close()


if __name__ == "__main__":
    validate_positive_pairs()