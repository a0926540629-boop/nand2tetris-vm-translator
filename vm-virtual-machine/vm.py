import sys
import os


class Parser:
    def __init__(self, filepath):
        self.commands = []
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                
                if line and not line.startswith("//"):
                    real = line.split("//")[0].strip()
                    self.commands.append(real)
        self.pos = -1
        self.current = ""

    def has_more(self):
        return self.pos + 1 < len(self.commands)

    def advance(self):
        self.pos += 1
        self.current = self.commands[self.pos]

    def cmd_type(self):
        first = self.current.split()[0]
        if first == "push":
            return "C_PUSH"
        elif first == "pop":
            return "C_POP"
        elif first == "label":
            return "C_LABEL"
        elif first == "goto":
            return "C_GOTO"
        elif first == "if-goto":
            return "C_IF"
        elif first == "function":
            return "C_FUNCTION"
        elif first == "call":
            return "C_CALL"
        elif first == "return":
            return "C_RETURN"
        else:
            return "C_ARITHMETIC"

    def arg1(self):
        parts = self.current.split()
        if self.cmd_type() == "C_ARITHMETIC":
            return parts[0]
        return parts[1]

    def arg2(self):
        return int(self.current.split()[2])


class CodeWriter:
    def __init__(self, outfile):
        self.f = open(outfile, "w", encoding="utf-8")
        self.label_id = 0
        self.funcname = ""

    def write_bootstrap(self):
        
        self.f.write("@256\nD=A\n@SP\nM=D\n")
        self.write_call("Sys.init", 0)

    def write_arithmetic(self, op):
        code = {
            "add": """@SP
AM=M-1
D=M
A=A-1
M=M+D
""",
            "sub": """@SP
AM=M-1
D=M
A=A-1
M=M-D
""",
            "neg": """@SP
A=M-1
M=-M
""",
            "and": """@SP
AM=M-1
D=M
A=A-1
M=M&D
""",
            "or": """@SP
AM=M-1
D=M
A=A-1
M=M|D
""",
            "not": """@SP
A=M-1
M=!M
""",
        }
        if op in ("eq", "gt", "lt"):
            self.f.write(self._compare(op.upper()))
        else:
            self.f.write(code[op])

    def _compare(self, jmp):
        L1 = f"L{self.label_id}"
        L2 = f"L{self.label_id + 1}"
        self.label_id += 2
        return f"""@SP
AM=M-1
D=M
A=A-1
D=M-D
@{L1}
D;{jmp}
@SP
A=M-1
M=0
@{L2}
0;JMP
({L1})
@SP
A=M-1
M=-1
({L2})
"""

    def write_push_pop(self, ctype, seg, idx):
        seg_map = {
            "local": "LCL",
            "argument": "ARG",
            "this": "THIS",
            "that": "THAT",
        }
        if seg in seg_map:
            base = seg_map[seg]
            if ctype == "C_PUSH":
                self.f.write(f"""@{idx}
D=A
@{base}
A=M+D
D=M
@SP
A=M
M=D
@SP
M=M+1
""")
            else:
                self.f.write(f"""@{idx}
D=A
@{base}
D=M+D
@R13
M=D
@SP
AM=M-1
D=M
@R13
A=M
M=D
""")
        elif seg == "constant":
            self.f.write(f"""@{idx}
D=A
@SP
A=M
M=D
@SP
M=M+1
""")
        elif seg == "static":
            sym = f"{self.funcname}.{idx}" if self.funcname else f"static.{idx}"
            if ctype == "C_PUSH":
                self.f.write(f"""@{sym}
D=M
@SP
A=M
M=D
@SP
M=M+1
""")
            else:
                self.f.write(f"""@SP
AM=M-1
D=M
@{sym}
M=D
""")
        elif seg == "temp":
            addr = 5 + idx
            if ctype == "C_PUSH":
                self.f.write(f"""@{addr}
D=M
@SP
A=M
M=D
@SP
M=M+1
""")
            else:
                self.f.write(f"""@SP
AM=M-1
D=M
@{addr}
M=D
""")
        elif seg == "pointer":
            tar = "THIS" if idx == 0 else "THAT"
            if ctype == "C_PUSH":
                self.f.write(f"""@{tar}
D=M
@SP
A=M
M=D
@SP
M=M+1
""")
            else:
                self.f.write(f"""@SP
AM=M-1
D=M
@{tar}
M=D
""")

    def write_label(self, label):
        self.f.write(f"({self.funcname}${label})\n")

    def write_goto(self, label):
        self.f.write(f"@{self.funcname}${label}\n0;JMP\n")

    def write_if(self, label):
        self.f.write(f"""@SP
AM=M-1
D=M
@{self.funcname}${label}
D;JNE
""")

    def write_function(self, fname, nlocal):
        self.funcname = fname
        self.f.write(f"({fname})\n")
        for _ in range(nlocal):
            self.f.write("""@0
D=A
@SP
A=M
M=D
@SP
M=M+1
""")

    def write_call(self, fname, narg):
        retlabel = f"ret{self.label_id}"
        self.label_id += 1
        self.f.write(f"""@{retlabel}
D=A
@SP
A=M
M=D
@SP
M=M+1
@LCL
D=M
@SP
A=M
M=D
@SP
M=M+1
@ARG
D=M
@SP
A=M
M=D
@SP
M=M+1
@THIS
D=M
@SP
A=M
M=D
@SP
M=M+1
@THAT
D=M
@SP
A=M
M=D
@SP
M=M+1
@{narg + 5}
D=A
@SP
D=M-D
@ARG
M=D
@SP
D=M
@LCL
M=D
@{fname}
0;JMP
({retlabel})
""")

    def write_return(self):
        self.f.write("""@LCL
D=M
@R14
M=D
@5
D=A
@R14
A=M-D
D=M
@R15
M=D
@SP
AM=M-1
D=M
@ARG
A=M
M=D
@ARG
D=M+1
@SP
M=D
@R14
A=M-1
D=M
@THAT
M=D
@R14
A=M-1
A=M-1
D=M
@THIS
M=D
@R14
A=M-1
A=M-1
A=M-1
D=M
@ARG
M=D
@R14
A=M-1
A=M-1
A=M-1
A=M-1
D=M
@LCL
M=D
@R15
A=M
0;JMP
""")

    def close(self):
        self.f.close()


def main():
    if len(sys.argv) != 2:
        print("用法：python vm.py xxx.vm 或是資料夾")
        return
    target = sys.argv[1]
    if os.path.isdir(target):
        outname = os.path.basename(target) + ".asm"
        outpath = os.path.join(target, outname)
        cw = CodeWriter(outpath)
        cw.write_bootstrap()
        for f in os.listdir(target):
            if f.endswith(".vm"):
                p = Parser(os.path.join(target, f))
                while p.has_more():
                    p.advance()
                    t = p.cmd_type()
                    if t == "C_ARITHMETIC":
                        cw.write_arithmetic(p.arg1())
                    elif t in ("C_PUSH", "C_POP"):
                        cw.write_push_pop(t, p.arg1(), p.arg2())
                    elif t == "C_LABEL":
                        cw.write_label(p.arg1())
                    elif t == "C_GOTO":
                        cw.write_goto(p.arg1())
                    elif t == "C_IF":
                        cw.write_if(p.arg1())
                    elif t == "C_FUNCTION":
                        cw.write_function(p.arg1(), p.arg2())
                    elif t == "C_CALL":
                        cw.write_call(p.arg1(), p.arg2())
                    elif t == "C_RETURN":
                        cw.write_return()
        cw.close()
    else:
        base, _ = os.path.splitext(target)
        outpath = base + ".asm"
        cw = CodeWriter(outpath)
        cw.write_bootstrap()
        p = Parser(target)
        while p.has_more():
            p.advance()
            t = p.cmd_type()
            if t == "C_ARITHMETIC":
                cw.write_arithmetic(p.arg1())
            elif t in ("C_PUSH", "C_POP"):
                cw.write_push_pop(t, p.arg1(), p.arg2())
            elif t == "C_LABEL":
                cw.write_label(p.arg1())
            elif t == "C_GOTO":
                cw.write_goto(p.arg1())
            elif t == "C_IF":
                cw.write_if(p.arg1())
            elif t == "C_FUNCTION":
                cw.write_function(p.arg1(), p.arg2())
            elif t == "C_CALL":
                cw.write_call(p.arg1(), p.arg2())
            elif t == "C_RETURN":
                cw.write_return()
        cw.close()


if __name__ == "__main__":
    main()

