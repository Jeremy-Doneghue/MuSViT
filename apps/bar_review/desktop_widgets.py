"""Reusable BUI image, range-editing and resizable-region components.

Widgets communicate through callbacks and do not depend on the application host.
Keep the synchronous RGBA image path here: it avoids BUI's native async crash.
"""
from math import ceil

from PIL import Image as PILImage, ImageDraw, ImageFont
from blenderui.components import (
    Checkbox, Column, Component, Image, NumberField, NumberSlider, Panel, Row,
)


class RasterImage(Image):
    """Supply decoded pixels to BUI, avoiding 0.4.1's macOS async callback.

    The wheel's image-poll wake can invoke a Python Tk redraw without holding
    the GIL. Pillow decoding on the UI thread avoids that native callback;
    BUI still owns layout, fitting and drawing. Unchanged pages are reused.
    """
    @Image.src.setter
    def src(self, path):
        path = str(path or '')
        if path and path == self._src:
            return
        self._src = path
        self.set_image_source(None, self.FITS[self._fit])
        if path:
            with PILImage.open(path) as opened:
                image = opened.convert('RGBA')
                self.set_image(image.width, image.height, image.tobytes())

    def show_pixels(self, image):
        """Visible pixels already exist in memory; no PNG write/read round trip."""
        rgba = image.convert('RGBA')
        self.set_image(rgba.width, rgba.height, rgba.tobytes())


class PageImage(RasterImage):
    """A clipped image viewport; only visible pixels are supplied to BUI."""
    def __init__(self, on_pan, on_zoom):
        super().__init__('', fit='fill', fill=True)
        self.geom(0, reqwidth=1, reqheight=1)
        self.on_pan, self.on_zoom = on_pan, on_zoom
        self.picture = None
        self.center = (.5, .5)
        self.zoom = 'Fit page'
        self.scale = 1
        self.offset = (0, 0)
        self.drag = None
        self._draw_key = None
        self._reduced_key = None
        self._reduced = None
        self.set('events', True)

    def show_page(self, picture, center, zoom):
        self.picture, self.center, self.zoom = picture, center, zoom
        self.draw_view()

    def clear_page(self):
        self.picture=None
        self._draw_key = self._reduced_key = self._reduced = None
        self.set_image()

    def draw_view(self):
        if self.picture is None or self.w < 2 or self.h < 2:
            return
        image = self.picture
        self.scale = (min(self.w/image.width, self.h/image.height) if self.zoom == 'Fit page'
                      else float(self.zoom.removesuffix('%'))/100)
        width, height = self.w/self.scale, self.h/self.scale
        left = (max(0, min(image.width-width, self.center[0]*image.width-width/2))
                if width < image.width else (image.width-width)/2)
        top = (max(0, min(image.height-height, self.center[1]*image.height-height/2))
               if height < image.height else (image.height-height)/2)
        self.offset = left, top
        draw_key = (image, self.w, self.h, self.scale, left, top)
        if draw_key == self._draw_key:
            return
        if self.scale < 1:
            # Downsample once per source/zoom. Panning then only copies pixels;
            # never allocate a magnified full-page cache at 100–400% zoom.
            reduced_key = (image, self.scale)
            if reduced_key != self._reduced_key:
                self._reduced = image.transform(
                    (ceil(image.width*self.scale), ceil(image.height*self.scale)),
                    PILImage.Transform.AFFINE,
                    (1/self.scale, 0, 0, 0, 1/self.scale, 0),
                    resample=PILImage.Resampling.BICUBIC, fillcolor=(48,48,48))
                self._reduced_key = reduced_key
            view = self._reduced.transform((self.w, self.h), PILImage.Transform.AFFINE,
                (1, 0, left*self.scale, 0, 1, top*self.scale),
                resample=PILImage.Resampling.NEAREST, fillcolor=(48,48,48))
        else:
            self._reduced = self._reduced_key = None
            view = image.transform((self.w, self.h), PILImage.Transform.AFFINE,
                (1/self.scale, 0, left, 0, 1/self.scale, top),
                resample=PILImage.Resampling.NEAREST, fillcolor=(48,48,48))
        self.show_pixels(view)
        self._draw_key = draw_key

    def pan(self, dx, dy):
        if self.picture is None:
            return
        image = self.picture
        width, height = self.w/self.scale, self.h/self.scale
        if width >= image.width and height >= image.height:
            return
        left = max(0, min(max(0, image.width-width), self.offset[0]-dx/self.scale))
        top = max(0, min(max(0, image.height-height), self.offset[1]-dy/self.scale))
        x = (left+width/2)/image.width if width < image.width else .5
        y = (top+height/2)/image.height if height < image.height else .5
        self.on_pan(x, y)

    def _on_event(self, kind, ref, a, b):
        if kind == 19:  # Resize/workspace change; redraw at the actual viewport size.
            self.draw_view()
        elif kind in (8, 10):  # A quick second press must also start a drag.
            self.drag = (a, b)
        elif kind == 9:
            self.drag = None
        elif kind == 11 and self.drag is not None:
            previous, self.drag = self.drag, (a,b)
            self.pan(a-previous[0], b-previous[1])
        elif kind == 15:  # Raw wheel ref carries modifier bits; a is delta.
            mods = int(ref.split()[0])
            if mods & 2:
                self.on_zoom(1 if a > 0 else -1)
            elif mods & 1:
                self.pan(a*48, 0)
            else:
                self.pan(0, a*48)


class SourceText(RasterImage):
    """Read-only, line-numbered source with independent two-axis scrolling.

    BUI 0.4.1 has only single-line text fields. Draw just the visible lines using
    the existing synchronous pixel path; retain the original text unchanged.
    """
    def __init__(self):
        super().__init__('', fit='fill', fill=True)
        self.geom(0, reqwidth=1, reqheight=1)
        self.set('events', True)
        for name in ('/System/Library/Fonts/Menlo.ttc', 'DejaVuSansMono.ttf'):
            try:
                self.font = ImageFont.truetype(name, 13)
                break
            except OSError:
                continue
        else:
            self.font = ImageFont.load_default()
        self.line_height = 19
        self.text = ''
        self.lines = []
        self.message = ''
        self.first_line = self.horizontal = 0
        self.max_width = 0

    def show_source(self, text='', message=''):
        self.text, self.message = text, message
        self.lines = text.expandtabs(12).splitlines()
        self.first_line = self.horizontal = 0
        self.max_width = max((self.font.getlength(line) for line in self.lines), default=0)
        self.draw_text()

    def top(self):
        self.first_line = self.horizontal = 0
        self.draw_text()

    def draw_text(self):
        if self.w < 2 or self.h < 2:
            return
        count = max(1, (self.h-8)//self.line_height)
        self.first_line = int(max(0, min(self.first_line, len(self.lines)-count)))
        gutter = max(42, int(self.font.getlength(str(len(self.lines))))+18)
        self.horizontal = max(0, min(self.horizontal, int(max(0, self.max_width-self.w+gutter+12))))
        image = PILImage.new('RGB', (self.w, self.h), (247,248,250))
        draw = ImageDraw.Draw(image)
        for row, line in enumerate(self.lines[self.first_line:self.first_line+count]):
            draw.text((gutter+6-self.horizontal, 4+row*self.line_height), line,
                      font=self.font, fill=(30,37,47))
        draw.rectangle((0, 0, gutter, self.h), fill=(231,234,239))
        for row in range(min(count, len(self.lines)-self.first_line)):
            number = str(self.first_line+row+1)
            draw.text((gutter-8-self.font.getlength(number), 4+row*self.line_height), number,
                      font=self.font, fill=(98,106,120))
        if not self.lines:
            # Fit placeholder text without requiring horizontal scrolling.
            import textwrap
            width = max(12, int((self.w-gutter-16)/self.font.getlength('M')))
            for row, line in enumerate(textwrap.wrap(self.message, width)):
                draw.text((gutter+6, 8+row*self.line_height), line, font=self.font, fill=(80,88,100))
        self.show_pixels(image)

    def _on_event(self, kind, ref, a, b):
        if kind == 19:
            self.draw_text()
        elif kind == 15:
            if int(ref.split()[0]) & 1:
                self.horizontal -= a*48
            else:
                self.first_line -= a*3
            self.draw_text()


class NumericParameter(Column):
    """Fixed value or seeded uniform range, with bounded numeric endpoints."""
    def __init__(self, item, key, field, on_edit, preview_values=None, displayed_values=None):
        self.item, self.key, self.field, self.on_edit = item, key, field, on_edit
        self.preview_values = preview_values if preview_values is not None else {}
        options = dict(min=field['min'],max=field['max'],step=field['step'],
                       integer=field['step']==1,precision=2)
        value = item['parameters'][key]
        ranged = key in item.get('ranges',{})
        self.saved_bounds = list(item['ranges'][key]) if ranged else None
        low,high = item.get('ranges',{}).get(key,[value,value])
        if ranged:
            value=self.preview_values.get(item['id'],{}).get(key,
                (displayed_values or {}).get(item['id'],{}).get(key,value))
            value=max(low,min(high,value))
            options.update(min=low,max=high)
        self.fixed = NumberSlider(field['label'],value,on_change=self.change_fixed,
            description='Current preview value; edit and Generate to try a specific value',**options)
        bounds_options={**options,'min':field['min'],'max':field['max']}
        self.low = NumberField('Min',low,on_change=lambda value:self.change_bound(0,value),**bounds_options)
        self.high = NumberField('Max',high,on_change=lambda value:self.change_bound(1,value),**bounds_options)
        self.bounds = Row(self.low,self.high,visible=ranged,spacing=4)
        self.toggle = Checkbox('Range',ranged,on_change=self.toggle_range,weight=.3,
                               description='Sample a value between Min and Max using the recipe seed')
        super().__init__(Row(self.fixed,self.toggle,spacing=4),self.bounds,spacing=4)

    def change_fixed(self,value):
        self.item['parameters'][self.key]=value
        if self.key in self.item.get('ranges',{}):
            self.preview_values.setdefault(self.item['id'],{})[self.key]=value
        self.on_edit()

    def toggle_range(self,enabled):
        if enabled:
            bounds = (list(self.saved_bounds) if self.saved_bounds is not None else
                      [self.field['min'],self.field['max']] if self.item['type']=='rotation'
                      else [self.fixed.value,self.fixed.value])
            self.item.setdefault('ranges',{})[self.key]=bounds
            self.low.set_value(bounds[0],notify=False)
            self.high.set_value(bounds[1],notify=False)
        else:
            self.saved_bounds = list(self.item['ranges'][self.key])
            self.item['parameters'][self.key]=self.fixed.value
            self.item.get('ranges',{}).pop(self.key,None)
            if not self.item.get('ranges'):
                self.item.pop('ranges',None)
            self.preview_values.get(self.item['id'],{}).pop(self.key,None)
        self.update_limits()
        self.bounds.visible = enabled
        self.on_edit()

    def change_bound(self,index,value):
        bounds=self.item['ranges'][self.key]
        bounds[index]=value
        if bounds[0]>bounds[1]:
            bounds[1-index]=value
            (self.high if index==0 else self.low).set_value(value,notify=False)
        self.update_limits()
        self.on_edit()

    def update_limits(self):
        low,high=self.item.get('ranges',{}).get(self.key,[self.field['min'],self.field['max']])
        self.fixed.set('min',low)
        self.fixed.set('max',high)
        value=max(low,min(high,self.fixed.value))
        self.fixed.set_value(value,notify=False)
        overrides=self.preview_values.get(self.item['id'],{})
        if self.key in overrides:
            overrides[self.key]=value


class ResizeDivider(Component):
    """Blender-style region edge, driven by the kit's captured pointer events."""
    TYPE = 'frame'

    def __init__(self, row, index):
        super().__init__(weight=0, description='Drag to resize · double-click to reset widths')
        self.row, self.index, self.drag = row, index, None
        self.geom(0, reqwidth=7, reqheight=1)
        self.set('events', True)
        self.set('cursor', 1)  # Horizontal resize cursor.
        self.set('bg', (.14,.14,.14,1))

    def _on_event(self, kind, ref, a, b):
        if kind == 8:
            left, right = self.row.panes[self.index:self.index+2]
            self.drag = (self.x+a, left.w, left.w+right.w, left.weight+right.weight)
        elif kind == 11 and self.drag:
            x, width, total, weight = self.drag
            low, high = self.row.minimums[self.index:self.index+2]
            # If a window is smaller than both minima, retain usable proportions.
            factor = min(1, total/(low+high))
            size = max(low*factor, min(total-high*factor, width+self.x+a-x))
            left, right = self.row.panes[self.index:self.index+2]
            left.weight, right.weight = weight*size/total, weight*(total-size)/total
        elif kind == 9:
            self.drag = None
        elif kind == 10:
            self.drag = None
            self.row.reset_sizes()
        elif kind == 12:
            self.set('bg', (.30,.40,.55,1))
        elif kind == 13:
            self.set('bg', (.14,.14,.14,1))


class ResizableRow(Row):
    def __init__(self, *panes, minimums, **kwargs):
        self.panes, self.minimums = list(panes), list(minimums)
        self.default_weights = [pane.weight for pane in panes]
        self.dividers = [ResizeDivider(self, i) for i in range(len(panes)-1)]
        children = []
        for index, pane in enumerate(panes):
            if index:
                children.append(self.dividers[index-1])
            children.append(pane)
        super().__init__(*children, spacing=0, **kwargs)

    def sync_visibility(self):
        for index, divider in enumerate(self.dividers):
            divider.visible = self.panes[index].visible and self.panes[index+1].visible

    def reset_sizes(self):
        for pane, weight in zip(self.panes, self.default_weights):
            pane.weight = weight


class RecipePanel(Panel):
    """Keep Blender's native panel-grip reordering in the executable recipe."""
    def __init__(self, *args, recipe_item, on_order, **kwargs):
        super().__init__(*args, **kwargs)
        self.recipe_item = recipe_item
        self.on_order = on_order
        self.set('events', True)

    def _on_event(self, kind, ref, a, b):
        super()._on_event(kind, ref, a, b)
        if kind == 9:  # BK_EV_RELEASE; motion has already reordered siblings.
            self.on_order()
