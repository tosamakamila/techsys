# 启动效率优化方案

> 响应体验报告第 1、2 条。两个改动都在 `map.py` 一个文件内，互不冲突。

---

## 一、快速续课：`--go` 参数

### 行为

```
python scripts/map.py --go
```

跳过整个导航 UI，直接读取 `map_state.json` 的（位置+老师+课程+同学），验证引用有效后写 scene 文件并退出。

### 具体流程

1. 加载 `map_state.json` → 取出 `last_location / last_teacher / last_course / last_classmate`
2. 验证：老师仍在 `characters/` 下、课程仍在 `courses/` 下
3. 如果验证失败 → 打印错误提示，退回校门口（或直接报错退出）
4. 根据 `last_location` 推断 scene：
   - `classroom` → 同位置的动作表中取 scene 类型动作（正常上课/课后辅导），默认 `teaching`
   - `study_room` → `review_with_teacher`
   - `library` → 默认 `chat`
   - 其他 → 报错（gate/classroom_door 不可直接进入教学场景）
5. 如果当前位置有多个 scene 动作（如教室有"正常上课"和"课后辅导"），`--go` 默认取第一个 scene 类型动作，可通过 `--mode` 覆盖：

```
python scripts/map.py --go                  # 默认教学场景
python scripts/map.py --go --mode tutoring  # 课后辅导
```

6. 写 `current_scene.json` → 退出

### map.py 改动量

- `parse_args()` 加 `--go` 和 `--mode` 参数
- `main()` 开头：若 `--go` 为真，走快捷路径（加载 state → 验证 → 推断 scene → 写文件 → 直接 return），不进入主循环
- 约 30 行新增

### 使用场景

| 命令 | 场景 |
|------|------|
| `python scripts/map.py --go` | 和上次一模一样的课继续上 |
| `python scripts/map.py --go --course uv` | 换课但同老师同上课模式 |
| `python scripts/map.py --go --mode tutoring` | 上次上课但这次换辅导模式 |

---

## 二、一键启动：`--server` 参数

### 行为

```
python scripts/map.py --server
```

在 map.py 启动前/后自动拉起 `map_server.py` 作为后台进程。map.py 退出时自动关闭 server。

### 两种实现路径

**路径 A：map.py 内嵌 server 线程**

```python
# map.py 新增
def start_server(port=8765):
    """在守护线程中启动 HTTP 服务器。"""
    from map_server import MapHandler
    server = HTTPServer(("127.0.0.1", port), MapHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, f"http://127.0.0.1:{port}"
```

- 优点：一个进程，自动同生命周期
- 缺点：map.py 和 map_server.py 的依赖耦合；线程异常处理
- 改动量：map.py 约 15 行

**路径 B：map.py 启动时 spawn 子进程**

```python
def start_server(port=8765):
    """启动 map_server.py 子进程。"""
    server_script = SCRIPTS_DIR / "map_server.py"
    proc = subprocess.Popen(
        [sys.executable, str(server_script), "--port", str(port), "--no-browser"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    return proc
```

map.py 退出前 `proc.terminate()`。

- 优点：进程隔离，改动更少
- 缺点：Windows 上子进程清理可能不可靠（Ctrl+C 不一定传播到子进程）
- 改动量：map.py 约 10 行

### 推荐：路径 A（线程）

理由：
- `--server` 的典型场景是"看一眼知识地图面板，同时用终端导航上课"，生命周期绑定
- `HTTPServer` 本身就是线程安全的，`serve_forever` 在 daemon 线程中运行，主线程退出时自动结束
- 路径 B 的 Windows 子进程清理是个真实问题——用户 Ctrl+C 退出 map.py，server 进程可能残留

### 细节

- `--server` 默认端口 8765，`--port` 覆盖
- `--server` 时不自动打开浏览器（因为用户已经在终端里了），除非加 `--open`
- map.py 启动时在顶栏显示 server 地址

---

## 三、两个参数可以组合

```
python scripts/map.py --go --server    # 一键进课堂 + 面板后台
```

这是最快的启动路径：一条命令，课堂就绪 + 地图面板在线。

---

## 四、改动总结

| 参数 | 改动文件 | 新增行数 |
|------|---------|---------|
| `--go` | map.py | ~30 行 |
| `--server` | map.py | ~15 行 |
| 两者组合 | 无额外改动 | 天然兼容 |

全部改动只在一个文件（`map.py`），不影响其他脚本或协议。

---

## 五、边界情况处理

| 情况 | --go 行为 |
|------|----------|
| 首次使用，无 `map_state.json` | 报错提示："还没有上课记录，请先运行 map.py 选择场景" |
| 上次的老师角色被删除 | 报错提示："上次的老师（XX）已不存在，请重新选择" |
| 上次的课程被删除 | 回退到选课程，或报错提示换课 |
| 上次位置是 gate/classroom_door | 报错提示："上次未进入教学场景，请先手动选择" |
| 教室有多个 scene（上课/辅导）| 默认取第一个 scene 动作，`--mode` 覆盖 |
| `--server` 端口被占用 | 自动尝试下一个端口（8765→8766→8767）|
