import glob, itertools
def parse_blif(p):
    ins=outs=None; gates=[]
    lines=[l.strip() for l in open(p) if l.strip() and not l.startswith('#')]
    i=0
    while i<len(lines):
        t=lines[i].split()
        if t[0]=='.inputs': ins=t[1:]
        elif t[0]=='.outputs': outs=t[1:]
        elif t[0]=='.names':
            a,b,y=t[1],t[2],t[3]
            cov={lines[i+1],lines[i+2]}
            assert cov=={'0- 1','-0 1'}, f"{p}: 非 NAND 覆盖 {cov}"
            gates.append((a,b,y)); i+=2
        elif t[0]=='.end': pass
        i+=1
    return ins,outs,gates

for p in sorted(glob.glob('tapeout_260_*.blif')):
    ins,outs,gates=parse_blif(p)
    order=[g[2] for g in gates]
    assert order[-9:]==[f's{j}' for j in range(9)], f"{p}: 末 9 门不是 s0..s8"
    ai=[ins.index(f'a{i}') for i in range(4)]; bi=[ins.index(f'b{i}') for i in range(8)]
    bad=0
    for vec in range(1<<len(ins)):
        bits=[(vec>>k)&1 for k in range(len(ins))]
        v={'gnd':0,'vdd':1}
        for k,nm in enumerate(ins): v[nm]=bits[k]
        for a,b,y in gates: v[y]=1-(v[a]&v[b])
        got=sum(v[f's{j}']<<j for j in range(9))
        A=sum(bits[ai[i]]<<i for i in range(4)); B=sum(bits[bi[i]]<<i for i in range(8))
        bad+= (got!=A+B)
    # 与 hex 交叉核对
    h=open(p[:-5]+'.hex').read().strip()
    assert len(bytes.fromhex(h[2:]))==7*len(gates) and all(bytes.fromhex(h[2:])[k*7]==0 for k in range(len(gates)))
    print(f"{p:34s} 门 {len(gates):3d}  穷举 {1<<len(ins)} 向量  失败 {bad}  末尾断言 OK  hex {7*len(gates)} 字节 tag 全 0x00")
