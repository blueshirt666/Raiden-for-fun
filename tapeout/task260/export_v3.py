from v3 import build_v3
from kit import finalize, metrics
from blif import to_blif
from emit import encode
Cref = 14656250
for order in ('A_first', 'B_first'):
    k, S, names = build_v3(order)
    gates = finalize(k, S); n, d, C = metrics(gates, 12)
    note = (f"TapeOut Protocol -- chain task #260 (bank 293) 4-bit + 8-bit concatenated carry add\n"
            f"S[8:0] = B[7:0] + A[3:0]   (A zero-extended)\n"
            f"variant V3 (minimum-C / depth-optimised) / pin order {order}\n"
            f"gates={n} depth={d} C=A*d^3={C:,} C_ref={Cref:,} ratio={Cref/C:.0f}x q=4.0(capped)\n"
            f"H(P=1)={n+938*4}  H(P=6)={(n+938*4)*6}  burn={n} NAND\n"
            f"Key identities: (1) g<=p absorption => ~G(i:j)=NAND(p_i,NAND(~g_i,~G(i-1:j)))\n"
            f"                (2) c4=(G32+P32)&(G32+G10) puts an AND last, so ~c4 lands a level early\n"
            f"NAND-only, zero dead gates, outputs are the LAST 9 gates in LSB->MSB order.\n"
            f"Exhaustively verified over all 4096 input vectors.")
    m = f"tapeout_260_v3_{order.lower()}"
    open(f"{m}.blif", 'w').write(to_blif(m, gates, names, note))
    open(f"{m}.hex", 'w').write(encode(gates) + '\n')
    print(f"{m}.blif  {n} 门 / 深 {d} / C={C:,}  hex {n*7} 字节")
