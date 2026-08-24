"""带 CSE 的 NAND 构建器 + 输出落尾 finalize"""
class K:
    def __init__(self, n_in):
        self.n_in = n_in; self.first = 2 + n_in
        self.gates = []; self.cache = {}
        self.dep = {0: 0, 1: 0}
        for k in range(n_in): self.dep[2 + k] = 0
    def nd(self, x, y):
        key = (x, y) if x <= y else (y, x)
        if key in self.cache: return self.cache[key]
        nid = self.first + len(self.gates); self.gates.append((x, y))
        self.dep[nid] = max(self.dep[x], self.dep[y]) + 1
        self.cache[key] = nid; return nid
    NOT = lambda s, x: s.nd(x, x)
    def AND(s, x, y): return s.NOT(s.nd(x, y))
    def OR(s, x, y):  return s.nd(s.NOT(x), s.NOT(y))
    def XOR(s, x, y):
        t = s.nd(x, y); return s.nd(s.nd(x, t), s.nd(y, t))
    def XOR2(s, x, nx, y, ny):        # 两极都有时的 XOR: 深度只 +2
        return s.nd(s.nd(x, ny), s.nd(nx, y))
    def XNOR2(s, x, nx, y, ny):
        return s.nd(s.nd(x, y), s.nd(nx, ny))
    def MUX(s, sel, nsel, x0, x1):    # sel=1 -> x1
        return s.nd(s.nd(sel, x1), s.nd(nsel, x0))

def finalize(K_, outs):
    """把 outs 变成末尾 O 个门；有扇出的输出插缓冲(+2门+2深)"""
    fan = {}
    for x, y in K_.gates:
        fan[x] = fan.get(x, 0) + 1
        if y != x: fan[y] = fan.get(y, 0) + 1
    seen = set(); fixed = []
    for o in outs:
        if o < K_.first or fan.get(o, 0) > 0 or o in seen:
            o = K_.NOT(K_.NOT(o))                     # 缓冲
        seen.add(o); fixed.append(o)
    tail = set(fixed)
    body = [K_.first + i for i in range(len(K_.gates)) if K_.first + i not in tail]
    order = body + fixed
    num = {0: 0, 1: 1}
    for k in range(K_.n_in): num[2 + k] = 2 + k
    gates = []
    for old in order:
        x, y = K_.gates[old - K_.first]
        num[old] = K_.first + len(gates); gates.append((num[x], num[y]))
    return gates

def metrics(gates, n_in):
    first = 2 + n_in; dep = {0: 0, 1: 0}
    for k in range(n_in): dep[2 + k] = 0
    for i, (x, y) in enumerate(gates):
        assert x < first + i and y < first + i
        dep[first + i] = max(dep[x], dep[y]) + 1
    d = max(dep.values()); return len(gates), d, len(gates) * max(d, 1) ** 3

def verify(gates, n_in, n_out, spec):
    first = 2 + n_in; last = first + len(gates) - 1; bad = 0
    for vec in range(1 << n_in):
        v = {0: 0, 1: 1}
        for k in range(n_in): v[2 + k] = (vec >> k) & 1
        for i, (x, y) in enumerate(gates): v[first + i] = 1 - (v[x] & v[y])
        got = sum(v[last - n_out + 1 + j] << j for j in range(n_out))
        bad += (got != spec(vec))
    live = set(range(first + len(gates) - n_out, first + len(gates)))
    for i in range(len(gates) - 1, -1, -1):
        if first + i in live: live.add(gates[i][0]); live.add(gates[i][1])
    dead = [first + i for i in range(len(gates)) if first + i not in live]
    return bad, dead
