# Spin按钮偶发卡死 — 根因分析与修复 (v24)

## 一、问题描述

PG Soft Bali Vacation (gid:94) 本地部署，使用伪造静态API响应。

**现象**：游戏加载进入后，spin按钮偶发不可用（~5%），发生在**点击spin之前**。

**已排除**：
- 后端API JSON round-trip无数据丢失
- engine.js SpinButtonController状态机逻辑正确
- 5135.js Q0z状态机逻辑正确（v20/v22 patch有效）
- 996b.js资源完整性验证Hook仅启动阶段运行，不影响运行时
- Promise链断裂假设无效（v23已回滚）

---

## 二、根因链

### 2.1 FSM Transition 中间件阻塞机制

5135.js中的游戏状态机 `n7_[124]` 管理状态循环：

```
566(INIT) → 553(LOADED) → 365(PLAYING) → 1802(RESULT) → 608(ANIMATE) → 553(LOADED)
```

FSM的transition方法 `[1524]` 通过**中间件链**执行。两个全局中间件在每次transition时向消息总线派发事件 `"15"` 和 `"1705"`，等待所有handler完成后才调用 `next()` 推进链。

handler可以调用 `eventData[110]()` **暂停**transition链，必须后续调用 `eventData[1870]()` **恢复**。如果 `[1870]` 从未被调用，FSM永久锁定（`this[1025]`不清除），所有后续transition抛异常。

### 2.2 关键handler — offset 263180

**唯一**响应 target=553 的 event `"15"` handler位于 offset 263180。该handler在**每次进入553(LOADED)状态时触发**，包括：
- 初始加载 `566→553`（进游戏时）
- spin完成 `608→553` 或 `1802→553`（每轮spin后）

handler逻辑（伪代码）：

```javascript
// offset 263180 — event "15" handler
if (betData[677] === 1 && target === "553") {
    eventData[110]();  // 暂停transition

    // 两条恢复路径:
    if (antiTamperCheckA || (antiTamperCheckB === n7_[220] || n7_[107])) {
        y2y(config);          // 路径A: 弹对话框，必须用户点击按钮才恢复
    } else {
        finalCallback(false); // 路径B: 直接调用[1870]恢复FSM
    }
}
```

### 2.3 Anti-tamper决定路径选择

路径选择由**两个anti-tamper校验**决定（offset 264090）：

```javascript
H4x.U11()[5][16][15] != H4x.k09()[0][10][ p5.d2(p5.C3()[405](), 249, 264120, 405) ]
||
( p5.d2(p5.C3()[421](), 9, 264177, 421) === n7_[220] || n7_[107] )
```

- **Check A**: 不透明数组比较，索引由 `p5.d2(C3[405]...)` 计算
- **Check B**: `p5.d2(C3[421]...)` 结果与 `n7_[220]`（初始值=0）比较

`p5.C3()` 是一个 **Proxy对象**，其行为取决于各region的访问顺序：
- **首次访问** `C3[N]` → 返回构造函数 `g8[4]`
- **再次访问** `C3[N]` → 返回 `F8`（返回null的函数）

因此 `p5.d2(C3[N](), ...)` 的返回值**取决于该region是否已被其他anti-tamper调用先访问过**。5135.js中共有**307处** `p5.d2`/`p5.j8` 调用，它们的执行顺序因异步事件处理的微妙timing差异而变化。

### 2.4 偶发机制

当offset 264090处的检查恰好遇到特定的C3缓存状态时：
1. `p5.d2` 返回异常值 → Check A 为 TRUE → 条件整体为 TRUE
2. 走**路径A** → `y2y()` 弹出对话框
3. 对话框在本地部署环境中**不可见或不可交互**（CSS被patch、本地化缺失等）
4. `finalCallback` 永远不被调用 → `eventData[1870]()` 不执行 → **FSM永久锁死**
5. spin按钮永远不enable

~5%的概率对应307处anti-tamper调用的特定执行序列导致C3[405]/C3[421]产生异常返回值的比例。

---

## 三、修复方案

### 3.1 Patch点

| # | 文件 | Offset | 原始内容 | 替换内容 | 说明 |
|---|------|--------|---------|---------|------|
| **v24-1** | 5135.js | 264232 | `?y2y(S_3[1]):` | `?S_3[8]( !1):` | 强制绕过对话框 |

**效果**：无论anti-tamper条件为true或false，ternary两侧都执行 `S_3[8](!1)` = `finalCallback(false)` = 调用 `[1870]` 恢复FSM。

**文件大小**：替换前后均为13字符，文件488,230 bytes不变。

### 3.2 与已有Patch兼容性

| Patch | Offset | 内容 | 状态 |
|-------|--------|------|------|
| v20 n7_[544]#1 | 156802 | `~6` → `!1` | 保留 |
| v20 n7_[544]#2 | 156977 | `!0` → `!1` | 保留 |
| v22 Q0z强制 | 284522 | opaque → `!0` + 空格 | 保留（冗余但无害） |
| **v24-1 (新)** | 264232 | `?y2y(S_3[1]):` → `?S_3[8]( !1):` | **新增** |

### 3.3 v22 Patch冗余说明

v22在offset 284522将Q0z的else-if条件patch为 `!0`。经纠正的不透明数组映射验证，原始opaque条件本身就评估为TRUE（`!(arr[9]==arr[5])` = `!(FALSE)` = TRUE），所以v22 patch是冗余的。保留它不影响功能。

---

## 四、附带发现：不透明数组映射纠错

### 4.1 v2手册映射错误

5135.js的不透明数组 `A4z(18, 6, [18])` 生成18×18循环引用数组。

v2手册中行1和行2的shift方向**写反了**：

| 行 (i%3) | v2手册（错误） | 实际（正确） |
|----------|--------------|------------|
| 0 | identity (shift 0) | identity (shift 0) |
| 1 | shift +6 | **shift +12** |
| 2 | shift +12 | **shift +6** |

### 4.2 正确公式

```
arr[i][j] = arr[(j + shift) % 18]

其中 shift:
  i%3=0 → 0    (identity)
  i%3=1 → 12   (即 -6 mod 18)
  i%3=2 → 6    (即 -12 mod 18)
```

源自A4z算法: `M24[t_v][S3g] = M24[P27]`，其中 `S3g = (P27 + 6*t_v) % 18`，反推得 `arr[i][j]` 对应 `M24[(j - 6*i) % 18]`。

### 4.3 验证

| 条件（来自v2手册） | 手册结论 | 正确映射计算 | 匹配 |
|-------------------|---------|-------------|------|
| `arr[8][9][9] != arr[7][11][17]` | TRUE | arr[9]!=arr[5] → TRUE | ✓ |
| `arr[5][7][15] == arr[8][9][5]` | FALSE | arr[9]==arr[5] → FALSE | ✓ |
| FSM [1524] guard | FALSE (正常) | arr[9]!=arr[9] → FALSE | ✓ |
| Q0z else-if (v22 patch位) | TRUE | !(arr[9]==arr[5]) = TRUE | ✓ (v22冗余) |

---

## 五、spin完成后的卡死风险

同一个handler（offset 263180）在**每次进入553状态**时都会触发。因此spin完成后的 `608→553` 或 `1802→553` transition也面临相同的anti-tamper对话框阻塞风险。v24 patch同样覆盖了这些场景，因为patch点在handler内部，对所有进入553的transition生效。

---

## 六、技术细节

### 6.1 p5.C3 Proxy机制

```javascript
p5[283597] = (function() {
    var cache = {};
    var constructorRef = (function(x) { return x.constructor; })();
    function F8() { return null; }
    
    return {
        a1DPYLb: new Proxy({}, {
            get(target, prop) {
                if (cache[prop]) return cache[prop]; // 已缓存→返回F8
                cache[prop] = F8;                     // 标记已访问
                return constructorRef;                // 首次→返回构造函数
            }
        })
    };
})();
```

首次vs再次访问返回不同值 → p5.d2计算结果不确定 → 偶发触发错误路径。

### 6.2 FSM [1524] 锁机制

```javascript
W4n.prototype[1524] = function(target, enterCb, completeCb) {
    if (this[1025]) throw "transition in progress"; // 锁检查
    this[1025] = target;                             // 加锁
    // ...执行中间件链...
    // 链完成后调用 [858] 清锁:
    // this[1025] = void 0;
    // this[451] = target; // 更新当前状态
};
```

如果中间件链挂起 → `[858]`不执行 → `[1025]`不清 → FSM永久锁死。

### 6.3 y2y对话框

`y2y()` 显示包含action按钮的对话框（可能是demo模式/session提示）。`finalCallback`（调用`[1870]`恢复FSM）绑定在按钮的click handler上。本地部署环境中该对话框不可交互 → FSM无法恢复。

---

## 七、v25补充修复 — C3 Proxy中和

### 7.1 v24测试结果

v24单独patch（offset 264232绕过y2y对话框）**未解决问题**，偶发卡死仍在。

说明问题不仅限于y2y对话框路径。anti-tamper系统的Proxy缓存不确定性影响范围远大于单个条件分支——它影响全部307处p5.d2/p5.j8调用，任何一处计算出错误值都可能导致：
- 错误的数组索引 → TypeError (undefined is not a function)
- 错误的方法名 → 调用错误方法或undefined
- 错误的条件值 → 进入惩罚/异常路径

这些异常如果发生在FSM middleware chain执行期间，throw会传播到[1524]外部，而[1025]已设置但未清除 → FSM永久锁死。

### 7.2 根因深化：Proxy缓存不确定性

`p5.C3()` 的Proxy get handler行为：

```javascript
get(target, prop) {
    if (cache[prop]) return cache[prop]; // 已缓存 → 返回F8 → F8()=null
    cache[prop] = F8;                     // 标记
    return constructorRef;                // 首次 → 返回Function → Function()=空函数
}
```

- **首次**访问C3[N]：返回Function构造函数 → C3[N]() = Function() → p5.d2得到正确结果
- **再次**访问C3[N]：返回F8 → C3[N]() = null → p5.d2得到**错误结果**

307处调用的执行顺序取决于异步事件处理timing，每次页面加载可能不同 → 同一region在关键检查点可能是首次或再次访问 → 结果不确定。

### 7.3 v25修复

| # | Offset | 原始 | 替换 | 说明 |
|---|--------|------|------|------|
| v25 | 8782 | `?1:5` | `?5:5` | Proxy get handler永远走case 5 |

**效果**：Proxy永远返回首次访问值（Function构造函数），跳过缓存。所有307处anti-tamper调用获得一致的输入 → p5.d2/p5.j8计算结果正确且确定。

**文件大小**：1字符替换，488,230 bytes不变。

### 7.4 完整Patch列表 (v25)

| # | 版本 | Offset | 原始 | 替换 | 说明 |
|---|------|--------|------|------|------|
| 1 | v20 | 156802 | `~6` | `!1` | n7_[544]赋值#1 → false |
| 2 | v20 | 156977 | `!0` | `!1` | n7_[544]赋值#2 → false |
| 3 | v22 | 284522 | opaque | `!0`+空格 | Q0z正常路径（冗余但无害） |
| 4 | v24 | 264232 | `?y2y(S_3[1]):` | `?S_3[8]( !1):` | 绕过对话框阻塞 |
| 5 | **v25** | **8782** | `?1:5` | `?5:5` | **C3 Proxy缓存中和** |
