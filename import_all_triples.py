#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from neo4j import GraphDatabase

# ============ 配置区域 ============
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "neo4jDIONG"
ROOT_DIR = "."  # 根目录（默认为当前目录）

def setup_indexes(session):
    """创建索引/约束（与原始代码一致）"""
    # 确保实体名称唯一
    session.run("""
        CREATE CONSTRAINT IF NOT EXISTS 
        FOR (e:Entity) REQUIRE e.name IS UNIQUE
    """)
    # 创建关系唯一性约束（通过关系的组合唯一标识）
    session.run("""
        CREATE CONSTRAINT IF NOT EXISTS 
        FOR ()-[r:RELATION]->() REQUIRE (r.name, r.startNode, r.endNode) IS UNIQUE
    """)

def import_graph_file(session, graph_path):
    """导入单个 graph.txt 文件"""
    try:
        with open(graph_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            total = len(lines)
            print(f"共有 {total} 条数据")
            cnt = 0
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                parts = line.split('\t')
                if len(parts) < 3:
                    print(f"格式错误: {line}")
                    continue

                h, r, t = parts[0], parts[1], parts[2]
                # 使用 MERGE 确保节点和关系不重复插入
                cypher = """
                MERGE (h:Entity {name: $h_name})
                MERGE (t:Entity {name: $t_name})
                MERGE (h)-[rel:RELATION {name: $r_name}]->(t)
                """
                session.run(cypher, h_name=h, r_name=r, t_name=t)
                cnt += 1
                if cnt % 10000 == 0:
                    print(f"已成功插入了 {cnt} 条三元组")

            print(f"成功从 [{graph_path}] 导入 {cnt} 条三元组")
    except Exception as e:
        print(f"导入文件 {graph_path} 失败: {e}")

def main():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    # 1. 创建索引/约束
    with driver.session() as session:
        setup_indexes(session)
        print("索引/约束已就绪")

    # 2. 遍历所有子目录下的 graph.txt
    graph_files = []
    for root, dirs, files in os.walk(ROOT_DIR):
        if "graph.txt" in files:
            graph_files.append(os.path.join(root, "graph.txt"))

    if not graph_files:
        print("未找到任何 graph.txt 文件")
        return

    print(f"共发现 {len(graph_files)} 个 graph.txt 文件")

    # 3. 批量导入
    with driver.session() as session:
        for idx, graph_path in enumerate(graph_files):
            print(f"\n正在处理文件 [{idx + 1}/{len(graph_files)}]: {graph_path}")
            import_graph_file(session, graph_path)

    driver.close()
    print("\n全部导入完成")

if __name__ == "__main__":
    main()
