# mogscript
Mogscript is a simple text processing markup. It works by running through a block of text, processing various triggers, and outputting a result at the end.

This project is inspired by AI markup languages such as AIML and Rive. I saw how interesting those were, and decided I wanted something similar, but more generalized, more multi-purpose. My aim was to have a text processing system that could set and get variables, modify the global state (effect things in the main program the script is running in), allow dynamic text replacement, run inline code, and have a flexible tags system to easily add new features.

This whole thing is a work-in-progress, not even a day old from conception at the time of writing, so it's still pretty primitive. Things may change in time, get more advanced, who knows. For now, it's a fun side project for me.

## Getting started

To read a single file; (extension doesn't matter, as long as its a valid file with text)

```py
from mogscript import Mog

f = Mog.load(file='/home/kaiz0r/Documents/data.txt')
```

To read a string;

```py
from mogscript import Mog

f = Mog.load(str="""This is some code.
---
Seperate entity.
""")
```

To read all files in a directory, to check for specific extensions, pass a list to the functions `exts` keyword argument. Defaults to only loading `.txt` files. Instead of returning an object like the previous examples, it returns a list of those objects.

```py
from mogscript import Mog

ls = Mog.load(dir='/home/kaiz0r/Documents/')
```
Use `Mog.loadasync` to create an Asyncronous version of the Parser.

Once you have a Parser object from one of these methods, you can start doing stuff!


```
{META}
version: 1
author: Kai
description: This is a valid script, crazy!
---
The above section is a META section. 
If the first line of a `block`, each section seperated by `---`, 
contains the special {META} tag, the body is converted in to variables, in the format of
key: value
and saved in to the parsers .vars value.
---
You can get vars from the parser by using {var: author}, when parsed, this'll turn in to `Kai`
You can also SET vars, including overwriting the meta tags, with {set: author=Mog}
And now, {var: author} is Mog.
NEW:
You can use {local: author=Me} to set a local var for this entity block only, NOT the entire parser.
And {local: author} gets it, same as var.
---
var is basically a shortcut for `parser.vars[key] = value`, you can run it manually using the eval tag, 
which runs raw Python code inline
{eval: p.vars["author"] = "Mog"}
If you return anything in the eval, that's what the tag gets replaced with during parsing. 
Any tags that don't return anything, are hidden.
Thats two ways of changing the author!{add: counter}{add: counter}
`add` is another preset command, like var, set, eval
`add` increments a digit, assigned to the name `counter`, in parser.vars
There is also `sub`, `div`, `mult`
And just like with any variable, you can {var: counter} to get it!
---
Hm, which author is better... {choice: kaiz0r;mog}
choice is another preset, and takes multiple arguments split with ;, and randomly returns one.
---
Thats alot of presets! 
You can add your own command tags pretty easily too, either in the python code itself, 
or right here in-script, using the {CODE} tag. 
It's like META, but instead of turning the block in to vars, 
it turns it in to a python function that is accessible using the {} calls, 
for example, we name this one `test`, and you can use {test} to call it, 
and giving it arguments is as simple as {test: this is an argument}
---
{CODE: test}
result = args[0]
return result.upper()
---
Now if we run {test: shout}, this becomes SHOUT.
Whatever is returned in the function is what the tag gets replaced with during parsing.
Inside eval and code blocks, 
two values are exposed; `p` which is the main Parser class, 
so you can access things like other variables and functions, and `args`,
a tuple of the arguments given to it.
For the sake of order, code blocks are best defined early on in the line, 
as each block is processed in order by default, 
so the function wont be available until that particular code block has been parsed.
---
Replacement stuff;
%me% - when poll() is used(see below), it'll just show `me` 
%me=A person; yourself% - will show `me`, but also `A person etc`, as a description
---
{IF: author=Kaiser}
This block only shows if author is Kaiser! there is also NOT, instead of IF, for the reverse.
If its capitalized at the start of a block, it checks the paramaters to decide if the entity block itself should be parsed.
For small-scale, theres also; {if: author=Kaiser;The stuff before this is the check, this message is shown if the check is met.}
Both ways have a NOT variant.
---
If you want delays between various processing for whatever reason, there is a preset {sleep: count} to sleep the process. Uses time.sleep() for default, and asyncio.sleep() for async.
---
NEW:
You can use $author, or ?v as a replacement for {var: author} and {local: v}.
They work in plain text blocks, or as arguments, like {local: ts=Me} {var: author=?ts}
Now $author displays as Me.
---
! transient
Adding a ! transient line will stop the parser from using this block, BUT any defined classes and functions here, do get added to parsers .globals

*cls CTest
	def __init__(self):
		self.b = "lol"
		self.count = 3

	def fprint(self, prefix, suffix):
		for i in range(0, self.count):
			print(f"{prefix} {self.b} {suffix}")
*endcls

*fn bork
	print( "no")
*endfn
```

```py
f.body
#String contains the raw text

f.vars
#Dict contains vars used for the "global" state inside the parser, used for evals, and {get: var}

f.addReplacement(old, new)
# Adds a new keyword that gets replaced during parsing
# if `old` is given as `test`, it'll look for %test% in the code.
# `new` can be either a plain string, or a function call, if its a string, it's a simple replacement
# if it's a function, it should be defined witb the signature of
  def func(p, word):
		return word.upper()
# Like eval and code blocks, it takes arguments of the parser and the input string, 
#whatever is returned is the replacement
# You can also pass new function calls in to the script, for use with {name}, with the signature of
	def upperize(host, *args):
		return args[0].upper()
# This method, lets you define a function to capitalize things, in this case {upperize: test} returns TEST.

f.parse() #runs through the blocks, and each parsed result is given to the parsers `parsed` list
#pass `partial=True` to parse() to only parse the META block and dump that to .vars

for entry in f.entities:
  entry.parse() 
  #each entry can be manually parsed, 
  #useful for if `partial` was used and they weren't parsed before, or they just need to be parsed again
  if entry.valid(): 
  #valid checks if .parsed has any content, 
  #useful if a block was only used for setting/eval and has no text, you can easily ignore them
     print(entry.poll()) ##this gets all unreplaced tags currently in the body
     print(entry.parsed) #prints the new parsed body, after processing all tags

f.insert("You can add new entity blocks to the parser at any time!")

#.walk is basically the same as .parse, but only parses entity blocks that aren't 
already parsed, like ones added with .insert, or ones where the IF check failed.
#both .parse and .walk return a plaintext output of all the parsed text
out = f.walk()

f.body = f.export()
# Inserting doesn't update the body, so any parse runs after that, will forget insertions.
# But, export dumps the current structure of entites and meta data back in to a string,
# So, you can just update the body this way, and now any new parses will remember inserted blocks.
# Passing update_meta=True to export() will replace the orginal meta header with a new one
# populated by the global vars.
# It always returns a string of the new body, but you can export it to file by passing;
# f.export(file="/path/to/file")
```
