#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
读取 graph.txt 并将 (头实体, 关系, 尾实体) 导入 Neo4j
"""

from neo4j import GraphDatabase

# ============ 配置区域 ============
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "neo4jDIONG"

GRAPH_FILE = "graph.txt"  # 存储三元组的文件路径

def setup_indexes(session):
    """
    在 Neo4j 中创建或确保存在以下索引：
      1) 对实体的 :Entity(name) 建唯一约束（同时具备索引功能）
      2) 对关系属性 :RELATION(name) 建索引（仅 Neo4j 5.x+ 支持）
    """
    # 1) 节点唯一约束
    # Neo4j 4.4+ / 5.x 写法
    session.run("""
        CREATE CONSTRAINT IF NOT EXISTS 
        FOR (e:Entity) REQUIRE e.name IS UNIQUE
    """)

    # 2) 关系属性索引 (仅 5.x 及以上版本支持)
    session.run("""
        CREATE INDEX rel_name_index IF NOT EXISTS
        FOR ()-[r:RELATION]->() ON (r.name)
    """)


def main():
    # 连接数据库
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    # 1. 先创建索引/约束
    with driver.session() as session:
        setup_indexes(session)
        print("已创建(或确保存在)实体与关系的索引/约束。")

    # 2. 读取 graph.txt 并插入三元组
    with open(GRAPH_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()
        print(f"共有{len(lines)}条数据。")
        print(f"示例数据：{lines[0:5]}")

    total = 0
    with driver.session() as session:
        for line in lines:
            line = line.strip()
            if not line:
                continue
            parts = line.split('\t')
            if len(parts) < 3:
                print(f"There is an error in {line}")
                continue

            head_name = parts[0]
            rel_name = parts[1]
            tail_name = parts[2]

            # 将三元组导入Neo4j:
            #  - 节点(:Entity {name:xxx})
            #  - 边[:RELATION {name:xxx}]
            cypher = """
            MERGE (h:Entity {name: $h_name})
            MERGE (t:Entity {name: $t_name})
            MERGE (h)-[:RELATION {name: $r_name}]->(t)
            """
            session.run(cypher, h_name=head_name, r_name=rel_name, t_name=tail_name)
            total += 1
            if(total % 10000 == 0):
                print(f"已成功插入了 {total} 条三元组信息。")

    print(f"成功插入了 {total} 条三元组信息。")
    driver.close()
    print("导入完成。")


if __name__ == "__main__":
    main()
