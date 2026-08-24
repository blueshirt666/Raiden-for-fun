from build2 import build_v2
from emit import metrics, simulate, read_outputs, find_dead, encode

def assemble2(order):
    N, S, names = build_v2(order)
    n_in = len(names); first = 2 + n_in
    tail_key = S[8][1]
    body = [g for g in N.gates if g[0] != tail_key]
    tail = next(g for g in N.gates if g[0] == tail_key)
    num = {('I', i): 2 + i for i in range(n_in)}
    gates = []
    for k, x, y in body:
        num[k] = first + len(gates); gates.append((num[x], num[y]))
    outs = []
    for i in range(8):
        _, x, y = S[i]; outs.append(first + len(gates)); gates.append((num[x], num[y]))
    num[tail_key] = first + len(gates); outs.append(num[tail_key])
    gates.append((num[tail[1]], num[tail[2]]))
    return gates, names, outs
