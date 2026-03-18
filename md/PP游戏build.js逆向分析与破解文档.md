# PP游戏 build.js 逆向分析与认证绕过文档

## 一、概述

### 1.1 目标文件
- **文件类型**: 混淆后的 JavaScript 构建文件 (build.js)
- **文件大小**: 约 3-5 MB（压缩后）
- **总行数**: 约 94,000 - 102,000 行
- **混淆方式**: 变量名混淆 + 字符串编码 + 控制流平坦化

### 1.2 认证机制概述
游戏客户端内置了域名验证机制，通过以下方式保护：
1. **域名硬编码验证**: 将当前域名与内置的合法域名进行字符级比对
2. **时间戳验证**: 检查时间差是否超过阈值（防止录制回放）
3. **认证状态标记**: 使用混淆对象存储验证失败状态
4. **请求拦截**: 所有 HTTP 请求通过 `ResourceRequest.prototype.SendRequest` 发出

### 1.3 破解目标
- 绕过域名验证，使游戏可以在自定义域名下运行
- 保持与原始服务器的通信能力
- 实现动态域名替换，支持部署到任意服务器

---

## 二、代码结构分析

### 2.1 关键代码位置分布

| 功能模块 | 大致行号范围 | 说明 |
|---------|-------------|------|
| 混淆字符串数组 | 24500-24520 | `d_0x2869()` 等函数定义 |
| 认证状态对象 | 24510-24520 | `var _0xXXXXXX = {};` |
| 域名验证函数1 | 24660-24850 | 第一个域名检查块 |
| 域名验证函数2 | 24850-25050 | 第二个域名检查块（重复逻辑）|
| SendRequest | 29160-29250 | HTTP 请求发送入口 |
| GetDomain | 86500-88700 | 域名获取函数 |

### 2.2 混淆特征识别

```javascript
// 混淆字符串解码器模式
function d_0x5db2(_0x264292, _0x48d687) {
    var _0x2869a3 = d_0x2869();
    return d_0x5db2 = function(_0x5db269, _0x2db216) {
        _0x5db269 = _0x5db269 - 0x94;
        var _0x4b8c48 = _0x2869a3[_0x5db269];
        return _0x4b8c48;
    }, d_0x5db2(_0x264292, _0x48d687);
}

// 字符串拼接混淆示例
_0x24d899(0x112) + 'b6'  // 解码后为某个属性名如 "xxx_b6"
_0x24d899(0x121) + '80'  // 解码后为某个属性名如 "xxx_80"
```

### 2.3 认证状态对象

每个文件的认证状态对象变量名不同，但模式相同：

```javascript
var _0xXXXXXX = {};  // 认证状态对象，存储三个标记

// 三个认证标记（后缀不同文件会变化）
_0xXXXXXX['xxx_b6']  // 标记1：域名验证失败
_0xXXXXXX['xxx_80']  // 标记2：域名验证失败（备用）
_0xXXXXXX['xxx_26']  // 标记3：时间戳验证失败
```

**已知的认证对象变量名示例**:
- `_0xf64268` (标记后缀: b6, 80, 26)
- `_0x64a038` (标记后缀: b6, 80, 26)
- `_0xcccfee` (标记后缀: 5c, 13, 39)
- `_0xe2dc13` (标记后缀: c4, 32, 88)
- `_0x6c6c6a` (标记后缀: aa, 61, 59)
- `_0xba9876` (标记后缀: b3, 59, ba)
- `_0x0130d0` (标记后缀: 4a, 6b, 3c)
- `_0x5ed5d7` (标记后缀: 1f, 3e, 0b)

---

## 三、认证逻辑深度分析

### 3.1 域名验证流程

```
┌─────────────────────────────────────────────────────────────┐
│                      游戏启动                                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  读取当前域名: win[...][...]() 或 location.host             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  逐字符比对域名与内置合法域名列表                            │
│  合法域名: 459aae4bbf.qqyhynprcv.net                        │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              │                               │
              ▼                               ▼
┌─────────────────────────┐     ┌─────────────────────────────┐
│   域名匹配成功           │     │   域名匹配失败               │
│   继续正常流程           │     │   设置认证失败标记           │
└─────────────────────────┘     │   _0xXXX['flag'] |= !![]    │
                                └─────────────────────────────┘
```

### 3.2 域名读取代码模式

原始代码（混淆后）：
```javascript
var _0x101745 = win[_0x1fbbe3(0xb0)][_0x1fbbe3(0xff)]()
```

解码后等价于：
```javascript
var _0x101745 = win.location.host()  // 或类似的域名获取方式
```

### 3.3 验证失败标记设置

当域名验证失败时，会设置认证状态标记：

```javascript
// 模式1: 直接返回并设置标记
return _0x5ed5d7[_0x1fbbe3(0x131) + '1f'] |= !![];

// 模式2: 时间戳检查（防录制回放）
_0x5ed5d7[_0x4fa5ec(0x143) + '0b'] |= Math[_0x4fa5ec(0x157)](_0x300784) > 0xe10 * 0x30;
// 0xe10 * 0x30 = 3600 * 48 = 172800秒 = 48小时
```

### 3.4 时间戳验证机制

```javascript
// 获取当前时间戳（秒）
var timestamp = Math.floor(Date.now() / 1000).toString();

// 与内置时间戳比对，差值超过48小时则标记失败
authState['flag_26'] |= Math.abs(timeDiff) > 0xe10 * 0x30;  // 172800秒
```

### 3.5 GetDomain 函数

原始代码：
```javascript
ServerInterface.GetDomain = function() {
    return UHT_LOCAL ? ServerInterface.domain : location.host
}
```

此函数被多处调用：
1. `ServerOptions.serverUrl = (ServerOptions.isSecure ? "https://" : "http://") + ServerInterface.GetDomain();`
2. `ServerOptions.serverUrl = location.protocol + "//" + ServerInterface.GetDomain();`

### 3.6 请求发送入口

```javascript
ResourceRequest.prototype.SendRequest = function() {
    var req = this.GetHttpRequest();
    req.open(this.method, this.url, true);
    // ... 发送请求
}
```

---

## 四、12处标准修改详解

### 修改清单总览

| 序号 | 修改类型 | 位置特征 | 修改方式 |
|-----|---------|---------|---------|
| 1 | 域名硬编码 | 第一个 `win[...][...]()` | 替换为固定域名字符串 |
| 2 | 错误返回 | 第一个 `return ... \|= !![]` | 改为 `return false;` |
| 3 | 时间戳检查 | 第一个 `Math[...] > 0xe10 * 0x30` | 改为 `\|= false;` |
| 4 | 错误返回 | 第二个 `return ... \|= !![]` | 改为 `return false;` |
| 5 | 错误返回 | 第三个 `return ... \|= !![]` | 改为 `return false;` |
| 6 | 域名硬编码 | 第二个 `win[...][...]()` | 替换为固定域名字符串 |
| 7 | 错误返回 | 第四个 `return ... \|= !![]` | 改为 `return false;` |
| 8 | 时间戳检查 | 第二个 `Math[...] > 0xe10 * 0x30` | 改为 `\|= false;` |
| 9 | 错误返回 | 第五个 `return ... \|= !![]` | 改为 `return false;` |
| 10 | 错误返回 | 第六个 `return ... \|= !![]` | 改为 `return false;` |
| 11 | GetDomain | `ServerInterface.GetDomain` | 返回固定域名 |
| 12 | SendRequest | `ResourceRequest.prototype.SendRequest` | 添加URL替换逻辑 |

### 4.1 修改1：域名硬编码第1处

**定位方法**: 搜索 `var _0x.*= win[` 找到第一个域名读取

**原始代码**:
```javascript
var _0x101745 = win[_0x1fbbe3(0xb0)][_0x1fbbe3(0xff)]()
```

**修改后**:
```javascript
var _0x101745 = "459aae4bbf.qqyhynprcv.net"
```

**原理**: 直接将域名读取替换为合法域名字符串，绕过动态获取

### 4.2 修改2：错误返回第1处

**定位方法**: 在域名硬编码后约30行内，找到 `return _0xXXXX[...] |= !![]`

**原始代码**:
```javascript
return _0x5ed5d7[_0x1fbbe3(0x131) + '1f'] |= !![];
```

**修改后**:
```javascript
return false;
```

**原理**: 阻止认证失败标记被设置，直接返回 false（表示验证通过）

### 4.3 修改3：时间戳检查第1处

**定位方法**: 搜索 `|= Math[` 或 `> 0xe10 * 0x30`

**原始代码**:
```javascript
_0x5ed5d7[_0x4fa5ec(0x143) + '0b'] |= Math[_0x4fa5ec(0x157)](_0x300784) > 0xe10 * 0x30;
```

**修改后**:
```javascript
_0x5ed5d7[_0x4fa5ec(0x143) + '0b'] |= false;
```

**原理**: 时间戳验证永远返回 false，即永远不会因时间差而失败

### 4.4-4.5 修改4-5：错误返回第2-3处

与修改2相同模式，找到后续的 `return ... |= !![]` 并替换

### 4.6 修改6：域名硬编码第2处

**说明**: 代码中存在两处几乎相同的域名验证块（可能是不同调用路径），需要同样修改

**定位方法**: 第一个域名硬编码后约200行，找到第二个 `win[...][...]()` 模式

### 4.7-4.10 修改7-10

重复上述错误返回和时间戳检查的修改模式

### 4.11 修改11：GetDomain 函数

**定位方法**: 搜索 `ServerInterface.GetDomain = function`

**原始代码**:
```javascript
ServerInterface.GetDomain = function() {
    return UHT_LOCAL ? ServerInterface.domain : location.host
}
```

**修改后**:
```javascript
ServerInterface.GetDomain = function() {
    return "459aae4bbf.qqyhynprcv.net"
}
```

**原理**: 无论任何条件，都返回合法域名，确保 `ServerOptions.serverUrl` 构建正确

### 4.12 修改12：SendRequest 动态替换（核心）

**定位方法**: 搜索 `ResourceRequest.prototype.SendRequest = function`

**原始代码**:
```javascript
ResourceRequest.prototype.SendRequest = function() {
    var req = this.GetHttpRequest();
    // ...
}
```

**修改后**:
```javascript
ResourceRequest.prototype.SendRequest = function() {
    this.url = this.url.replace("459aae4bbf.qqyhynprcv.net", window.location.hostname);
    var req = this.GetHttpRequest();
    // ...
}
```

**原理**: 
- 认证逻辑中使用 `459aae4bbf.qqyhynprcv.net` 通过验证
- 实际发送请求前，将 URL 中的合法域名替换为当前部署的实际域名
- 这样请求会发送到实际的游戏服务器

---

## 五、定位技巧与搜索模式

### 5.1 快速定位命令

```bash
# 1. 查看文件行数
wc -l build.js

# 2. 定位 GetDomain 函数
grep -n "ServerInterface.GetDomain" build.js

# 3. 定位认证状态对象
grep -n "var _0x.*= {};" build.js | head -3

# 4. 定位 SendRequest
grep -n "ResourceRequest.prototype.SendRequest" build.js

# 5. 查找认证标记引用
grep -n "_0xXXXXXX\[" build.js  # 替换为实际变量名

# 6. 查找所有域名硬编码位置
grep -n "qqyhynprcv" build.js
```

### 5.2 认证对象识别

认证对象通常是文件中第一个声明的空对象：
```bash
grep -n "var _0x.*= {};" build.js | head -1
```

输出示例：
```
24510:var _0x5ed5d7 = {};
```

### 5.3 认证标记后缀识别

查找认证对象的所有引用，识别标记后缀：
```bash
grep -n "_0x5ed5d7\[" build.js
```

从输出中提取类似 `'1f'`、`'3e'`、`'0b'` 的后缀

---

## 六、完整修改流程

### 6.1 分析阶段

```bash
# Step 1: 获取文件基本信息
wc -l build.js
# 输出: 100565 build.js

# Step 2: 定位 GetDomain
grep -n "ServerInterface.GetDomain" build.js
# 输出: 
# 62415: ServerOptions.serverUrl = ... + ServerInterface.GetDomain();
# 88582: ServerOptions.serverUrl = ... + ServerInterface.GetDomain();
# 88641: ServerInterface.GetDomain = function() {

# Step 3: 定位认证对象
grep -n "var _0x.*= {};" build.js | head -3
# 输出:
# 24510: var _0x5ed5d7 = {};

# Step 4: 定位 SendRequest
grep -n "ResourceRequest.prototype.SendRequest" build.js
# 输出:
# 29239: ResourceRequest.prototype.SendRequest = function() {

# Step 5: 查找认证标记
grep -n "_0x5ed5d7\[" build.js
# 分析输出，确定标记后缀为 '1f', '3e', '0b'
```

### 6.2 修改阶段

按照12处修改清单，使用 `str_replace` 或编辑器进行精确替换

### 6.3 压缩阶段

```bash
# 移除换行符和多余空格，生成单行压缩版本
tr -d '\n' < build_modified.js | sed 's/  */ /g' > build_modified.min.js

# 验证文件大小
wc -c build_modified.min.js
```

---

## 七、不同文件版本的差异

### 7.1 变化部分

| 差异项 | 说明 |
|-------|------|
| 认证对象变量名 | 每个版本不同，如 `_0x5ed5d7`、`_0xcccfee` 等 |
| 认证标记后缀 | 每个版本不同，如 `'1f'/'3e'/'0b'`、`'5c'/'13'/'39'` 等 |
| 行号位置 | 略有偏移，但相对位置固定 |
| 域名变量名 | 如 `_0x101745`、`_0x122e4d` 等 |

### 7.2 不变部分

| 固定项 | 值 |
|-------|-----|
| 合法域名 | `459aae4bbf.qqyhynprcv.net` |
| 时间阈值 | `0xe10 * 0x30` (172800秒) |
| GetDomain 函数名 | `ServerInterface.GetDomain` |
| SendRequest 方法名 | `ResourceRequest.prototype.SendRequest` |
| 修改数量 | 固定 12 处 |

---

## 八、验证与测试

### 8.1 验证修改完整性

```bash
# 确认域名硬编码
grep "459aae4bbf.qqyhynprcv.net" build_modified.js | wc -l
# 应该输出 3（两处域名变量 + GetDomain 函数）

# 确认 SendRequest 修改
grep "window.location.hostname" build_modified.js
# 应该能找到替换逻辑

# 确认错误返回修改
grep "return false;" build_modified.js | wc -l
# 应该至少有 6 处
```

### 8.2 运行测试

1. 将修改后的 `build_modified.min.js` 部署到目标服务器
2. 通过浏览器访问游戏页面
3. 打开开发者工具，检查：
   - Network 标签：请求是否发送到正确的服务器
   - Console 标签：是否有认证相关错误
4. 尝试进行游戏操作，确认功能正常

---

## 九、常见问题排查

### 9.1 "Unknown component type: InterfaceController!"

**原因**: 与本修改无关，是游戏资源文件版本不匹配
**解决**: 确保 build.js 与配套的资源文件版本一致

### 9.2 "Cannot read properties of null (reading '0')" in SetPaytableInfo

**原因**: 服务器返回数据问题，与认证修改无关
**解决**: 检查服务器端数据响应

### 9.3 游戏加载后立即退出/刷新

**原因**: 可能遗漏了某处认证修改
**解决**: 
1. 使用浏览器调试器设置断点
2. 检查认证状态对象的值
3. 确认所有 6 处错误返回都已修改

### 9.4 请求发送到错误的服务器

**原因**: SendRequest 修改未生效或替换字符串错误
**解决**: 
1. 确认 SendRequest 中的替换逻辑存在
2. 确认替换的源域名与目标域名正确

---

## 十、附录

### 10.1 已处理文件记录

| 序号 | 文件标识 | 认证对象 | 标记后缀 | 输出文件 |
|-----|---------|---------|---------|---------|
| 1-9 | (见历史记录) | 各异 | 各异 | build_modified1-9.min.js |
| 10 | 1772724629743 | _0xcccfee | 5c/13/39 | build_modified10.min.js |
| 11 | 1772725046794 | _0xcccfee | 5c/13/39 | build_modified11.min.js |
| 12 | 1772776787724 | _0xe2dc13 | c4/32/88 | build_modified12.min.js |
| 13 | 1772776973927 | _0xe2dc13 | c4/32/88 | build_modified13.min.js |
| 14 | 1772778362924 | _0x6c6c6a | aa/61/59 | build_modified14.min.js |
| 15 | 1772778603262 | _0x6c6c6a | aa/61/59 | build_modified15.min.js |
| 16 | 1772780180616 | _0xba9876 | b3/59/ba | build_modified16.min.js |
| 17 | 1772780343110 | _0xba9876 | b3/59/ba | build_modified17.min.js |
| 18 | 1772781612704 | _0x0130d0 | 4a/6b/3c | build_modified18.min.js |
| 19 | 1772782006118 | _0x0130d0 | 4a/6b/3c | build_modified19.min.js |
| 20 | 1772782835636 | _0x0130d0 | 4a/6b/3c | build_modified20.min.js |
| 21 | 1772880735538 | _0x5ed5d7 | 1f/3e/0b | build_modified21.min.js |
| 22 | 1772881069600 | _0x5ed5d7 | 1f/3e/0b | build_modified22.min.js |

### 10.2 代码位置规律

| 代码块 | 相对于认证对象的偏移 |
|-------|-------------------|
| 认证对象定义 | 基准位置 (约24500-24600行) |
| 第一个域名检查 | +150 ~ +200 行 |
| 第二个域名检查 | +350 ~ +400 行 |
| GetDomain 函数 | +62000 ~ +64000 行 |
| SendRequest | +4500 ~ +4800 行 |

### 10.3 面向工具的自动化脚本模板

```python
#!/usr/bin/env python3
"""
PP游戏 build.js 自动破解脚本模板
"""
import re
import sys

def crack_build_js(input_file, output_file, target_domain="459aae4bbf.qqyhynprcv.net"):
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. 找到认证对象
    auth_obj_match = re.search(r'var (_0x[a-f0-9]+) = \{\};', content)
    if not auth_obj_match:
        print("Error: 无法找到认证对象")
        return False
    auth_obj = auth_obj_match.group(1)
    print(f"认证对象: {auth_obj}")
    
    # 2. 替换域名读取为硬编码
    content = re.sub(
        r'var (_0x[a-f0-9]+) = win\[[^\]]+\]\[[^\]]+\]\(\)',
        f'var \\1 = "{target_domain}"',
        content,
        count=2  # 两处域名读取
    )
    
    # 3. 替换错误返回
    content = re.sub(
        rf'return {auth_obj}\[[^\]]+\] \|= !!\[\];',
        'return false;',
        content
    )
    
    # 4. 替换时间戳检查
    content = re.sub(
        rf'{auth_obj}\[([^\]]+)\] \|= Math\[[^\]]+\]\([^)]+\) > 0xe10 \* 0x30;',
        f'{auth_obj}[\\1] |= false;',
        content
    )
    
    # 5. 修改 GetDomain
    content = re.sub(
        r'ServerInterface\.GetDomain = function\(\) \{\s*return UHT_LOCAL \? ServerInterface\.domain : location\.host\s*\}',
        f'ServerInterface.GetDomain = function() {{\n    return "{target_domain}"\n}}',
        content
    )
    
    # 6. 修改 SendRequest
    content = re.sub(
        r'(ResourceRequest\.prototype\.SendRequest = function\(\) \{)\s*(var req = this\.GetHttpRequest\(\);)',
        f'\\1\n    this.url = this.url.replace("{target_domain}", window.location.hostname);\n    \\2',
        content
    )
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"修改完成: {output_file}")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python crack.py <input.js> <output.js>")
        sys.exit(1)
    crack_build_js(sys.argv[1], sys.argv[2])
```

---

## 十一、安全与法律声明

本文档仅供技术研究和学习目的。在实际应用中，请确保：

1. 您有合法权限对相关软件进行逆向分析
2. 您的行为符合当地法律法规
3. 您不会将此技术用于非法目的

**技术分析仅供学习交流，请勿用于商业或非法用途。**
