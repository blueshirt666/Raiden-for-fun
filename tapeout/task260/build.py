"""#260 4位与8位拼接进位加  S[8:0] = B[7:0] + A[3:0]"""

class Net:
    def __init__(self, in_names):
        self.in_names = in_names
        self.gates = []          # list of (refA, refB) using symbolic keys
        self.name = {}           # key -> label
        self.key_of_const = {'ZERO':0, 'ONE':1}
        self._n = 0
    def inp(self, nm): return ('I', self.in_names.index(nm))
    def nand(self, a, b, label=None):
        k = ('G', self._n); self._n += 1
        self.gates.append((k, a, b))
        if label: self.name[k] = label
        return k
    def NOT(self, a, label=None): return self.nand(a, a, label)

def build(order):
    """order: 'A_first' -> pins A0..A3,B0..B7 ; 'B_first' -> B0..B7,A0..A3"""
    A = [f'a{i}' for i in range(4)]; B = [f'b{i}' for i in range(8)]
    names = (A + B) if order == 'A_first' else (B + A)
    N = Net(names)
    a = [N.inp(x) for x in A]; b = [N.inp(x) for x in B]
    S = [None]*9

    # --- bit0: 半加器 (b0, a0) ---
    n1 = N.nand(b[0], a[0], 'ng0')
    n2 = N.nand(b[0], n1); n3 = N.nand(a[0], n1)
    S[0] = ('OUT', n2, n3)                       # s0 = XOR
    c = N.NOT(n1, 'c1')                          # c1 = g0

    # --- bits1..3: 全加器，复用 t=NAND(p,c) 同时做进位和和 ---
    for i in (1, 2, 3):
        m1 = N.nand(b[i], a[i], f'ng{i}')        # = ¬g_i
        m2 = N.nand(b[i], m1); m3 = N.nand(a[i], m1)
        p  = N.nand(m2, m3, f'p{i}')             # p_i = b_i ^ a_i
        t  = N.nand(p, c, f't{i}')               # ¬(p_i·c_i)
        u  = N.nand(p, t); v = N.nand(c, t)
        S[i] = ('OUT', u, v)                     # s_i = p_i ^ c_i
        c  = N.nand(m1, t, f'c{i+1}')            # c_{i+1} = ¬(¬g_i · ¬(p_i c_i))

    # --- bits4..7: 高半只是把 c4 当增量往上传，半加器 (b_i, c) ---
    for i in (4, 5, 6, 7):
        m = N.nand(b[i], c, f'm{i}')             # ¬(b_i·c_i)
        u = N.nand(b[i], m); v = N.nand(c, m)
        S[i] = ('OUT', u, v)                     # s_i = b_i ^ c_i
        c = N.NOT(m, f'c{i+1}')                  # c_{i+1} = b_i·c_i
    S[8] = ('LAST_IS', c)                        # s8 = c8 —— 复用，不额外开销
    return N, S, names

print(open(__file__).read().count('\n'), 'lines loaded')
