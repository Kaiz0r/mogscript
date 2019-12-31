import re, random, os, textwrap, asyncio, time

# TODO
# Maybe have the remaining kargs passed to the constructor become env vars in the parser
"""
Todo
{include: filename} 
Replaces with the read text of a file 

{sh: command}
Run bash commands, replaces with output

{http: url; p}
{json: url; key}
replaces with text gotten from the URL, requests.get or asyncio.get
second arg is the block of html to return, or json key
or if its an @arg, run function on url

Add tag to turn block in to a class

Make a parsing engine for Python, go, Ruby, js

implement comments in code

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
			body = "{META}\n"
			for item in self.vars:
				body += f"{item}: {str(self.vars[item])}\n"
		else:
			body = self.meta_header
			
		for item in self.entities:
			if item.body.startswith("\n"):
				body += f"---{item.body}"
			else:
				body += f"---\n{item.body}"
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
			
	def parse(self, partial=False):
		self.entities = []
		out = ""
		for entry in self.body.split("---"):
			if entry.split("\n")[0] == "{META}":
				self.meta_header = entry
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
						if len(calls) > 0 and calls[0].startswith("IF"):
							ent.body = entry.replace("{"+calls[0]+"}", '')
							v = calls[0].split(": ")[1]
							key = v.split("=")[0]
							value = v.split("=")[1]
							if self.vars.get(key) == value:
								ent.parse()
						elif len(calls) > 0 and calls[0].startswith("NOT"):
							ent.body = entry.replace("{"+calls[0]+"}", '')
							v = calls[0].split(": ")[1]
							key = v.split("=")[0]
							value = v.split("=")[1]
							if self.vars.get(key) == value:
								ent.parse()
						else:
							ent.parse()
					if ent.valid():
						out += ent.parsed
					self.entities.append(ent)
		return out

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
		self.vars = {}
	
	def write(self, code):
		self.body = code
		self.parsed = ""
		return self
			
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
				line = self.parser.replacing(item)
				
				if line != "" and item != " " and item != "	" and line != "\n":
					self.lines.append(line)
		
		self.lines = self.parser.parseMSymbols(self, self.lines)
			
		for item in self.lines:
			if line != "" and item != " " and item != "	" and line != "\n":
				self.parsed += f"{item}\n"	
				
		

class AsyncParser:
	def __init__(self, script, **kargs):
		self.__version = 1
		
		self.body = script
		self.rep = {}
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
			body = "{META}\n"
			for item in self.vars:
				body += f"{item}: {str(self.vars[item])}\n"
		else:
			body = self.meta_header
			
		for item in self.entities:
			if item.body.startswith("\n"):
				body += f"---{item.body}"
			else:
				body += f"---\n{item.body}"
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
			
	async def parse(self, partial=False):
		out = ""
		self.entities = []
		for entry in self.body.split("---"):
			
			if entry.split("\n")[0] == "{META}":
				self.meta_header = entry
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
						if len(calls) > 0 and calls[0].startswith("IF"):
							ent.body = entry.replace("{"+calls[0]+"}", '')
							v = calls[0].split(": ")[1]
							key = v.split("=")[0]
							value = v.split("=")[1]
							if self.vars.get(key) == value:
								await ent.parse()
						elif len(calls) > 0 and calls[0].startswith("NOT"):
							ent.body = entry.replace("{"+calls[0]+"}", '')
							v = calls[0].split(": ")[1]
							key = v.split("=")[0]
							value = v.split("=")[1]
							if self.vars.get(key) == value:
								await ent.parse()
						else:
							await ent.parse()
							
					if ent.valid():
						out += ent.parsed
					self.entities.append(ent)
		return out
						
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
		self.vars = {}
	
	def write(self, code):
		self.body = code
		self.parsed = ""
		return self
					
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
						
				line = self.parser.replacing(item)
				
				if line != "" and item != " " and item != "	" and line != "\n":
					self.lines.append(line)
		
		#print(f"LINES: {self.lines}")
		self.lines = await self.parser.parseMSymbols(self, self.lines)
		#print(f"LINES AFT: {self.lines}")
		
		for item in self.lines:
			if line != "" and item != " " and item != "	" and line != "\n":
				self.parsed += f"{item}\n"	
				
		
