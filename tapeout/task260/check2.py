from emit2 import assemble2
from emit import metrics, simulate, read_outputs, find_dead
Cref = 14656250
for order in ('A_first', 'B_first'):
    gates, names, outs = assemble2(order); n_in = len(names); n_out = 9
    n, d, C = metrics(gates, n_in)
    ai = [names.index(f'a{i}') for i in range(4)]; bi = [names.index(f'b{i}') for i in range(8)]
    fails = 0
    for vec in range(1 << n_in):
        bits = [(vec >> k) & 1 for k in range(n_in)]
        A = sum(bits[ai[i]] << i for i in range(4)); B = sum(bits[bi[i]] << i for i in range(8))
        got = sum(x << j for j, x in enumerate(read_outputs(simulate(gates, n_in, bits), gates, n_in, n_out)))
        fails += (got != A + B)
    assert outs == list(range(2+n_in+n-n_out, 2+n_in+n))
    print(f"[V2 {order}] 门 {n} / 深 {d} / C = {C:,}  q={Cref/C:.1f}->4.0  失败 {fails}  死门 {find_dead(gates,n_in,n_out)}  H/n={(n+3752)/n:.1f}")
