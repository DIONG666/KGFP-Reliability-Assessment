#!/usr/bin/env python
# -*- coding: utf-8 -*-

from neo4j import GraphDatabase

# ============ 配置区域 ============
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "neo4jDIONG"
ENTITY_LABEL = "Entity"  # 实体的标签


def get_max_degree(session):
    """查询并返回最高连接度数及对应实体"""
    cypher_query = f"""
        MATCH (n:{ENTITY_LABEL})
        RETURN n.name AS entity, 
               COUNT {{ (n)--() }} AS degree
        ORDER BY degree DESC
        LIMIT 1
        """
    result = session.run(cypher_query)
    record = result.single()
    if record:
        return record["entity"], record["degree"]
    else:
        return None, 0


def main():
    driver = None
    try:
        # 连接到Neo4j数据库
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

        with driver.session() as session:
            entity, max_degree = get_max_degree(session)
            if entity:
                print(f"最高连接度数的实体: {entity}")
                print(f"连接度数: {max_degree}")
            else:
                print("未找到任何实体")

    except Exception as e:
        print(f"发生错误: {str(e)}")
    finally:
        if driver is not None:
            driver.close()


if __name__ == "__main__":
    main()