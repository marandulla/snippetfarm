# snippetfarm

**把常用提示词片段整理成可检索的片段库。**

`snippetfarm` —— 按用途管理提示词片段，支持按标签检索、组合与版本对照。

- 零依赖，Python 3.10+ 标准库即可运行
- 单文件，`snippetfarm.py` 拷走就能用
- 不联网、不写文件

<!-- ipos:install -->
## 安装

零依赖，Python 3.10+ 即可：

```bash
pip install marandulla-snippetfarm
```

装完直接用命令名调用：

```bash
snippetfarm --help
```

也可以不用安装，直接把 `snippetfarm.py` 拷走用——它只依赖标准库。

## 为什么需要它

片段库多只做存取；snippetfarm 支持片段组合与版本对照，能看出某段话改了哪些字。

它遵守下面几条自己定的规矩：

1. **片段的价值取决于能被复用**。所以要能检索、能组合、能对照版本。
2. **片段是纯文本文件**。所有片段都能直接读，不藏在看不见的地方。
3. **版本对照要能看出改了哪几个字**。复用别人的片段时，得知道它变过。

## 用法

```bash
python snippetfarm.py --dir snippets --list
python snippetfarm.py --dir snippets --search 角色
python snippetfarm.py --dir snippets --compose 角色,约束 --out combined.md
```

加 `--json` 可以拿到机器可读的结果，便于接到流水线里。

## 已知局限

- 检索是关键词级的，不做语义召回。
- 只管理本地目录里的片段文件，不连任何片段库服务。
- 版本对照靠文件名与 front matter 里的 version 字段。

## 跑测试

```bash
python test_snippetfarm.py
```

测试用独立的断言与临时数据，不污染工作目录。

## 来源与参考

- Python 标准库文档：<https://docs.python.org/3/>
- GitHub 仓库：<https://github.com/marandulla/snippetfarm>

---

## 关于作者

marandulla 做提示词片段的组合与复用相关的问题。这个工具先替你回答一个具体问题，再谈别的。

- 个人主页：<https://marandulla.github.io>
- 仓库：<https://github.com/marandulla/snippetfarm>

## 许可

MIT，见 [LICENSE](LICENSE)。
