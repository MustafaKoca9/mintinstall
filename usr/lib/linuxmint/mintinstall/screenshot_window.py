#!/usr/bin/python3
# encoding=utf-8
# -*- coding: UTF-8 -*-

from gi.repository import GLib, Gtk, GObject, Gdk
import cairo

class ScreenshotWindow(Gtk.Window):
    __gsignals__ = {
        'next-image': (GObject.SignalFlags.RUN_LAST, bool, (Gtk.DirectionType,))
    }

    def __init__(self, parent, multiple_screenshots):
        super().__init__(
            type=Gtk.WindowType.TOPLEVEL,
            decorated=False,
            transient_for=parent,
            destroy_with_parent=True,
            skip_taskbar_hint=True,
            skip_pager_hint=True,
            type_hint=Gdk.WindowTypeHint.UTILITY,
            name="ScreenshotWindow"
        )

        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        self.screen = Gdk.Screen.get_default()
        self.visual = self.screen.get_rgba_visual()

        if self.visual and self.screen.is_composited():
            self.set_visual(self.visual)
            self.set_app_paintable(True)
            self.connect("draw", self.on_draw)

        self.overlay = Gtk.Overlay()
        self.add(self.overlay)

        self.connect("realize", self.on_realize)

        self.multiple_screenshots = multiple_screenshots
        self.setup_cursors()

        self.connect("button-press-event", self.on_button_press_event)
        self.busy = False

        self.stack = Gtk.Stack(homogeneous=False, transition_duration=500, no_show_all=True)
        self.overlay.add(self.stack)

        self.setup_gestures()
        self.setup_event_controllers()

        self.first_image_name = None
        self.last_image_name = None

        if self.visual:
            self.show_all()
            self.present()

    def setup_cursors(self):
        display = Gdk.Display.get_default()
        self.loading_pointer = Gdk.Cursor.new_from_name(display, "wait")
        self.normal_pointer = Gdk.Cursor.new_from_name(display, "grab") if self.multiple_screenshots else None
        self.grabbing_pointer = Gdk.Cursor.new_from_name(display, "grabbing") if self.multiple_screenshots else None

    def setup_gestures(self):
        self.swipe_handler = Gtk.GestureSwipe.new(self)
        self.swipe_handler.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        self.swipe_handler.connect("swipe", self.swipe_or_button_release)

    def setup_event_controllers(self):
        self.scroll_handler = Gtk.EventControllerScroll.new(self, Gtk.EventControllerScrollFlags.VERTICAL)
        self.scroll_handler.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        self.scroll_handler.connect("scroll", self.on_scroll_event)
        self.previous_scroll_event_time = 0

    def on_realize(self, widget):
        self.window = self.get_window()
        self.set_busy(True)

    def set_busy(self, busy):
        self.busy = busy
        cursor = self.loading_pointer if busy else self.normal_pointer
        self.window.set_cursor(cursor)

    def on_button_press_event(self, window, event):
        if self.busy:
            return Gdk.EVENT_STOP
        self.window.set_cursor(self.grabbing_pointer)
        return Gdk.EVENT_PROPAGATE

    def has_image(self, location):
        return any(self.stack.child_get_property(image, "name") == location for image in self.stack.get_children())

    def any_images(self):
        return bool(self.stack.get_children())

    def add_image(self, image, location):
        if image.cancellable.is_cancelled():
            self.set_busy(False)
            return

        image.show()
        self.stack.add_named(image, location)
        self.first_image_name = self.first_image_name or location
        self.last_image_name = location
        self.show_image(location)

    def show_image(self, image_location):
        self.stack.show()
        self.set_busy(False)
        self.stack.set_visible_child_name(image_location)

        image = self.stack.get_visible_child()
        self.resize(image.width, image.height)

        if not self.visual:
            self.show_all()
            self.present()

    def emit_next_image(self, direction):
        if self.emit("next-image", direction):
            self.set_busy(True)
        else:
            self.set_busy(False)

    def on_key_press_event(self, window, event):
        keyval = event.get_keyval()[1]
        if keyval in (Gdk.KEY_Left, Gdk.KEY_KP_Left):
            self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_RIGHT)
            direction = Gtk.DirectionType.TAB_BACKWARD
        elif keyval in (Gdk.KEY_Right, Gdk.KEY_KP_Right):
            self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT)
            direction = Gtk.DirectionType.TAB_FORWARD
        else:
            self.hide()
            return Gdk.EVENT_STOP

        self.emit_next_image(direction)
        return Gdk.EVENT_STOP

    def on_scroll_event(self, controller, xd, yd):
        event_time = Gtk.get_current_event().get_time()
        if event_time == self.previous_scroll_event_time or not self.multiple_screenshots:
            return Gdk.EVENT_STOP

        direction = Gtk.DirectionType.TAB_BACKWARD if (xd < 0 or yd < 0) else Gtk.DirectionType.TAB_FORWARD
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_RIGHT if direction == Gtk.DirectionType.TAB_BACKWARD else Gtk.StackTransitionType.SLIDE_LEFT)

        self.previous_scroll_event_time = event_time
        self.emit_next_image(direction)
        return Gdk.EVENT_PROPAGATE

    def on_focus_out_event(self, window, event):
        GLib.timeout_add(200, lambda: self.hide())
        return Gdk.EVENT_STOP

    def swipe_or_button_release(self, handler, vx, vy):
        if self.busy:
            return

        self.window.set_cursor(self.normal_pointer)

        if vx == 0 and vy == 0:
            GLib.idle_add(self.hide)
            return

        if not self.multiple_screenshots:
            return

        direction = Gtk.DirectionType.TAB_FORWARD if vx < 0 else Gtk.DirectionType.TAB_BACKWARD
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT if vx < 0 else Gtk.StackTransitionType.SLIDE_RIGHT)
        self.emit_next_image(direction)

    def on_draw(self, window, cr):
        cr.set_source_rgba(0, 0, 0, 0)
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)
        return Gdk.EVENT_PROPAGATE
