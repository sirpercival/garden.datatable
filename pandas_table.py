# -*- coding: utf-8 -*-

import pandas as pd
#from functools import wraps
from kivy.properties import (AliasProperty, BooleanProperty, DictProperty,
                             ListProperty, NumericProperty, ObjectProperty)
from kivy.uix.label import Label
from kivy.uix.popup import Popup
import inspect
import pydoc
from kivy.lang import Builder
from kivy.factory import Factory
from kivy.graphics import Color, InstructionGroup, Line


class Data(pd.DataFrame):
    """A wrapper for DataFrame with a generalized data loader."""
    allowed_types = {'csv': pd.DataFrame.from_csv,
                     'dict': pd.DataFrame.from_dict,
                     'items': pd.DataFrame.from_items,
                     'records': pd.DataFrame.from_records,
                     'recs': pd.DataFrame.from_records,
                     'rec': pd.DataFrame.from_records,
                     'table': pd.read_table,
                     'clipboard': pd.read_clipboard,
                     'hdf': pd.read_hdf,
                     'excel': pd.read_excel,
                     'sql': pd.read_sql,
                     'json': pd.read_json,
                     'html': pd.read_html,
                     'pickle': pd.read_pickle}

    def __init__(self, *args, **kw):
        '''
        TODO: figure out how to perform the wrapping correctly
              so that we can programmatically add load_*key* for each
              key in allowed_types as a wrapper for load. Could use
              partials, but I'd rather have wrappers.'''
        super(self.__class__, self).__init__(*args, **kw)

    @classmethod
    def load(cls, datatype, *args, **kw):
        '''This way, we can have one loader for the data instead
        of needing the user to ness around with a variety of pandas
        loaders. Any particular loading option will need to be set
        as per the pandas reader, of course...'''
        if datatype not in cls.allowed_types:
            raise TypeError('data type must be one of (' +
                            ', '.join([str(key) for key
                            in cls.allowed_types.keys()]) + ')')
        return cls.allowed_types[datatype](*args, **kw)


Builder.load_string("""
#:import ismethod inspect.ismethod

<FormEntry@BoxLayout>:
    text: ''
    default: ''
    value: val.text
    orientation: 'horizontal'
    size_hint_y: None
    height: '20dp'
    Label:
        text: root.text
        size_hint_x: 0.3
    TextInput:
        id: val
        multiline: False
        text: root.default
        size_hint_x: 0.7

<AxisPopup>:
    actions: [x for x in dir(self.data) if (ismethod(getattr(self.data, x))
              and not x.startswith('_'))]
    BoxLayout:
        orientation: 'horizontal'
        BoxLayout:
            orientation: 'vertical'
            BoxLayout:
                orientation: 'horizontal'
                size_hint_y: None
                height: '20dp'
                Label:
                    text: 'Label: '
                TextInput:
                    id: aname
                    text: str(root.axname)
                    multiline: False
                Button:
                    text: 'Update'
                    on_press: root.rename()
            Spinner:
                id: action_choose
                text: 'Choose an action'
                values: root.actions
                on_text: root.update_action(self.text)
                size_hint: 0.8, None
                height: '20dp'
            Label:
                id: info_label
                text: ''
            BoxLayout:
                orientation: 'horizontal'
                size_hint_y: None
                height: '20dp'
                Button:
                    text: 'Go'
                    on_press: root.take_action()
                Button:
                    text: 'Cancel'
                    on_press: root.dismiss()
        ScrollView:
            do_scroll_y: True
            GridLayout:
                cols: 1
                id: func_args
                size_hint_y: None
                height: self.minimum_height

<ColumnPopup>:
    series: self.data.icol[self.column]
    axname: self.data.columns[self.column]
    title: 'Actions for column '+str(self.colname)

<RowPopup>:
    series: self.data.irow[self.row]
    axname: str(self.data.rows[self.column])
    title: 'Actions for row '+str(self.rowname)

<CellPopup>:
    size_hint: 0.4, 0.7
    BoxLayout:
        orientation: 'vertical'
        FormEntry:
            text: 'Cell value:'
            default: self.data.iloc[self.cell_coords[0], self.cell_coords[1]]
        BoxLayout:
            orientation: 'horizontal'
            Label:
                text: 'Cell type'
            Spinner:
                id: celltype
                values: root.celltypes.keys()
        Button:
            text: 'Update Cell'
            on_press: root.update_cell()
""")


class AxisPopup(Popup):
    actions = ListProperty([])
    data = ObjectProperty(None)
    series = ObjectProperty(None)
    axname = ObjectProperty(None)
    action = ObjectProperty(None)

    def update_action(self, text):
        o, n = pydoc.resolve(self.data, getattr(self.data, text))
        self.ids.info_label.text = pydoc.text.document(o, n)
        self.action = getattr(self.data, self.ids.action_choose.text)
        self.ids.func_args.clear_widgets()
        argspec = inspect.getargspec(self.action)
        args, defs = argspec.args[1:], argspec.defaults
        while len(defs) < len(args):
            defs = [''] + defs
        for i, a in enumerate(args):
            entry = Factory.FormEntry(text=a,
                                      default=defs[i])
            self.ids.func_args.add_widget(entry)

    def take_action(self):
        kw = {x.text: x.value for x in self.ids.func_args.children}
        self.action(self.data, **kw)


class ColumnPopup(AxisPopup):
    column = NumericProperty(0)

    def rename(self, text):
        self.data.rename(columns={self.axname: self.ids.aname.text})


class RowPopup(AxisPopup):
    row = NumericProperty(0)

    def rename(self, text):
        self.data.rename(index={self.axname: self.ids.aname.text})


class CellPopup(Popup):
    '''Popup for editing a cell.
       TODO: use pyparsing to allow calculated cells
       TODO: add more allowed types'''

    data = ObjectProperty(None)
    cell_coords = ListProperty([0, 0])
    celltypes = DictProperty({'int': int,
                              'float': float,
                              'long': long,
                              'complex': complex,
                              'str': str,
                              'bool': bool,
                              'unicode': unicode})

    def on_open(self):
        x, y = self.cell_coords
        for s, t in self.celltypes.items():
            if type(self.data.iloc[x, y]) == t:
                self.ids.celltype.text = s


class DataTable(Label):
    data = ObjectProperty(Data(index=range(10), columns=range(5)))
    format_keywords = DictProperty({})
    gridaxes = DictProperty({})
    gridlines = ObjectProperty(InstructionGroup())
    grid = BooleanProperty(True)

    def __init__(self, **kw):
        '''Need to ensure that markup is enabled, and then set
        the text of the label to the markup version of the data.'''
        super(Label, self).__init__(**kw)
        self.markup = True
        self.text = self.markup_text
        fmt = inspect.getargspec(self.data.to_string)
        self.format_keywords = dict(zip(fmt.args[2:],
                                        fmt.defaults[2:]))
        if self.grid:
            self.draw_grid()
            self.canvas.add(self.gridlines)

    def _get_markup(self):
        '''Getter for the markup_text AliasProperty, so that we can
        use refs to interact with the table.
        TODO: figure out how to handle format keywords without
              getting messed up by ref insertion...'''
        text = self.data.copy()
        rows, cols = [x.to_list() for x in text.axes]
        ref = lambda x, y, z: "[ref='{}-{}']{}[/ref]".format(str(x),
                                                             str(y),
                                                             str(z))
        for i, row in enumerate(rows):
            for j, col in enumerate(cols):
                text[row, col] = ref(i, j, text[row, col])
        rows = {row: ref(i, 'r', row) for i, row in enumerate(rows)}
        cols = {col: ref('c', i, col) for i, col in enumerate(cols)}
        text.rename(index=rows, columns=cols, inplace=True)
        #return text.to_string(**self.format_keywords)
        return text.to_string()

    markup_text = AliasProperty(_get_markup, None, bind=('data'))

    @staticmethod
    def get_x(label, ref_x):
        """ Return the x value of the ref relative to the canvas """
        return label.center_x - label.texture_size[0] * 0.5 + ref_x

    @staticmethod
    def get_y(label, ref_y):
        """ Return the y value of the ref relative to the canvas """
        # Note the inversion of direction, as y values start at the top of
        # the texture and increase downwards
        return label.center_y + label.texture_size[1] * 0.5 - ref_y

    def _get_gridaxes(self):
        '''Getter for the gridaxes AliasProperty, which defines
        the axes for grid-drawing purposes'''
        lox, hiy, hix, loy = zip(*self.refs.values())
        lox = map(self.get_x, lox)
        hix = map(self.get_x, hix)
        loy = map(self.get_y, loy)
        hiy = map(self.get_y, hiy)
        lx = min(lox)
        hx = max(hix)
        ly = min(loy)
        hy = max(hiy)
        #now we use the ref ids to split by rows & columns

        class Cell(object):
            def __init__(self, name, box):
                r, c = name.split('-')
                self.row = 0 if r == 'r' else int(r) + 1
                self.col = 0 if c == 'c' else int(c) + 1
                self.box = box
                self.lox, self.hiy, self.hix, self.loy = box
        cells = map(Cell, self.refs.items())
        ncol = max([x.col for x in cells])
        nrow = max([x.row for x in cells])
        colpoints = [lx]
        current_colx = lx
        rowpoints = [hy]
        current_rowy = hy
        for i in range(ncol + 1):
            thiscol = filter(lambda x: x.col == i, cells)
            locol = min([x.lox for x in thiscol])
            hicol = max([x.hix for x in thiscol])
            if locol > current_colx:
                colpoints.append((locol + current_colx) / 2.)
            current_colx = hicol
        colpoints.append(hx)
        for i in range(nrow + 1):
            thisrow = filter(lambda x: x.row == i, cells)
            lorow = min([x.loy for x in thisrow])
            hirow = max([x.hiy for x in thisrow])
            if hirow < current_rowy:
                rowpoints.append((hirow + current_rowy) / 2.)
            current_rowy = lorow
        rowpoints.append(ly)
        return {'cols': colpoints, 'rows': rowpoints}

    gridaxes = AliasProperty(_get_gridaxes, None, bind=('refs'))

    def draw_grid(self):
        lx, hx, ly, hy = (min(self.gridaxes['cols']),
                          max(self.gridaxes['cols']),
                          min(self.gridaxes['rows']),
                          max(self.gridaxes['rows']))
        self.gridlines.clear()
        self.gridlines.add(Color(0.5, 0.5, 0.5))
        for c in self.gridaxes['cols']:
            self.gridlines.add(Line(points=[c, ly, c, hy], cap='none'))
        for r in self.gridaxes['rows']:
            self.gridlines.add(Line(points=[lx, r, hx, r], cap='none'))

    def on_ref_press(self, cell):
        row, col = cell.split('-')
        if row == 'c':
            popup = ColumnPopup()
            popup.open()
        elif col == 'r':
            popup = RowPopup()
            popup.open()
        else:
            popup = CellPopup()
            popup.open()

if __name__ == "__main__":
    from kivy.base import runTouchApp
    runTouchApp(DataTable(grid=False))
