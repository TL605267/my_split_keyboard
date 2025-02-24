#!/usr/bin/env python3
from os import listdir
from enum import Enum, auto

class State(Enum):
	COPY = auto()
	SKIP = auto()

class GenVinylCut:
	def __init__(self):
		# Select F/B_Paste svg file
		try:
			self.paste_svg = next(file for file in listdir('.') if file.endswith('F_Paste.svg'))
		except StopIteration:
			raise FileNotFoundError("No F_Paste.svg file found in the current directory.")
		
		self.state = State.COPY
		# gray stroke for easier look in dark mode :)
		self.style_template ='''<g style="fill:none; stroke:#999999; stroke-width:0.0500; stroke-opacity:1; '''
		self.path_style = '<path '

	def process_svg(self):
		try:
			with open(self.paste_svg, 'r') as paste_file, open('autogen_cut.svg', 'w') as output:
				for line in paste_file:
					if self.state == State.COPY:
						if line.startswith('<g'):  # Replace group style
							output.write(self.style_template)
						elif line.startswith('<path style'):
							if 'fill:none;' in line:  # Existing edge cut paths
								self.state = State.SKIP
							else:  # Pads that need to be converted to stroke
								output.write(self.path_style)
						else:
							output.write(line)
					elif self.state == State.SKIP:
						if '/>' in line:  # Skip <path fill:none .../> block
							self.state = State.COPY
		except FileNotFoundError as e:
			print(f"Error: {e}")
		except IOError as e:
			print(f"Error: {e}")

def main():
	m = GenVinylCut()
	m.process_svg()

if __name__ == "__main__":
	main()