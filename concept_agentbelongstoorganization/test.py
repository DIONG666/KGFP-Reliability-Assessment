from neo4j import GraphDatabase

# ============ 配置区域 ============
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "neo4jDIONG"
PATH_STATS_FILE = "path_stats-20240124.txt"  # 规则文件
OUTPUT_FILE = "sd_results.txt"  # 结果输出文件


def parse_rule_line(line):
    """解析 path_stats-20240124.txt 文件中的一行规则"""
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
    """根据关系链生成 Cypher 查询语句"""
    var_list = ["a"] + [f"n{i}" for i in range(len(relation_chain) - 1)] + ["b"]
    match_parts = [f"({var_list[i]})-[:RELATION {{name: '{relation_chain[i]}'}}]->({var_list[i+1]})" for i in range(len(relation_chain))]
    cypher = f"MATCH {'-'.join(match_parts)} RETURN a, b"
    return cypher


def normalize_confidence(rule_list):
    """归一化规则的频率"""
    freqs = [r["freq"] for r in rule_list]
    freq_min, freq_max = min(freqs), max(freqs)
    for r in rule_list:
        r["conf"] = (r["freq"] - freq_min) / (freq_max - freq_min) if freq_max != freq_min else 1.0
    rule_list.sort(key=lambda x: x["conf"], reverse=True)


def find_matching_rules(driver, case_pair, rule_list):
    """遍历 case_pairs 并为每条规则匹配路径"""
    matched_rules_count = 0
    total_confidence = 0

    with driver.session() as session:
        for rule in rule_list:
            chain = rule["relations"]
            cypher = create_cypher_for_chain(chain)
            result = session.run(cypher)
            predicted_pairs = set()
            for record in result:
                a_name = record["a"].get("name")
                b_name = record["b"].get("name")
                if a_name and b_name and (a_name, b_name) in case_pairs:
                    predicted_pairs.add((a_name, b_name))

            if predicted_pairs:
                matched_rules_count += 1
                total_confidence += rule["conf"]

    return matched_rules_count, total_confidence


def SD(driver, case_pairs):
    """计算 SD 指标"""
    # 读取规则文件并进行归一化
    with open(PATH_STATS_FILE, "r", encoding="utf-8") as f:
        rule_list = [parse_rule_line(line) for line in f.readlines()]

    # 归一化规则的频率
    normalize_confidence(rule_list)

    # 计算匹配规则的数量以及总置信度
    matched_rules_count, total_confidence = find_matching_rules(driver, case_pairs, rule_list)

    # 计算 SD 指标
    if matched_rules_count > 0:
        sd_value = total_confidence / matched_rules_count
    else:
        sd_value = 0

    return sd_value

def find_cases(driver, relation):
    """找到和预测三元组有相同关系的三元组"""
    case_pairs = set()  # 存放 (headName, tailName)

    # Cypher 查询，找到具有相同关系的所有三元组
    query = """
    MATCH (h)-[r:RELATION]->(t)
    WHERE r.name = $relation_name
    RETURN h.name AS head, t.name AS tail
    """

    with driver.session() as session:
        result = session.run(query, relation_name=relation)
        for record in result:
            head_name = record["head"]
            tail_name = record["tail"]
            case_pairs.add((head_name, tail_name))  # 添加到集合中，确保去重

    return case_pairs

if __name__ == "__main__":
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    relation = 'concept:agentbelongstoorganization'

    # 调用函数，获取相同关系的三元组
    case_pairs = find_cases(driver, relation)



    # 输出结果
    print(f"对于关系'{relation}'，找到{len(case_pairs)}个案例")
    # print("找到的案例：")
    # for pair in case_pairs:
    #     print(pair)