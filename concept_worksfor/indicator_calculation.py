#!/usr/bin/env python
# -*- coding: utf-8 -*-

from neo4j import GraphDatabase
from tqdm import tqdm
import pickle
import numpy as np

# ============ 配置区域 ============
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "neo4jDIONG"

RULES_FILE = "path_stats-20240124.txt"  # 规则文件
PREDICTED_PAIRS_FILE = "test_pairs.txt"
OUTPUT_FILE = "indicators_output_0.7_0.3.txt"

PATH_CACHE = {}
ENTITY_PROP_CACHE = {}

I_MAX = 1000 # 实体最大连接度数
R = 400 # 图谱总关系数
topk = 3
sigma = 1
miu = 0


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

def rules_preprocessing(rules_file):
    """规则文件预处理，划分链路，归一化置信度"""
    rules_list = []
    with open(rules_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for line in lines:
        rule, confidence, _ = line.strip().split("\t")
        rule = [c.strip() for c in rule.split("->")]
        confidence = float(confidence)
        rules_list.append({"rule": rule, "conf": confidence})

    conf = [r["conf"] for r in rules_list]
    conf_min, conf_max = min(conf), max(conf)
    for r in rules_list:
        r["conf"] = (r["conf"] - conf_min) / (conf_max - conf_min) if conf_max > conf_min else 1.0

    return rules_list

def generate_cypher_query(rule_chain):
    """动态生成路径匹配的Cypher查询"""
    nodes = ["h"]
    for i in range(len(rule_chain) - 1):
        nodes.append(f"n{i}")
    nodes.append("t")

    pattern = []
    for i in range(len(rule_chain)):
        rel = rule_chain[i]
        pattern.append(f"({nodes[i]})-[:RELATION {{name: '{rel}'}}]->({nodes[i + 1]})")

    return f"""
    MATCH {', '.join(pattern)}
    WHERE h.name = $h_name AND t.name = $t_name
    RETURN COUNT(*) > 0 AS exists
    """

def SD(driver, case_pair, rules_list):
    """计算支持度分数"""
    h_name, t_name = case_pair
    matched_confs = []

    with driver.session() as session:
        for rule in rules_list:
            # 生成动态Cypher查询
            cypher = generate_cypher_query(rule["rule"])

            try:
                result = session.run(cypher, h_name=h_name, t_name=t_name)
                exists = result.single()["exists"]
                if exists:
                    matched_confs.append(rule["conf"])
            except Exception as e:
                print(f"规则 {rule['rule']} 查询失败: {str(e)}")
                continue

    # 计算平均置信度
    return sum(matched_confs) / len(matched_confs) if matched_confs else 0

def cosine_similarity(vec1, vec2):
    """计算余弦相似度"""
    if np.all(vec1 == 0) or np.all(vec2 == 0):
        return 0.0
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

def get_entity_similarity(embeddings, entity1, entity2):
    """获取两个实体的嵌入相似度"""
    vec1 = embeddings.get(entity1, None)
    vec2 = embeddings.get(entity2, None)
    if vec1 is None or vec2 is None:
        return 0.0
    cos = cosine_similarity(vec1, vec2)
    return (cos + 1) / 2

def get_paths_between(driver, h_name, t_name, max_depth=3):
    """获取头尾实体间的所有非环路径"""
    cache_key = (h_name, t_name)
    if cache_key in PATH_CACHE:
        return PATH_CACHE[cache_key].copy()

    paths = []
    query = """
    MATCH path = (h:Entity {name: $h_name})-[*1..%d]->(t:Entity {name: $t_name})
    WHERE all(n IN nodes(path) WHERE single(x IN nodes(path) WHERE x = n))
    RETURN nodes(path) AS nodes, relationships(path) AS rels
    """ % max_depth

    with driver.session() as session:
        result = session.run(query, h_name=h_name, t_name=t_name)
        for record in result:
            node_names = [node["name"] for node in record["nodes"]]
            rel_names = [rel["name"] for rel in record["rels"]]
            paths.append({
                "nodes": node_names,
                "rels": rel_names,
                "path_str": "->".join(rel_names)
            })

    PATH_CACHE[cache_key] = paths
    return paths

def PS(driver, pred_pair, case_pair):
    """计算路径相似度"""
    pred_h, pred_t = pred_pair
    case_h, case_t = case_pair

    # 获取预测对路径
    pred_paths = [p["path_str"] for p in get_paths_between(driver, pred_h, pred_t)]
    if not pred_paths:
        return 0.0

    # 获取案例对路径
    case_paths = [p["path_str"] for p in get_paths_between(driver, case_h, case_t)]

    # 计算交集比例
    intersection = len(set(pred_paths) & set(case_paths))
    # print(f"预测三元组子图路径数：{len(pred_paths)}，案例三元组子图路径数：{len(case_paths)}，相同路径数：{intersection}")
    return intersection / len(pred_paths)

def SS(driver, pred_pair, case_pair):
    """计算子图相似度"""
    # 加载嵌入字典
    with open('../entity_embeddings.pkl', 'rb') as f:
        entity_embeddings = pickle.load(f)

    # 分解实体对
    pred_h, pred_t = pred_pair
    case_h, case_t = case_pair

    # 计算头实体相似度
    hes = get_entity_similarity(entity_embeddings, pred_h, case_h)
    # print(f"HES:{hes}")
    # 计算尾实体相似度
    tes = get_entity_similarity(entity_embeddings, pred_t, case_t)
    # print(f"TES:{tes}")
    # 计算路径相似度
    ps = PS(driver, pred_pair, case_pair)
    # print(f"PS:{ps}")

    # 返回平均分
    return (hes + tes + ps) / 3

def get_top_cases(case_sd_list, topk=3):
    """获取TopK案例（含并列排名）"""
    if not case_sd_list:
        return []

    # 按SD降序排序
    sorted_cases = sorted(case_sd_list, key=lambda x: x[1], reverse=True)

    top_cases = []
    current_rank = 1
    prev_sd = None

    for (case, sd) in sorted_cases:
        if prev_sd is None:
            prev_sd = sd
        elif sd != prev_sd:
            current_rank = current_rank + 1
            prev_sd = sd
        if current_rank > topk:
            break
        top_cases.append((case, sd))

    return top_cases

def CSSM(driver, pred_pair, top_cases):
    cssm = 0
    idx = 0
    for case_pair, sd in top_cases:
        # print(f"案例三元组{idx}:")
        ss = SS(driver, pred_pair, case_pair)
        # print(f"SS:{ss}")
        cssm += sd * ss
        idx += 1

    return cssm / len(top_cases) if top_cases else 0


def get_entity_degree_and_relation_type(session, entity_name):
    """获取实体连接度数和不同关系类型数（带缓存）"""
    if entity_name in ENTITY_PROP_CACHE:
        return ENTITY_PROP_CACHE[entity_name]

    query = """
    MATCH (n:Entity {name: $name})-[r:RELATION]-()
    RETURN 
      COUNT(r) AS degree,
      COUNT(DISTINCT r.name) AS relation_types
    """

    result = session.run(query, name=entity_name).single()
    props = {
        "degree": result["degree"] or 0,
        "relation_types": result["relation_types"] or 0
    }

    ENTITY_PROP_CACHE[entity_name] = props
    return props

def AV_ART(driver, h_name, t_name):
    """计算AV和ART指标"""
    av_sum, art_sum = 0, 0

    with driver.session() as session:
        paths = PATH_CACHE[(h_name, t_name)]
        if not paths:
            return 0.0, 0.0

        for path in paths:
            # 去重路径中的节点
            unique_nodes = list(set(path["nodes"]))

            # 计算当前路径的指标
            path_av, path_art = 0, 0
            for node in unique_nodes:
                # 获取度数和关系类型数
                props = get_entity_degree_and_relation_type(session, node)
                degree = props["degree"]
                types = props["relation_types"]
                path_av += degree / I_MAX
                path_art += types / R

            # 累加到总和
            av_sum += path_av / len(unique_nodes) if unique_nodes else 0
            art_sum += path_art / len(unique_nodes) if unique_nodes else 0

    # 计算全局平均
    av = av_sum / len(paths) if paths else 0
    art = art_sum / len(paths) if paths else 0
    av = av if av <= 1 else 1
    # print(f"AV: {av} ART: {art}")
    return av, art

def FSCM(driver, h_name, t_name):
    av, art = AV_ART(driver, h_name, t_name)
    return (av + art) / 2

def RIS(cssm, fscm, sigma, miu):
    return sigma * cssm - miu * fscm


if __name__ == "__main__":
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    relation = 'concept:agentbelongstoorganization'
    predicted_pairs = []
    with open(PREDICTED_PAIRS_FILE, 'r', encoding="utf-8") as f:
        lines = f.readlines()
        for line in lines:
            h, t, fp = line.strip().split('\t')
            predicted_pairs.append({'pair': (h, t), 'fp': fp})

    case_pairs = find_cases(driver, relation)
    print(f"找到 {len(case_pairs)} 个案例对")

    SDs =[]
    for case_pair in tqdm(case_pairs, desc="计算案例三元组SD值"):
        sd = SD(driver, case_pair, rules_preprocessing(RULES_FILE))
        SDs.append((case_pair, sd))

    # # 按SD值降序输出结果
    # sorted_results = sorted(SDs, key=lambda x: x[1], reverse=True)
    # for case_pair, sd in sorted_results:
    #     print(f"{case_pair[0]} -> {case_pair[1]} : {sd:.4f}")

    # test_pred_pair = predicted_pairs[0]
    # test_case_pair = list(case_pairs)[0]
    # print(f"测试预测三元组：{test_pred_pair}\t测试案例三元组：{test_case_pair}")
    # ss = SS(driver, test_pred_pair, test_case_pair)
    # print(f"SS值：{ss}")

    top_cases = get_top_cases(SDs, topk)
    print(f"选取Top {topk} SD值共 {len(top_cases)} 个案例对")

    indicators = []
    cnt = 0
    for pred_pair in tqdm(predicted_pairs, desc="计算预测三元组可靠性分数"):
        pair = pred_pair['pair']
        fp = pred_pair['fp']
        # print(f"预测三元组{cnt}:")
        cssm = CSSM(driver, pair, top_cases)
        fscm = FSCM(driver, pair[0], pair[1])
        ris =RIS(cssm, fscm, sigma, miu)
        indicators.append((pair, cssm, fscm, ris, fp))
        cnt += 1

    with open(f"indicators_output_{sigma}_{miu}.txt", 'w', encoding="utf-8") as f:
        for (h, t), cssm, fscm, ris, fp in sorted(indicators, key=lambda x: x[-2], reverse=True):
            print(f"\n预测对: {h}->{t} | CSSM={cssm:.4f} | FSCM={fscm:.4f} | RIS={ris:.4f} | 是否为假阳性结果: {fp}")
            f.write(f"{h}\t{t}\t{cssm:.4f}\t{fscm:.4f}\t{ris:.4f}\t{fp}\n")
    driver.close()