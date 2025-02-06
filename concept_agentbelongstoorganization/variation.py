# !/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from neo4j import GraphDatabase
import matplotlib.pyplot as plt
import numpy as np
from itertools import accumulate

# ============ 配置区域 ============
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "neo4jDIONG"
PATH_STATS_FILE = "path_stats-20240124.txt"  # 规则文件
LABEL_FILE = "sort_test.pairs"  # 标签文件


def parse_rule_line(line):
    """解析规则文件中的单行数据，返回关系链和置信度"""
    line = line.strip()
    if not line:
        return None
    parts = line.split('\t')
    chain_part, freq_part = parts[0], parts[1]
    relation_chain = [rel.strip() for rel in chain_part.split("->")]
    freq = float(freq_part)
    return relation_chain, freq


def create_cypher_for_chain(relation_chain):
    """生成匹配路径的Cypher语句"""
    nodes = ["a"] + [f"n{i}" for i in range(len(relation_chain) - 1)] + ["b"]
    pattern_segments = []
    for i, rel in enumerate(relation_chain):
        pattern_segments.append(f"({nodes[i]})-[:RELATION {{name: '{rel}'}}]->({nodes[i + 1]})")
    match_str = "MATCH " + ", ".join(pattern_segments) + "\nRETURN a, b"
    return match_str


def load_label_data():
    """加载标签数据，返回正负例实体对"""
    label_dict = {}  # {(h, t): '+'/'-'}
    with open(LABEL_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                pair_part, label_part = line.split(":", 1)
                label = label_part.strip()[0]  # '+'或'-'
                left, right = pair_part.split(",", 1)
                h = left.split("$")[1].strip()
                t = right.split("$")[1].strip()
                label_dict[(h, t)] = label
            except Exception as e:
                print(f"解析标签行失败: {line} | 错误: {e}")
    return label_dict


def group_rules_by_confidence(sorted_rules):
    """按置信度分组规则"""
    groups = []
    current_conf = None
    for rule in sorted_rules:
        if rule[1] != current_conf:
            groups.append([])
            current_conf = rule[1]
        groups[-1].append(rule)
    return groups


def evaluate_predictions(predicted_pairs, label_dict):
    """计算评估指标"""
    TP, FP, FN, TN = 0, 0, 0, 0
    for pair, lab in label_dict.items():
        if pair in predicted_pairs:
            if lab == '+':
                TP += 1
            else:
                FP += 1
        else:
            if lab == '+':
                FN += 1
            else:
                TN += 1
    precision = TP / (TP + FP) if (TP + FP) > 0 else 0
    recall = TP / (TP + FN) if (TP + FN) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    fp_rate = FP / (TP + FP) if (TP + FP) > 0 else 0
    return TP, FP, precision, recall, f1, fp_rate


def main():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    # 1. 加载规则并分组
    with open(PATH_STATS_FILE, "r", encoding="utf-8") as f:
        rules = [parse_rule_line(l) for l in f if parse_rule_line(l)]

    # 按置信度降序排序并分组
    sorted_rules = sorted(rules, key=lambda x: x[1], reverse=True)
    rule_groups = group_rules_by_confidence(sorted_rules)
    group_counts = [len(g) for g in rule_groups]
    accumulated_counts = list(accumulate(group_counts))

    # 2. 加载标签数据
    label_dict = load_label_data()
    print(f"标签数据加载完成，总实体对数: {len(label_dict)}")

    # 3. 初始化评估结果存储
    TPs, FPs = [], []
    precisions, recalls, f1_scores, fp_rates = [], [], [], []
    x_labels = []

    # 4. 逐步添加规则组
    predicted_pairs = set()
    for i, count in enumerate(accumulated_counts):
        # 获取当前组所有规则
        current_group = rule_groups[i]

        # 匹配当前组规则
        with driver.session() as session:
            for rule in current_group:
                cypher = create_cypher_for_chain(rule[0])
                result = session.run(cypher)
                for rec in result:
                    h = rec["a"]["name"]
                    t = rec["b"]["name"]
                    predicted_pairs.add((h, t))

        # 计算评估指标
        TP, FP, precision, recall, f1, fp_rate = evaluate_predictions(predicted_pairs, label_dict)
        TPs.append(TP)
        FPs.append(FP)
        precisions.append(precision)
        recalls.append(recall)
        f1_scores.append(f1)
        fp_rates.append(fp_rate)
        x_labels.append(f"G{i + 1}\n({count} rules)")

        print(
            f"规则组 {i + 1} | 规则数: {count} | TP: {TP} | FP: {FP} | precision: {precision:.4f} | Recall: {recall:.4f} | FP率: {fp_rate:.4f}")

    driver.close()

    # 5. 绘制组合图表
    fig, ax1 = plt.subplots(figsize=(14, 8))

    # 柱状图参数
    bar_width = 0.2
    x = np.arange(len(x_labels))

    # 绘制TP/FP柱状图
    tp_bars = ax1.bar(x - bar_width / 2, TPs, bar_width, label='TP', color='green', alpha=0.5)
    fp_bars = ax1.bar(x + bar_width / 2, FPs, bar_width, label='FP', color='red', alpha=0.5)

    # 在柱状图上添加数据标签
    for bar in tp_bars:
        height = bar.get_height()
        ax1.text(
            bar.get_x() + bar.get_width() / 2,  # x坐标
            height + 1,  # y坐标（稍微高于柱状图顶部）
            f'{int(height)}',  # 显示的文本
            ha='center',  # 水平居中
            va='bottom',  # 垂直底部对齐
            fontsize=9,  # 字体大小
            color='black'  # 字体颜色
        )

    for bar in fp_bars:
        height = bar.get_height()
        ax1.text(
            bar.get_x() + bar.get_width() / 2,  # x坐标
            height + 1,  # y坐标（稍微高于柱状图顶部）
            f'{int(height)}',  # 显示的文本
            ha='center',  # 水平居中
            va='bottom',  # 垂直底部对齐
            fontsize=9,  # 字体大小
            color='black'  # 字体颜色
        )
    ax1.set_xlabel('Number of rules')
    ax1.set_ylabel('Number')
    ax1.set_title('Evaluation for Rule Matching')
    ax1.set_xticks(x)
    ax1.set_xticklabels(x_labels)

    # 创建第二个Y轴
    ax2 = ax1.twinx()

    # 绘制指标折线图
    ax2.plot(x, precisions, 'b-', marker='o', label='precision')
    ax2.plot(x, recalls, 'm-', marker='s', label='Recall')
    ax2.plot(x, f1_scores, 'c-', marker='^', label='F1-score')
    ax2.plot(x, fp_rates, 'y--', marker='x', label='FP-rate')
    ax2.set_ylabel('Percentage')
    ax2.set_ylim(0, 1.2)

    # 添加图例
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    lines = lines1 + lines2
    labels = labels1 + labels2
    ax1.legend(lines, labels, loc='upper left')

    plt.grid(True)
    plt.tight_layout()
    plt.savefig('Evaluation_for_Rule_Matching.png', dpi=300)
    plt.show()


if __name__ == "__main__":
    main()