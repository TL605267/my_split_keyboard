#!/usr/bin/env python3
import os,sys, pcbnew
from pcbnew import VECTOR2I, VECTOR2I_MM, FromMM, ToMM, F_Cu, B_Cu
from math import sin, cos, radians

class kbd_place_n_route(pcbnew.ActionPlugin):
	def __init__(self):
		self.col_offsets = [0, 0, -9, -11.5, -9, -6.5]
		self.sw0_pos = VECTOR2I_MM(60,60)
		self.sw_x_spc = 19 # 17.5 #19.05
		self.sw_y_spc = 17 #19.05

	def load_board(self):
		self.filename = [file for file in os.listdir('.') if file.endswith('.kicad_pcb')][0]
		self.board = pcbnew.LoadBoard(self.filename)

	def remove_old_tracks(self):
		for t in self.board.GetTracks():
				self.board.Delete(t)

	def defaults(self):
		self.name = "KBD Placement"
		self.category = "Category name"
		self.description = "Longer description of the plugin"
		self.board = pcbnew.GetBoard()

	def add_track(self, start, end, layer=F_Cu, width=0.2):
		track = pcbnew.PCB_TRACK(self.board)
		track.SetStart(start)
		track.SetEnd(end)
		track.SetWidth(FromMM(width)) # default 0.2mm
		track.SetLayer(layer)
		self.board.Add(track)

	def add_tracks(self, points):
		for i in range(len(points)-1):
			if (points[i+1][1] < 0): # via
				self.add_via(points[i+1][0], 0.3, 0.6)
				self.add_track(points[i][0], points[i+1][0], points[i][1])
			else: #F_Cu, B_Cu
				self.add_track(points[i][0], points[i+1][0], points[i+1][1])
	
	def add_via(self, pos, drill, width):
		via = pcbnew.PCB_VIA(self.board)
		via.SetPosition(pos)
		via.SetDrill(FromMM(drill)) # defaults 0.4mm, 0.8mm
		via.SetWidth(FromMM(width))
		self.board.Add(via)

	def place_fp(self, pos, fp, orientation):
		fp.SetPosition(pos) 
		fp.SetOrientationDegrees(orientation)
	
	def rotate(self, origin, point, angle): # TODO
		"""
		Rotate a point counterclockwise by a given angle around a given origin.
		The angle should be given in radians.
		"""
		ox, oy = origin
		px, py = point
		angle_rad = radians(angle)
		qx = ox + cos(angle_rad) * (px - ox) - sin(angle_rad) * (py - oy)
		qy = oy + sin(angle_rad) * (px - ox) + cos(angle_rad) * (py - oy)
		return qx, qy

	def get_fp_list(self, fp_val):
		return [fp for fp in self.board.GetFootprints() if fp.GetValue() == fp_val]

	def gen_led_track(self, netname, s_offset = VECTOR2I_MM(0,0)): #TODO put the start point track at top
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
		
	# place switches and leds
	def place_sw(self):
		for sw_fp in self.get_fp_list('SW_Push'): 
			sw_row = int(sw_fp.GetReference()[2])
			sw_col = int(sw_fp.GetReference()[3])
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
			self.place_fp(self.sw0_pos+sw_offset, sw_fp, sw_orienation)
			sw_fp.Reference().SetTextPos(self.sw0_pos+sw_offset + VECTOR2I_MM(4.4, 7.1))
			for item in sw_fp.GraphicalItems():
				if type(item) == pcbnew.PCB_TEXT:
					item.SetPosition(self.sw0_pos+sw_offset+VECTOR2I_MM(-4.4,7.1))

	# place LEDs
	def place_led(self):
		for led_fp in self.get_fp_list('SK6812MINI'):
			idx = led_fp.GetReference()[-2:]
			sw_row = int(idx[0])
			sw_col = int(idx[1])
			sw_pos = self.board.FindFootprintByReference('SW'+idx).GetPosition()
			led_pos = sw_pos + VECTOR2I_MM(0, -4.7)
			if  (sw_col < 6): 
				'''
				self.place_fp(led_pos, led_fp, 180)
				'''
				if (sw_col == 0 or sw_col == 3 or sw_col == 5):
					self.place_fp(led_pos, led_fp, 180)
				else: # col1/2/5
					self.place_fp(led_pos, led_fp, 0)
				led_fp.Reference().SetTextPos(led_pos + VECTOR2I_MM(0, 2.3))
			elif(sw_col == 6):
				self.place_fp(led_pos, led_fp, -23)
			else: # 7
				self.place_fp(led_pos, led_fp, 60)

	# place diode
	def place_diode(self):
		for d_fp in self.get_fp_list('BAV70'):
			# get left switch position
			sw_ref_l = 'SW'+d_fp.GetReference()[1:3]
			sw_fp_l = self.board.FindFootprintByReference(sw_ref_l)
			sw_pos_l_x = sw_fp_l.GetPosition().x
			sw_pos_l_y = sw_fp_l.GetPosition().y
			# get right switch position
			sw_ref_r = 'SW'+d_fp.GetReference()[3:5]
			sw_fp_r = self.board.FindFootprintByReference(sw_ref_r)
			sw_pos_r_x = sw_fp_r.GetPosition().x
			sw_pos_r_y = sw_fp_r.GetPosition().y
			# place diode in between switches
			d_pos = VECTOR2I((sw_pos_l_x + sw_pos_r_x)>>1, min(sw_pos_l_y, sw_pos_r_y))
			self.place_fp(d_pos, d_fp, 90)
			d_fp.Reference().SetTextPos(d_pos + VECTOR2I_MM(0, 2.4))
			d_fp.Reference().SetTextAngleDegrees(180)

	# place vias
	def place_via(self):
		via_offset_x = [-3.3-0.3, -3.3+0.3, 3.3-0.3, 3.3+0.3]
		for led_fp in self.get_fp_list('SK6812MINI'):
			led_pos = led_fp.GetPosition()
			#FIXME rotate via by column
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
	
	# connect switch pad1 on both sides
	def connect_pad1(self):
		for sw_fp in self.get_fp_list('SW_Push'): 
			sw_pos = sw_fp.GetPosition()
			# pad1
			track_points = []
			track_points.append((sw_pos+(VECTOR2I_MM( 3.3, 6.0)), B_Cu))
			track_points.append((sw_pos+(VECTOR2I_MM( 1.5, 4.0)), B_Cu))
			track_points.append((sw_pos+(VECTOR2I_MM(-2.2, 4.0)), -1  )) #Via
			self.add_tracks(track_points)

	# connect diode and switches pad2
	def connect_diode_and_sw(self):
		for d_fp in self.get_fp_list('BAV70'):
			# diode to left switch
			sw_ref_l = 'SW'+d_fp.GetReference()[1:3]
			sw_fp_l = self.board.FindFootprintByReference(sw_ref_l)
			sw_pos_l = sw_fp_l.GetPosition()
			sw_l_pad2_y = [p for p in sw_fp_l.Pads() if p.GetNumber() == '2'][0].GetCenter().y
			d_p1_pos = d_fp.FindPadByNumber('1').GetCenter()
			track_points = []
			track_points.append((VECTOR2I(d_p1_pos.x, sw_l_pad2_y), F_Cu))
			track_points.append((d_p1_pos, F_Cu))
			track_points.append((sw_pos_l+VECTOR2I_MM( 5.8, 2.0), B_Cu))
			track_points.append((sw_pos_l+VECTOR2I_MM(-6.5, 2.0), B_Cu))
			track_points.append((sw_pos_l+VECTOR2I_MM(-8.2, 3.6), B_Cu))
			self.add_tracks(track_points)
			# diode to right switch
			sw_ref_r = 'SW'+d_fp.GetReference()[3:5]
			sw_fp_r = self.board.FindFootprintByReference(sw_ref_r)
			sw_pos_r = sw_fp_r.GetPosition()
			sw_r_pad2_y = [p for p in sw_fp_r.Pads() if p.GetNumber() == '2'][0].GetCenter().y
			d_p2_pos = d_fp.FindPadByNumber('2').GetCenter()
			track_points = []
			track_points.append((d_p2_pos, B_Cu))
			track_points.append((VECTOR2I(d_p2_pos.x, sw_r_pad2_y), B_Cu))
			track_points.append((sw_pos_r+VECTOR2I_MM(-6.5, 2.0), B_Cu))
			track_points.append((sw_pos_r+VECTOR2I_MM( 8.2, 2.0), -1)) # via
			track_points.append((sw_pos_r+VECTOR2I_MM( 8.2, 3.6), F_Cu))
			self.add_tracks(track_points)
		
	# connect col pad from top to bottom
	def connect_sw_col(self):
		for col in range(6): # 6 column
			start = self.sw0_pos + VECTOR2I_MM(-2.2, 4.0) + VECTOR2I_MM(self.sw_x_spc*col, self.col_offsets[col])
			end   = self.sw0_pos + VECTOR2I_MM(-2.2, 5.2) + VECTOR2I_MM(self.sw_x_spc*col, self.col_offsets[col]+ self.sw_y_spc*3)
			self.add_track(start, end, F_Cu)

	# connect rows
	def connect_rows(self):
		for diode_fp in self.get_fp_list('BAV70'): 
			if diode_fp.GetReference().endswith('1'): # left most col
				padk_pos = diode_fp.FindPadByNumber('3').GetCenter() # offset
				self.add_track(padk_pos + VECTOR2I_MM(  0.0,   0.0), padk_pos + VECTOR2I_MM(  1.0,  -1.0), B_Cu)
				self.add_track(padk_pos + VECTOR2I_MM(  1.0,  -1.0), padk_pos + VECTOR2I_MM( 13.9,  -1.0), B_Cu)
				self.add_track(padk_pos + VECTOR2I_MM( 13.9,  -1.0), padk_pos + VECTOR2I_MM( 22.9, -10.0), B_Cu)
				self.add_track(padk_pos + VECTOR2I_MM( 22.9, -10.0), padk_pos + VECTOR2I_MM( 35.3, -10.0), B_Cu)
				self.add_track(padk_pos + VECTOR2I_MM( 35.3, -10.0), padk_pos + VECTOR2I_MM( 40.7, -12.5), B_Cu)
				self.add_track(padk_pos + VECTOR2I_MM( 40.7, -12.5), padk_pos + VECTOR2I_MM( 52.6, -12.5), B_Cu)
				self.add_track(padk_pos + VECTOR2I_MM( 52.6, -12.5), padk_pos + VECTOR2I_MM( 55.1, -10.0), B_Cu)
				self.add_track(padk_pos + VECTOR2I_MM( 55.1, -10.0), padk_pos + VECTOR2I_MM( 75.0, -10.0), B_Cu)
				self.add_track(padk_pos + VECTOR2I_MM( 75.0, -10.0), padk_pos + VECTOR2I_MM( 76.0,  -9.0), B_Cu)

	def connect_leds_by_row(self):
		# for leds in row0
		for sw in [fp for fp in self.board.GetFootprints() if (fp.GetValue() == 'SW_Push' and fp.GetReference().endswith('0'))]: 
			offset = sw.GetPosition() - self.sw0_pos
			# POWER RAIL TOP PAD
			self.add_track(offset + VECTOR2I_MM( 63.3,  54.5), offset + VECTOR2I_MM( 64.4,  53.4), B_Cu)
			self.add_track(offset + VECTOR2I_MM( 64.4,  53.4), offset + VECTOR2I_MM( 81.2,  53.4), B_Cu)
			self.add_track(offset + VECTOR2I_MM( 81.2,  53.4), offset + VECTOR2I_MM( 82.3,  54.5), B_Cu)
			self.add_track(offset + VECTOR2I_MM( 82.3,  54.5), offset + VECTOR2I_MM( 92.4,  44.4), B_Cu)
			self.add_track(offset + VECTOR2I_MM( 92.4,  44.4), offset + VECTOR2I_MM(100.2,  44.4), B_Cu)
			self.add_track(offset + VECTOR2I_MM(100.2,  44.4), offset + VECTOR2I_MM(101.3,  45.5), B_Cu)
			self.add_track(offset + VECTOR2I_MM(101.3,  45.5), offset + VECTOR2I_MM(104.9,  41.9), B_Cu)
			self.add_track(offset + VECTOR2I_MM(104.9,  41.9), offset + VECTOR2I_MM(119.2,  41.9), B_Cu)
			self.add_track(offset + VECTOR2I_MM(119.2,  41.9), offset + VECTOR2I_MM(120.3,  43.0), B_Cu)
			self.add_track(offset + VECTOR2I_MM(120.3,  43.0), offset + VECTOR2I_MM(136.8,  43.0), B_Cu)
			self.add_track(offset + VECTOR2I_MM(136.8,  43.0), offset + VECTOR2I_MM(139.3,  45.5), B_Cu)
			self.add_track(offset + VECTOR2I_MM(155.8,  45.5), offset + VECTOR2I_MM(139.3,  45.5), B_Cu)
			self.add_track(offset + VECTOR2I_MM(158.3,  48.0), offset + VECTOR2I_MM(155.8,  45.5), B_Cu)
			# POWER RAIL BOTTOM PAD
			self.add_track(offset + VECTOR2I_MM( 56.7,  56.1), offset + VECTOR2I_MM( 57.8,  57.2), B_Cu)
			self.add_track(offset + VECTOR2I_MM( 57.8,  57.2), offset + VECTOR2I_MM( 74.6,  57.2), B_Cu)
			self.add_track(offset + VECTOR2I_MM( 74.6,  57.2), offset + VECTOR2I_MM( 75.7,  56.1), B_Cu)
			self.add_track(offset + VECTOR2I_MM( 75.7,  56.1), offset + VECTOR2I_MM( 76.8,  57.2), B_Cu)
			self.add_track(offset + VECTOR2I_MM( 76.8,  57.2), offset + VECTOR2I_MM( 83.8,  57.2), B_Cu)
			self.add_track(offset + VECTOR2I_MM( 83.8,  57.2), offset + VECTOR2I_MM( 94.0, 47.03), B_Cu)
			self.add_track(offset + VECTOR2I_MM( 93.9,  47.1), offset + VECTOR2I_MM( 94.7,  47.1), B_Cu)
			self.add_track(offset + VECTOR2I_MM( 94.7,  47.1), offset + VECTOR2I_MM( 95.8,  48.2), B_Cu)
			self.add_track(offset + VECTOR2I_MM( 95.8,  48.2), offset + VECTOR2I_MM(103.3,  48.2), B_Cu)
			self.add_track(offset + VECTOR2I_MM(103.3,  48.2), offset + VECTOR2I_MM(105.5,  46.0), B_Cu)
			self.add_track(offset + VECTOR2I_MM(105.5,  46.0), offset + VECTOR2I_MM(112.3,  46.0), B_Cu)
			self.add_track(offset + VECTOR2I_MM(112.3,  46.0), offset + VECTOR2I_MM(113.7,  44.6), B_Cu)
			self.add_track(offset + VECTOR2I_MM(113.7,  44.6), offset + VECTOR2I_MM(115.1,  46.0), B_Cu)
			self.add_track(offset + VECTOR2I_MM(115.1,  46.0), offset + VECTOR2I_MM(131.6,  46.0), B_Cu)
			self.add_track(offset + VECTOR2I_MM(131.6,  46.0), offset + VECTOR2I_MM(132.7,  47.1), B_Cu)
			self.add_track(offset + VECTOR2I_MM(132.7,  47.1), offset + VECTOR2I_MM(134.2,  48.6), B_Cu)
			self.add_track(offset + VECTOR2I_MM(134.2,  48.6), offset + VECTOR2I_MM(150.7,  48.6), B_Cu)
			self.add_track(offset + VECTOR2I_MM(150.7,  48.6), offset + VECTOR2I_MM(151.7,  49.6), B_Cu)
			# LEDx0
			self.add_track(offset + VECTOR2I_MM( 63.9,  56.1), offset + VECTOR2I_MM( 63.3,  56.1), B_Cu)
			self.add_track(offset + VECTOR2I_MM( 65.5,  54.5), offset + VECTOR2I_MM( 63.9,  56.1), B_Cu)
			self.add_track(offset + VECTOR2I_MM( 75.7,  54.5), offset + VECTOR2I_MM( 65.5,  54.5), B_Cu)
			# LEDx1
			self.add_track(offset + VECTOR2I_MM( 82.3,  56.1), offset + VECTOR2I_MM( 82.4,  56.1), B_Cu)
			self.add_track(offset + VECTOR2I_MM( 82.4,  56.1), offset + VECTOR2I_MM( 93.0,  45.5), B_Cu)
			self.add_track(offset + VECTOR2I_MM( 93.0,  45.5), offset + VECTOR2I_MM( 94.7,  45.5), B_Cu)
			# LEDx2
			self.add_track(offset + VECTOR2I_MM(101.3,  47.1), offset + VECTOR2I_MM(101.9,  47.1), B_Cu)
			self.add_track(offset + VECTOR2I_MM(101.9,  47.1), offset + VECTOR2I_MM(106.0,  43.0), B_Cu)
			self.add_track(offset + VECTOR2I_MM(106.0,  43.0), offset + VECTOR2I_MM(113.7,  43.0), B_Cu)
			# LEDx3
			self.add_track(offset + VECTOR2I_MM(120.3,  44.6), offset + VECTOR2I_MM(121.2,  45.5), B_Cu)
			self.add_track(offset + VECTOR2I_MM(121.2,  45.5), offset + VECTOR2I_MM(132.7,  45.5), B_Cu)
			# LEDx4
			self.add_track(offset + VECTOR2I_MM(139.3,  47.1), offset + VECTOR2I_MM(140.2,  48.0), B_Cu)
			self.add_track(offset + VECTOR2I_MM(140.2,  48.0), offset + VECTOR2I_MM(151.7,  48.0), B_Cu)
	
	def connect_leds_by_col(self):
		for sw_fp in self.get_fp_list('SW_Push'):
			sw_col = int(sw_fp.GetReference()[-1])
			sw_row = int(sw_fp.GetReference()[-2])
			offset = sw_fp.GetPosition()
			if sw_row == 0: # top row
				# power rail - left
				virtical_track_length = 3*self.sw_y_spc - (9.0-3.8)
				track_points = []
				self.add_track(offset + VECTOR2I_MM(-3.3, -5.5), offset + VECTOR2I_MM(-5.0, -5.5))	
				self.add_track(offset + VECTOR2I_MM(-5.0, -5.5), offset + VECTOR2I_MM(-6.7, -3.8))	
				self.add_track(offset + VECTOR2I_MM(-6.7, -3.8), offset + VECTOR2I_MM(-6.7, -3.8 + virtical_track_length)) 
				# power rail - right
				virtical_track_length = 3*self.sw_y_spc - (7.3-0.5)
				track_points = []
				self.add_track(offset + VECTOR2I_MM(3.3, -3.9), offset + VECTOR2I_MM(6.7, -0.5))
				self.add_track(offset + VECTOR2I_MM( 6.7, -0.5), offset + VECTOR2I_MM(6.7, -0.5 + virtical_track_length))
			else:
				# power rail - left
				self.add_track(offset + VECTOR2I_MM(-3.3, -5.6), offset + VECTOR2I_MM(-6.7, -9.0))	
				# power rail - right
				self.add_track(offset + VECTOR2I_MM(3.3, -3.9), offset + VECTOR2I_MM(6.7, -7.3))
				# led dout -> led din
				virtical_track_length = self.sw_y_spc - 2.6
				track_points = []
				track_points.append((offset + VECTOR2I_MM(-3.3, -5.5), B_Cu))
				track_points.append((offset + VECTOR2I_MM(-1.9, -6.9), B_Cu))
				track_points.append((offset + VECTOR2I_MM( 2.1, -6.9),   -1)) # via
				track_points.append((offset + VECTOR2I_MM( 2.1, -6.9-virtical_track_length), F_Cu))
				track_points.append((offset + VECTOR2I_MM( 3.3,-22.5), F_Cu)) 
				self.add_tracks(track_points)
			
	# Do all the things
	def Run(self):
		self.remove_old_tracks()
		self.place_sw()
		self.place_led()
		self.place_diode()
		self.connect_diode_and_sw()
		self.connect_rows()
		self.connect_pad1()
		self.connect_sw_col()
		self.connect_leds_by_col()
		self.place_via()
		pcbnew.Refresh()
		pcbnew.SaveBoard(self.filename, self.board)
		
#kbd_place_n_route().register()

def main():
	plugin = kbd_place_n_route()
	plugin.load_board()
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