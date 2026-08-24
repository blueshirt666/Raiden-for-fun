"""#260 变体 V2：高半 4 位改用前缀 AND 树，压深度换 C"""
from build import Net

def build_v2(order):
    A = [f'a{i}' for i in range(4)]; B = [f'b{i}' for i in range(8)]
    names = (A + B) if order == 'A_first' else (B + A)
    N = Net(names)
    a = [N.inp(x) for x in A]; b = [N.inp(x) for x in B]
    S = [None]*9

    n1 = N.nand(b[0], a[0]); n2 = N.nand(b[0], n1); n3 = N.nand(a[0], n1)
    S[0] = ('OUT', n2, n3)
    c = N.NOT(n1, 'c1')
    for i in (1, 2, 3):
        m1 = N.nand(b[i], a[i]); m2 = N.nand(b[i], m1); m3 = N.nand(a[i], m1)
        p = N.nand(m2, m3, f'p{i}'); t = N.nand(p, c, f't{i}')
        u = N.nand(p, t); v = N.nand(c, t)
        S[i] = ('OUT', u, v)
        c = N.nand(m1, t, f'c{i+1}')
    c4 = c
    AND = lambda x, y, l=None: N.NOT(N.nand(x, y), l)
    P45   = AND(b[4], b[5], 'P45')          # 与 c4 无关, 深度 2
    P67   = AND(b[6], b[7], 'P67')
    P456  = AND(P45, b[6], 'P456')
    P4567 = AND(P45, P67, 'P4567')
    c5 = AND(c4, b[4],  'c5')               # 4 条进位并行, 都是 c4 深度 +2
    c6 = AND(c4, P45,   'c6')
    c7 = AND(c4, P456,  'c7')
    c8 = AND(c4, P4567, 'c8')
    for i, ci in ((4, c4), (5, c5), (6, c6), (7, c7)):
        m = N.nand(b[i], ci); u = N.nand(b[i], m); v = N.nand(ci, m)
        S[i] = ('OUT', u, v)
    S[8] = ('LAST_IS', c8)
    return N, S, names
