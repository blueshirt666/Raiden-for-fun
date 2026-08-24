from emit import *
for order in ('A_first', 'B_first'):
    gates, labels, names, outs = assemble(order)
    n_in = len(names); n_out = 9
    n, d, C = metrics(gates, n_in)
    ai = [names.index(f'a{i}') for i in range(4)]
    bi = [names.index(f'b{i}') for i in range(8)]
    fails = []
    for vec in range(1 << n_in):
        bits = [(vec >> k) & 1 for k in range(n_in)]
        A = sum(bits[ai[i]] << i for i in range(4))
        B = sum(bits[bi[i]] << i for i in range(8))
        got = sum(bit << j for j, bit in enumerate(
            read_outputs(simulate(gates, n_in, bits), gates, n_in, n_out)))
        if got != A + B: fails.append((A, B, got, A + B))
    dead = find_dead(gates, n_in, n_out)
    assert outs == list(range(2 + n_in + n - n_out, 2 + n_in + n)), "输出不在末尾!"
    Cref = 14656250; q = min(4.0, max(0.25, Cref / C))
    print(f"[{order}] pins={names}")
    print(f"  门数 {n} / 深度 {d} / C = {C:,}   q = {Cref/C:.1f} -> 顶满 {q}")
    print(f"  穷举 {1<<n_in} 向量失败数 = {len(fails)}   死门 = {dead}   输出末尾断言 OK")
    print(f"  H(P=1) = {n} + 938*4 = {n + 938*4}     H(P=6) = {(n + 938*4)*6}")
    print(f"  性价比 H/n = {(n+938*4)/n:.1f}\n")
