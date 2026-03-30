# prompts.py

PROMPT_SYSTEM = """
你是一个资深面试专家，请你针对于给出的模板，将其中使用`{{}}`圈起的内容，给出替换。
最终你应当输出一个JSON，JSON中对于每个Key，给出对应的Value。

模板内容如下：
{TEMPLATE}

面试者简历如下：
{RESUME}

面试过程录音如下（要注意，录音转文字存在一定误差，对于谐音，通常要考虑不是录音的问题，也不要尝试针对于发音问题进行纠正）：
{VOICE2TEXT}

"""
PROMPT_COVER = """
# 单人候选人面试评估报告（{{TargetPosition}}专用）

- 应聘岗位：{{AppliedPosition}}
- 候选人姓名：{{CandidateName}}
- 面试时间：{{InterviewTime}}
- 面试形式：{{InterviewFormat}}
- 面试评估官：{{InterviewerInfo}}
- 报告编制人：{{ReportCreator}}
- 报告编制时间：{{ReportCreateDate}}

## 报告导读

本报告为{{CandidateName}}应聘{{AppliedPosition}}的单人面试评估专项报告，
围绕{{TargetPosition}}岗位核心任职要求，从候选人基本信息、能力维度可视化评估、
核心能力专项分析、面试表现优劣势等方面展开客观研判，明确综合评估结论及后续录用建议，
为录用决策提供精准、可追溯的参考依据。报告同步附面试相关记录资料等内容，供后续核对查阅。
"""
PROMPT_BASIC_INFO = f"""
# 第一部分 候选人基本信息与简历核心分析
## 1.1 候选人基础信息档案
| *项目* | *具体内容*        |
| --    | --               |
|姓名	 |{{CandidateName}}|
|年龄	 |{{Age}}          |
|性别	 |{{Gender}}       |
|学历/专业|{{Education}}    |
|工作年限/电销经验	|{{YearsOfExperience}}/{{HasSalesExp}}|
|过往背景	|{{Background}}|
|求职薪资	|{{ExpectedSalary}}|
|意向岗位	|{{IntendedPosition}}|
## 1.2 简历核心分析
1.简历核心亮点：{{ResumeHighlights}}；
2.简历信息核实：{{VerificationDetails}}；
3.简历初筛结论：{{PreScreeningResult}}；
4.初筛核心依据：{{PreScreeningReason}}。

*注意（这里不是文档模板的一部分）*：
1. 简历核心亮点、简历信息核实这部分内容，要用连续的一段文字表述，而不是分点；
2. 一定注意标点符号的情况。所有`{{}}`包裹的内容，都不应该有最后的句号；
3. 如果关键信息不确定，请你填写”无“/”未提及“。
"""
PROMPT_CORE_SCORE = """
## 2.1 核心能力维度评分表（满分 100 分，基准线≥70 分）
本部分标注面试官打分、智能评分、平均分及评估等级，为可视化图表提供数据支撑。

| 评估维度 | 面试官打分 | 智能评分 | 平均分 | 评估等级（优秀≥90/良好 80-89/合格 70-79/不合格<70） |
| :--- | :--- | :--- | :--- | :--- |
| 普通话标准程度 | {{Score_Putonghua_Interviewer}} | {{Score_Putonghua_AI}} | {{Score_Putonghua_Avg}} | {{Grade_Putonghua}} |
| 对话流畅程度 | {{Score_Liuchang_Interviewer}} | {{Score_Liuchang_AI}} | {{Score_Liuchang_Avg}} | {{Grade_Liuchang}} |
| 逻辑思维能力 | {{Score_Luoji_Interviewer}} | {{Score_Luoji_AI}} | {{Score_Luoji_Avg}} | {{Grade_Luoji}} |
| 专业销售能力 | {{Score_Sales_Interviewer}} | {{Score_Sales_AI}} | {{Score_Sales_Avg}} | {{Grade_Sales}} |
| 抗压应变能力 | {{Score_Stress_Interviewer}} | {{Score_Stress_AI}} | {{Score_Stress_Avg}} | {{Grade_Stress}} |
| 沟通表达能力 | {{Score_Comm_Interviewer}} | {{Score_Comm_AI}} | {{Score_Comm_Avg}} | {{Grade_Comm}} |
| 职业稳定性 | {{Score_Stability_Interviewer}} | {{Score_Stability_AI}} | {{Score_Stability_Avg}} | {{Grade_Stability}} |

## 2.3 数据核心解读
1. 综合表现：候选人综合平均分为{{TotalAvgScore}}，{{ScoreComparison}}70分基准线，
整体能力{{GoalAchievement}}；
2. 维度达标情况：7个维度中，达标{{MetCount}}个、不合格{{UnmetCount}}个；
其中，基础沟通维度（普通话、流畅度、逻辑）{{BasicCommStatus}}；
3. 核心特征：优势维度{{StrengthDimensions}}；薄弱维度{{WeakDimensions}}；
4. 评分一致性：面试官与智能评分{{ScoreConsistency}}，偏差原因{{ConsistencyReason}}。

*注意（这里不是文档模板的一部分）*：
1. 一定注意标点符号的情况。所有`{{}}`包裹的内容，都不应该有最后的句号
"""

PROMPT_CORE_BILITY = """
# 第三部分 候选人核心能力维度专项评估

本部分结合电销一线工作场景，对7大核心维度展开专项分析，研判与岗位匹配度。

## 3.1 基础沟通核心维度（普通话/流畅度/逻辑思维）
1. 表现还原：{{BasicCommStatusDesc}}；
2. 是否满足电销沟通基础：{{SatisfiesBasicComm}}；
3. 待提升点：{{BasicCommImprovement}}；
4. 匹配结论：{{BasicCommMatch}}。

## 3.2 专业销售能力
1. 表现还原：{{SalesAbilityDesc}}；
2. 匹配结论：{{BasicCommMatch}}。

## 3.3 抗压应变能力
1. 表现还原：{{StressHandlingDesc}}；
2. 匹配结论：{{BasicCommMatch}}。

## 3.4 沟通表达能力
1. 表现还原：{{CommExpressionDesc}}；
2. 匹配结论：{{BasicCommMatch}}。

## 3.5 职业稳定性
1. 表现还原：{{StabilityDesc}}；
2. 匹配结论：{{StabilityReason}}。

*注意（这里不是文档模板的一部分）*：
1. 一定注意标点符号的情况。所有`{{}}`包裹的内容，都不应该有最后的句号
"""
PROMPT_COMPREHENSIVE_ANALYSIS = """
# 第四部分 候选人面试表现优劣势综合分析

本部分优劣势贴合电销岗核心要求，按影响程度排序。

## 4.1 核心优势
1. 基础沟通类：{{Strength_Comm}}；
2. 专业销售类：{{Strength_Sales}}；
3. 抗压心态类：{{Strength_Stress}}；
4. 经验背景类：{{Strength_Back}}；
5. 其他类：{{Strength_Other}}。

## 4.2 主要劣势/待改进点
1. 基础沟通类：{{Weakness_Comm}}；
2. 专业销售类：{{Weakness_Sales}}；
3. 职业稳定性类：{{Weakness_Stability}}；
4. 其他待磨合点：{{Weakness_Other}}。

## 4.3 面试关键备注
1. 薪资协商：{{SalaryAlignment}}；
2. 到岗时间：{{ArrivalDate}}；
3. 模拟电销表现：{{MockPerformance}}；
4. 产品知识：{{ProductKnowledge}}；
5. 是否需培训：{{NeedsTraining}}；
6. 其他细节：{{OtherDetails}}。

*注意（这里不是文档模板的一部分）*：
1. 一定注意标点符号的情况。所有`{{}}`包裹的内容，都不应该有最后的句号
"""

PROMPT_CONCLUSION = """
## 5.1 综合评估核心结论
候选人综合平均分为{{TotalAvgScore}}，评估等级{{FinalGrade}}（D/C/B/A/S），
基础沟通维度{{BasicCommStatus}}，与电销岗适配度方面，{{SuitabilityLevel}}，
总体上，{{FinalConclusionReason}}。
## 5.2 最终录用建议
- 建议类型：{{FinalDecision}}。
- 建议核心依据：{{FinalDecisionReason}}。

*注意（这里不是文档模板的一部分）*：
1. 一定注意标点符号的情况。所有`{{}}`包裹的内容，都不应该有最后的句号
2. 建议类型包括`录用`/`不录用`。
"""