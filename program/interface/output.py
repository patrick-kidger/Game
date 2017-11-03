import Tools as tools


import config.config as config
import config.internal_strings as internal_strings
import config.strings as strings

import program.interface.base as base
import program.interface.menu_elements as menu_elements

import program.misc.helpers as helpers
import program.misc.sdl as sdl


class BaseOverlay(base.BaseIO, helpers.EnablerMixin, helpers.NameMixin):
    """Abstract base class for all overlays. An 'overlay' is a layer on the screen that may be outputted to."""
    default_output_kwargs = {}

    def __init__(self, name, location, size, background_color, *args, **kwargs):
        super(BaseOverlay, self).__init__(name=name, enabled=False, *args, **kwargs)
        self.location = location
        self.screen = sdl.Surface(size)
        self.background_color = background_color

        self.reset()

    def reset(self, flush=False):
        """Resets all extra data associated with this overlay."""
        self.wipe(flush)

    def __call__(self, output_val, flush=False):
        # Just a convenience, to allow for just calling with flush=True as an argument, rather than putting an
        # output.flush() on the next line.
        if flush:
            self.out.flush()

    def wipe(self, flush=False):
        """Fills the overlay with its background color."""
        self.screen.fill(self.background_color)
        if flush:
            self.out.flush()


class GraphicsOverlay(BaseOverlay):
    """Handles outputting graphics to the screen."""


class MenuOverlay(GraphicsOverlay, base.FontMixin, helpers.AlignmentMixin):
    """A graphics overlay for menus."""

    def reset(self):
        self.menu_elements = set()
        self.necessary_elements = set()
        self.submit_elements = set()
        super(MenuOverlay, self).reset()

    def list(self, title, entries, **kwargs):
        necessary, horz_alignment, vert_alignment = self._standard_args(kwargs)
        list_screen = self._view(menu_elements.List.size, horz_alignment, vert_alignment)
        created_list = menu_elements.List(list_screen, title, entries, self.font)
        self.menu_elements.add(created_list)
        if necessary:
            self.necessary_elements.add(created_list)
        return created_list

    def button(self, text, **kwargs):
        necessary, horz_alignment, vert_alignment = self._standard_args(kwargs)
        button_screen = self._view(menu_elements.Button.size, horz_alignment, vert_alignment)
        created_button = menu_elements.Button(button_screen, text, self.font)
        self.menu_elements.add(created_button)
        if necessary:
            self.necessary_elements.add(created_button)
        return created_button

    def submit(self, text, **kwargs):
        horz_alignment = kwargs.get('horz_alignment', internal_strings.Alignment.RIGHT)
        vert_alignment = kwargs.get('vert_alignment', internal_strings.Alignment.BOTTOM)
        submit_button = self.button(text, horz_alignment=horz_alignment, vert_alignment=vert_alignment)
        self.submit_elements.add(submit_button)
        return submit_button

    def _standard_args(self, dict_):
        necessary = dict_.get('necessary', False)
        horz_alignment = dict_.get('horz_alignment', internal_strings.Alignment.CENTER)
        vert_alignment = dict_.get('vert_alignment', internal_strings.Alignment.CENTER)
        return necessary, horz_alignment, vert_alignment


class TextOverlay(BaseOverlay, base.FontMixin):
    """Handles outputting text to the screen."""

    def reset(self):
        self.text = ''
        super(TextOverlay, self).reset()

    def __call__(self, output_val, width=None, end='', **kwargs):
        """Outputs text.

        :str outputstr: The string to output.
        :int width: Optional. The text with be padded to this width."""

        if width is not None:
            output_val = '{{:{}}}'.format(width).format(output_val)
        output_val += end
        self.text += output_val
        # \x08 = backspace. \b doesn't work for some reason.
        self.text = helpers.re_sub_recursive(r'[^\x08]\x08', '', self.text)
        self.text.lstrip('\b')

        self.wipe()

        split_text = self.text.split('\n')
        text_cursor = (0, 0)
        for output_text in split_text:
            text = self.render_text(output_text)
            text_area = self.screen.blit(text, text_cursor)
            text_cursor = (0, text_area.bottom)
        super(TextOverlay, self).__call__(output_val, **kwargs)

    def sep(self, length, **kwargs):
        """Prints a separator of the given length."""
        self(strings.Sep.SEP * length, **kwargs)

    def table(self, title, columns, headers=None, edge_space=''):
        """Prints a table in text.

        :str title: A title to put at the top of the table
        :iter[iter] columns: The component iterables should be the data to put in the columns. Each component iterable
            should be the same length.
        :iter[str] headers: Optional. The name of each column. This iter should have the same length as :columns:.
        :str edge_space: Optional. Any horizontal spacing to put around each element of the table.
        """
        if headers is None:
            header_names = ['' for _ in range(len(columns))]
        else:
            header_names = headers
        column_widths = []
        # In case we're passed generators that get consumed
        columns = [list(column) for column in columns]
        for column, header in zip(columns, header_names):
            column_width = len(header)
            for column_entry in column:
                column_width = max(column_width, len(column_entry))
            column_widths.append(column_width)
        overall_title_width = len(title) + len(
            edge_space) * 2  # The width of the header text, plus space to either side of it
        overall_column_width = (sum(column_widths) +  # The width of the columns
                                len(column_widths) * len(
                                    edge_space) * 2 +  # The width of the space either side of the entry in each column
                                (len(column_widths) - 1) * len(
                                    strings.Sep.VERT_SEP))  # The width of the lines separating columns
        overall_width = max(overall_title_width, overall_column_width)
        if overall_title_width > overall_column_width:
            column_widths[-1] += overall_title_width - overall_column_width

        rows = zip(*columns)

        self(strings.Sep.DR_SEP)
        self.sep(overall_width)
        self(strings.Sep.DL_SEP, end='\n')
        self(strings.Sep.UD_SEP)
        self(edge_space + title + edge_space, width=overall_width)
        self(strings.Sep.UD_SEP, end='\n')
        self(strings.Sep.UDR_SEP)
        self.sep(overall_width)
        self(strings.Sep.UDL_SEP, end='\n')
        if headers is not None:
            self(strings.Sep.UD_SEP)
            for header, column_width in zip(headers, column_widths):
                self(edge_space)
                self(header, width=column_width)
                self(edge_space)
                self(strings.Sep.UD_SEP)
            self('\n')
            self(strings.Sep.UD_SEP)
            for column_width in column_widths[:-1]:
                self.sep(column_width)
                self(strings.Sep.UDLR_SEP)
            self.sep(column_widths[-1])
            self(strings.Sep.UD_SEP, end='\n')
        for row in rows:
            self(strings.Sep.UD_SEP)
            for entry, column_width in zip(row, column_widths):
                self(edge_space)
                self(entry, width=column_width)
                self(edge_space)
                self(strings.Sep.UD_SEP)
            self('\n')
        self(strings.Sep.UR_SEP)
        self.sep(overall_width)
        self(strings.Sep.UL_SEP, end='\n')


class Output(base.BaseIO):
    """The overall output. It takes its various overlays and then combines them to produce output to the screen."""

    def __init__(self, overlays, *args, **kwargs):
        self.overlays = overlays

        self.screen = sdl.display.set_mode(config.SCREEN_SIZE)
        sdl.display.set_caption(config.WINDOW_NAME)
        super(Output, self).__init__(*args, **kwargs)

    def reset(self):
        for overlay in self.overlays.values():
            overlay.reset()
            overlay.disable()
        self.flush()

    def register_interface(self, interface):
        for overlay in self.overlays.values():
            overlay.register_interface(interface)
        super(Output, self).register_interface(interface)

    def flush(self):
        """Pushes the changes from the overlays to the main screen."""
        for overlay in self.overlays.values():
            if overlay.enabled:
                self.screen.blit(overlay.screen, overlay.location)

        sdl.display.update()

    def use(self, overlay_name):
        return self.overlays[overlay_name].use()
