# IPTables 当前规则

> 数据来源：`iptables -L -n` + `ip6tables -L -n`
> 提取时间：2026-06-21

---

## IPv4 (iptables)

### INPUT Chain (policy: ACCEPT)

| 规则 | 协议 | 源 | 目标 | 说明 |
|------|------|-----|------|------|
| DROP | * | 87.251.64.145 | 0.0.0.0/0 | 封禁 IP |
| DROP | * | 81.90.28.163 | 0.0.0.0/0 | 封禁 IP |
| DROP | * | 45.148.10.183 | 0.0.0.0/0 | 封禁 IP |
| DROP | * | 47.236.245.255 | 0.0.0.0/0 | 封禁 IP |
| DROP | * | 185.204.171.193 | 0.0.0.0/0 | 封禁 IP |
| DROP | * | 61.75.245.101 | 0.0.0.0/0 | 封禁 IP |
| SSH rate-limit | TCP | 0.0.0.0/0 | dpt:22 NEW | `recent` 模块：60s 内 4 次连接 → 封禁 |
| DROP | * | 59.153.245.232 | 0.0.0.0/0 | 封禁 IP |
| DROP | * | 87.251.64.144 | 0.0.0.0/0 | 封禁 IP |

### FORWARD Chain (policy: DROP)

| 规则 | 说明 |
|------|------|
| DOCKER-USER | Docker 用户链 |
| DOCKER-FORWARD | Docker 转发链 |

### OUTPUT Chain (policy: ACCEPT)

无额外规则。

### Docker 相关链

| 链 | 规则 |
|----|------|
| **DOCKER** | DROP all (默认拒绝) |
| **DOCKER-BRIDGE** | DOCKER |
| **DOCKER-CT** | ACCEPT RELATED,ESTABLISHED |
| **DOCKER-FORWARD** | DOCKER-CT → DOCKER-INTERNAL → DOCKER-BRIDGE → ACCEPT all |
| **DOCKER-INTERNAL** | (空) |
| **DOCKER-USER** | (空) |

---

## IPv6 (ip6tables)

### INPUT Chain (policy: ACCEPT)

无规则。

### FORWARD Chain (policy: ACCEPT)

| 规则 | 说明 |
|------|------|
| DOCKER-USER | Docker 用户链 |
| DOCKER-FORWARD | Docker 转发链 |

### OUTPUT Chain (policy: ACCEPT)

无规则。

### Docker 相关链

所有 Docker 链均为空（0 references 或空规则）。

---

## 安全分析

1. **封禁 IP 列表**（IPv4 INPUT）：
   - `87.251.64.144/145` — 同一 /24 网段，可能是扫描器
   - `81.90.28.163` — 单独 IP
   - `45.148.10.183` — 单独 IP
   - `47.236.245.255` — 单独 IP
   - `185.204.171.193` — 单独 IP
   - `61.75.245.101` — 单独 IP
   - `59.153.245.232` — 单独 IP

2. **SSH 防护**：使用 `recent` 模块限制 60s 内最多 4 次新连接，超出则封禁。

3. **Docker 隔离**：
   - FORWARD 默认 DROP，只允许 Docker 内部转发
   - DOCKER 链默认 DROP all
   - 只允许 RELATED,ESTABLISHED 的 Docker 容器流量

4. **IPv6 未配置**：ip6tables 所有链均为空，policy 为 ACCEPT — IPv6 流量不受限制。
