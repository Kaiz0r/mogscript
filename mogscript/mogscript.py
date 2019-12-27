import re, random, os, textwrap

class VersionError(Exception):
	pass
	
class Loader:
	@staticmethod
	def fromString(code, **kargs):
		if kargs.get('enableAsync'):
			del kargs['enableAsync']
			return AsyncParser(code, kargs)
		else:
			return Parser(code, kargs)

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
		for file in os.listdir(path):
			do = False
			for item in exts:
				if str(file).endswith(item):
					do = True
			if do:
				with open(f"{path}{file}", 'r') as f:
					if kargs.get('enableAsync'):
						del kargs['enableAsync']
						p.append(AsyncParser(f.read(), **kargs))
					else:
						p.append(Parser(f.read(), **kargs))
		return p
					
class Parser:
	def __init__(self, script, **kargs):
		self.__version = 1
		self.body = script
		self.rep = {}
		self.parsed = []
		self.globals = {}
		self.vars = {}
		self.asyncs = []
		self.addGlobal('add', self.add)
		self.addGlobal('sub', self.sub)
		self.addGlobal('div', self.div)
		self.addGlobal('mult', self.mult)
		self.addGlobal('set', self.set)
		self.addGlobal('get', self.get)
		self.addGlobal('choose', self.choose)
		self.addGlobal('eval', self.eval)
			
	def stream(self, code):
		self.body += f"\n{code}"

	def read(self, filepath):
		with open(filepath, 'r') as f:
				self.body += f.read()
	
	def addGlobal(self, name, call):
		self.globals[name.lower()] = call
	
	def choose(self, parser, *args):
		return random.choice(list(args))
		
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
					
	def set(self, parser, *args):
		try:
			self.vars[args[0]] = args[1]
		except:
			self.vars[args[0].split("=")[0]] = args[0].split("=")[1]
			
	def get(self, parser, *args):
		return self.vars[args[0]]
		
	def eval(self, parser, *args):
		for entry in args:
			body = f'def func(p, args):\n{textwrap.indent(entry, "  ")}'
			env = {'p': self}
			exec(body, env)
			return env['func'](self, [])
						
	def parse(self, partial=False):
		self.parsed = []
		for entry in self.body.split("---"):
			if entry.split("\n")[0] == "{META}":
				l = entry.replace("{META}", "").split("\n")
				for item in l:
					if item != "\n" and item != "":
						self.vars[item.split(": ")[0]] = item.split(": ")[1]
				
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
						ent.parse()
					self.parsed.append(ent)
						
	def addReplacement(self, key, new):
		self.rep[key.lower()] = new

	def replacing(self, line):
		out = line
		calls = re.findall('%(.+?)%', line)
		for item in calls:
			if "=" in item:
				n = item.split("=")[0]
			else:
				n = item
			if self.rep.get(n):		
				if type(self.rep[n]) == str:
					out = out.replace(f"%{item}%", self.rep[n])
				else:
					out = out.replace(f"%{item}%", self.rep[n](self, item))
				
		return out
				
class Entity:
	def __init__(self, parser, text):
		self.body = text
		self.events = []
		self.parser = parser
		self.lines = []
		self.parsed = ""
	
	def poll(self):
		replacements = []
		for item in self.lines:
			calls = re.findall('%(.+?)%', item)
			for c in calls:
				if "=" in c:
					name = c.split("=")[1]
					alias = c.split("=")[0]
				else:
					name = c
					alias = c	
					
				replacements.append({'name': name, 'alias': alias})
		return replacements
	
	def valid(self):
		if self.parsed != "" and self.parsed != " " and self.parsed != "	" and self.parsed != "\n":
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

					call = None
					if name == "var":
						call = self.parser.get
					elif name == "set":
						call = self.parser.set	
					elif name == "add":
						call = self.parser.add	
					elif name == "sub":
						call = self.parser.sub	
					elif name == "eval":
						call = self.parser.eval		
					else:
						call = self.parser.globals.get(name)
					
					if call:	
						r = call(self.parser, *other.split(";"))
						if r:
							item = item.replace("{"+c+"}", r)
						else:
							item = item.replace(c, '')
							item = item.replace("{}", '')
					
					else:
						print(f"Invalid call {name} {other}")
				line = self.parser.replacing(item)
				
				if line != "" and item != " " and item != "	" and line != "\n":
					self.lines.append(line)
			
		for item in self.lines:
			if line != "" and item != " " and item != "	" and line != "\n":
				self.parsed += f"{item}\n"	
				
		

class AsyncParser:
	def __init__(self, script, **kargs):
		self.__version = 1
		
		self.body = script
		self.rep = {}
		self.parsed = []
		self.globals = {}
		self.vars = {}
		self.asyncs = []
		self.addGlobal('add', self.add)
		self.addGlobal('sub', self.sub)
		self.addGlobal('div', self.div)
		self.addGlobal('mult', self.mult)
		self.addGlobal('set', self.set)
		self.addGlobal('get', self.get)
		self.addGlobal('choose', self.choose)
		self.addGlobal('eval', self.eval)
			
	def stream(self, code):
		self.body += f"\n{code}"

	def read(self, filepath):
		with open(filepath, 'r') as f:
				self.body += f.read()
	
	def addGlobal(self, name, call):
		self.globals[name.lower()] = call
	
	async def choose(self, parser, *args):
		return random.choice(list(args))
		
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
					
	async def set(self, parser, *args):
		try:
			self.vars[args[0]] = args[1]
		except:
			self.vars[args[0].split("=")[0]] = args[0].split("=")[1]
			
	async def get(self, parser, *args):
		return self.vars[args[0]]
		
	async def eval(self, parser, *args):
		for entry in args:
			body = f'async def func(p, args):\n{textwrap.indent(entry, "  ")}'
			env = {'p': self}
			exec(body, env)
			return await env['func'](self, [])
						
	async def parse(self, partial=False):
		self.parsed = []
		for entry in self.body.split("---"):
			if entry.split("\n")[0] == "{META}":
				l = entry.replace("{META}", "").split("\n")
				for item in l:
					if item != "\n" and item != "":
						self.vars[item.split(": ")[0]] = item.split(": ")[1]
				
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
						await ent.parse()
					self.parsed.append(ent)
						
	def addReplacement(self, key, new):
		self.rep[key.lower()] = new

	def replacing(self, line):
		out = line
		calls = re.findall('%(.+?)%', line)
		for item in calls:
			if "=" in item:
				n = item.split("=")[0]
			else:
				n = item
			if self.rep.get(n):		
				if type(self.rep[n]) == str:
					out = out.replace(f"%{item}%", self.rep[n])
				else:
					out = out.replace(f"%{item}%", self.rep[n](self, item))
				
		return out
				
class AsyncEntity:
	def __init__(self, parser, text):
		self.body = text
		self.events = []
		self.parser = parser
		self.lines = []
		self.parsed = ""
	
	def poll(self):
		replacements = []
		for item in self.lines:
			calls = re.findall('%(.+?)%', item)
			for c in calls:
				if "=" in c:
					name = c.split("=")[1]
					alias = c.split("=")[0]
				else:
					name = c
					alias = c	
					
				replacements.append({'name': name, 'alias': alias})
		return replacements
	
	def valid(self):
		if self.parsed != "" and self.parsed != " " and self.parsed != "	" and self.parsed != "\n":
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

					call = None
					if name == "var":
						call = self.parser.get
					elif name == "set":
						call = self.parser.set	
					elif name == "add":
						call = self.parser.add	
					elif name == "sub":
						call = self.parser.sub	
					elif name == "eval":
						call = self.parser.eval		
					else:
						call = self.parser.globals.get(name)
					
					if call:	
						r = await call(self.parser, *other.split(";"))
		
						if r:
							item = item.replace("{"+c+"}", r)
						else:
							item = item.replace(c, '')
							item = item.replace("{}", '')
					
					else:
						print(f"Invalid call {name} {other}")
				line = self.parser.replacing(item)
				
				if line != "" and item != " " and item != "	" and line != "\n":
					self.lines.append(line)
			
		for item in self.lines:
			if line != "" and item != " " and item != "	" and line != "\n":
				self.parsed += f"{item}\n"	
				
		
