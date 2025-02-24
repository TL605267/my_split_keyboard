#!/usr/bin/env python3
from os import listdir

class paste():
	def __init__(self):
		self.paste_svg = [file for file in listdir('.') if file.endswith('B_Paste.svg')][0]
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
		self.file_end = '''</g> 
</svg>
'''

	def process_svg(self):
		with open(self.paste_svg, 'r') as paste_file, open('autogen_cut.svg', 'w') as output:
				outline_style_added = 0
				for line in paste_file.readlines():
					'''	
					if line.startswith('<path style'):
						if 'fill:none' in line:
							output.write(self.file_end)                    
							break                                          
						elif outline_style_added == 0:
							output.write(self.style_template)
							outline_style_added = 1
						output.write(self.path_style)
					else:
						output.write(line)                             
					'''	
					# remove led and board edge cuts
					if outline_style_added == 1 and line.startswith('<path style="fill:none'):	
						output.write(self.file_end)                    
						break                                          
					# change paste style from filled to non
					elif line.startswith('<path style'):
						if outline_style_added == 0:
							output.write(self.style_template)
							outline_style_added = 1
						output.write(self.path_style)
					else:	                                           
						output.write(line)                             
                                                           
if __name__ == "__main__":                                 
	p = paste()                                              
	p.process_svg()                                          