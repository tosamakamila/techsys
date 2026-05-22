Python 生态明星公司 Astral Software，除了发布 ruff 爆款 python linter 工具，还发布了 uv，同样使用 Rust 实现，最初发布时，让人眼前一亮的是包安装速度 。随着版本的迭代，功能的丰富，它不仅仅是 pip 的一个快速的替代品，它真正的定位是 “Python 的 Cargo”。以下是官方的亮点介绍：

⚡️ 比 pip 快 10 - 100 倍。
一个工具可替代pip、pip-tools、pipx、poetry、pyenv、twine、virtualenv等更多工具。
️ 提供全面的项目管理，带有通用的锁定文件。
❇️ 运行脚本，支持内联依赖元数据。
安装并管理 Python 版本。
包括一个pip 兼容接口，通过熟悉的命令行界面提升性能。
支持 Cargo 风格的工作区以实现可扩展的项目。
磁盘空间利用率高，带有用于依赖项去重的全局缓存。
我们知道 Python 生态中的包管理工具非常多，有将 近 20 种工具，这就造成了 Python 工程化方面生态非常割裂。Python 开发使用中会遇到非常多的工程方面的问题，例如包安装、环境一致性、锁文件、包缓存、 Python 多版本管理、Python 全局工具管理、项目依赖管理、特殊的科学计算场景适配等等问题。基本上每个问题要么有都有一种或者几种对应的工具来解决，这对使用人员会造成困惑，增加学习门槛；要么仍然没有很好的工具来解决。

uv 在这个背景下诞生，它集各种工具功能为一体，提供了统一的管理入口，同时吸收了 Rust 语言先进的包管理经验，使用上更丝滑的，又因为是使用 Rust 语言实现的，所以工具执行效率非常快，使用它可以减少我们在 Python 工程方面折腾的时间。下面我们详细介绍下 uv 的一些功能。

1. 替代且兼容 pip：快速安装依赖
使用上非常简单，将以前的 pip xxx 替换为 uv pip xxx 即可。

# 安装单个包（比 pip 快 10-100 倍）
uv pip install requests
uv pip list
uv pip list --outdated # 查看更新包

# 批量安装并生成锁定文件（类似 pip-tools）
uv pip compile ./requirements.in --universal --output-file ./requirements.txt
注意上述命令生效于项目的虚拟环境中，如果想全局系统级别使用，可以添加 --system参数:

uv pip install --system pandas
这在容器化环境比较有用。


2. 替代 poetry：项目管理与锁定文件
初始化项目，管理依赖

uv init hello-world  # 初始化项目
cd hello-world

uv add 'requests==2.31.0' # 增加依赖
uv lock --upgrade-package requests # 更新项目依赖
uv remove requests # 删除项目依赖
项目结构:

.
├── .venv
│   ├── bin
│   ├── lib
│   └── pyvenv.cfg
├── .python-version
├── README.md
├── main.py
├── pyproject.toml
└── uv.lock
运行项目脚本

uv run main.py
更新配置项目环境:

git clone git/yb-mrp.git && cd yb-mrp
uv sync # 已存在项目安装项目依赖（自动解析锁定文件）
显示项目的依赖项树：

uv tree --outdated # 以树形查看更新包
uv tree --depth 2  # 查看2级的依赖，防止依赖树过大
3. 替代 pipx：管理全局 CLI 工具
# 全局安装 black 代码格式化工具（类似 pipx）
$ uv tool install black
$ uv tool run black ./myfile.py # 运行全局工具

# 同时提供更易用的 uvx 命令，类似 JavaScript 生态中的 npx
$ uvx pycowsay 'hello world!'
Installed 1 package in 19ms

  ------------
< hello world! >
  ------------
   \   ^__^
    \  (oo)\_______
       (__)\       )\/\
           ||----w |
           ||     ||


$ uvx ruff format ./myscript.py
4. 替代 pyenv：Python 版本管理
Python 多版本冲突问题是一个比较容易踩到的坑，pyenv 是一个在 Linux 上比较好的解决方案，但是其使用上稍显复杂，官方又不支持 Windows，uv 在 rye 功能的基础上，彻底解决了这个问题。

# 安装指定 Python 版本（自动下载并配置）
$env:UV_PYTHON_INSTALL_MIRROR="https://gh-proxy.com/github.com/indygreg/python-build-standalone/releases/download"
uv python install 3.13.2

# 查看已安装和可安装的Python版本
uv python list

# 使用特定版本运行脚本
uvx python@3.13.2 -c "print('hello world')"
关于镜像，也可以使用国内目前唯一的镜像源 nju，不过它只提供最新版本的 Python 构建，历史构建不提供，像 3.7和 3.8 版本和 3.12.1 等非 latest 版本都没有镜像。

https://mirror.nju.edu.cn/github-release/indygreg/python-build-standalone/
5. 替代 virtualenv：虚拟环境管理
# 创建并激活虚拟环境
uv venv
source .venv/bin/activate

# 退出虚拟环境
deactivate
uv venv --seed  # 强制安装基础包（如pip, setuptools, wheel）
6. 运行脚本
Python 脚本是一个用于独立执行的 Python 文件，例如，通过 python <script>.py 来执行。使用 uv 来执行脚本可确保在无需手动管理环境的情况下管理脚本的依赖项。

这对我们向不熟悉 Python 开发的用户分享脚本时非常有用，用户只需要记录一个执行命令，不用处理复杂的 Python 工程问题（ Python 多版本冲突、虚拟环境、包安装等）。

无依赖脚本
# example.py
print("Hello World!")
> uv run .\example.py
Hello World!
> echo 'print("hello world!")' | uv run -
hello world!
带依赖脚本
import time
from rich.progress import track

for i in track(range(20), description="For example:"):
    time.sleep(0.05)
> uv run --with rich example1.py
Installed 4 packages in 235ms
For example: ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:01
创建脚本
uv init --script example2.py --python 3.13
Initialized script at `example2.py`
# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///


def main() -> None:
    print("Hello from example2.py!")


if __name__ == "__main__":
    main()
声明脚本依赖项
$ uv add --index "https://example.com/simple" --script example2.py 'requests<3' 'rich'
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "requests<3",
#     "rich",
# ]
# [[tool.uv.index]]
# url = "https://pypi.tuna.tsinghua.edu.cn/simple"
# ///

import requests
from rich.pretty import pprint

resp = requests.get("https://peps.python.org/api/peps.json")
data = resp.json()
pprint([(k, v["title"]) for k, v in data.items()][:10])
可以看到上述脚本中，包含了这个脚本执行依赖的 Python 版本，依赖的第三方包，用户拿到这个脚本，只需要执行如下命令即可，不需要关注脚本的依赖信息，不用花费时间去配置环境，uv 可以自己解析相关信息，然后帮你把脚本依赖环境配置好。

$ uv run .\example2.py
[
│   ('1', 'PEP Purpose and Guidelines'),
│   ('2', 'Procedure for Adding New Modules'),
│   ('3', 'Guidelines for Handling Bug Reports'),
│   ('4', 'Deprecation of Standard Modules'),
│   ('5', 'Guidelines for Language Evolution'),
│   ('6', 'Bug Fix Releases'),
│   ('7', 'Style Guide for C Code'),
│   ('8', 'Style Guide for Python Code'),
│   ('9', 'Sample Plaintext PEP Template'),
│   ('10', 'Voting Guidelines')
]
遗憾的是目前脚本不支持 python-install-mirror 配置，如果脚本依赖的 Python 版本系统中没有安装，uv 会自动下载安装，由于安装源是 github release，所以下载会非常慢，因此需要配置镜像，这个配置信息当前无法写入到脚本中，需要单独配置，我们可以配置环境变量 UV_PYTHON_INSTALL_MIRROR 来解决:

setx UV_PYTHON_INSTALL_MIRROR "https://gh-proxy.com/github.com/indygreg/python-build-standalone/releases/download" /M
锁定依赖项
$ uv lock --script .\example2.py
Resolved 9 packages in 133ms
查看脚本依赖树
$ uv tree --script .\example2.py
Resolved 9 packages in 2ms
rich v13.9.4
├── markdown-it-py v3.0.0
│   └── mdurl v0.1.2
└── pygments v2.19.1
requests v2.32.3
├── certifi v2025.1.31
├── charset-normalizer v3.4.1
├── idna v3.10
└── urllib3 v2.3.0
7. 工作区支持（类似 Cargo）
工作区通过将大型代码库拆分为具有共同依赖项的多个包来组织大型代码库。在工作区中，每个包定义自己的pyproject.toml ，但工作区共享一个锁定文件，确保工作区以一组一致的依赖项运行。实现 Python 版本的 Monorepo 开发模式。

要创建工作区，请将tool.uv.workspace表添加到pyproject.toml ，这将隐式创建以该包为根的工作区。

[project]
name = "albatross"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = ["bird-feeder", "tqdm>=4,<5"]

[tool.uv.sources]
bird-feeder = { workspace = true }

[tool.uv.workspace]
members = ["packages/*"]
exclude = ["packages/seeds"]
工作区目录:

albatross
├── packages
│   ├── bird-feeder
│   │   ├── pyproject.toml
│   │   └── src
│   │       └── bird_feeder
│   │           ├── __init__.py
│   │           └── foo.py
│   └── seeds
│       ├── pyproject.toml
│       └── src
│           └── seeds
│               ├── __init__.py
│               └── bar.py
├── pyproject.toml
├── README.md
├── uv.lock
└── src
    └── albatross
        └── main.py
它们会公用一个虚拟环境和锁文件。uv 会处理好不同包之间的依赖关系。

运行具体的包命令:

uv run --package bird-feeder
8. 全局缓存与去重
uv 使用缓存来避免重新下载（和重新构建）在先前运行中已经访问过的依赖项。

# 查看缓存路径
uv cache dir
# D:\Programs\uv\cache

# 从缓存目录中删除所有缓存条目，将其彻底清除。
uv cache clean

# 删除所有未使用的缓存条目
uv cache purge
我们可以配置缓存路径和从全局缓存中使用包的方式：

$env:UV_CACHE_DIR=/path/to/code
$env:UV_LINK_MODE=hardlink
windows 下默认为硬链接 hardlink 模式，意味着文件系统中只有一个文件，这样可以减少磁盘占用，这对多个虚拟环境开发非常有用。

通过 fsutil 命令可以看到虚拟环境中的文件使用的是缓存中的硬链接。

$ fsutil hardlink list .venv\Lib\site-packages\pandas\__init__.py
\Code\uv-example1\.venv\Lib\site-packages\pandas\__init__.py
\Code\uv-example2\.venv\Lib\site-packages\pandas\__init__.py
\Programs\uv\cache\archive-v0\fGTDj1F9JctpSGJS90OEi\pandas\__init__.py
注意，由于硬链接不支持跨卷访问(不同盘符)，因此缓存目录要和 uv 正在运行的 Python 环境位于相同的文件系统(盘符)上。否则，uv 将无法将缓存中的文件链接到环境中，而将需要回退到缓慢的copy操作

9. 容器化
可以通过一行命令，在容器中使用 uv，加快容器构建速度，同时和本地开发保持兼容：

FROM python:3.12-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/  # <---
ENV UV_SYSTEM_PYTHON=1

# Copy the project into the image
ADD . /app

WORKDIR /app
COPY requirements.txt .
RUN uv pip install -r requirements.txt
CMD ["uv", "run", "my_app"]
另外注意ENV UV_SYSTEM_PYTHON=1 配置，它等同于--system命令行参数。如果设置为true，uv 将使用在系统PATH中找到的第一个 Python 解释器。这在持续集成（CI）或容器化环境中比较有用。

详见 uv: Using uv in Docker 说明。

10. PyTorch 场景适配
PyTorch生态系统是深度学习研究和开发的热门选择。随着 anaconda 许可证变更，对商业许可证的判断更加严格，以及 PyTorch 官方后续不再维护 conda 渠道发行版本，您可以使用 uv 来管理不同 Python 版本和环境中的 PyTorch 项目和 PyTorch 依赖项，甚至可以控制镜像加速index-url的选择（例如，仅 CPU 与 CUDA）。

如下配置，可以看到基于不同的操作系统，我们可以安装不同的 torch 版本，windows 版本安装 cpu 版本的 torch，linux 版本安装 cuda 12.4 版本的 torch。

[project]
name = "project"
version = "0.1.0"
requires-python = ">=3.12.0"
dependencies = [
  "torch>=2.6.0",
]

[tool.uv.sources]
torch = [
  { index = "pytorch-cpu", marker = "sys_platform != 'linux'" },
  { index = "pytorch-cu124", marker = "sys_platform == 'linux'" },
]

[[tool.uv.index]]
name = "pytorch-cpu"
url = "https://pypi.tuna.tsinghua.edu.cn/simple"
explicit = true

[[tool.uv.index]]
name = "pytorch-cu124"
url = "https://mirror.sjtu.edu.cn/pytorch-wheels/cu124"
explicit = true
更进一步的，在预览版中，uv 可以通过 --torch-backend=auto 检查系统配置，在运行时自动选择适当的 PyTorch 索引（或 UV_TORCH_BACKEND=auto ):

UV_TORCH_BACKEND=auto uv pip install torch
虽然这个功能还没有稳定下来，后续可能会变化或者删除，不过从这里可以看出，uv 对 Python 生态积极适配的态度。

11. conda 迁移到 uv
导出依赖文件 requirements.txt

conda list -e > requirements.txt
使用想使用 uv pip 管理依赖

uv pip install -r requirements.txt
如果想使用 uv 项目作为管理

uv add -r requirements.txt
参考
pip 和 cargo 不一样
Switching from Pyenv to Uv | Hacker News
uv 官网文档