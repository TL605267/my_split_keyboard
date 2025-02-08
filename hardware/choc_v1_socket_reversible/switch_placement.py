#!/usr/bin/env python3
import os,sys, pcbnew
from pcbnew import wxPoint, wxPointMM, wxSize, VECTOR2I, VECTOR2I_MM, FromMM, ToMM, F_Cu, B_Cu, LoadBoard, SaveBoard, Refresh
from math import sin, cos, radians, ceil

def add_track(start, end, layer=F_Cu):
	#board = pcbnew.GetBoard()
	track = pcbnew.PCB_TRACK(board)
	track.SetStart(start)
	track.SetEnd(end)
	#track.SetWidth(FromMM(0.5)) # default 0.2mm
	track.SetLayer(layer)
	board.Add(track)

def add_tracks(points):
	for i in range(len(points)-1):
		if (points[i+1][1] < 0): # via
			add_via(points[i+1][0], 0.3, 0.6)
			add_track(points[i][0], points[i+1][0], points[i][1])
		else: #F_Cu, B_Cu
			add_track(points[i][0], points[i+1][0], points[i+1][1])
	
def add_via(pos, drill, width):
	#board = pcbnew.GetBoard()
	via = pcbnew.PCB_VIA(board)
	via.SetPosition(pos)
	via.SetDrill(FromMM(drill)) # defaults 0.4mm, 0.8mm
	via.SetWidth(FromMM(width))
	board.Add(via)

def place_fp(pos, fp, orientation):
	fp.SetPosition(pos) 
	fp.SetOrientationDegrees(orientation)
	
def rotate(origin, point, angle):
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

def get_fp_list(fp_val):
	return [(fp.GetReference(), fp) for fp in board.GetFootprints() if fp.GetValue() == fp_val]

def get_existing_track(netname):
	s_list = []
	s_offset = VECTOR2I(69500000, 59062500)
	for t in board.GetTracks():
		if t.GetNetname() == netname:
			#track_points.append((padk_pos + VECTOR2I_MM(39.0, -12.5), B_Cu))
			sx = round(ToMM((t.GetStart()-s_offset).x), 1)
			sy = round(ToMM((t.GetStart()-s_offset).y), 1)
			ex = round(ToMM((t.GetEnd()  -s_offset).x), 1)
			ey = round(ToMM((t.GetEnd()  -s_offset).y), 1)
			format_code = f"add_track(padk_pos + VECTOR2I_MM({sx:>5.1f}, {sy:>5.1f}), padk_pos + VECTOR2I_MM({ex:>5.1f}, {ey:>5.1f}), B_Cu)"
			print(format_code)

#filename = sys.argv[1]
filename = [file for file in os.listdir('.') if file.endswith('.kicad_pcb')][0]
print(filename)
board = LoadBoard(filename)

for t in board.GetTracks():
    board.Delete(t)
Refresh()
# Do all the things
# place switches and leds
col_offsets = [0, 0, -9, -11.5, -9, -6.5]
sw0_x = 60
sw0_y = 60
sw0_pos = VECTOR2I_MM(60,60)
sw_x_spc = 19# 17.5 #19.05
sw_y_spc = 17 #19.05
for (sw_ref, sw_fp) in get_fp_list('SW_Push'): 
	sw_row = int(sw_ref[2])
	sw_col = int(sw_ref[3])
	idx = sw_ref[-2:]
	sw_orienation = 0
	if(sw_col < 6): # 4 fingers
		sw_offset = VECTOR2I_MM(sw_x_spc*sw_col, sw_y_spc*sw_row + col_offsets[sw_col])
		sw_orienation = 0
	# thumb, respective to index bottom switch
	elif (sw_col == 6): 
		sw_offset = VECTOR2I_MM(sw_x_spc*5+2.9, sw_y_spc*3+14.8)
		sw_orienation = -23
	else: # 7 
		sw_offset = VECTOR2I_MM(sw_x_spc*5+23.8, sw_y_spc*3+19.8)
		sw_orienation = 60
	# place switches
	place_fp(sw0_pos+sw_offset, sw_fp, sw_orienation)

# place LEDs
for (led_ref, led_fp) in get_fp_list('SK6812MINI'):
	idx = led_ref[-2:]
	sw_row = int(idx[0])
	sw_col = int(idx[1])
	sw_pos = board.FindFootprintByReference('SW'+idx).GetPosition()
	led_pos = sw_pos + VECTOR2I_MM(0, -4.7)
	if(sw_col < 6): 
		if(sw_row % 2 == 0): # row0/row2
			place_fp(led_pos, led_fp, 180)
		else:
			place_fp(led_pos, led_fp, 0)
	elif(sw_col == 6):
		place_fp(led_pos, led_fp, -23)
	else: # 7
		place_fp(led_pos, led_fp, 60)

# place diode
for (d_ref, d_fp) in get_fp_list('BAV70'):
	# get left switch position
	sw_ref_l = 'SW'+d_ref[1:3]
	sw_fp_l = board.FindFootprintByReference(sw_ref_l)
	sw_pos_l_x = sw_fp_l.GetPosition().x
	sw_pos_l_y = sw_fp_l.GetPosition().y
	# get right switch position
	sw_ref_r = 'SW'+d_ref[3:5]
	sw_fp_r = board.FindFootprintByReference(sw_ref_r)
	sw_pos_r_x = sw_fp_r.GetPosition().x
	sw_pos_r_y = sw_fp_r.GetPosition().y
	# place diode in between switches
	d_pos = VECTOR2I((sw_pos_l_x + sw_pos_r_x)>>1, min(sw_pos_l_y, sw_pos_r_y))
	place_fp(d_pos, d_fp, 90)

# place vias
via_offset_x = [-3.4, -2.8, 2.8, 3.4]
for (led_ref, led_fp) in get_fp_list('SK6812MINI'):
	led_pos = led_fp.GetPosition()
	for i in range(4): 
		via_pos = led_pos + VECTOR2I_MM(via_offset_x[i], 0)
		add_via(via_pos, 0.3, 0.4)
		led1_pos = led_pos + VECTOR2I_MM(via_offset_x[i], -0.5)
		led2_pos = led_pos + VECTOR2I_MM(via_offset_x[i], 0.5)
		if (i%2 == 0):
			add_track(led1_pos, via_pos, pcbnew.F_Cu)
			add_track(led2_pos, via_pos, pcbnew.B_Cu)
		else:
			add_track(led1_pos, via_pos, pcbnew.B_Cu)
			add_track(led2_pos, via_pos, pcbnew.F_Cu)

# connect switch pad1 on both sides
for (sw_ref, sw_fp) in get_fp_list('SW_Push'): 
	sw_pos = sw_fp.GetPosition()
	# pad1
	track_points = []
	track_points.append((sw_pos+(VECTOR2I_MM( 3.3, 6.0)), B_Cu))
	track_points.append((sw_pos+(VECTOR2I_MM( 1.5, 4.0)), B_Cu))
	track_points.append((sw_pos+(VECTOR2I_MM(-2.2, 4.0)), -1  )) #Via
	add_tracks(track_points)

# connect diode and switches pad2
for (d_ref, d_fp) in get_fp_list('BAV70'):
	# get left switch position
	sw_ref_l = 'SW'+d_ref[1:3]
	sw_fp_l = board.FindFootprintByReference(sw_ref_l)
	sw_pos_l = sw_fp_l.GetPosition()
	sw_l_pad2_y = [p for p in sw_fp_l.Pads() if p.GetNumber() == '2'][0].GetCenter().y
	d_p1_pos = d_fp.FindPadByNumber('1').GetCenter()
	track_points = []
	track_points.append((VECTOR2I(d_p1_pos.x, sw_l_pad2_y), F_Cu))
	track_points.append((d_p1_pos, F_Cu))
	track_points.append((sw_pos_l+VECTOR2I_MM( 5.8, 2.0), B_Cu))
	track_points.append((sw_pos_l+VECTOR2I_MM(-6.5, 2.0), B_Cu))
	track_points.append((sw_pos_l+VECTOR2I_MM(-8.2, 3.6), B_Cu))
	add_tracks(track_points)
	# get right switch position
	sw_ref_r = 'SW'+d_ref[3:5]
	sw_fp_r = board.FindFootprintByReference(sw_ref_r)
	sw_pos_r = sw_fp_r.GetPosition()
	sw_r_pad2_y = [p for p in sw_fp_r.Pads() if p.GetNumber() == '2'][0].GetCenter().y
	d_p2_pos = d_fp.FindPadByNumber('2').GetCenter()
	track_points = []
	track_points.append((d_p2_pos, B_Cu))
	track_points.append((VECTOR2I(d_p2_pos.x, sw_r_pad2_y), B_Cu))
	track_points.append((sw_pos_r+VECTOR2I_MM(-6.5, 2.0), B_Cu))
	track_points.append((sw_pos_r+VECTOR2I_MM( 6.5, 2.0), -1)) # via
	track_points.append((sw_pos_r+VECTOR2I_MM( 8.2, 3.6), F_Cu))
	add_tracks(track_points)
		
# connect col pad from top to bottom
for col in range(6): # 6 column
	start = sw0_pos + VECTOR2I_MM(-2.2, 4.0) + VECTOR2I_MM(sw_x_spc*col, col_offsets[col])
	end   = sw0_pos + VECTOR2I_MM(-2.2, 5.2) + VECTOR2I_MM(sw_x_spc*col, col_offsets[col]+ sw_y_spc*3)
	add_track(start, end, F_Cu)

# connect rows
# [(t.GetStart().x, t.GetStart().y) for t in board.GetTracks() if t.GetNetname() == 'ROW0']
for padk in [fp.FindPadByNumber('3') for fp in board.GetFootprints() if (fp.GetValue() == 'BAV70' and fp.GetReference().endswith('1'))]: # 4 rows
	padk_pos = padk.GetCenter()
	add_track(padk_pos + VECTOR2I_MM( 39.0, -12.5), padk_pos + VECTOR2I_MM( 52.6, -12.5), B_Cu)
	add_track(padk_pos + VECTOR2I_MM( 38.0, -11.5), padk_pos + VECTOR2I_MM( 39.0, -12.5), B_Cu)
	add_track(padk_pos + VECTOR2I_MM( 37.7, -11.5), padk_pos + VECTOR2I_MM( 38.0, -11.5), B_Cu)
	add_track(padk_pos + VECTOR2I_MM(  1.0,  -1.0), padk_pos + VECTOR2I_MM( 13.9,  -1.0), B_Cu)
	add_track(padk_pos + VECTOR2I_MM( 55.1, -10.0), padk_pos + VECTOR2I_MM( 75.0, -10.0), B_Cu)
	add_track(padk_pos + VECTOR2I_MM(  0.0,   0.0), padk_pos + VECTOR2I_MM(  1.0,  -1.0), B_Cu)
	add_track(padk_pos + VECTOR2I_MM( 13.9,  -1.0), padk_pos + VECTOR2I_MM( 22.9, -10.0), B_Cu)
	add_track(padk_pos + VECTOR2I_MM( 36.2, -10.0), padk_pos + VECTOR2I_MM( 37.7, -11.5), B_Cu)
	add_track(padk_pos + VECTOR2I_MM( 75.0, -10.0), padk_pos + VECTOR2I_MM( 76.0,  -9.0), B_Cu)
	add_track(padk_pos + VECTOR2I_MM( 22.9, -10.0), padk_pos + VECTOR2I_MM( 36.2, -10.0), B_Cu)
	add_track(padk_pos + VECTOR2I_MM( 52.6, -12.5), padk_pos + VECTOR2I_MM( 55.1, -10.0), B_Cu)

Refresh()
SaveBoard(filename, board)
'''
get_existing_track('ROW0')
'''