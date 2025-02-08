import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

INPUT_FILE = "indicators_output.txt"

sigma = 1.8
miu = 0.8
theta = 0.4

def RIS(cssm, fscm, sigma, miu):
    return sigma * cssm - miu * fscm

def plot_ris_distribution(indicators, sigma, miu, theta):
    """绘制RIS指标分布图"""
    plt.figure(figsize=(8, 6))

    # 准备数据
    indices = range(len(indicators))
    ris_values = [item[3] for item in indicators]
    fp_flags = [int(item[4]) for item in indicators]  # 转换为整型

    # 创建颜色映射
    colors = ['green' if flag == 0 else 'red' for flag in fp_flags]

    # 绘制散点图
    plt.scatter(indices, ris_values, c=colors, alpha=0.6,
                edgecolors='w', linewidths=0.5)

    # 添加辅助线（显示阈值）
    plt.axhline(y=theta, color='gray', linestyle='--', linewidth=0.8)
    plt.text(
        x=len(indicators)-1,
        y=theta,
        s='threshold',
        color='gray',
        ha='right',
        va='center',
        bbox=dict(boxstyle="square,pad=0.2", fc="white", ec="none", alpha=0.5)
    )

    # 设置图表属性
    plt.xlabel('predicted triples', fontsize=12)
    plt.ylabel('RIS', fontsize=12)
    plt.xticks([])
    plt.ylim(0, 1)
    plt.yticks(np.arange(0, 1.1, 0.1))
    plt.title(f'RIS Distribution (σ={sigma}, μ={miu})', fontsize=14)
    plt.grid(axis='x', alpha=0.3)

    # 创建图例
    legend_elements = [
        Line2D([0], [0], marker='o', color='w',
               markerfacecolor='green', markersize=8, label='TP'),
        Line2D([0], [0], marker='o', color='w',
               markerfacecolor='red', markersize=8, label='FP')
    ]
    plt.legend(handles=legend_elements, loc='upper right')

    # 优化布局
    plt.tight_layout()

    # 保存并关闭
    plt.savefig(f'./experiment_results/RIS_distribution_{sigma}_{miu}_{theta}.png', dpi=300, bbox_inches='tight')
    plt.close()

if __name__ == '__main__':
    tp_sum, fp_sum = 0, 0
    tp_cnt, fp_cnt = 0, 0
    indicators = []
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        for line in lines:
            h, t, cssm, fscm, fp = line.strip().split('\t')
            cssm, fscm, fp = float(cssm), float(fscm), int(fp)
            ris = RIS(cssm, fscm, sigma, miu)
            indicators.append(((h, t), cssm, fscm, ris, fp))
            if fp == 1:
                fp_sum += 1
            else:
                tp_sum += 1
            if ris <= theta:
                if fp == 1:
                    fp_cnt += 1
                else:
                    tp_cnt += 1

        tp_ratio = (tp_cnt / tp_sum) * 100
        fp_ratio = (fp_cnt / fp_sum) * 100
        print(f"{fp_ratio:.1f}%的假阳性结果低于阈值{theta}，{tp_ratio:.1f}%的真阳性结果低于阈值{theta}")
        plot_ris_distribution(indicators, sigma, miu, theta)

        sorted_indicators = sorted(indicators, key=lambda x: x[-2], reverse=True)
        with open(f'./experiment_results/RIS_{sigma}_{miu}.txt', 'w', encoding="utf-8") as f:
            for (h, t), cssm, fscm, ris, fp in sorted_indicators:
                print(f"\n预测对: {h}->{t} | CSSM={cssm:.2f} | FSCM={fscm:.2f} | RIS={ris:.2f} | 是否为假阳性结果: {fp}")
                f.write(f"{h}\t{t}\t{cssm:.2f}\t{fscm:.2f}\t{ris:.2f}\t{fp}\n")