"""#260 V3：深度优先。两个代数恒等式把进位链压到 nc4@d5。
   (1) 吸收律 g<=p  =>  G(i:j) = p_i & (g_i + G(i-1:j))
       故 ¬G(i:j) = NAND(p_i, NAND(ng_i, ¬G(i-1:j)))  —— 每级只 2 层，且补码进补码出
   (2) 分配律      c4 = G32 + P32*G10 = (G32+P32) & (G32+G10)
       末级变成 AND，于是 nc4 = NAND(X,Y) 一个门就出来，比 NOT(c4) 早一层
       且 G32+P32 = g3 + p3*(g2+p2) = g3 + p3*p2   (再次用 g2<=p2)
"""
from kit import K, finalize, metrics, verify

def build_v3(order):
    An = [f'a{i}' for i in range(4)]; Bn = [f'b{i}' for i in range(8)]
    names = (An + Bn) if order == 'A_first' else (Bn + An)
    k = K(12); pin = lambda s: 2 + names.index(s)
    a = [pin(f'a{i}') for i in range(4)]; b = [pin(f'b{i}') for i in range(8)]

    ng = [k.nd(a[i], b[i]) for i in range(4)]                 # ¬g_i        d1
    g0 = k.NOT(ng[0])                                          #             d2
    p  = {i: k.nd(k.NOT(a[i]), k.NOT(b[i])) for i in (1,2,3)}  # p_i = a+b   d2
    xo = [k.XOR(a[i], b[i]) for i in range(4)]                 # a^b         d3
    nxo= {i: k.nd(ng[i], p[i]) for i in (1,2,3)}               # ¬(a^b)      d3

    nG10 = k.nd(p[1], k.nd(ng[1], ng[0]))                      # ¬c2         d3
    c2   = k.NOT(nG10)                                          #             d4
    nc3  = k.nd(p[2], k.nd(ng[2], nG10))                       # ¬c3         d5
    c3   = k.NOT(nc3)                                           #             d6
    nG32 = k.nd(p[3], k.nd(ng[3], ng[2]))                      # ¬G(3:2)     d3
    Y    = k.nd(nG32, nG10)                                    # G32+G10     d4
    X    = k.nd(ng[3], k.nd(p[3], p[2]))                       # g3+p3p2     d4
    nc4  = k.nd(X, Y)                                          # ¬c4         d5
    c4   = k.NOT(nc4)                                          #             d6

    S = [None]*9
    S[0] = xo[0]                                                #             d3
    S[1] = k.MUX(g0,   ng[0], xo[1], nxo[1])                   #             d5
    S[2] = k.MUX(c2,   nG10,  xo[2], nxo[2])                   #             d6
    S[3] = k.MUX(c3,   nc3,   xo[3], nxo[3])                   #             d8

    nQ45   = k.nd(b[4], b[5]); Q45   = k.NOT(nQ45)             #             d1/d2
    nQ456  = k.nd(Q45, b[6]);  Q456  = k.NOT(nQ456)            #             d3/d4
    nQ4567 = k.nd(Q456, b[7]); Q4567 = k.NOT(nQ4567)           # 复用 Q456, 省掉 Q67 两个门
    nb = {i: k.NOT(b[i]) for i in (4, 6, 7)}
    # 高半条件和：x1_i = b_i ^ (b4..b_{i-1} 全 1)，用补码版 XNOR 抢一层
    x1 = {4: nb[4],
          5: k.XOR(b[4], b[5]),                                 #             d3
          6: k.XNOR2(b[6], nb[6], nQ45,  Q45),                  #             d4
          7: k.XNOR2(b[7], nb[7], nQ456, Q456)}                 #             d6
    for i in (4, 5, 6, 7):
        S[i] = k.MUX(c4, nc4, b[i], x1[i])                      #             d8
    S[8] = k.NOT(k.nd(c4, Q4567))                               #             d8
    return k, S, names

if __name__ == '__main__':
    Cref = 14656250
    for order in ('A_first', 'B_first'):
        k, S, names = build_v3(order)
        gates = finalize(k, S)
        n, d, C = metrics(gates, 12)
        ai = [names.index(f'a{i}') for i in range(4)]; bi = [names.index(f'b{i}') for i in range(8)]
        spec = lambda v: (sum(((v >> ai[i]) & 1) << i for i in range(4))
                        + sum(((v >> bi[i]) & 1) << i for i in range(8)))
        bad, dead = verify(gates, 12, 9, spec)
        print(f"[V3 {order}] 门 {n} / 深 {d} / C = {C:,}  C_ref/C = {Cref/C:.0f}x  "
              f"失败 {bad}  死门 {dead}  H(P=1)={n+3752}  H/n={(n+3752)/n:.1f}")
