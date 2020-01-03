import re, random, os, textwrap, asyncio, time

# TODO
"""
{include: filename} 
Replaces with the read text of a file 

{sh: command}
Run bash commands, replaces with output

{http: url; p}
{json: url; key}
replaces with text gotten from the URL, requests.get or asyncio.get
second arg is the block of html to return, or json key
or if its an @arg, run function on url

{expr: expression}
runs math expression (using the calc function used in athenas utils?)


for auto-meta values
$OS - operating system
$PYVER - python version


{PROCESS: name} tag to define a new function processor the parser calls on the body
if
! process: name
is found, run the func on the body and dont parse, cause if the thing itself wants to parse, it can do it there

strip out the replacement system cause it doesnt fit
split it off in to its own function tag
{repl: current; prompt}
adds a new item to a list

Make a parsing engine for Python, go, Ruby, js

Maybe have the remaining kargs passed to the constructor become env vars in the parser
"""
	
class VersionError(Exception):
	pass

class Mog:
	@staticmethod
	def load(**kargs):
		if kargs.get('str'):
			i = kargs['str']
			del kargs['str']
			return Loader.fromString(i, **kargs)
		elif kargs.get('file'):
			i = kargs['file']
			del kargs['file']
			return Loader.fromFile(i, **kargs)
		elif kargs.get('dir'):
			i = kargs['dir']
			del kargs['dir']
			return Scanner.read(i, **kargs)
			
	@staticmethod
	async def loadasync(**kargs):
		kargs['enableAsync'] = True
		return Mog.load(**kargs)	
			
class Loader:
	@staticmethod
	def fromString(code, **kargs):
		if kargs.get('enableAsync'):
			del kargs['enableAsync']
			return AsyncParser(code, **kargs)
		else:
			return Parser(code, **kargs)

	@staticmethod
	def fromFile(filepath, **kargs):
		with open(filepath, 'r') as f:
			if kargs.get('enableAsync'):
				del kargs['enableAsync']
				return AsyncParser(f.read(), **kargs)
			else:
				return Parser(f.read(), **kargs)
				
class Scanner:
	@staticmethod
	def read(path, **kargs):
		if not kargs.get('exts'):
			exts = ['txt']
		else:
			exts = kargs['exts']
			del kargs['exts']
			
		p = []
		doAsync = False
		if kargs.get('enableAsync'):
			del kargs['enableAsync']
			doAsync = True
		for file in os.listdir(path):
			do = False
			for item in exts:
				if str(file).endswith(item):
					do = True
			if do:
				with open(f"{path}{file}", 'r') as f:
					if doAsync:
						p.append(AsyncParser(f.read(), **kargs))
					else:
						p.append(Parser(f.read(), **kargs))
		return p
					
class Parser:
	def __init__(self, script, **kargs):
		self.__version = 1
		self.body = script
		self.entities = []
		self.globals = {}
		self.vars = {}
		self.meta_header = ""
		
		#Core globals
		self.addGlobal('add', self.add)
		self.addGlobal('sub', self.sub)
		self.addGlobal('div', self.div)
		self.addGlobal('mult', self.mult)
		self.addGlobal('var', self.var)
		self.addGlobal('local', self.local)
		self.addGlobal('choose', self.choose)
		self.addGlobal('eval', self.eval)
		self.addGlobal('sleep', self.sleep)	
		self.addGlobal('recheck', self.recheck)	
		self.addGlobal('if', self.getif)
		self.addGlobal('not', self.getnot)		
		self.addGlobal('print', self.spr)
		
		#Extra stuff
		self.addGlobal('repl', self.insertReplacement)	
		
	def spr(self, p, *args):
		return ' '.join(args)
		
	def parseMSymbol(self, entity, word):
		if word.startswith("$"): #from vars
			v = word.replace("$", '')
			end = None
			if v[-1] in [".", "?", "!", ";", ":", "~", ","]:
				end = v[-1]
				v = v.replace(end, '')
			fin = self.vars.get(v, word)
			if end:
				fin = fin+end
			return fin
			
		elif word.startswith("?"): #from entity locals
			v = word.replace("?", '')
			end = None
			if v[-1] in [".", "?", "!", ";", ":", "~", ","]:
				end = v[-1]
				v = v.replace(end, '')
			fin = entity.vars.get(v, word)
			if end:
				fin = fin+end
			return fin
		else:
			return word
			
	def parseMSymbols(self, entity, ls):
		out = []
		for item in ls:

			phr = item.split(" ")

			for word in phr:
				item = item.replace(word, self.parseMSymbol(entity, word))

			out.append(item)		
		return out				
		
	def write(self, code):
		self.body += f"\n{code}"

	def read(self, filepath):
		with open(filepath, 'r') as f:
				self.body += f.read()
	
	def addGlobal(self, name, call):
		self.globals[name.lower()] = call

	def insertReplacement(self, p, *args):
		if len(args) == 2:
			if p.parser.vars.get('repls', {}).get(args[0], {}).get('new'):
				return p.parser.vars.get('repls', {}).get(args[0]).get('new')
			repls = p.parser.vars.get('repls', {})
			repls[args[0]] = {'alias': args[1], 'new': ''}
			p.parser.vars['repls'] = repls
		return f'%{args[0]}% ({args[1].strip()})'
		
	def giveRepl(self, name, new):
		self.vars.get('repls', {}).get(name, {})['new'] = new
		
	def choose(self, parser, *args):
		return random.choice(list(args))
	
	def recheck(self, parser, *args):
		self.parse(partial=True)
	
	def getif(self, parser, *args):
		key = args[0].split("=")[0]
		value = args[0].split("=")[1]
		if self.vars.get(key) == value:
			return args[1]
			
	def getnot(self, parser, *args):
		key = args[0].split("=")[0]
		value = args[0].split("=")[1]
		if self.vars.get(key) != value:
			return args[1]	
							
	def add(self, parser, *args):
		if not self.vars.get(args[0]):
			self.vars[key] = "0"
		
		i = int(self.vars[args[0]])
		i += int(args[1])
		self.vars[args[0]] = str(i)
		
	def sub(self, parser, *args):
		if not self.vars.get(args[0]):
			self.vars[args[0]] = "0"
		
		i = int(self.vars[args[0]])
		i -= int(args[1])
		self.vars[args[0]] = str(i)	
	
	def div(self, parser, *args):
		if not self.vars.get(args[0]):
			self.vars[args[0]] = "0"
		
		i = int(self.vars[args[0]])
		i /= int(args[1])
		self.vars[args[0]] = str(i)	
		
	def mult(self, parser, *args):
		if not self.vars.get(args[0]):
			self.vars[args[0]] = "0"
		
		i = int(self.vars[args[0]])
		i *= int(args[1])
		self.vars[args[0]] = str(i)	
	
	def var(self, parser, *args):
		try:
			if "=" in args[0]:
				self.vars[args[0].split("=")[0]] = self.parseMSymbol(parser, args[0].split("=")[1])
			else:
				if len(args) == 1:
					return self.vars[args[0]]
				elif len(args) == 2:
					self.vars[args[0]] = args[1]
				else:
					self.vars[args[0]] = ':'.join(args[1:])	
		except Exception as e:
			return f"{e}"
				
	def local(self, parser, *args):
		try:
			if "=" in args[0]:
				parser.vars[args[0].split("=")[0]] = self.parseMSymbol(parser, args[0].split("=")[1])
			else:
				if len(args) == 1:
					return parser.vars[args[0]]
				elif len(args) == 2:
					parser.vars[args[0]] = args[1]
				else:
					parser.vars[args[0]] = ':'.join(args[1:])	
		except Exception as e:
			return f"{e}"
			
	def sleep(self, parser, *args):
		time.sleep(int(args[0]))	
		
	def eval(self, parser, *args):
		for entry in args:
			body = f'def func(p, args):\n{textwrap.indent(entry, "  ")}'
			env = {'p': self}
			exec(body, env)
			return env['func'](parser, [])
			
	def walk(self):
		out = ""
		for ent in self.entities:
			if not ent.valid():
				calls = re.findall('{(.+?)}', ent.body)	
				if len(calls) > 0 and calls[0].startswith("IF"):
					ent.body = ent.body.replace("{"+calls[0]+"}", '')
					v = calls[0].split(": ")[1]
					key = v.split("=")[0]
					value = v.split("=")[1]
					if self.vars.get(key) == value:
						ent.parse()
				elif len(calls) > 0 and calls[0].startswith("NOT"):
					ent.body = ent.body.replace("{"+calls[0]+"}", '')
					v = calls[0].split(": ")[1]
					key = v.split("=")[0]
					value = v.split("=")[1]
					if self.vars.get(key) == value:
						ent.parse()
				else:
					ent.parse()
				if ent.valid():
					out += ent.parsed
		return out		
	
	def export(self, **kargs):
		body = ""
		if kargs.get('update_meta'):
			body = "! META\n"
			for item in self.vars:
				body += f"{item}: {str(self.vars[item])}\n"
		else:
			body = self.meta_header
			
		for item in self.entities:
			if item.body.startswith("\n"):
				body += f"---{item._body}"
			else:
				body += f"---\n{item._body}"
		if kargs.get('file'):	
			with open(kargs['file'], 'w+') as f:
				f.write(body)
		
		return body
		
	def insert(self, body, ind=-1):
		ent = Entity(self, body)
		
		if ind < 0:
			self.entities.append(ent)
		else:
			self.entities.insert(ind, ent)
	
	def extractComments(self, entity):
		body = entity.body.split("\n")
		comments = []
		for line in entity.body.split("\n"):
			if line.startswith("//"):
				comments.append(line[2:])
				body.remove(line)
			elif "//" in line:
				comments.append(line.split("//")[1])
				body[body.index(line)] = line.replace("//"+line.split("//")[1], '')
		entity.body = '\n'.join(body)
		entity.comments = comments

	def parseDefPrps(self, prop):
		if prop == "$RNG":
			return str(random.random())
		elif prop == "$USER":
			return os.environ.get('USER')
		elif prop == "$HOME":
			return os.environ.get('HOME')
		else:
			return prop
							
	def parse(self, partial=False):
		self.entities = []
		out = ""
		
		for entry in self.body.split("---"):
			transient = False
			if entry.split("\n")[0] == "! META":
				self.meta_header = entry
				l = entry.replace("! META", "").split("\n")
				for item in l:
					if item != "\n" and item != "":
						self.vars[item.split(": ")[0]] = self.parseDefPrps(item.split(": ")[1])
				
				if self.vars.get('version'):
					v = int(self.vars['version'])
					if v != self.__version:
						raise VersionError("Versions mismatch, script may be incompatible.")					
				
			else:
				calls = re.findall('{(.+?)}', entry)
				if len(calls) > 0 and calls[0].startswith("CODE: "):
					entry = entry.replace("{"+calls[0]+"}", '')
					name = calls[0].split(": ")[1]
					
					body = f'def func(p, args):\n{textwrap.indent(entry, "  ")}'
					env = {'p': self}
					exec(body, env)
					self.addGlobal(name, env['func'])
				
				else:
					ent = Entity(self, entry)

					if not partial:
						if len(calls) > 0 and calls[0].startswith("IF"):
							ent.body = entry.replace("{"+calls[0]+"}", '')
							val = calls[0].split(": ")[1]
							checks = val.split(";")
							passed = 0
							
							if checks[0].startswith("need"):
								x = checks[0].split()
								tocheck = x[1]
								need = int(x[2])
								checks.pop(0)
							else:
								tocheck = "="
								need = len(checks)
								
							for v in checks:

								key = v.split("=")[0].strip()
								value = v.split("=")[1].strip()
								if "!=" in v:
									key = v.split("!=")[0].strip()
									value = v.split("!=")[1].strip()
									if self.vars.get(key) != value:
										passed += 1
								elif ">=" in v:
									key = v.split(">=")[0].strip()
									value = v.split(">=")[1].strip()
									if self.vars.get(key) >= value:
										passed += 1
								elif ">" in v:
									key = v.split(">")[0].strip()
									value = v.split(">")[1].strip()
									if self.vars.get(key) > value:
										passed += 1
								elif "<=" in v:
									key = v.split("<=")[0].strip()
									value = v.split("<=")[1].strip()
									if self.vars.get(key) <= value:
										passed += 1
								elif "<" in v:
									key = v.split("<")[0].strip()
									value = v.split("<")[1].strip()
									if self.vars.get(key) < value:
										passed += 1

								elif "==" in v:
									key = v.split("==")[0].strip()
									value = v.split("==")[1].strip()
									if self.vars.get(key) == value:
										passed += 1
								
							if eval(f"{passed} {tocheck} {need}"):
								ent.parse()
								
						else:
							ent.body = self.extractFn(ent.body)
							ent.body = self.extractCls(ent.body)
							ent.transient = self.isTransient(ent.body)
							self.extractComments(ent)
							if not ent.transient:
								ent.parse()
					if ent.valid():
						out += ent.parsed
						
					self.entities.append(ent)

		return out

	def extractFn(self, entity):
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
				builder += item.replace("*fn", 'def')+"(p, *args):\n"
				
		env = {'p': self}
		
		if not builder:
			return entity
			
		try:
			exec(builder, env)
			self.globals[name] = env[name]
			return entity.replace(builder, '')
		except Exception as e:
			print(e)
			return entity.replace(builder, e)
			
	def extractCls(self, entity):
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
				if len(item.split()) > 2 and item.split()[2] in ['extends', 'expands']:
					builder += f"class {name}("+item.split()[2]+"):\n"
				else:
					builder += item.replace("*cls", 'class')+":\n"
				
		env = {'p': self}
		
		if not builder:
			return entity
			
		try:
			exec(builder, env)
			self.globals[name] = env[name]
			return entity.replace(builder, '')
		except Exception as e:
			print(e)
			return entity.replace(builder, e)
			
	def isTransient(self, entity):
		lines = entity.split("\n")	
		for line in lines:
			if line == "! transient":
				return True
		
		return False
				
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
		if self.parsed != "" and self.parsed != " " and self.parsed != "	" and self.parsed != "\n" and not self.transient:
			return True
			
	def parse(self):
		self.parsed = ""
		for item in self.body.split("\n"):
			if item != "" and item != "\n":
				calls = re.findall('{(.+?)}', item)
				for c in calls:
					if ":" in c:
						name = c.split(": ")[0]
						other = c.split(": ")[1]
					else:
						name = c
						other = ""

					call = self.parser.globals.get(name)
					
					if call:	
						args = self.parser.parseMSymbols(self, other.split(";"))
						r = call(self, *args)
						if r:
							item = item.replace("{"+c+"}", r)
						else:
							item = item.replace(c, '')
							item = item.replace("{}", '')
					
					else:
						print(f"Invalid call {name} {other}")
				
				if item != "" and item != " " and item != "	" and item != "\n":
					self.lines.append(item)
		
		self.lines = self.parser.parseMSymbols(self, self.lines)
			
		for item in self.lines:
			if item != "" and item != " " and item != "	" and item != "\n":
				self.parsed += f"{item}\n"	
				
		

class AsyncParser:
	def __init__(self, script, **kargs):
		self.__version = 1
		
		self.body = script
		self.entities = []
		self.globals = {}
		self.vars = {}
		self.meta_header = ""
		self.addGlobal('add', self.add)
		self.addGlobal('sub', self.sub)
		self.addGlobal('div', self.div)
		self.addGlobal('mult', self.mult)
		self.addGlobal('var', self.var)
		self.addGlobal('local', self.local)
		self.addGlobal('choose', self.choose)
		self.addGlobal('eval', self.eval)
		self.addGlobal('sleep', self.sleep)
		self.addGlobal('recheck', self.recheck)	
		self.addGlobal('if', self.getif)
		self.addGlobal('not', self.getnot)		
		self.addGlobal('print', self.spr)
			
		#Extras
		self.addGlobal('repl', self.insertReplacement)
		
	async def spr(self, p, *args):
		return ' '.join(args)
		
	async def parseMSymbol(self, entity, word):
		if word.startswith("$"): #from vars
			v = word.replace("$", '')
			end = None
			if v[-1] in [".", "?", "!", ";", ":", "~", ","]:
				end = v[-1]
				v = v.replace(end, '')
			fin = self.vars.get(v, word)
			if end:
				fin = fin+end
			return fin
			
		elif word.startswith("?"): #from entity locals
			v = word.replace("?", '')
			end = None
			if v[-1] in [".", "?", "!", ";", ":", "~", ","]:
				end = v[-1]
				v = v.replace(end, '')
			fin = entity.vars.get(v, word)
			if end:
				fin = fin+end
			return fin
		else:
			return word
			
	async def parseMSymbols(self, entity, ls):
		out = []
		for item in ls:

			phr = item.split(" ")

			for word in phr:
				item = item.replace(word, await self.parseMSymbol(entity, word))

			out.append(item)		
		return out			
	
	def write(self, code):
		self.body += f"\n{code}"

	def read(self, filepath):
		with open(filepath, 'r') as f:
				self.body += f.read()
	
	def addGlobal(self, name, call):
		self.globals[name.lower()] = call

	async def insertReplacement(self, p, *args):
		if len(args) == 2:
			if p.parser.vars.get('repls', {}).get(args[0], {}).get('new'):
				return p.parser.vars.get('repls', {}).get(args[0]).get('new')
			repls = p.parser.vars.get('repls', {})
			repls[args[0]] = {'alias': args[1], 'new': ''}
			p.parser.vars['repls'] = repls
		return f'%{args[0]}% ({args[1].strip()})'
		
	async def giveRepl(self, name, new):
		self.vars.get('repls', {}).get(name, {})['new'] = new
	
	async def getif(self, parser, *args):
		key = args[0].split("=")[0]
		value = args[0].split("=")[1]
		if self.vars.get(key) == value:
			return args[1]
			
	async def getnot(self, parser, *args):
		key = args[0].split("=")[0]
		value = args[0].split("=")[1]
		if self.vars.get(key) != value:
			return args[1]	
				
	async def choose(self, parser, *args):
		return random.choice(list(args))
	
	async def sleep(self, parser, *args):
		await asyncio.sleep(int(args[0]))	
	
	async def recheck(self, parser, *args):
		await self.parse(partial=True)
					
	async def add(self, parser, *args):
		if not self.vars.get(args[0]):
			self.vars[key] = "0"
		
		i = int(self.vars[args[0]])
		i += int(args[1])
		self.vars[args[0]] = str(i)
		
	async def sub(self, parser, *args):
		if not self.vars.get(args[0]):
			self.vars[args[0]] = "0"
		
		i = int(self.vars[args[0]])
		i -= int(args[1])
		self.vars[args[0]] = str(i)	
	
	async def div(self, parser, *args):
		if not self.vars.get(args[0]):
			self.vars[args[0]] = "0"
		
		i = int(self.vars[args[0]])
		i /= int(args[1])
		self.vars[args[0]] = str(i)	
		
	async def mult(self, parser, *args):
		if not self.vars.get(args[0]):
			self.vars[args[0]] = "0"
		
		i = int(self.vars[args[0]])
		i *= int(args[1])
		self.vars[args[0]] = str(i)	
		
	async def var(self, parser, *args):
		try:
			if "=" in args[0]:
				self.vars[args[0].split("=")[0]] = await self.parseMSymbol(parser, args[0].split("=")[1])
			else:
				if len(args) == 1:
					return self.vars[args[0]]
				elif len(args) == 2:
					self.vars[args[0]] = args[1]
				else:
					self.vars[args[0]] = ':'.join(args[1:])	
		except Exception as e:
			return f"{e}"
				
	async def local(self, parser, *args):
		try:
			if "=" in args[0]:
				parser.vars[args[0].split("=")[0]] = await self.parseMSymbol(parser, args[0].split("=")[1])
			else:
				if len(args) == 1:
					return parser.vars[args[0]]
				elif len(args) == 2:
					parser.vars[args[0]] = args[1]
				else:
					parser.vars[args[0]] = ':'.join(args[1:])	
		except Exception as e:
			return f"{e}"
		
	async def eval(self, parser, *args):
		for entry in args:
			body = f'async def func(p, args):\n{textwrap.indent(entry, "  ")}'
			env = {'p': self}
			exec(body, env)
			return await env['func'](parser, [])
	
	async def walk(self):
		out = ""
		for ent in self.entities:
			if not ent.valid():
				calls = re.findall('{(.+?)}', ent.body)	
				if len(calls) > 0 and calls[0].startswith("IF"):
					ent.body = ent.body.replace("{"+calls[0]+"}", '')
					v = calls[0].split(": ")[1]
					key = v.split("=")[0]
					value = v.split("=")[1]
					if self.vars.get(key) == value:
						await ent.parse()
				elif len(calls) > 0 and calls[0].startswith("NOT"):
					ent.body = ent.body.replace("{"+calls[0]+"}", '')
					v = calls[0].split(": ")[1]
					key = v.split("=")[0]
					value = v.split("=")[1]
					if self.vars.get(key) == value:
						await ent.parse()
				else:
					await ent.parse()
				if ent.valid():
					out += ent.parsed
		return out		
	
	def export(self, **kargs):
		body = ""
		if kargs.get('update_meta'):
			body = "! META\n"
			for item in self.vars:
				body += f"{item}: {str(self.vars[item])}\n"
		else:
			body = self.meta_header
			
		for item in self.entities:
			if item.body.startswith("\n"):
				body += f"---{item._body}"
			else:
				body += f"---\n{item._body}"
		if kargs.get('file'):	
			with open(kargs['file'], 'w+') as f:
				f.write(body)
		
		return body
			
	async def insert(self, body, ind=-1):
		ent = AsyncEntity(self, body)
		
		if ind < 0:
			self.entities.append(ent)
		else:
			self.entities.insert(ind, ent)

	def extractComments(self, entity):
		body = entity.body.split("\n")
		comments = []
		for line in entity.body.split("\n"):
			if line.startswith("//"):
				comments.append(line[2:])
				body.remove(line)
			elif "//" in line:
				comments.append(line.split("//")[1])
				body[body.index(line)] = line.replace("//"+line.split("//")[1], '')
		entity.body = '\n'.join(body)
		entity.comments = comments
		
	def parseDefPrps(self, prop):
		if prop == "$RNG":
			return str(random.random())
		elif prop == "$USER":
			return os.environ.get('USER')
		elif prop == "$HOME":
			return os.environ.get('HOME')
		else:
			return prop
					
	async def parse(self, partial=False):
		out = ""
		self.entities = []
		for entry in self.body.split("---"):
			
			if entry.split("\n")[0] == "! META":
				self.meta_header = entry
				l = entry.replace("! META", "").split("\n")
				for item in l:
					if item != "\n" and item != "":
						self.vars[item.split(": ")[0]] = self.parseDefPrps(item.split(": ")[1])
				
				if self.vars.get('version'):
					v = int(self.vars['version'])
					if v != self.__version:
						raise VersionError("Versions mismatch, script may be incompatible.")
						
				
			else:
				calls = re.findall('{(.+?)}', entry)
				if len(calls) > 0 and calls[0].startswith("CODE: "):
					entry = entry.replace("{"+calls[0]+"}", '')
					name = calls[0].split(": ")[1]

					body = f'async def func(p, args):\n{textwrap.indent(entry, "  ")}'
		
					env = {'p': self}
					exec(body, env)
					self.addGlobal(name, env['func'])					
				else:
					ent = AsyncEntity(self, entry)
					if not partial:
						if len(calls) > 0 and calls[0].startswith("IF"):
							ent.body = entry.replace("{"+calls[0]+"}", '')
							val = calls[0].split(": ")[1]
							checks = val.split(";")
							passed = 0
							
							if checks[0].startswith("need"):
								x = checks[0].split()
								tocheck = x[1]
								need = int(x[2])
								checks.pop(0)
							else:
								tocheck = "="
								need = len(checks)
								
							print(checks)	
							for v in checks:
								print(f"Checking {v}")
								key = v.split("=")[0].strip()
								value = v.split("=")[1].strip()
								if "!=" in v:
									key = v.split("!=")[0].strip()
									value = v.split("!=")[1].strip()
									if self.vars.get(key) != value:
										passed += 1
								elif ">=" in v:
									key = v.split(">=")[0].strip()
									value = v.split(">=")[1].strip()
									if self.vars.get(key) >= value:
										passed += 1
								elif ">" in v:
									key = v.split(">")[0].strip()
									value = v.split(">")[1].strip()
									if self.vars.get(key) > value:
										passed += 1
								elif "<=" in v:
									key = v.split("<=")[0].strip()
									value = v.split("<=")[1].strip()
									if self.vars.get(key) <= value:
										passed += 1
								elif "<" in v:
									key = v.split("<")[0].strip()
									value = v.split("<")[1].strip()
									if self.vars.get(key) < value:
										passed += 1

								elif "==" in v:
									key = v.split("==")[0].strip()
									value = v.split("==")[1].strip()
									if self.vars.get(key) == value:
										passed += 1
								print(f"Check: {passed}/{need} {tocheck}")
								
							if eval(f"{passed} {tocheck} {need}"):
								await ent.parse()

						else:
							ent.body = self.extractFn(ent.body)
							ent.body = self.extractCls(ent.body)
							ent.transient = self.isTransient(ent.body)
							self.extractComments(ent)
							if not ent.transient:
								await ent.parse()
							
					if ent.valid():
						out += ent.parsed
					
					self.entities.append(ent)
		return out

	def extractFn(self, entity):
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
				builder += item.replace("*fn", 'async def')+"(p, *args):\n"
				
		env = {'p': self}
		
		if not builder:
			return entity
			
		try:
			exec(builder, env)
			self.globals[name] = env[name]
			return entity.replace(builder, '')
		except Exception as e:
			print(e)
			return entity.replace(builder, e)
			
	def extractCls(self, entity):
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
				if len(item.split()) > 2 and item.split()[2] in ['extends', 'expands']:
					builder += f"class {name}("+item.split()[2]+"):\n"
				else:
					builder += item.replace("*cls", 'class')+":\n"
				
		env = {'p': self}
		
		if not builder:
			return entity
			
		try:
			exec(builder, env)
			self.globals[name] = env[name]
			return entity.replace(builder, '')
		except Exception as e:
			print(e)
			return entity.replace(builder, e)
			
	def isTransient(self, entity):
		lines = entity.split("\n")	
		for line in lines:
			if line == "! transient":
				return True
		
		return False

class AsyncEntity:
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
		if self.parsed != "" and self.parsed != " " and self.parsed != "	" and self.parsed != "\n" and not self.transient:
			return True
			
	async def parse(self):
		self.parsed = ""
		for item in self.body.split("\n"):
			if item != "" and item != "\n":
				calls = re.findall('{(.+?)}', item)
				for c in calls:
					if ":" in c:
						name = c.split(": ")[0]
						other = c.split(": ")[1]
					else:
						name = c
						other = ""

					call = self.parser.globals.get(name)
					
					if call:	
						args = await self.parser.parseMSymbols(self, other.split(";"))
						r = await call(self, *args)
		
						if r:
							item = item.replace("{"+c+"}", r)
						else:
							item = item.replace(c, '')
							item = item.replace("{}", '')
					
					else:
						print(f"Invalid call {name} {other}")
					
				
				if item != "" and item != " " and item != "	" and item != "\n":
					self.lines.append(item)
		
		#print(f"LINES: {self.lines}")
		self.lines = await self.parser.parseMSymbols(self, self.lines)
		#print(f"LINES AFT: {self.lines}")
		
		for item in self.lines:
			if item != "" and item != " " and item != "	" and item != "\n":
				self.parsed += f"{item}\n"	
				
		
