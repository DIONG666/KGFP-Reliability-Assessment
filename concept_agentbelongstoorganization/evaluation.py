#!/usr/bin/env python
# -*- coding: utf-8 -*-

def main():
    predicted_file = "predicted_pairs.txt"
    sort_test_file = "sort_test.pairs"

    # 1. 读取predicted_pairs
    predicted_pairs = set()
    with open(predicted_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            h, t = line.split("\t")
            predicted_pairs.add((h, t))

    # 2. 读取sort_test.pairs 并解析标签
    #    格式例如: "thing$concept astronaut mail,thing$concept bank site: -"
    label_dict = {}  # {(entityA, entityB): '+' or '-'}
    with open(sort_test_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            pair_part, label_part = line.split(":", 1)
            label_part = label_part.strip()
            lab = label_part[0]  # 取 '+' 或 '-'

            if "," in pair_part:
                left_ent, right_ent = pair_part.split(",", 1)
                left_ent = left_ent.split('$')[1]
                right_ent = right_ent.split('$')[1]
                label_dict[(left_ent, right_ent)] = lab

    # 3. 计算 TP, FP, FN, TN
    TP, FP, FN, TN = 0, 0, 0, 0
    test_pairs = []
    for (pair, lab) in label_dict.items():
        if pair in predicted_pairs:
            isFP = 0
            # 预测正例
            if lab == '+':
                TP += 1
            else:
                FP += 1
                isFP = 1
            test_pairs.append((pair, isFP))
        else:
            # 未预测
            if lab == '+':
                FN += 1
            else:
                TN += 1
    with open("test_pairs.txt", "w", encoding="utf-8") as f:
        for(pair, isFP) in test_pairs:
            f.write(f"{pair[0]}\t{pair[1]}\t{isFP}\n")


    # 4. 计算指标
    accuracy = (TP + TN) / (TP + TN + FP + FN) if (TP + TN + FP + FN) else 0
    precision = TP / (TP + FP) if (TP + FP) else 0
    recall = TP / (TP + FN) if (TP + FN) else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0

    print("评估结果：")
    print(f"  TP = {TP}, FP = {FP}, FN = {FN}, TN = {TN}")
    print(f"  Accuracy = {accuracy:.4f}")
    print(f"  Precision = {precision:.4f}")
    print(f"  Recall = {recall:.4f}")
    print(f"  F1 = {f1:.4f}")


if __name__ == "__main__":
    main()
