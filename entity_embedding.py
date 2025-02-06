#!/usr/bin/env python
# -*- coding: utf-8 -*-

import struct
import pickle
import numpy as np

# ============ 配置区域 ============
ENTITY2ID_FILE = "entity2id.txt"
ENTITY2VEC_FILE = "entity2vec.bern"
OUTPUT_FILE = "entity_embeddings.pkl"  # 输出字典文件


def parse_entity2vec():
    """解析实体到向量的映射文件"""
    entities = []
    with open(ENTITY2ID_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()
        for line in lines[1:]:
            parts = line.strip().split("\t")
            entity = parts[0]
            entities.append(entity)
    embeddings = {}
    with open(ENTITY2VEC_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()
        for i, line in enumerate(lines):
            vector = [float(x) for x in line.strip().split("\t")]
            embeddings[entities[i]] = vector
    return embeddings


def main():
    # 解析文件
    try:
        embeddings = parse_entity2vec()
    except ValueError as e:
        print(f"解析失败: {e}")
        return

    # 保存字典
    with open(OUTPUT_FILE, "wb") as f:
        pickle.dump(embeddings, f)
    print(f"\n已保存嵌入字典到 {OUTPUT_FILE}")

    # 验证示例
    test_entity = next(iter(embeddings.keys()))
    print(f"\n示例验证 - 实体: '{test_entity}'")
    print(f"嵌入向量: {embeddings[test_entity]}")

if __name__ == "__main__":
    main()