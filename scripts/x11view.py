#!/usr/bin/env python3
"""DOOM viewer — reads PPM, displays via GTK3 Cairo."""
import gi, os, sys, array, traceback
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib
import cairo

PPM = "/tmp/doom_frame.ppm"
W, H = 320, 200
SCALE = 2
SW, SH = W * SCALE, H * SCALE

argb = array.array('B', [64] * (W * H * 4))
has_frame = False
frames = 0

def load_frame():
    global has_frame
    try:
        if not os.path.exists(PPM):
            return False
        with open(PPM, "rb") as f:
            line1 = f.readline()
            line2 = f.readline()
            line3 = f.readline()
            rgb = f.read(W * H * 3)
        if len(rgb) != W * H * 3:
            return False
        for i in range(W * H):
            argb[i*4] = rgb[i*3+2]
            argb[i*4+1] = rgb[i*3+1]
            argb[i*4+2] = rgb[i*3]
            argb[i*4+3] = 255
        has_frame = True
        return True
    except Exception as e:
        print(f"load error: {e}", file=sys.stderr)
        return False

def on_draw(widget, cr):
    if not has_frame:
        cr.set_source_rgb(0.2, 0.0, 0.0)
        cr.paint()
        cr.set_source_rgb(1, 1, 1)
        cr.move_to(10, 30)
        cr.set_font_size(16)
        cr.show_text("Waiting for DOOM...")
        cr.move_to(10, 55)
        cr.set_font_size(12)
        cr.show_text("Run: ./doom DOOM1.WAD")
        return
    try:
        surface = cairo.ImageSurface.create_for_data(
            argb, cairo.FORMAT_ARGB32, W, H, W * 4)
        cr.scale(SCALE, SCALE)
        cr.set_source_surface(surface, 0, 0)
        cr.get_source().set_filter(cairo.FILTER_NEAREST)
        cr.paint()
    except Exception as e:
        print(f"draw error: {e}", file=sys.stderr)

def on_tick(da):
    global frames
    if load_frame():
        frames += 1
        da.queue_draw()
        if frames % 30 == 0:
            da.get_toplevel().set_title(f"DOOM — frame {frames}")
    return True

win = Gtk.Window(title="DOOM — cyrius-doom")
win.set_default_size(SW, SH)
win.set_resizable(False)
win.connect("destroy", Gtk.main_quit)

da = Gtk.DrawingArea()
da.connect("draw", on_draw)
win.add(da)

win.show_all()
print(f"DOOM viewer ({SW}x{SH})")
print(f"Watching: {PPM}")
print("Window is open. Run: ./doom DOOM1.WAD")

GLib.timeout_add(30, on_tick, da)
Gtk.main()
