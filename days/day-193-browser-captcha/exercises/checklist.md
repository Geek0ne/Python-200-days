# Day 193 练习与验收清单

> 所有命令都在本目录内执行：
> ```bash
> cd days/day-193-browser-captcha/code
> ```
> 每个脚本都支持 `--self-test`，离线即可验证逻辑；涉及浏览器的脚本会自动拉起本地靶站。

---

## 一、今日完成清单

- [ ] 能说清"数据不在 HTML 里"与"请求被拦截"的区别，并用 `curl | grep` 判断
- [ ] 用 Playwright 渲染一个动态页，拿到 JS 注入的内容
- [ ] 说出 4 种不可靠等待策略各自为什么不可靠
- [ ] 用 `wait_for_selector` 与 `wait_for_function` 各写一次等待
- [ ] 用 `context.route()` 阻断图片/字体，并比较渲染耗时
- [ ] 采集 UA / platform / timezone / screen / Canvas / WebGL / 字体 七项指纹
- [ ] 解释为什么"只改 UA"可能让风险评分变高
- [ ] 用 ddddocr 识别一张验证码，打印结果与耗时
- [ ] 用 Otsu 二值化做对比，说明什么噪声强度下它有用
- [ ] 实现"失败换图 + 最多 3 次"的登录重试
- [ ] 用 `INSERT ... ON CONFLICT` 做幂等入库
- [ ] 跑通 `04-production-scraper.py` 的浏览器模式与 `--dry-run` 两种路径

---

## 二、基础练习

### 练习 1：判断该不该渲染（5 分钟）

靶站首页：`python3 00-lab-target.py --port 8931` 然后另开一个终端：

```bash
curl -s http://127.0.0.1:8931/ | grep -c '<li>'
curl -s http://127.0.0.1:8931/api/items?page=1\&ds=0 | head -c 200
```

**要求**：解释为什么第一条是 0，第二条有数据；说出这种情况下"上浏览器"和"直接打接口"
哪个更划算，以及"直接打接口"需要什么前提。

---

### 练习 2：把 4 种错误等待各写一遍

在 `01-basic-render.py` 里新增一个策略 `"wait-for-text"`：

```python
page.wait_for_selector("#status:has-text('ready')", timeout=10000)
```

**要求**：
1. 跑一遍，记录耗时与 items；
2. 解释它和 `wait_for_selector("#status")` 的区别（提示：文本谓词 vs 存在性）；
3. 如果页面永远不出现 `ready`，超时异常是什么类型？把它捕获并计入结果。

---

### 练习 3：指纹字段补全（进阶）

在 `02-pitfall-fingerprint.py` 的页面 JS 里增加三项：

- `navigator.plugins.length`
- `Intl.DateTimeFormat().resolvedOptions().locale`
- `navigator.connection?.effectiveType`

**要求**：跑四个配置，回答"哪一项在四配置下都不变"，并解释原因。

---

### 练习 4：验证码噪声强度扫描

用 `captcha_lib.py` 生成 4 档噪声（可以自己加 `"severe"`），每档 50 张：

```bash
python3 -c "
from captcha_lib import build_dataset
for n in ['clean','medium','hard']:
    build_dataset(f'/tmp/cap-{n}', 50, n)
"
python3 03-captcha-ocr.py --n 50 --datasets /tmp/captcha-ds
```

**要求**：画一张"噪声强度 × 准确率"的表（终端文本即可），
指出准确率开始断崖式下跌的拐点，并解释该拐点对应的图像特征。

---

### 练习 5：给登录加上"失败原因"分类

现在 `04-production-scraper.py` 只记录 `ok`。请把失败原因分成三类并入库：

| 原因 | 判据 |
|---|---|
| `ocr_empty` | 识别结果为空串 |
| `ocr_wrong` | 非空但 403 |
| `rate_limited` | 403 且连续 2 次同一 IP 失败（靶站可加一个 `X-Fail-Streak` 头） |

**要求**：新增一列 `fail_reason`，跑 20 次，统计三类占比。

---

## 三、进阶挑战

### 挑战 1：把固定等待改成"内容指纹"等待

有些页面列表长度固定，但内容会变。写一个 `wait_for_content`：

```python
def wait_for_content(page, sel, expect_hash, timeout=10):
    page.wait_for_function(
        "([s, h]) => { const els=[...document.querySelectorAll(s)];"
        "const t=els.map(e=>e.textContent).join('|');"
        "let x=0; for (let i=0;i<t.length;i++) x=(x*31+t.charCodeAt(i))>>>0;"
        "return els.length>0 && x.toString(16)===h; }",
        arg=[sel, expect_hash], timeout=timeout*1000)
```

**要求**：说明它比"等数量"强在哪，以及 expect_hash 应该怎么获得（不能写死）。

---

### 挑战 2：验证码预处理的自动选择

实现 `auto_mode(img)`：根据图像统计量（边缘密度、连通域数量、Otsu 类间方差）
自动选 `none/gray/otsu/denoise`，并在 300 张数据集上报告相对固定 `none` 的提升。

**要求**：给出准确率与"选错档"的比例；如果提升为负，说明为什么（这很可能是真实结果）。

---

### 挑战 3：并发渲染的吞吐与内存

用 `asyncio + async_playwright` 同时渲染 1/4/8 个页面（同一 browser，多 context）：

**要求**：记录
- 总耗时、单页均摊耗时
- 峰值内存（`ps -o rss= -p <browser_pid>`）
- 失败率

回答：为什么并发到某个数量后总耗时不再下降？

---

## 四、验收：读者在本机的确切命令

按顺序执行，全部应通过：

```bash
cd days/day-193-browser-captcha/code

# 1) 靶站逻辑（8 项断言，无需浏览器）
python3 00-lab-target.py --self-test

# 2) 渲染策略（自动起靶站，约 25s）
python3 01-basic-render.py

# 3) 指纹（4 个配置，约 15s）
python3 02-pitfall-fingerprint.py

# 4) 验证码基准（先自检，再跑 300 张，约 3–5 分钟）
python3 03-captcha-ocr.py --self-test
python3 03-captcha-ocr.py --n 100

# 5) 端到端（浏览器 + 纯 HTTP 两条路径）
python3 04-production-scraper.py --logins 10
python3 04-production-scraper.py --dry-run --logins 5 --db /tmp/day193-dry.db
```

**通过标准**：

| 步骤 | 通过标准 |
|---|---|
| 1 | 输出"全部通过"，8 项 ✅ |
| 2 | 至少 `selector-items` 与 `wait-function` 拿到 12 条 |
| 3 | 输出四行 risk，B 的 risk 不低于 A（复现"越改越露"） |
| 4 | clean 下 `none` ≥ 95%；hard 下 `otsu` 高于 `none` |
| 5 | 浏览器 10/10；dry-run 5/5；指标里 `items=12` |

**若某项不通过**：
- 浏览器相关 → `python3 -c "import playwright; print(playwright.__version__)"`，
  并检查 `~/.cache/ms-playwright` 是否有 chromium；脚本会自动用 `executable_path` 回退。
- OCR 相关 → `python3 -c "import ddddocr"`；缺依赖时 `04` 的 `--dry-run` 会跳过登录并明确提示。
- 端口冲突 → `01`/`02`/`04` 都用随机端口，不会冲突；手动起靶站时换 `--port`。

---

## 五、清理

```bash
# 删除实验数据（可选）
rm -rf /tmp/captcha-ds /tmp/cap-* /tmp/day193-*.json /tmp/day193-*.db
# 确认没有残留靶站
pgrep -af '00-lab-target.py' || echo '无残留'
```

**注意**：脚本退出时会 `terminate()` 自己拉起的靶站；
如果你用 `--port 8931` 手动起的，需要自己 `Ctrl-C`。

---

## 六、常见失败排查（实测过的坑）

| 现象 | 根因 | 处理 |
|---|---|---|
| §Executable doesn't exist at .../chromium_headless_shell-1248§ | pip 的 Playwright 版本与本地浏览器 revision 不匹配 | 脚本自动回退：用 §executable_path§ 指向 §~/.cache/ms-playwright/chromium-*/chrome-linux64/chrome§ |
| §正确答案也 403，reason=no_sid§ | 闭包捕获了旧 §sid§，第二次仍用第一张图的会话 | 会话显式传参；区分 §no_sid§ 与 §wrong§ |
| §networkidle§ 很快返回但列表为空 | 定时器未触发，页面"确实"无网络活动 | 改用 §wait_for_selector("#list li")§ 或 §wait_for_function§ |
| §sleep(1)§ 后 items 仍为 0 | 总延迟 ≈1.4s，固定等待不够 | 不要用固定 sleep；等待目标内容 |
| OCR 在干净图上是 94% 而不是 98% | 多做了去噪/二值化 | 干净图用 §none§，强噪声才用 §otsu§ |
| §pip install playwright§ 报 PEP 668 | 系统 Python 受管 | 用 venv，或明确加 §--break-system-packages§（本课实测环境即如此） |

> 以上每一条都对应 README 里的原始输出，可作为回归检查项。

