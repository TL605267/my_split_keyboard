#!/usr/bin/env python3
from os import listdir
from enum import Enum, auto

class State(Enum):
	COPY = auto()
	SKIP = auto()
	MOD = auto()

class gen_vinyl_cut():
	def __init__(self):
		self.paste_svg = [file for file in listdir('.') if file.endswith('B_Paste.svg')][0]
		self.state = State.COPY
		self.style_template = '''<style>
	.outlineStyle {
	  fill:none; 
	  stroke:#000000; 
	  stroke-width:0.0500; 
	  stroke-opacity:1; 
	  stroke-linecap:round;  
	  stroke-linejoin:round;
	}
</style>
'''
		self.path_style = '<path class="outlineStyle"\n'

	def process_svg(self):
		with open(self.paste_svg, 'r') as paste_file, open('autogen_cut.svg', 'w') as output:
			for line in paste_file.readlines():
				# state transition
				if self.state == State.COPY:
					if line.startswith('<title'):
							self.state = State.MOD
					elif line.startswith('<path style'):
						if 'fill:none;' in line:
							self.state = State.SKIP
						else:
							self.state = State.MOD
				elif self.state == State.SKIP:
					if '/>' in line: 
						# FIXME move to COPY in next state
						self.state = State.COPY
				elif self.state == State.MOD:
					self.state = State.COPY
				# state action
				if self.state == State.COPY:
					output.write(line)
				elif self.state == State.SKIP:
					continue
				elif self.state == State.MOD:
					if line.startswith('<title'):
						output.write(self.style_template)
						output.write(line)
					elif line.startswith('<path style'):
						output.write(self.path_style)
						
					
def main():
	m = gen_vinyl_cut()                                              
	m.process_svg()                                          
	                                          
if __name__ == "__main__":                                 
	main()