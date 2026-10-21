# SubBoost-Surge-Rules

参考 SubBoost 的服务分类，为 Surge 5 生成可通过 URL 加载的 RULE-SET 文本规则。规则数据来自 MetaCubeX/meta-rules-dat，由 GitHub Actions 定时更新。

```text
catalog.json + 固定版本的上游 .list → Python 生成器 → rules/*.list → Surge
```

## 接入 Surge

1. 在现有配置中准备对应策略组。查看 [策略组示例](examples/groups.conf)，将 `YOUR_PROXY_NODE` 替换成已有节点或节点组；已有同名策略组直接使用。各业务组初始指向 `Proxy`，之后可在 Surge 中选择业务组的节点。
2. 将 [完整引用清单](examples/rules.conf) 合入现有 `[Rule]`，按文件中的顺序排列。按实际配置替换策略组名，最后只保留一条 `FINAL`。
3. 在 Surge 中重新加载配置，检查规则集是否成功下载，并在请求记录中确认命中规则和策略。

单个规则集的引用形式如下，完整清单以 examples/rules.conf 为准：

```ini
[Rule]
RULE-SET,https://raw.githubusercontent.com/leorxx11/SubBoost-Surge-Rules/main/rules/gemini.list,Gemini
RULE-SET,https://raw.githubusercontent.com/leorxx11/SubBoost-Surge-Rules/main/rules/ai.list,AI 服务
RULE-SET,https://raw.githubusercontent.com/leorxx11/SubBoost-Surge-Rules/main/rules/youtube.list,YouTube
RULE-SET,https://raw.githubusercontent.com/leorxx11/SubBoost-Surge-Rules/main/rules/google.list,Google
FINAL,Proxy
```

`rules/*.list` 不携带策略名。添加引用后，由主配置决定每类流量使用哪个节点或策略组。引用的 URL 对应本仓库 main 分支中已发布的文件；现有文件内容更新时无需更换 URL。Surge 默认每 24 小时更新远程规则集。

## 分类

| 范围 | 文件名（位于 rules/） | 示例中的策略 |
| --- | --- | --- |
| 广告 | ad.list | REJECT |
| 私有域名、私有 IP | private.list、private-ip.list | DIRECT |
| AI、Gemini | ai.list、gemini.list | AI 服务、Gemini |
| 国内域名、国内 IP | cn.list、cn-full.list、cn-ip.list | DIRECT |
| YouTube、Google、Google 学术 | youtube.list、google.list、google-ip.list、google-scholar.list | 对应业务组 |
| Microsoft、Apple | microsoft.list、apple.list | 对应业务组 |
| Telegram、X、Meta、Discord、其他社交 | telegram.list、twitter.list、meta.list、discord.list、social-other.list | 对应业务组 |
| Netflix、Disney+、欧美及亚洲流媒体 | netflix.list、disney.list、streaming-west.list、streaming-asia.list | 对应业务组 |
| Steam、PC 游戏、主机游戏 | steam.list、gaming-pc.list、gaming-console.list | 对应业务组 |
| 代码托管、云服务、开发工具、网盘 | github.list、cloud.list、dev-tools.list、storage.list | 对应业务组 |
| 支付、加密货币、教育、新闻、购物、成人内容 | payment.list、crypto.list、education.list、news.list、shopping.list、adult.list | 对应业务组 |
| 其他非中国域名 | global.list | Proxy |

Telegram、X、Meta、Netflix 和云服务还分别提供同名的 `-ip.list` 文件。每份数据的来源、条数、校验值和上游版本见 [manifest.json](rules/manifest.json)。

## 匹配顺序

catalog.json 的 groups 数组决定域名分类的顺序，生成器据此生成引用清单：

- 广告和私有域名在前；Gemini、AI、国内精简域名随后。
- YouTube、Google 学术位于 Google 前。开发工具位于代码托管前，避免 npm 被 GitHub 合集提前匹配。
- 具体服务位于非中国通用域名集前；国内完整域名集排在所有业务及非中国域名之后，避免其中较宽的条目覆盖业务分类。
- 域名阶段之后再排列 IP 规则：私有 IP → 业务 IP → 国内 IP。
- IP 子规则携带 `no-resolve`：未解析的域名不会因匹配这些规则而触发 DNS；IP 字面量及已解析的地址可以参与 IP 匹配。

同一分类内删除完全重复的规则，保留不同分类间的重叠，由主配置顺序决定最终命中。`cn.list` 是上游 geolocation-cn 精简集；`cn-full.list` 是上游完整 cn 集，两者位置各有用途。

## 构建与验证

Python 3.9 或更新版本，仅使用标准库。在仓库根目录执行：

```bash
python3 -m unittest discover -s tests -v
python3 scripts/build.py
python3 scripts/verify.py
```

构建先将上游 meta 分支解析成完整提交 SHA，随后从该提交下载全部来源。脚本完成全部下载与转换后才写出规则；下载错误、空来源或无法表达的输入格式会使构建失败。分类修改写入 catalog.json，生成文件由脚本维护。

按 manifest.json 中的 revision 复现某次构建：

```bash
python3 scripts/build.py --revision <完整的上游提交SHA> --output-dir /tmp/subboost-surge-rebuild
python3 scripts/verify.py --root /tmp/subboost-surge-rebuild
```

验证器独立读取生成后的 Surge 规则，检查文件集合、SHA-256、重复项、引用清单及 tests/routes.json 中的正反向分流用例。发布后，还应验证公开 URL 实际提供的文件与本地完全一致：

```bash
python3 scripts/verify.py --base-url https://raw.githubusercontent.com/leorxx11/SubBoost-Surge-Rules/main/rules
```

本地核验 HTTP 传输时，在一个终端运行以下命令，再在另一个终端执行验证命令；完成后按 Ctrl-C 结束临时服务：

```bash
python3 -m http.server 18765 --bind 127.0.0.1
```

```bash
python3 scripts/verify.py --base-url http://127.0.0.1:18765/rules
```

Surge 原生验收应另外检查配置加载和实际请求记录。Python 分流校验验证的是生成内容与顺序，不能替代客户端真实请求命中的验收。

## 自动更新

[更新工作流](.github/workflows/update.yml) 在每天北京时间 10:17 左右触发，也支持手动触发。修改分类、脚本或校验用例后，main 分支会触发构建；PR 只执行构建与校验。

工作流依次执行转换测试、构建、分流校验，全部通过后将 rules/ 与 examples/ 的变化提交到 main。GitHub Actions 需要仓库的 contents 写入权限；分支保护也需要允许该更新提交。定时任务的实际运行时间由 GitHub 调度决定。

## 来源与许可

代码和分类配置采用 AGPL-3.0-only，见 [LICENSE](LICENSE)。规则数据的上游来源与许可说明见 [NOTICE.md](NOTICE.md)。
