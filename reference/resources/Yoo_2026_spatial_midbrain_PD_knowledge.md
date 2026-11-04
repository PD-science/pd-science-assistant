# 韩国尸检黑质的单核与空间转录组图谱：PD 选择性易损

- 原文：Spatiotemporally resolved single-nucleus transcriptomics reveals cellular and regional vulnerability in the midbrain in Parkinson’s disease
- 作者：Sooyeon Yoo、Kwanghoon Lee、Junseo Seo 等；通讯 Junil Kim、Jae-Kyung Won、Sung-Hye Park。
- 期刊：Signal Transduction and Targeted Therapy，2026，11:468。
- DOI：https://doi.org/10.1038/s41392-026-02794-2
- 来源：用户 PDF `/Users/liudt/Downloads/s41392-026-02794-2.pdf`，17 页。核对依据为 PDF，未取得补充病例表。
- 类型：人脑尸检横断面观察研究，无治疗干预；“时间”来自分组与拟时序推断。

## 样本与单位

单核测序：8 位供者，CON 4、PD 4；PD Braak 6、CON 0。初始质控保留 33,293 核，去除一个混合标记簇后最终 31,760 核。神经元分析 722 核；星形胶质 6,128 核、小胶质 5,891 核（图注）。细胞核不是独立受试者。

空间测序：6 切片，CON 1、iLBD 2、PD 3。方法明确 PD-1 与 PD-2 来自同一供者，PD-2 分内/外侧，因此全部 PD 切片仅代表一个独立供者。未有 iLBD 单核参考队列；其细胞组成由 snRNA 参考反卷积推断。

对照病理说明存在正文差异：Figure 1 注记 PART，方法写无其他神经病理；需补充表核对。切片重复不可当独立供者重复。

## 方法

10x Chromium snRNA-seq；Visium v2（约 55 μm 采样点）；α-syn 免疫荧光及 RNAscope/IHC；scVI 空间整合；15 个空间簇；Cell2location 反卷积；Monocle2 和其他轨迹方法、RNA velocity；TENET 调控网络；LIANA+ 配体–受体空间分析；DESeq2 pseudobulk；MAGMA GWAS 富集。

东亚 GWAS 6,724 病例/24,851 对照；主要欧洲 GWAS 15,056 病例/12,637 对照，并有其他欧洲数据集及效能匹配敏感性分析。47 个基因集。

## 主要发现

1. iLBD α-syn 信号突出位于腹外侧 SN；PD 外侧组织严重丢失，背内侧及 VTA 相对保留。不是直接的纵向病理传播证据。
2. NC3 易损，与 SOX6/AGTR1 易损程序相近；NC8 相对保留，TTC6/KLHL1/SEMA6D 特征及 OXR1/UNC5D 上调。不能判定先天耐受，可能有幸存者偏倚。
3. 星形胶质 AC3 到 AC6/AC8 两条拟时序分支，分别涉及营养/代谢适应及基质/损伤反应。CHI3L1 在 iLBD 增强，PD CHI3L1 阳性细胞 CD44 更明显。
4. 小胶质 MC1→MC4 偏免疫/抗原呈递，MC2→MC5 偏 ER/吞噬/代谢；MC3 与血管及 SN–CP 边界有关。均为状态推断，不是谱系追踪。
5. SC6 为微静脉/免疫交通相关混合空间簇（ACKR1），SC8 为动脉壁细胞相关簇（MYH11/ACTA2）；SC6 iLBD 免疫相关变化，PD 比例下降，SC8 相对保留。
6. iLBD 两张片共同的 α-syn 邻域 L–R：LAMA5–SV2C、LAMC1–SV2A、MDK–SDC4、COL1A2–SDC4、CNTN1–NOTCH2。PD 不同组合包含 COL27A1–(ITGA2–ITGB1)。共定位不等于结合/因果。
7. EAS 7/47 基因集 FDR 显著：PD_SC0/4/6/8/9、MIC_T1_ALL、MIC_T2_ALL；EUR 无通过 FDR。不能从显著性差异直接推出祖源机制差异；没有直接跨祖源空间组织比较。

## 解释与限制

提示神经元内在状态和胶质、血管空间环境共同关联选择性易损。无干预实验证明驱动关系。独立供者极少、横断面、PD 单一空间供者、iLBD 结局未知、Visium 混合信号、反卷积及拟时序依赖模型、遗传富集为关联。不可用于临床分型或选药。

## 数据与代码

- https://kbds.re.kr/KAP240761
- https://github.com/whistle-ch0i/SNUH_PD_analysis
- 公共验证数据：GSE243639、GSE178265、GSE157783、GSE184950。
- 资助：韩国公共研究项目；作者声明无竞争性利益。
