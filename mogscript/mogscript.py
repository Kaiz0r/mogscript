import re, random, os, textwrap, asyncio, time, platform, sys

try:
    from pyparsing import (
        Literal,
        CaselessLiteral,
        Word,
        Combine,
        Group,
        Optional,
        ZeroOrMore,
        Forward,
        nums,
        alphas,
        oneOf,
    )
    import math
    import operator

    EXPR_PARSING = True
except:
    EXPR_PARSING = False

try:
    import art

    ART_LIB = True
except:
    ART_LIB = False
# TODO
"""
{include: filename} 
Replaces with the read text of a file 

{sh: command}
Run bash commands, replaces with output

{PROCESS: name} tag to define a new function processor the parser calls on the body
if
! process: name
is found, run the func on the body and dont parse, cause if the thing itself wants to parse, it can do it there


Make a parsing engine for Python, go, Ruby, js

Maybe have the remaining kargs passed to the constructor become env vars in the parser

some kind of [ ] natural language commands?
[make all text upper] to uppercase whole block?
[make a <class>]
[send to <global>] - sends body to some class/method on the parser globals
[send "test" to <global>] - sends this instead of whole block
to decide more things later
"""


class VersionError(Exception):
    pass


class Mog:
    @staticmethod
    def load(**kargs):
        if kargs.get("str"):
            i = kargs["str"]
            del kargs["str"]
            return Parser(code, **kargs)
        elif kargs.get("file"):
            i = kargs["file"]
            del kargs["file"]
            with open(i, 'r+') as f:
                return Parser(f.read(), **kargs)
            
        elif kargs.get("dir"):
            i = kargs["dir"]
            del kargs["dir"]
            return Scanner.read(i, **kargs)

class Scanner:
    @staticmethod
    def read(path, **kargs):
        if not kargs.get("exts"):
            exts = ["txt"]
        else:
            exts = kargs["exts"]
            del kargs["exts"]

        p = []
        for file in os.listdir(path):
            do = False
            for item in exts:
                if str(file).endswith(item):
                    do = True
            if do:
                with open(f"{path}{file}", "r") as f:
                    p.append(Parser(f.read(), **kargs))
        return p

class MogLibrary:
    @staticmethod
    def spr(*args):
        return " ".join(args)
    
    @staticmethod
    def parseMSymbol(p, entity, word):
        if word.startswith("$"):  # from vars
            v = word.replace("$", "")
            end = None
            if v[-1] in [".", "?", "!", ";", ":", "~", ","]:
                end = v[-1]
                v = v.replace(end, "")
            fin = p.vars.get(v, word)
            if end:
                fin = fin + end
            return fin

        elif word.startswith("?"):  # from entity locals
            v = word.replace("?", "")
            end = None
            if v[-1] in [".", "?", "!", ";", ":", "~", ","]:
                end = v[-1]
                v = v.replace(end, "")
            fin = entity.vars.get(v, word)
            if end:
                fin = fin + end
            return fin
        else:
            return word

    @staticmethod    
    def parseMSymbols(p, entity, ls):
        out = []
        for item in ls:

            phr = item.split(" ")

            for word in phr:
                item = item.replace(word, MogLibrary.parseMSymbol(p, entity, word))

            out.append(item)
        return out

    @staticmethod
    def write(p, code):
        p.body += f"\n{code}"

    @staticmethod    
    def read(p, filepath):
        with open(filepath, "r") as f:
            p.body += f.read()
            
    @staticmethod
    def addGlobal(p, name, call):
        p.globals[name.lower()] = call
        
    @staticmethod      
    def recheck(p, *args):
        p.parse(partial=True)
        
    @staticmethod    
    def insert(p, body, ind=-1):
        ent = Entity(p, body)

        if ind < 0:
            p.entities.append(ent)
        else:
            p.entities.insert(ind, ent)
            
    @staticmethod        
    def extractComments(entity):
        body = entity.body.split("\n")
        comments = []
        for line in entity.body.split("\n"):
            if line.startswith("//"):
                comments.append(line[2:])
                body.remove(line)
            elif "//" in line:
                comments.append(line.split("//")[1])
                body[body.index(line)] = line.replace("//" + line.split("//")[1], "")
        entity.body = "\n".join(body)
        entity.comments = comments
        
    @staticmethod    
    def export(p, **kargs):
        body = ""
        if kargs.get("update_meta"):
            body = "! META\n"
            for item in p.vars:
                body += f"{item}: {str(self.vars[item])}\n"
        else:
            body = p.meta_header

        for item in p.entities:
            if item.body.startswith("\n"):
                body += f"---{item._body}"
            else:
                body += f"---\n{item._body}"
                
        if kargs.get("file"):
            with open(kargs["file"], "w+") as f:
                f.write(body)

        return body
    

    @staticmethod
    def parseDefPrps(prop):
        if prop == "$RNG":
            return str(random.random())
        elif prop == "$USER":
            return os.environ.get("USER")
        elif prop == "$HOME":
            return os.environ.get("HOME")
        elif prop == "$OS":
            return platform.system()
        elif prop == "$RELEASE":
            return platform.release()
        elif prop == "$VER":
            f = ""
            for item in list(sys.version_info):
                f = f"{f}.{item}"
            return f[1:-1]
        else:
            return prop
        
    @staticmethod    
    def walk(p):
        out = ""
        for ent in p.entities:
            if not ent.valid():
                calls = re.findall("{(.+?)}", ent.body)
                if len(calls) > 0 and calls[0].startswith("IF"):
                    ent.body = ent.body.replace("{" + calls[0] + "}", "")
                    v = calls[0].split(": ")[1]
                    key = v.split("=")[0]
                    value = v.split("=")[1]
                    if p.vars.get(key) == value:
                        ent.parse()
                elif len(calls) > 0 and calls[0].startswith("NOT"):
                    ent.body = ent.body.replace("{" + calls[0] + "}", "")
                    v = calls[0].split(": ")[1]
                    key = v.split("=")[0]
                    value = v.split("=")[1]
                    if p.vars.get(key) == value:
                        ent.parse()
                else:
                    ent.parse()
                    
                if ent.valid():
                    out += ent.parsed
        return out        


    @staticmethod
    def parse(p, *args, **kargs):
        partial = kargs.get('partial', False)
        p.entities = []
        out = ""

        for entry in p.body.split("---"):
            transient = False
            if entry.split("\n")[0] == "! META":
                p.meta_header = entry
                l = entry.replace("! META", "").split("\n")
                for item in l:
                    if item != "\n" and item != "":
                        p.vars[item.split(": ")[0]] = MogLibrary.parseDefPrps(
                            item.split(": ")[1]
                        )

                if p.vars.get("version"):
                    v = int(p.vars["version"])
                    if v != p.__version:
                        raise VersionError(
                            "Versions mismatch, script may be incompatible."
                        )

            else:
                calls = re.findall("{(.+?)}", entry)
                if len(calls) > 0 and calls[0].startswith("CODE: "):
                    entry = entry.replace("{" + calls[0] + "}", "")
                    name = calls[0].split(": ")[1]

                    body = f'def func(p, args):\n{textwrap.indent(entry, "  ")}'

                    env = {"p": p}
                    exec(body, env)
                    MogLibrary.addGlobal(p, name, env["func"])

                else:
                    ent = Entity(p, entry)
                        
                    if not partial:
                        if len(calls) > 0 and calls[0].startswith("IF"):
                            ent.body = entry.replace("{" + calls[0] + "}", "")
                            val = calls[0].split(": ")[1]
                            checks = val.split(";")
                            passed = 0

                            if checks[0].startswith("need"):
                                x = checks[0].split()
                                tocheck = x[1]
                                need = int(x[2])
                                checks.pop(0)
                            else:
                                tocheck = "=="
                                need = len(checks)

                            for v in checks:
                                if "!=" in v:
                                    key = v.split("!=")[0].strip()
                                    value = MogLibrary.parseMSymbol(p,
                                        ent, v.split("!=")[1].strip()
                                    )
                                    if p.vars.get(key) != value:
                                        passed += 1
                                elif ">=" in v:
                                    key = v.split(">=")[0].strip()
                                    value = p.parseMSymbol(p,
                                        ent, v.split(">=")[1].strip()
                                    )
                                    if p.vars.get(key) >= value:
                                        passed += 1
                                elif ">" in v:
                                    key = v.split(">")[0].strip()
                                    value = MogLibrary.parseMSymbol(p,
                                        ent, v.split(">")[1].strip()
                                    )
                                    if p.vars.get(key) > value:
                                        passed += 1
                                elif "<=" in v:
                                    key = v.split("<=")[0].strip()
                                    value = MogLibrary.parseMSymbol(p,
                                        ent, v.split("<=")[1].strip()
                                    )
                                    if p.vars.get(key) <= value:
                                        passed += 1
                                elif "<" in v:
                                    key = v.split("<")[0].strip()
                                    value = MogLibrary.parseMSymbol(p,
                                        ent, v.split("<")[1].strip()
                                    )
                                    if p.vars.get(key) < value:
                                        passed += 1

                                elif "==" in v:
                                    key = v.split("==")[0].strip()
                                    value = MogLibrary.parseMSymbol(p,
                                        ent, v.split("==")[1].strip()
                                    )
                                    if p.vars.get(key) == value:
                                        passed += 1

                            if eval(f"{passed} {tocheck} {need}"):
                                ent.parse()

                        else:
                            ent.body = MogLibrary.extractFn(p, ent.body)
                            ent.body = MogLibrary.extractCls(p, ent.body)
                            ent.transient = MogLibrary.isTransient(ent.body)
                            
                            MogLibrary.extractComments(ent)
                            if not ent.transient:
                                ent.parse()
                                
                    if ent.valid():
                        out += ent.parsed

                    p.entities.append(ent)

        return out
    
    @staticmethod
    def extractFn(p, entity):
        lines = entity.split("\n")
        do = False
        builder = ""
        name = ""
        for item in lines:
            if item.startswith("*endfn"):
                do = False

            if do:
                builder += f"{item}\n"

            if item.startswith("*fn"):
                do = True
                name = item.split()[1]
                builder += item.replace("*fn", "def") + "(p, *args):\n"

        env = {"p": p}

        if not builder:
            return entity

        try:
            exec(builder, env)
            p.globals[name] = env[name]
            return entity.replace(builder, "")
        except Exception as e:
            print(e)
            return entity.replace(builder, e)
        
    @staticmethod    
    def extractCls(p, entity):
        lines = entity.split("\n")
        do = False
        builder = ""
        name = ""
        for item in lines:
            if item.startswith("*endcls"):
                do = False

            if do:
                builder += f"{item}\n"

            if item.startswith("*cls"):
                do = True
                name = item.split()[1]
                if len(item.split()) > 2 and item.split()[2] in ["extends", "expands"]:
                    builder += f"class {name}(" + item.split()[2] + "):\n"
                else:
                    builder += item.replace("*cls", "class") + ":\n"

        env = {"p": p}

        if not builder:
            return entity

        try:
            exec(builder, env)
            p.globals[name] = env[name]
            return entity.replace(builder, "")
        except Exception as e:
            print(e)
            return entity.replace(builder, e)
        
    @staticmethod
    def isTransient(entity):
        lines = entity.split("\n")
        for line in lines:
            if line == "! transient":
                return True

        return False


class Parser:
    def __init__(self, script, **kargs):
        self.__version = 2
        self.body = script
        self.entities = []
        self.globals = {}
        self.vars = {}
        self.meta_header = ""
        self.lib = MogLibrary #Alias for calling the library externally
        
        # Core globals
        MogLibrary.addGlobal(self, "add", self.add)
        MogLibrary.addGlobal(self, "sub", self.sub)
        MogLibrary.addGlobal(self, "div", self.div)
        MogLibrary.addGlobal(self, "mult", self.mult)
        MogLibrary.addGlobal(self, "var", self.var)
        MogLibrary.addGlobal(self, "local", self.local)
        MogLibrary.addGlobal(self, "choose", self.choose)
        MogLibrary.addGlobal(self, "eval", self.eval)
        MogLibrary.addGlobal(self, "sleep", self.sleep)
        MogLibrary.addGlobal(self, "recheck", self.recheck)
        MogLibrary.addGlobal(self, "if", self.getif)
        MogLibrary.addGlobal(self, "not", self.getnot)
        MogLibrary.addGlobal(self, "print", self.spr)
        MogLibrary.addGlobal(self, "expr", self.expr)
        MogLibrary.addGlobal(self, "art", self.art)
        MogLibrary.addGlobal(self, "textart", self.textart)
        # Extra stuff
        MogLibrary.addGlobal(self, "repl", self.insertReplacement)
  
    def giveRepl(self, name, new):
        if not self.vars.get('repls'):
            self.vars['repls'] = {}
        if not self.vars['repls'].get(name):
            self.vars['repls'][name] = {}

        self.vars['repls'][name]["new"] = new

        
    def spr(self, entity, *args):
        return MogLibrary.spr(args)
    
    def recheck(self, entity, *args):
        return MogLibrary.recheck(self)
    
    def parse(self, *args, **kargs):
        return MogLibrary.parse(self, *args, **kargs)

    def export(self, *args, **kargs):
        return MogLibrary.export(self, *args, **kargs)
    
    def insert(self, body, ind=-1):
        return MogLibrary.insert(self, body, ind=-1)
    
    def addGlobal(self, name, call):
        return MogLibrary.addGlobal(self, name, call)
        
    def read(self, path):
        return MogLibrary.read(self, path)

    def write(self, code):
        return MogLibrary.write(self, code)
                
    def insertReplacement(self, entity, *args):
        if len(args) == 2:
            if self.vars.get("repls", {}).get(args[0], {}).get("new"):
                return self.vars.get("repls", {}).get(args[0]).get("new")
            repls = self.vars.get("repls", {})
            repls[args[0]] = {"alias": args[1], "new": ""}
            self.vars["repls"] = repls
        return f"%{args[0]}% ({args[1].strip()})"

    def choose(self, entity, *args):
        return random.choice(list(args))

    def art(self, entity, *args):
        if not ART_LIB:
            return "`art` module needed for art."

        try:
            if len(args) == 1:
                return art.art(args[0])
            elif len(args) == 2:
                return art.art(args[0], text=args[1])
        except Exception as e:
            return str(e)

    def textart(self, entity, *args):
        if not ART_LIB:
            return "`art` module needed for art."

        try:
            if len(args) == 1:
                return art.text2art(args[0])
            elif len(args) == 2:
                return art.text2art(args[0], args[1])
        except Exception as e:
            return str(e)

    def expr(self, entity, *args):
        if not EXPR_PARSING:
            return "`pyparsing` module needed for expr."
        return str(NumericStringParser().eval(args[0]))

    def getif(self, entity, *args):
        key = args[0].split("=")[0]
        value = args[0].split("=")[1]
        if self.vars.get(key) == value:
            return args[1]

    def getnot(self, entity, *args):
        key = args[0].split("=")[0]
        value = args[0].split("=")[1]
        if self.vars.get(key) != value:
            return args[1]

    def add(self, entity, *args):
        if not self.vars.get(args[0]):
            self.vars[key] = "0"

        i = int(self.vars[args[0]])
        i += int(args[1])
        self.vars[args[0]] = str(i)

    def sub(self, entity, *args):
        if not self.vars.get(args[0]):
            self.vars[args[0]] = "0"

        i = int(self.vars[args[0]])
        i -= int(args[1])
        self.vars[args[0]] = str(i)

    def div(self, entity, *args):
        if not self.vars.get(args[0]):
            self.vars[args[0]] = "0"

        i = int(self.vars[args[0]])
        i /= int(args[1])
        self.vars[args[0]] = str(i)

    def mult(self, entity, *args):
        if not self.vars.get(args[0]):
            self.vars[args[0]] = "0"

        i = int(self.vars[args[0]])
        i *= int(args[1])
        self.vars[args[0]] = str(i)

    def var(self, entity, *args):
        try:
            if "=" in args[0]:
                self.vars[args[0].split("=")[0]] = MogLibrary.parseMSymbol(
                    self, entity, args[0].split("=")[1]
                )
            else:
                if len(args) == 1:
                    return self.vars[args[0]]
                elif len(args) == 2:
                    self.vars[args[0]] = args[1]
                else:
                    self.vars[args[0]] = ":".join(args[1:])
        except Exception as e:
            return f"{e}"

    def local(self, entity, *args):
        try:
            if "=" in args[0]:
                entity.vars[args[0].split("=")[0]] = MogLibrary.parseMSymbol(
                    self, entity, args[0].split("=")[1]
                )
            else:
                if len(args) == 1:
                    return entity.vars[args[0]]
                elif len(args) == 2:
                    entity.vars[args[0]] = args[1]
                else:
                    entity.vars[args[0]] = ":".join(args[1:])
        except Exception as e:
            return f"{e}"

    def sleep(self, entity, *args):
        time.sleep(int(args[0]))

    def eval(self, entity, *args):
        for entry in args:
            body = f'def func(p, args):\n{textwrap.indent(entry, "  ")}'
            env = {"p": self}
            exec(body, env)
            return env["func"](self, [])


class Entity:
    def __init__(self, parser, text):
        self._body = text
        self.body = text
        self.events = []
        self.parser = parser
        self.lines = []
        self.parsed = ""
        self.vars = {}
        self.transient = False
        self.comments = []

    def write(self, code):
        self.body = code
        self.parsed = ""
        return self

    def valid(self):
        if (
            self.parsed != ""
            and self.parsed != " "
            and self.parsed != "	"
            and self.parsed != "\n"
            and not self.transient
        ):
            return True

    def parse(self):
        self.parsed = ""
        for item in self.body.split("\n"):
            if item != "" and item != "\n":
                calls = re.findall("{(.+?)}", item)
                for c in calls:
                    if ":" in c:
                        name = c.split(": ")[0]
                        other = c.split(": ")[1]
                    else:
                        name = c
                        other = ""

                    call = self.parser.globals.get(name)

                    if call:
                        args = MogLibrary.parseMSymbols(self.parser, self, other.split(";"))
                        r = call(self, *args)
                        if r:
                            item = item.replace("{" + c + "}", r)
                        else:
                            item = item.replace(c, "")
                            item = item.replace("{}", "")

                    else:
                        print(f"Invalid call {name} {other}")

                if item != "" and item != " " and item != "	" and item != "\n":
                    self.lines.append(item)

        self.lines = MogLibrary.parseMSymbols(self.parser, self, self.lines)

        for item in self.lines:
            if item != "" and item != " " and item != "	" and item != "\n":
                self.parsed += f"{item}\n"


class NumericStringParser(object):
    def pushFirst(self, strg, loc, toks):
        self.exprStack.append(toks[0])

    def pushUMinus(self, strg, loc, toks):
        if toks and toks[0] == "-":
            self.exprStack.append("unary -")

    def __init__(self):
        """
        expop   :: '^'
        multop  :: '*' | '/'
        addop   :: '+' | '-'
        integer :: ['+' | '-'] '0'..'9'+
        atom    :: PI | E | real | fn '(' expr ')' | '(' expr ')'
        factor  :: atom [ expop factor ]*
        term    :: factor [ multop factor ]*
        expr    :: term [ addop term ]*
        """
        point = Literal(".")
        e = CaselessLiteral("E")
        fnumber = Combine(
            Word("+-" + nums, nums)
            + Optional(point + Optional(Word(nums)))
            + Optional(e + Word("+-" + nums, nums))
        )
        ident = Word(alphas, alphas + nums + "_$")
        plus = Literal("+")
        minus = Literal("-")
        mult = Literal("*")
        div = Literal("/")
        lpar = Literal("(").suppress()
        rpar = Literal(")").suppress()
        addop = plus | minus
        multop = mult | div
        expop = Literal("^")
        pi = CaselessLiteral("PI")
        expr = Forward()
        atom = (
            (
                Optional(oneOf("- +"))
                + (ident + lpar + expr + rpar | pi | e | fnumber).setParseAction(
                    self.pushFirst
                )
            )
            | Optional(oneOf("- +")) + Group(lpar + expr + rpar)
        ).setParseAction(self.pushUMinus)
        # by defining exponentiation as "atom [ ^ factor ]..." instead of
        # "atom [ ^ atom ]...", we get right-to-left exponents, instead of left-to-right
        # that is, 2^3^2 = 2^(3^2), not (2^3)^2.
        factor = Forward()
        factor << atom + ZeroOrMore((expop + factor).setParseAction(self.pushFirst))
        term = factor + ZeroOrMore((multop + factor).setParseAction(self.pushFirst))
        expr << term + ZeroOrMore((addop + term).setParseAction(self.pushFirst))
        # addop_term = ( addop + term ).setParseAction( self.pushFirst )
        # general_term = term + ZeroOrMore( addop_term ) | OneOrMore( addop_term)
        # expr <<  general_term
        self.bnf = expr
        # map operator symbols to corresponding arithmetic operations
        epsilon = 1e-12
        self.opn = {
            "+": operator.add,
            "-": operator.sub,
            "*": operator.mul,
            "/": operator.truediv,
            "^": operator.pow,
        }
        self.fn = {
            "sin": math.sin,
            "cos": math.cos,
            "tan": math.tan,
            "exp": math.exp,
            "abs": abs,
            "trunc": lambda a: int(a),
            "round": round,
            "sgn": lambda a: abs(a) > epsilon and cmp(a, 0) or 0,
        }

    def evaluateStack(self, s):
        op = s.pop()
        if op == "unary -":
            return -self.evaluateStack(s)
        if op in "+-*/^":
            op2 = self.evaluateStack(s)
            op1 = self.evaluateStack(s)
            return self.opn[op](op1, op2)
        elif op == "PI":
            return math.pi  # 3.1415926535
        elif op == "E":
            return math.e  # 2.718281828
        elif op in self.fn:
            return self.fn[op](self.evaluateStack(s))
        elif op[0].isalpha():
            return 0
        else:
            return float(op)

    def eval(self, num_string, parseAll=True):
        self.exprStack = []
        results = self.bnf.parseString(num_string, parseAll)
        val = self.evaluateStack(self.exprStack[:])
        return val
