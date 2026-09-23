# 原生独立只读审阅记录（主线程整理）

节点：Descartes / 01a0c7d1-c533-7ce3-a89f-214534eae558。fresh context；只读英文工程；无其他派发、联网、浏览器或pytest。专家探针读后未执行；一次直接导入生产模块的合成输入探针。此记录整理真实返回，不代替原始会话，也不表示科学/发布终验。

## F05：confirmed

safety_denominator_crosswalk.py L65–141，_Entry缺module，lookup不接请求原组身份。探针：不同module/group同期同N→100；Drug X从Drug X Placebo→80；Period1显式入口→PERIOD1，标题提取→TP1。正确正例：TP2→40，TP3→未知。
build_pnh_a_payload.py L426–446、539–586为真实消费者；N进入A安全行。B build_pnh_b_audit.py L429–445仅接受int，而crosswalk给float，合法整数N可能被丢。修复身份链、显式关系、期别归一与类型往返，不用下游丢行当安全闭环。

## F06：confirmed，复合识别部分已修

safety_concepts.py L21–55、96–127；report_a.py L472–516。生产分类/投影：
Non-serious TEAEs→any_teae；
Participants without SAEs→any_sae；
Grade4和Grade1 or3→grade_3_plus，“3级及以上”。
复合标题正确composite_ae，但catalog L24–48把分母None改other没有适用证明。
B构建L394–445、1060–1082统一family=sae及SAE定义/类别，忽略term_key。
A父title分类，子class/category只作为measure_context显示（L525、570–581）。
最小修复保留原标题/父子、polarity/seriousness/grade集合/TEAE/relatedness/measure_object并贯穿消费者，复合不拆数/相加人数。

## F09：confirmed

endpoint_instances.py L30–130只遍历出现研究，(trial,outcome)配对缺role/group/期校验。helper与FreshC配对方法（fresh_c L286–331）均接受T1/T2 universe只有T1、primary/secondary错配、G1/G2错配；缺第二终点时间正确拒绝。
C构建L315–340所有intervention合并arm1。reports/c/pages.py L490–539按field后缀，不消费outcome_id；两完整primary helper通过但该旧投影拒“不唯一”。
限制：不是完整FreshC.model_validate或整发布链测试；C gate可能拦缺席研究；当前门户直接消费observations，不能把旧pages缺口直接称当前必然渲染失败。
修复全universe逐研究状态、统一实例/角色/组/期、arm-intervention映射、新旧入口一致；缺数据先例保留显式限制。

## 处置与身份

F05/F06建议一个安全契约批次，F09独立实例批次。正反例包含明确关系可用、同N不能借、剂量/安慰剂隔离、整数N JSON往返、否定/等级、复合、缺研究、多primary、角色/组/期、多给药臂。
不建新本体平台/逐行人工审批/重写全gate，也不能只添字符串特判。
开始HEAD5ebbc8785143758981c0260e1600d6ff32b70b80，结束2df24bb441e555f20b233ad2011b4ffd3610655b。仅外部runbook70提交，相关源/测试未变。关键文件hash由主线程重新计算并保存baseline.json，与节点报告一致。

