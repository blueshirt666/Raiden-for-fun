from build import build

def assemble(order):
    N, S, names = build(order)
    n_in = len(names); first = 2 + n_in
    tail_key = S[8][1]                     # c8 这个门要挪到最末尾当 s8
    body = [g for g in N.gates if g[0] != tail_key]
    tail_gate = next(g for g in N.gates if g[0] == tail_key)

    num = {}
    for idx, nm in enumerate(names): num[('I', idx)] = 2 + idx
    gates = []; labels = []
    def res(k): return num[k]
    for k, x, y in body:
        num[k] = first + len(gates); gates.append((res(x), res(y))); labels.append(N.name.get(k, ''))
    outs = []
    for i in range(8):                     # s0..s7 作为最后的门重新落地
        _, x, y = S[i]
        nid = first + len(gates); gates.append((res(x), res(y))); labels.append(f's{i}'); outs.append(nid)
    num[tail_key] = first + len(gates)     # s8 = c8
    gates.append((res(tail_gate[1]), res(tail_gate[2]))); labels.append('s8'); outs.append(num[tail_key])
    return gates, labels, names, outs

def metrics(gates, n_in):
    first = 2 + n_in; dep = {0: 0, 1: 0}
    for k in range(n_in): dep[2 + k] = 0
    for i, (x, y) in enumerate(gates):
        assert x < first + i and y < first + i, f"门 {first+i} 引用未定义节点"
        dep[first + i] = max(dep[x], dep[y]) + 1
    d = max(dep.values())
    return len(gates), d, len(gates) * max(d, 1) ** 3

def simulate(gates, n_in, bits):
    first = 2 + n_in; v = {0: 0, 1: 1}
    for k, b in enumerate(bits): v[2 + k] = b
    for i, (x, y) in enumerate(gates): v[first + i] = 1 - (v[x] & v[y])
    return v

def read_outputs(v, gates, n_in, n_out):
    first = 2 + n_in; last = first + len(gates) - 1
    return [v[last - n_out + 1 + j] for j in range(n_out)]

def find_dead(gates, n_in, n_out):
    first = 2 + n_in; n = len(gates)
    live = set(range(first + n - n_out, first + n))
    for i in range(n - 1, -1, -1):
        if first + i in live: live.add(gates[i][0]); live.add(gates[i][1])
    return [first + i for i in range(n) if first + i not in live]

def encode(gates):
    out = bytearray()
    for a, b in gates: out += b'\x00' + a.to_bytes(3, 'big') + b.to_bytes(3, 'big')
    return '0x' + out.hex()
