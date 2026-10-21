# 来源与许可

SubBoost-Surge-Rules 的代码与分类配置采用 AGPL-3.0-only，完整许可见 LICENSE。

- 分类及其上游映射参考 [SubBoost/subboost](https://github.com/SubBoost/subboost/blob/main/packages/core/src/generator/proxy-group-modules.ts)，该项目采用 AGPL-3.0-only。这里独立实现 Surge 文本生成器，并调整了开发工具优先级、域名与 IP 阶段的顺序。
- 规则数据来自 [MetaCubeX/meta-rules-dat](https://github.com/MetaCubeX/meta-rules-dat) 的 meta 分支。其仓库附带的 GPL-3.0 许可原文保存在 licenses/MetaCubeX-GPL-3.0.txt；规则数据及其原始来源保留各自许可与署名。更多数据来源见该项目 README 的说明与致谢。
- rules/manifest.json 记录本次生成使用的上游提交 SHA、每份输入的 SHA-256 和每个输出的 SHA-256，可据此定位原始数据并复现构建。

本项目未关联或获得 SubBoost、MetaCubeX、Surge 的官方授权或背书。
