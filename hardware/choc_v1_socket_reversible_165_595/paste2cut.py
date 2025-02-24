#!/usr/bin/env python3
from os import listdir
from enum import Enum, auto

class State(Enum):
	COPY = auto()
	SKIP = auto()

class gen_vinyl_cut():
	def __init__(self):
		# TODO select F/B_Paste svg file
		self.paste_svg = [file for file in listdir('.') if file.endswith('F_Paste.svg')][0]
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
				if self.state == State.COPY:
					if line.startswith('<title'): # add style defnition before title
						output.write(self.style_template)
						output.write(line)                             
					elif line.startswith('<path style'):
						if 'fill:none;' in line: # existing edge cut paths
							self.state = State.SKIP
						else: # pads that needs to be converted to stroke
							output.write(self.path_style)
					else: 
						output.write(line)

				elif self.state == State.SKIP: 
					if '/>' in line: # skip <path fill:none .../> block
						self.state = State.COPY

def main():
	m = gen_vinyl_cut()                                              
	m.process_svg()                                          
	                                          
if __name__ == "__main__":                                 
	main()