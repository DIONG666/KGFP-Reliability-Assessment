# KGFP-Reliability-Assessment
1. 安装依赖：pip install -r requirements.txt
2. 导入全部三元组：python import_all_triples.py
3. 选择一个任务文件夹（下面由task代替）
4. 匹配规则（参数：topk）：python task/rule_matching.py
5. 统计假阳性结果与计算相关评价指标：python task/evaluation.py
6. CSSM和FSCM指标计算：python task/indicator_calculation.py  
   > topk：选取topk支持度的案例参与指标计算
7. 可靠性分数计算（参数选择、阈值设置、结果可视化）：python task/parameter_adjustment.py
   > sigma：案例子图相似度指标占比  
   > miu：预测子图复杂度指标占比  
   > theta：可靠性分数阈值（低于阈值则认为是假阳性结果）
