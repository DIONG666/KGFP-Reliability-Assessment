#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from neo4j import GraphDatabase

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "neo4jDIONG"

PATH_STATS_FILE = "path_stats-20240124.txt"  # 规则文件
OUTPUT_PAIRS_FILE = "predicted_pairs.txt"


def parse_rule_line(line):
    line = line.strip()

    tokens = line.split('\t')
    chain = tokens[0]
    freq = float(tokens[1])

    relation_chain = [c.strip() for c in chain.split("->")]

    return {
        "relations": relation_chain,
        "freq": freq,
    }


def create_cypher_for_chain(relation_chain):
    """
    给定关系链(例如 ["r1", "r2", "r3"]),
    生成用于匹配的 Cypher 语句, 以获取 (a, b)，其中:
      a = 起点
      b = 终点
    示例输出:
      MATCH (a)-[:RELATION {name:'r1'}]->(n1)-[:RELATION {name:'r2'}]->(n2)-[:RELATION {name:'r3'}]->(b)
      RETURN a, b
    """

    # 为了在 Cypher 中引用不同节点，用 a, n1, n2, ..., b
    var_list = []
    var_list.append("a")  # start
    for i in range(len(relation_chain) - 1):
        var_list.append(f"n{i}")
    var_list.append("b")  # end

    # 构造中间语句
    match_parts = []
    for i in range(len(relation_chain)):
        # relation_chain[i] 是关系名
        curr_relation = relation_chain[i]
        left_node = var_list[i]
        right_node = var_list[i+1]

        seg = f"-[:RELATION {{name: '{curr_relation}'}}]->({right_node})"
        match_parts.append(seg)

    # 用连字符连接
    match_str = "("+var_list[0]+")"
    for seg in match_parts:
        match_str +=  seg

    cypher = f"""
    MATCH {match_str}
    RETURN a, b
    """
    return cypher


def main(top=3):
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    # ====== 1. 读取并解析规则 ======
    with open(PATH_STATS_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    rule_list = []
    for line in lines:
        rinfo = parse_rule_line(line)
        if rinfo:
            rule_list.append(rinfo)

    # 统计 freq 的最值，用于线性归一化 [0,1]
    freqs = [r["freq"] for r in rule_list]
    freq_min = min(freqs)
    freq_max = max(freqs)

    for r in rule_list:
        freq = r["freq"]
        if freq_max != freq_min:
            freq_norm = (freq - freq_min) / (freq_max - freq_min)
        else:
            freq_norm = 1.0
            
        r["conf"] = freq_norm

    # 按 conf 降序
    rule_list.sort(key=lambda x: x["conf"], reverse=True)

    # 取 top3(含并列)
    if len(rule_list) <= top:
        top_rules = rule_list
    else:
        third_conf = rule_list[top-1]["conf"]
        top_rules = [r for r in rule_list if r["conf"] >= third_conf]

    print(f"总规则数: {len(rule_list)}, 选取 top{top}(含并列): {len(top_rules)}")
    print(top_rules)

    # ====== 2. 在图中对每条规则做匹配，收集 (a,b) 对 ======
    predicted_pairs = set()  # 存放 (headName, tailName)

    with driver.session() as session:
        for rule in top_rules:
            chain = rule["relations"]
            # 生成匹配 Cypher
            cypher = create_cypher_for_chain(chain)
            # 执行
            result = session.run(cypher)
            records = list(result)
            for rec in records:
                a_node = rec["a"]
                b_node = rec["b"]
                if a_node and b_node:
                    # 这里假设节点属性 "name" 就是实体标识
                    a_name = a_node.get("name")
                    b_name = b_node.get("name")
                    if a_name and b_name:
                        predicted_pairs.add((a_name, b_name))

    driver.close()

    print(f"匹配得到实体对数量: {len(predicted_pairs)}")

    # ====== 3. 将 predicted_pairs 写入文件 ======
    with open(OUTPUT_PAIRS_FILE, "w", encoding="utf-8") as f:
        for (h, t) in sorted(predicted_pairs):
            f.write(f"{h}\t{t}\n")

    print(f"已将实体对保存到 {OUTPUT_PAIRS_FILE} 。")


if __name__ == "__main__":
    main(3)
