# PG Soft Spin按钮偶发卡死 — 深度调试手册 v2

> **适用游戏**: Bali Vacation (gid:94)
> **Shell版本**: 3.29.0.3 / 引擎 7.1.3 / 7.3.1-rc.2
> **日期**: 2026-03-15
> **前置文档**: `debug_complete_handbook_v20.md` + `spin_stuck_debug_handbook_v1.md`
>
> **本文档聚焦**: v1之后的新发现、不透明数组完全解码、engine.js分析、996b.js初步分析

---

## 一、本轮核心进展

### 1.1 v23 patch 失败（已回滚到 v22）

在 5135.js 的 subscribe 回调中给 Promise 链加了 try-catch 保护，**无效**。说明问题不是 Promise 链断裂。

| 版本 | Offset | 改动 | 结果 |
|------|--------|------|------|
| v23 | 451268 | `handler(result).then(s,e)` → `try{handler(result).then(s,e)}catch(e){s(result)}` | **无效，已回滚** |
| v23 | 451905 | 同上（第二个 subscribe 回调） | **无效，已回滚** |

### 1.2 ★★★ 不透明条件数组完全解码

**5135.js 的不透明数组**：`A4z(18, 6, [18])`

该函数生成 18×18 的**循环引用数组**。`arr[i][j]` 存储的是对 `arr[k]` 的**引用**（不是值），形成循环结构。所有不透明条件比较的是**对象引用相等性**（`===`），不是值。

解码后的引用映射表（每3行一个循环，共6个周期）：
```
arr[0]:  arr[0][j] → arr[j]       (identity: 0→0, 1→1, ..., 17→17)
arr[1]:  arr[1][j] → arr[(j+6)%18] (shift 6: 0→12, 1→13, ..., 17→11)
arr[2]:  arr[2][j] → arr[(j+12)%18] (shift 12: 0→6, 1→7, ..., 17→5)
arr[3]:  same as arr[0]
arr[4]:  same as arr[1]
arr[5]:  same as arr[2]
... (repeats every 3 rows)
```

**5135.js 所有关键不透明条件评估结果**：

| 位置 | 条件表达式 | 值 | 含义 |
|------|-----------|------|------|
| 1524 error分支 | `arr[8][9][9] != arr[7][11][17]` | **TRUE** | 错误处理正常执行 |
| 1524 完成分支 | `arr[5][7][15] == arr[8][9][5]` | **FALSE** | 依赖 `a$_[7]<0` 判断链完成（正确） |
| Q0z 惩罚入口 | `n7_[544] && arr[7][8][3] != arr[14][17][17]` | **FALSE** (n7_[544]=false) | 惩罚不触发 ✓ |
| Q0z enterCb | `arr[1][3][9] != arr[0][2][17] && n7_[544]` | **FALSE** (n7_[544]=false) | 惩罚不触发 ✓ |
| exitCb 条件A | `arr[11][11][3] != arr[4][4][11]` | **TRUE** | 存储的completeCb路径正常 |
| exitCb 条件B | `arr[13][5][12][9] != arr[6][13][11]` | **TRUE** | 直接completeCb路径正常 |

**结论：5135.js 状态机逻辑 100% 正确，不透明条件不影响正常流程。**

---

**996b.js 的不透明数组**：`l6t(21, 3, [21])`

同算法，21×21 循环引用数组，shift=3。

996b HTTP 响应处理中的关键不透明条件：

| 条件 | 值 | 含义 |
|------|------|------|
| `arr[14][10][16] != arr[18][9][19]` (外层fetch分支) | **FALSE** | 进入 `this[2546](url)` 判断分支 |
| `arr[0][14][7] == arr[12][18][6]` (response.ok检查) | **FALSE** | !ok 时正常抛错（不会误判） |
| `arr[13][10][4] == arr[9][10][9]` (content-type检查) | **FALSE** | 有content-type时不会误判 |
| `arr[5][17][13] == arr[3][8][4]` (wasm handler) | **TRUE** | wasm 分支走 g$N6bVaJ[2471] |
| `arr[10][5][16] != arr[8][4][20]` (css handler) | **TRUE** | css 分支正常处理 |

---

## 二、engine.js (index_acdaa.js) 完整分析

### 2.1 文件基本信息

- 文件大小：2,285,079 bytes
- 引擎：Cocos Creator
- 混淆方式：函数名混淆 + 十六进制字符串查找表

### 2.2 SpinButtonController 状态机

**类定义**：offset 2055652
**BV特化版**：offset 335250（BVSpinButtonController，继承SpinButtonController）

**状态枚举 G（SpinButtonState）**：
| 值 | 名称 | 含义 |
|----|------|------|
| 1 | IDLE | 空闲可点击 |
| 2 | SPINNING | 旋转中 |
| 3 | SUSPENDED | 挂起/等待 |

**模式枚举 g（SpinButtonMode）**：
| 值 | 名称 | 含义 |
|----|------|------|
| 0 | DISABLED | 不可用 |
| 1 | ENABLED | 可用 |
| 2 | AUTO_SPIN | 自动旋转 |

### 2.3 ★★★ yb 默认值确认

**offset 2057374**（构造函数/属性初始化）：
```javascript
Q['yb'] = G['SUSPENDED']  // = 3
Q['Bb'] = false
Q['Mb'] = undefined
Q['Hb'] = undefined
```

**yb 的初始值就是 3（SUSPENDED）。必须调用 enable() 才能变为 1（IDLE）。**

### 2.4 关键方法

| 方法 | Offset | yb变化 | 说明 |
|------|--------|--------|------|
| enable() | 2060812 | yb → 1 (IDLE) | 调用 onIdleAction 回调 |
| spin() | 2061151 | yb → 2 (SPINNING) | 调用 onSpinAction 回调 |
| stopSpin() | 2061959 | yb → 3 (SUSPENDED) | 调用 onSuspendedAction 回调 |

### 2.5 Oc 方法（spin完成处理）

**offset 874586**：
```javascript
Oc = function() {
    var Z = this.spinButtonController;
    Z.exitAutoSpinMode();    // 清理自动旋转
    Z.enable();              // ← 设置 yb=1 (IDLE)
    this.onAfterIdle();      // UI恢复
    this.Uc();               // 清理
    this.exitAutoSpinActions();
    this.Rc(this.onAfterSpin.bind(this));  // Rc = 状态机回调
}
```

### 2.6 Mc 方法（UI清理）

**offset 888255**：与 Oc 类似结构，也调用 enable()。
Mc 和 Oc 总是在 tryAutoSpin 逻辑中**一起调用**（offset 870267）：
```javascript
if (!isAutoSpinMode() || S) {
    this.Mc();  // UI清理
    this.Oc();  // enable + Rc callback
} else {
    // auto spin 逻辑
}
```

### 2.7 Oc/Mc 的所有引用位置

| Property | Offsets |
|----------|---------|
| 'Oc' | 441261, 823720, 870280, 871034, 874586(定义), 875630, 877935, 963907, 963924 |
| 'Mc' | 425994, 441248, 866622, 870267, 875617, 877922, 888255(定义), 1265317, 1265692, 1273685 |

**所有 Oc/Mc 调用都是在 spin 完成后。首次从 SUSPENDED→IDLE 的 enable() 调用必须来自初始化流程。**

---

## 三、5135.js 状态机完整解析

### 3.1 状态转换图

```
n7_[124] = new n7_[210]([
    { from: 566, to: 553 },   // INIT → LOADED
    { from: 553, to: 365 },   // LOADED → READY
    { from: 365, to: 1802 },  // READY → SPINNING
    { from: 1802, to: 608 },  // SPINNING → RESULT
    { from: 608, to: 553 },   // RESULT → LOADED (next cycle)
    { from: 1802, to: 553 },  // SPINNING → LOADED (error recovery)
    { from: 608, to: 566 },   // RESULT → INIT (full reset)
]);
```

定义位置：offset 408050

### 3.2 中间件链执行（method 1524）

**offset 404500**：状态转换方法。使用中间件链模式：

```javascript
method_1524(targetState, enterCb, completeCb) {
    // 验证：当前状态可以转换到目标状态
    // 合并 exit/enter 中间件列表
    middlewares = merge(exitCbs, [enterCb], enterCbs);
    
    // 从后向前执行中间件链
    idx = middlewares.length - 1;
    next = function(err, data) {
        idx--;
        if (err) {
            finalize(err);
            completeCb(err);          // 错误：completeCb被调用
        } else if (idx < 0) {
            finalize(undefined, data);
            completeCb(undefined, data); // 完成：completeCb被调用
        } else {
            middlewares[idx](data, next); // 继续下一个中间件
        }
    };
    middlewares[idx](undefined, next);  // 开始执行
}
```

**所有分支都有正确的 completeCb 调用路径**（通过不透明条件解码确认）。

### 3.3 Subscribe 回调（消息总线中间件）

**offset 450817 和 451454**：两个 subscribe 回调注册为状态机中间件。

回调结构（伪代码）：
```javascript
function middleware(stateInfo, next) {
    var successCb = function(result) { return next(undefined, result); };
    var errorCb = function(err) { next(err); };
    
    var msg = {
        to: stateInfo.to,
        reply: function(handler) {
            var oldSuccess = successCb;
            successCb = function(result) {
                handler(result).then(oldSuccess, errorCb);  // Promise链
            };
        }
    };
    
    messagebus.emit(topic, msg, function() {
        successCb(stateInfo);  // emit完成后调用（可能已被reply包装）
    });
}
```

- Topic 1: H4x.j_O(15)
- Topic 2: H4x.j_O(1705)

**reply handler** 由 996b.js 或 engine.js 通过消息总线注册。handler 返回 Promise。

### 3.4 消息总线

- `D4()` 返回 `n7_[57]`（单例消息总线实例）
- 方法：emit = H4x.j_O(351)，subscribe = H4x.r4H(1382)
- 定义位置：offset 131535

### 3.5 Q0z (goTo) 完整逻辑

**offset 283868**：

```javascript
function Q0z(targetState, callback, completeCb) {
    if (n7_[544] && opaque_TRUE) {
        // 惩罚路径：n7_[544]=false → 永远不进入
    } else if (true /* patched from opaque condition */) {
        // 正常路径：
        n7_[124].method_1524(targetState, 
            function enterCb(state, next) {
                callback && callback(state, function(err, result) {
                    if (opaque_TRUE && n7_[544]) {
                        // n7_[544]=false → 不进入
                    } else {
                        next(err, result);  // 正常传递
                    }
                });
            },
            function exitCb() {
                if (opaque_TRUE && n7_[376]) {
                    // 执行暂存的completeCb（来自惩罚路径残留）
                } else if (opaque_TRUE) {
                    completeCb && completeCb();  // 正常完成
                }
            }
        );
    }
}
```

### 3.6 完整导出表

| 导出名 | 内部函数 | 作用 |
|--------|---------|------|
| initMaxWinService | h3j | 最大赢奖服务 |
| initTransactionStateMachine | g_i | 交易状态机初始化（注册subscribe中间件） |
| goTo | Q0z | 状态转换 |
| subscribeStateEvent | g3k | 订阅状态事件 |
| unsubscribeStateEvent | B9N | 取消订阅 |
| getState | U$2 | 获取当前状态 |
| getNextState | R_9 | 获取下一状态 |
| addTransition | B3t | 添加转换规则 |
| pause | L$B | 暂停 |
| resume | z8c | 恢复 |
| initOperationSocket | G$q | 操作socket初始化（offset 133484） |
| initWalletSocket | T2X | 钱包socket初始化（offset 275075） |
| checkOperationSocketConnectionStatus | o7M | socket连接检查 |
| enableSocketBalanceUpdate | m0D | socket余额更新 |

---

## 四、996b.js 初步分析

### 4.1 文件基本信息

- 文件大小：931,611 bytes
- 混淆体系：k2 查找表 + S2D.l9j(N)/S2D.z6Y(N) 解码器
- 不透明条件：S2D.S3O() 和 S2D.F1s()（均返回 k2[634233].P0tf9LU）
- 不透明数组：`l6t(21, 3, [21])` — 21×21循环引用数组，shift=3
- 共享状态数组：q$q（3193个引用）

### 4.2 HTTP 客户端

**使用 fetch API**（不是 XMLHttpRequest），wrapper 在 offset ~402500：

```javascript
// 伪代码
method_1984(url, params) {
    if (this[2546](url) /* URL check */) {
        return this[261](url)  // fetch(url)
            .then(function(response) {
                if (!response.ok) {
                    throw error("status " + response.status + response.statusText);
                }
                var contentType = response.headers.get("content-type");
                if (!contentType) {
                    throw error("no content type");
                }
                // route by content type: wasm, css, json, etc.
            });
    } else {
        // non-fetch path (local resources?)
    }
}
```

### 4.3 已找到的关键位置

| Offset | 内容 |
|--------|------|
| 1-57000 | k2 字符串解码器 + 不透明数组初始化 |
| 82460 | 版本/配置信息（mode等） |
| 352739 | 状态 553 (LOADED) 的 handler：`e4X.prototype[553]` |
| 402500-405500 | HTTP fetch 客户端和响应处理 |
| 549987 | g$E6jH 引用 |
| 656746 | 错误码映射（1012/1302/1307/1308/1309/1204等） |
| 675674 | 错误码 1302 处理逻辑 |
| 773162 | q$q[358][2628] 赋值 |

### 4.4 错误码映射表（offset 656746）

```javascript
switch(errorCode) {
    case 1012: return "...701...";
    case 1302: case 1307: case 1308: return "...1667...";
    case 1309: return "...618...";
    case 1204: case 1209: case 1400: case 1401: case 1402: case 1403: return "...3048...";
    case 1210: return "...2650...";
    case 3008: return "...2412...";
    case 3009: return "...3050...";
}
```

### 4.5 状态 553 Handler

**offset 352739**：
```javascript
e4X.prototype[S2D.l9j(553)] = function(V7x, L0V) {
    this[S2D.z6Y(2628)] && this[S2D.l9j(2628)](V7x, L0V);
}
```
属性 [2628] 是一个可选回调，如果设置了就调用。**条件调用 = 如果 [2628] 未设置，静默返回，不执行任何初始化。**

---

## 五、后端API完整状态（已审阅源码）

### 5.1 接口清单与序列化方式

| 接口 | Handler | 序列化方式 | 参数校验 |
|------|---------|-----------|---------|
| verifyOperatorPlayerSession | VerifyOperatorPlayerSession | `c.JSON(toStruct)` Go结构体序列化 | btt,vc,pf,l,gi,os,otk (全required) |
| verifySession | VerifySession | `c.JSON(toStruct)` Go结构体序列化 | btt,vc(可选),pf,l,gi,tk,otk |
| GameInfo/Get | GameInfo | `c.Data()` 原始JSON | eatk,btt,atk,pf (全required) |
| GameName/Get | GameName | `c.Data()` 原始JSON | lang,btt,atk,pf,gid (全required) |
| GameUI/Get | GameUI | `c.Data()` 原始JSON | **无参数校验** |
| GetByReferenceIdsResourceTypeIds | GetByReferenceIds | `c.Data()` 原始JSON | btt,atk,pf,gid,du,rtids,otk,lang |
| GetByResourcesTypeIds | GetByResourcesTypeIds | `c.Data()` 原始JSON | **参数校验已注释掉** |
| /what-is-my-ip | nginx | nginx直接返回 | 无 |

### 5.2 关键发现：c.JSON vs c.Data

- verify_operator 和 verify_session 使用 `utils.ToStruct[T](VerifyTest)` → `c.JSON()` 
- 这意味着 JSON 经过 Go 结构体 **反序列化→重新序列化**
- 其他接口使用 `c.Data()` 直接返回原始字符串
- 经分析，JSON round-trip **不会丢失数据**（所有字段在结构体中定义完整）

### 5.3 verify_session 已修复

```go
// ★★★ 使用 VerifyTest（来自 verify_operator_player_session.go）
toStruct := utils.ToStruct[VerifySessionData](VerifyTest)
```
两个 verify 接口返回**完全相同**的 VerifyTest 数据。

### 5.4 GetByReferenceIdsResourceTypeIds 分支逻辑

根据 `rtids` 参数值分支：
- rtids == "7" → 返回 Small_Icon 图片列表
- 其他 → 返回 Tournament_Bg 图片列表

---

## 六、当前部署版本：v22

| # | Offset | 原文 | 改为 | 作用 |
|---|--------|------|------|------|
| 1 | 156802 | `~6` | `!1` | n7_[544]赋值端#1 → 永远false |
| 2 | 156977 | `!0` | `!1` | n7_[544]赋值端#2 → 永远false |
| 3 | 284522 | opaque条件 | `!0` + 空格填充 | Q0z正常路径强制进入 |

文件大小：488,230 bytes

**v23（Promise try-catch）已回滚，无效。**

---

## 七、已排除的假设（扩展）

| # | 假设 | 排除原因 |
|---|------|----------|
| 1-11 | 见 v1 手册 | — |
| 12 | Promise链断裂（handler抛异常/返回非Promise） | v23 try-catch patch无效 |
| 13 | 5135.js不透明条件误判 | 完全解码数组后验证所有条件正确 |
| 14 | 5135.js状态机逻辑错误 | method_1524中间件链逻辑正确 |
| 15 | 996b.js HTTP响应处理被不透明条件gate | 解码后条件均不影响正常流程 |
| 16 | Go结构体JSON round-trip数据丢失 | 所有字段在结构体中完整定义 |
| 17 | HTTP响应顺序竞态 | 生产环境延迟更大但从不卡死 |

---

## 八、下一步分析方向

### 8.1 核心思路（用户提出）

> 偶发是重点。类似之前的资源加载环境检测，是某一部分校验失败就会进入惩罚流程，而不是单一接口有问题。

### 8.2 具体待做

1. **在 996b.js 中找到接口调用点** — 找到 fetch 被调用的地方，确定哪些函数发起了哪些API请求
2. **追踪接口返回后的校验逻辑** — 找到 JSON 响应中 `dt`/`err` 字段的处理点，看是否有交叉校验
3. **找 996b.js 中的惩罚标记** — 类似 5135.js 的 `n7_[544]`，996b.js 中 q$q 数组可能有类似的惩罚flag
4. **重点关注**：校验可能不是检查单一接口，而是**多个接口返回值的交叉比较**（如 verify 的 tk 与 game_info 的某字段匹配检查），静态伪造数据可能在特定条件下触发校验失败

### 8.3 关键线索

- 生产环境 100% 正常 → 问题在**本地伪造的静态响应数据**
- 偶发 5% → 不是数据格式问题（否则 100% 失败），是**某个条件在大多数情况下碰巧通过**
- 类似环境检测惩罚 → 996b.js 可能有类似 n7_[544] 的标记，在某些校验失败时设为 true
- 该标记可能在初始化流程中影响 553→365 状态转换的完成

### 8.4 996b.js 分析切入点

| 切入点 | Offset | 说明 |
|--------|--------|------|
| HTTP fetch wrapper | 402500 | 从这里追踪 response → JSON parse → dt/err 分离 |
| 状态553 handler | 352739 | 从这里追踪 LOADED 状态的处理流程 |
| 错误码1302处理 | 675674 | 从这里找到 err 字段检查逻辑 |
| q$q 数组 | 全局 | 搜索类似 `q$q[N]=true/false` 的惩罚标记赋值模式 |
| g$N6bVaJ | 404639 | HTTP客户端对象，追踪请求发起 |

---

## 九、不透明数组解码工具

### 9.1 通用解码函数

```javascript
function genOpaqueArray(size, shift, boundaries) {
    var M = [];
    for (var i = 0; i < size; i++) M[i] = [];
    for (var row = 0; row < size; row++) {
        var P = size - 1;
        var bIdx = 0, cur = 0;
        var prev = cur;
        cur = boundaries[bIdx];
        var span = cur - prev;
        bIdx++;
        while (P >= 0) {
            if (P >= cur) {
                prev = cur;
                if (bIdx < boundaries.length) {
                    cur = boundaries[bIdx];
                    span = cur - prev;
                    bIdx++;
                } else break;
            } else {
                var target = prev + (P - prev + shift * row) % span;
                M[row][target] = M[P];
                P--;
            }
        }
    }
    return M;
}
```

### 9.2 已知参数

| 文件 | 参数 | 数组大小 |
|------|------|---------|
| 5135.js (H4x) | `genOpaqueArray(18, 6, [18])` | 18×18 |
| 996b.js (S2D) | `genOpaqueArray(21, 3, [21])` | 21×21 |

### 9.3 评估条件的方法

```javascript
// 条件格式: arr[a][b][c] == arr[d][e][f]
// 实际比较: arr[a][b] 引用的行的 [c] 位置 === arr[d][e] 引用的行的 [f] 位置
// 这是对象引用比较，结果取决于两边最终指向的是否是同一个行数组

var arr = genOpaqueArray(params...);
console.log(arr[a][b][c] === arr[d][e][f]);
```

---

## 十、需要的文件清单

下次继续时需要以下文件（按优先级）：

| 文件 | 作用 | 优先级 |
|------|------|--------|
| 996b5422dd.7934b.js | Shell主JS，包含init逻辑和接口调用 | ★★★ |
| 51353bae0e.98a44.js | 状态机（当前v22） | ★★★ |
| index_acdaa.js | 引擎bundle | ★★ |
| 7个Go handler源码 | 接口返回数据参考 | ★★ |
| debug_complete_handbook_v20.md | 全部patch历史 | ★ |
| 本文档 (v2) | 最新分析进展 | ★★★ |
