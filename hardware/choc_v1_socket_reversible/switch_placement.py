#!/usr/bin/env python3
import os, pcbnew
from pcbnew import VECTOR2I, VECTOR2I_MM, FromMM, ToMM, F_Cu, B_Cu
from math import sin, cos, radians

class kbd_place_n_route(pcbnew.ActionPlugin):
	def __init__(self):
		# Initialize column offsets and switch positions
		self.col_offsets = [0, 0, -9, -11.5, -9, -6.5]
		self.sw0_pos = VECTOR2I_MM(60,60)
		self.sw_x_spc = 19 # 17.5 #19.05
		self.sw_y_spc = 17 #19.05
		self.fp_dict = {} # footpint dictionary

	def load_board(self):
		# Load the board file
		if not hasattr(self, 'board'):
			self.filename = [file for file in os.listdir('.') if file.endswith('.kicad_pcb')][0]
			self.board = pcbnew.LoadBoard(self.filename)
		for fp in self.board.GetFootprints():
			self.fp_dict[fp.GetReference()]= {
				'fp': fp,
				'val': fp.GetValue(),
				#'pos': fp.GetPosition(), # position is not updated after placement
				'ref_inst': fp.Reference()
			}
			
	def remove_old_tracks(self):
		# Remove all existing tracks from the board
		for t in self.board.GetTracks():
			self.board.Delete(t)

	def defaults(self):
		# Set default values for the plugin
		self.name = "KBD Placement"
		self.category = "Category name"
		self.description = "Longer description of the plugin"
		self.board = pcbnew.GetBoard()

	def add_track(self, start, end, layer=F_Cu, width=0.2):
		# Add a track to the board
		track = pcbnew.PCB_TRACK(self.board)
		track.SetStart(start)
		track.SetEnd(end)
		track.SetWidth(FromMM(width)) # default 0.2mm
		track.SetLayer(layer)
		self.board.Add(track)

	def add_tracks(self, points): 
		# Add multiple tracks to the board
		# points is a list of tuple: 
		# [(coordinate(VECTOR2I), layer(F_Cu/B_Cu/-1(via))), (,)..]
		for i in range(len(points)-1):
			if (points[i+1][1] < 0): # via
				self.add_via(points[i+1][0], 0.3, 0.6)
				self.add_track(points[i][0], points[i+1][0], points[i][1])
			else: #F_Cu, B_Cu
				self.add_track(points[i][0], points[i+1][0], points[i+1][1])
	
	def add_via(self, pos, drill, width):
		# Add a via to the board
		via = pcbnew.PCB_VIA(self.board)
		via.SetPosition(pos)
		via.SetDrill(FromMM(drill)) # defaults 0.4mm, 0.8mm
		via.SetWidth(FromMM(width))
		self.board.Add(via)

	def place_fp(self, pos, fp, orientation):
		# Place a footprint on the board
		fp.SetPosition(pos) 
		fp.SetOrientationDegrees(orientation)
	
	def rotate(self, origin, point, angle): # TODO
		# Rotate a point counterclockwise by a given angle around a given origin
		ox, oy = origin
		px, py = point
		angle_rad = radians(angle)
		qx = ox + cos(angle_rad) * (px - ox) - sin(angle_rad) * (py - oy)
		qy = oy + sin(angle_rad) * (px - ox) + cos(angle_rad) * (py - oy)
		return qx, qy

	def get_fp_ref_list(self, fp_val):
		# Get a list of footprint references with a specific value
		return [key for key, value in self.fp_dict.items() if value['val'] == fp_val]

	def gen_led_track(self, netname, s_offset = VECTOR2I_MM(0,0)): #TODO put the start point track at top
		# Generate LED track code
		s_list = []
		for t in self.board.GetTracks():
			if t.GetNetname() == netname:
				sx = round(ToMM((t.GetStart()-s_offset).x), 1)
				sy = round(ToMM((t.GetStart()-s_offset).y), 1)
				ex = round(ToMM((t.GetEnd()  -s_offset).x), 1)
				ey = round(ToMM((t.GetEnd()  -s_offset).y), 1)
				if (sx != ex): # remove led via connection
					s_list.append((sx, sy, ex, ey))
		s_list_sorted = sorted(s_list, key=lambda x: x[0])	
		for s in s_list_sorted:
			format_code = f"self.add_track(offset + VECTOR2I_MM({s[0]:>5.1f}, {s[1]:>5.1f}), offset + VECTOR2I_MM({s[2]:>5.1f}, {s[3]:>5.1f}), B_Cu)"
			print(format_code)
		
	def place_sw(self):
		# Place switches on the board
		for sw_ref in self.get_fp_ref_list('SW_Push'): 
			sw_row = int(sw_ref[2])
			sw_col = int(sw_ref[3])
			sw_orienation = 0
			if(sw_col < 6): # 4 fingers
				sw_offset = VECTOR2I_MM(self.sw_x_spc*sw_col, self.sw_y_spc*sw_row + self.col_offsets[sw_col])
				sw_orienation = 0
			# thumb, respective to index bottom switch
			elif (sw_col == 6): 
				sw_offset = VECTOR2I_MM(self.sw_x_spc*5+2.9, self.sw_y_spc*3+14.8)
				sw_orienation = -23
			else: # 7 
				sw_offset = VECTOR2I_MM(self.sw_x_spc*5+23.8, self.sw_y_spc*3+19.8)
				sw_orienation = 60
			# place switches
			self.place_fp(self.sw0_pos+sw_offset, self.fp_dict[sw_ref]['fp'], sw_orienation)
			self.fp_dict[sw_ref]['ref_inst'].SetTextPos(self.sw0_pos+sw_offset + VECTOR2I_MM(4.4, 7.1))
			for item in self.fp_dict[sw_ref]['fp'].GraphicalItems(): #TODO store graphical items in dict
				if type(item) == pcbnew.PCB_TEXT:
					item.SetPosition(self.sw0_pos+sw_offset+VECTOR2I_MM(-4.4,7.1))

	def place_led(self):
		# Place LEDs on the board
		for led_ref in self.get_fp_ref_list('SK6812MINI'):
			idx = led_ref[-2:]
			sw_row = int(idx[0])
			sw_col = int(idx[1])
			sw_pos = self.fp_dict['SW'+idx]['fp'].GetPosition()
			led_pos = sw_pos + VECTOR2I_MM(0, -4.7)
			led_orientation = 0
			if  (sw_col < 6): 
				#self.fp_dict[led_ref]['ref_inst'].SetTextPos(led_pos + VECTOR2I_MM(0, 2.3))
				#TODO separate thumb cluster placement
				if (sw_col == 0 or sw_col == 3 or sw_col == 5):
					led_orientation = 180
				else: # col1/2/5
					led_orientation = 0
			elif(sw_col == 6):
				led_orientation = -23
			else: # 7
				led_orientation = 60
			self.place_fp(led_pos, self.fp_dict[led_ref]['fp'], led_orientation)

	def place_diode(self):
		# Place diodes on the board
		for d_ref in self.get_fp_ref_list('BAV70'):
			# get left switch position
			sw_ref_l = 'SW'+d_ref[1:3]
			sw_pos_l_x = self.fp_dict[sw_ref_l]['fp'].GetPosition().x
			sw_pos_l_y = self.fp_dict[sw_ref_l]['fp'].GetPosition().y
			# get right switch position
			sw_ref_r = 'SW'+d_ref[3:5]
			sw_pos_r_x = self.fp_dict[sw_ref_r]['fp'].GetPosition().x
			sw_pos_r_y = self.fp_dict[sw_ref_r]['fp'].GetPosition().y
			# place diode in between switches
			d_pos = VECTOR2I((sw_pos_l_x + sw_pos_r_x)>>1, min(sw_pos_l_y, sw_pos_r_y))
			self.place_fp(d_pos, self.fp_dict[d_ref]['fp'], 90)
			self.fp_dict[d_ref]['ref_inst'].SetTextPos(d_pos + VECTOR2I_MM(0, 2.4))
			self.fp_dict[d_ref]['ref_inst'].SetTextAngleDegrees(180)

	def place_via_for_led(self):
		# Place vias on the board
		via_offset_x = [-3.3-0.3, -3.3+0.3, 3.3-0.3, 3.3+0.3]
		for led_ref in self.get_fp_ref_list('SK6812MINI'):
			led_pos = self.fp_dict[led_ref]['fp'].GetPosition()
			for i in range(4): 
				via_pos  = led_pos + VECTOR2I_MM(via_offset_x[i], 0)
				led1_pos = led_pos + VECTOR2I_MM(via_offset_x[i], -0.5)
				led2_pos = led_pos + VECTOR2I_MM(via_offset_x[i], 0.5)
				if (i%2 == 0):
					self.add_track(led1_pos, via_pos, F_Cu)
					self.add_via(via_pos, 0.3, 0.4)
					self.add_track(via_pos, led2_pos, B_Cu)
				else:
					self.add_track(led1_pos, via_pos, B_Cu)
					self.add_via(via_pos, 0.3, 0.4)
					self.add_track(via_pos, led2_pos, F_Cu)

	#TODO def connect_thumb_cluster(self):
	#rotate thumb keys and connect

	def place_shift_register_and_resistor(self):
		for fp_ref in self.get_fp_ref_list('74HC165'):
			self.place_fp(VECTOR2I_MM(10, 10), self.fp_dict[fp_ref]['fp'], 0)

	def connect_pad1(self):
		# Connect switch pad1 on both F_Cu and B_Cu layer
		for sw_ref in self.get_fp_ref_list('SW_Push'): 
			sw_pos = self.fp_dict[sw_ref]['fp'].GetPosition()
			# pad1
			self.add_tracks([	
				(sw_pos+(VECTOR2I_MM( 3.3, 6.0)), B_Cu), 
				(sw_pos+(VECTOR2I_MM( 1.5, 4.0)), B_Cu),
				(sw_pos+(VECTOR2I_MM(-2.2, 4.0)), -1  ) #Via
			])

	def connect_diode_and_sw(self):
		# Connect diode and switches pad2 on both F_cu and B_Cu layer
		for d_ref in self.get_fp_ref_list('BAV70'):
			# each diode is named in the format of DXXYY, 
			# where YY is the left switch and YY is the right switch
			# connect diode to the switch on its left
			sw_ref_l = 'SW'+d_ref[1:3]
			sw_pos_l = self.fp_dict[sw_ref_l]['fp'].GetPosition()
			# Get pad2 y coordinate. 
			# There are two pad 2 on the switch footprint, 
			# but one of them is flipped to the back side for reverse mount. 
			# therefore their y coordinate is the same, we can use either one
			for pad in self.fp_dict[sw_ref_l]['fp'].Pads():
				if pad.GetNumber() == '2':
					sw_l_pad2_y = pad.GetCenter().y
					break
			#sw_l_pad2_y = [p for p in self.fp_dict[sw_ref_l]['fp'].Pads() if p.GetNumber() == '2'][0].GetCenter().y
			d_p1_pos = self.fp_dict[d_ref]['fp'].FindPadByNumber('1').GetCenter()
			# Added hard-coded track to connect diode to the switch
			self.add_tracks([
				(VECTOR2I(d_p1_pos.x, sw_l_pad2_y), F_Cu),
				(d_p1_pos                         , F_Cu),
				(sw_pos_l+VECTOR2I_MM( 5.8, 2.0)  , B_Cu),
				(sw_pos_l+VECTOR2I_MM(-6.5, 2.0)  , B_Cu),
				(sw_pos_l+VECTOR2I_MM(-8.2, 3.6)  , B_Cu)
			])
			# connect diode to the switch on its right
			sw_ref_r = 'SW'+d_ref[3:5]
			sw_pos_r = self.fp_dict[sw_ref_r]['fp'].GetPosition()
			for pad in self.fp_dict[sw_ref_r]['fp'].Pads():
				if pad.GetNumber() == '2':
					sw_r_pad2_y = pad.GetCenter().y
					break
			#sw_r_pad2_y = [p for p in sw_fp_r.Pads() if p.GetNumber() == '2'][0].GetCenter().y
			d_p2_pos = self.fp_dict[d_ref]['fp'].FindPadByNumber('2').GetCenter()
			# Added hard-coded track to connect diode to the switch
			self.add_tracks([
				(d_p2_pos                         , B_Cu),
				(VECTOR2I(d_p2_pos.x, sw_r_pad2_y), B_Cu),
				(sw_pos_r+VECTOR2I_MM(-6.5, 2.0)  , B_Cu),
				(sw_pos_r+VECTOR2I_MM( 8.2, 2.0)  ,   -1), # via
				(sw_pos_r+VECTOR2I_MM( 8.2, 3.6)  , F_Cu)
			])
		
	def connect_sw_col(self):
		# Connect column pads from top to bottom
		for col in range(6): # 6 column
			start = self.sw0_pos + VECTOR2I_MM(-2.2, 4.0) + VECTOR2I_MM(self.sw_x_spc*col, self.col_offsets[col])
			end   = self.sw0_pos + VECTOR2I_MM(-2.2, 5.2) + VECTOR2I_MM(self.sw_x_spc*col, self.col_offsets[col]+ self.sw_y_spc*3)
			self.add_track(start, end, F_Cu)

	def connect_rows(self):
		# Connect rows
		for diode_ref in self.get_fp_ref_list('BAV70'): 
			if diode_ref.endswith('1'): # left most col
				padk_pos = self.fp_dict[diode_ref]['fp'].FindPadByNumber('3').GetCenter() # offset
				# the following code is auto generated by gen_led_track
				self.add_track(padk_pos + VECTOR2I_MM(  0.0,   0.0), padk_pos + VECTOR2I_MM(  1.0,  -1.0), B_Cu)
				self.add_track(padk_pos + VECTOR2I_MM(  1.0,  -1.0), padk_pos + VECTOR2I_MM( 13.9,  -1.0), B_Cu)
				self.add_track(padk_pos + VECTOR2I_MM( 13.9,  -1.0), padk_pos + VECTOR2I_MM( 22.9, -10.0), B_Cu)
				self.add_track(padk_pos + VECTOR2I_MM( 22.9, -10.0), padk_pos + VECTOR2I_MM( 35.3, -10.0), B_Cu)
				self.add_track(padk_pos + VECTOR2I_MM( 35.3, -10.0), padk_pos + VECTOR2I_MM( 40.7, -12.5), B_Cu)
				self.add_track(padk_pos + VECTOR2I_MM( 40.7, -12.5), padk_pos + VECTOR2I_MM( 52.6, -12.5), B_Cu)
				self.add_track(padk_pos + VECTOR2I_MM( 52.6, -12.5), padk_pos + VECTOR2I_MM( 55.1, -10.0), B_Cu)
				self.add_track(padk_pos + VECTOR2I_MM( 55.1, -10.0), padk_pos + VECTOR2I_MM( 75.0, -10.0), B_Cu)
				self.add_track(padk_pos + VECTOR2I_MM( 75.0, -10.0), padk_pos + VECTOR2I_MM( 76.0,  -9.0), B_Cu)

	def connect_leds_by_col(self):
		# Connect LEDs by column
		for sw_ref in self.get_fp_ref_list('SW_Push'):
			sw_col = int(sw_ref[-1])
			sw_row = int(sw_ref[-2])
			offset = self.fp_dict[sw_ref]['fp'].GetPosition()
			if sw_row == 0: # top row
				# power rail - left
				virtical_track_length = 3*self.sw_y_spc - (9.0-3.8)
				self.add_tracks([
					(offset + VECTOR2I_MM(-3.3, -5.5), F_Cu),	
					(offset + VECTOR2I_MM(-5.0, -5.5), F_Cu),	
					(offset + VECTOR2I_MM(-6.7, -3.8), F_Cu), 
					(offset + VECTOR2I_MM(-6.7, -3.8 + virtical_track_length), F_Cu) 
				])
				# power rail - right
				virtical_track_length = 3*self.sw_y_spc - (7.3-0.5)
				self.add_tracks([
					(offset + VECTOR2I_MM( 3.3, -3.9), F_Cu),
					(offset + VECTOR2I_MM( 6.7, -0.5), F_Cu),
					(offset + VECTOR2I_MM( 6.7, -0.5 + virtical_track_length), F_Cu)
				])
			else:
				# power rail - left
				self.add_track(offset + VECTOR2I_MM(-3.3, -5.6), offset + VECTOR2I_MM(-6.7, -9.0))	
				# power rail - right
				self.add_track(offset + VECTOR2I_MM(3.3, -3.9), offset + VECTOR2I_MM(6.7, -7.3))
				# led dout -> led din
				virtical_track_length = self.sw_y_spc - 2.6
				self.add_tracks([
					(offset + VECTOR2I_MM(-3.3, -5.5), B_Cu),
					(offset + VECTOR2I_MM(-1.9, -6.9), B_Cu),
					(offset + VECTOR2I_MM( 2.1, -6.9),   -1), # via
					(offset + VECTOR2I_MM( 2.1, -6.9-virtical_track_length), F_Cu),
					(offset + VECTOR2I_MM( 3.3,-22.5), F_Cu)
				])
			
	# Do all the things
	def Run(self):
		# Execute the plugin
		self.load_board()
		self.remove_old_tracks()
		self.place_sw()
		self.place_led()
		self.place_diode()
		self.connect_diode_and_sw()
		#self.connect_thumb_cluster()
		self.connect_rows()
		self.connect_pad1()
		self.connect_sw_col()
		self.connect_leds_by_col()
		self.place_via_for_led()
		pcbnew.Refresh()
		pcbnew.SaveBoard(self.filename, self.board)
		
#kbd_place_n_route().register()

def main():
	plugin = kbd_place_n_route()
	'''
	print('# POWER RAIL TOP PAD')
	plugin.gen_led_track('+5V')
	print('# POWER RAIL BOTTOM PAD')
	plugin.gen_led_track('GND')
	for i in range(5):
		print(f'# LEDx{i}')
		plugin.gen_led_track(f'Net-(LED0{i}-DIN)')
	'''
	plugin.Run()

if __name__ == "__main__":
	main()