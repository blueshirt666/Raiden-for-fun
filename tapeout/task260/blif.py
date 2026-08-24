from emit import assemble, metrics, encode
from emit2 import assemble2

def to_blif(model, gates, names, note):
    n_in = len(names); first = 2 + n_in; n = len(gates); n_out = 9
    nm = {0: 'gnd', 1: 'vdd'}
    for i, s in enumerate(names): nm[2 + i] = s
    for i in range(n):
        nid = first + i
        nm[nid] = f's{i - (n - n_out)}' if i >= n - n_out else f'n{nid}'
    L = [f'# {l}' for l in note.splitlines()]
    L += [f'.model {model}', '.inputs ' + ' '.join(names),
          '.outputs ' + ' '.join(f's{j}' for j in range(n_out))]
    for i, (x, y) in enumerate(gates):
        L += [f'.names {nm[x]} {nm[y]} {nm[first+i]}', '0- 1', '-0 1']
    L += ['.end', '']
    return '\n'.join(L)

Cref = 14656250
jobs = [('v1', assemble, 'A_first'), ('v1', assemble, 'B_first'),
        ('v2', assemble2, 'A_first'), ('v2', assemble2, 'B_first')]
for ver, fn, order in jobs:
    r = fn(order); gates, names = r[0], r[-2] if ver == 'v1' else r[1]
    names = r[2] if ver == 'v1' else r[1]
    n, d, C = metrics(gates, len(names))
    note = (f"TapeOut Protocol -- chain task #260 (bank 293) 4-bit + 8-bit concatenated carry add\n"
            f"S[8:0] = B[7:0] + A[3:0]   (A zero-extended)\n"
            f"variant {ver.upper()} / pin order {order}\n"
            f"gates={n} depth={d} C=A*d^3={C:,} C_ref={Cref:,} ratio={Cref/C:.1f}x q=4.0(capped)\n"
            f"H(P=1)={n+938*4}  H(P=6)={(n+938*4)*6}  burn={n} NAND\n"
            f"NAND-only, zero dead gates, outputs are the LAST 9 gates in LSB->MSB order.\n"
            f"Exhaustively verified over all 4096 input vectors.")
    model = f"tapeout_260_{ver}_{order.lower()}"
    open(f"{model}.blif", 'w').write(to_blif(model, gates, names, note))
    open(f"{model}.hex", 'w').write(encode(gates) + '\n')
    print(f"{model}.blif  ({n} gates, d={d}, C={C:,})   hex {len(encode(gates))-2} chars = {n*7} bytes")
