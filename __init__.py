from cudatext import *
import cudax_lib as apx

open_bracket =  '{'
close_bracket = '}'
comment_chars = '//'
multiline_comment_start = '/*'
multiline_comment_end = '*/'
all_bracket_symbols = open_bracket+close_bracket
#all_bracket_symbols = apx.get_opt('bracket_symbols')
allowed_lexers = ('C', 'C++')

PLUGIN_ENABLED = True
GAP_MODE = False
UNIQUE_TAG = app_proc(PROC_GET_UNIQUE_TAG, '')
PLUGIN_NAME = 'Scope Description'

from cudax_lib import get_translation
_ = get_translation(__file__)  # I18N


class Command:
    
    def __init__(self):
        self.read_colors()
        
    def toggle_on_off_cmd(self):
        global PLUGIN_ENABLED
        global GAP_MODE
        
        
        PLUGIN_ENABLED = not PLUGIN_ENABLED
        if PLUGIN_ENABLED:
            self.read_colors()
            for edt in get_editors():
                self.on_caret_slow(edt)
        else:
            self.clean_up()
        
    def toggle_mode_cmd(self):
        global PLUGIN_ENABLED
        global GAP_MODE
        PLUGIN_ENABLED = True
        
        
        GAP_MODE = not GAP_MODE
        if GAP_MODE:
            print('{}: {}'.format(PLUGIN_NAME, _("Gap mode: ON")))
        else:
            print('{}: {}'.format(PLUGIN_NAME, _("Gap mode: OFF")))
        
        self.clean_up()
        self.read_colors()
        app_idle() # update all props of editors
        
        for edt in get_editors():
            self.on_caret_slow(edt)

    def place_comment(self, ed_self, line=None):
        global GAP_MODE
        lexer = ed_self.get_prop(PROP_LEXER_FILE)
        if not lexer in allowed_lexers:
            return
            
        
        caret = ed_self.get_carets()[0][:2]
        caret_y = caret[1] if line is None else line
        
        line_cur = get_line_strip_comment(ed_self, caret_y)
        bracket_pos = line_cur.rfind(close_bracket)
        if bracket_pos < 0:
            return

        res = find_brackets(ed_self, bracket_pos, caret_y)
        if res is None:
            # no matching bracket
            return
        
        x1, y1, x2, y2 = res
        
        last_char_x = ed_self.get_line_len(y2)
        scroll_horz = ed_self.get_prop(PROP_SCROLL_HORZ_SMOOTH)
        pixels0 = ed_self.convert(CONVERT_CARET_TO_PIXELS, 0, y2)
        pixels = ed_self.convert(CONVERT_CARET_TO_PIXELS, last_char_x, y2)
        offset_x, offset_y, offset_x_gap = 0, 0, 0
        if pixels0 and pixels:
            offset_x = pixels[0] 
            offset_y = pixels[1]
            offset_x_gap = pixels[0] - pixels0[0] - scroll_horz
        
        line_top = get_line_strip_comment(ed_self, y1)
        
        str_top = line_top[:x1].strip()
        # if top line contains only brackets and spaces, try to get description from previous lines 
        if str_top.replace(open_bracket,'').strip() == '':
            for i in range(y1-1, -1, -1):
                str_top = ed_self.get_text_line(i).strip()
                str_top = remove_comment(str_top, comment_chars).strip()
                if str_top.replace(open_bracket,'').strip() != '':
                    break
            
        if str_top != '':
            # in case of multiple scopes sitting on one line leave only the one we need
            another_br_pos = str_top.rfind(open_bracket)
            if another_br_pos >= 0:
                str_top = str_top[another_br_pos+1:].strip()
        else:
            str_top = _('unknown scope')

        if GAP_MODE:
            text = '{} {} {}'.format(comment_chars, _('end of'), str_top)
            self.create_gap(ed_self, y2, text, offset_x_gap, offset_y)
        else:
            text = '{} {}'.format(_('end of'), str_top)
            self.create_panel(ed_self, y2, text, offset_x, offset_y)
    
    def create_panel(self, ed_self, line, text, offset_x=0, offset_y=0):
        cell = ed_self.get_prop(PROP_CELL_SIZE)
        font = ed_self.get_prop(PROP_FONT)
        font_scale = ed_self.get_prop(PROP_SCALE_FONT) or 100
        
        first_col = ed_self.convert(CONVERT_PIXELS_TO_CARET, 0, 0)
        if first_col:
            first_col_px = ed_self.convert(CONVERT_CARET_TO_PIXELS, first_col[0], line)
            if first_col_px:
                offset_x = first_col_px[0] if offset_x < first_col_px[0] else offset_x
            
        text = truncate_string(text, 70)
        
        h = ed_self.get_prop(PROP_HANDLE_PARENT)
        n = dlg_proc(h, DLG_CTL_ADD, prop='panel')
        dlg_proc(h, DLG_CTL_PROP_SET, index=n, prop={
            'name': 'cuda_scope_description_panel',
            'cap': text,
            #'border': True,
            'color': self.color_back,
            'font_color': self.color_font,
            'font_size': font[1] * font_scale // 120,
            'x': offset_x + cell[0],
            'y': offset_y,
            'h': cell[1],
            'w': 500 * font_scale // 120,
        })
        
    def create_gap(self, ed_self, line, text, offset_x=0, offset_y=0):
        props = dlg_proc(ed_self.get_prop(PROP_HANDLE_PARENT), DLG_CTL_PROP_GET, name='ed1')
        ed_width = props['w']
        
        bitmap, canvas = ed_self.gap(GAP_MAKE_BITMAP, ed_width, 24)
        
        canvas_proc(canvas, CANVAS_SET_BRUSH, color=self.color_back, style=BRUSH_SOLID)
        canvas_proc(canvas, CANVAS_RECT_FILL, x=0, y=0, x2=ed_width, y2=24)
        canvas_proc(canvas, CANVAS_SET_FONT, '', self.color_font, 14)
        canvas_proc(canvas, CANVAS_TEXT, text, x=offset_x)
        
        ed_self.gap(GAP_ADD, line, bitmap, tag=UNIQUE_TAG)
        
    def remove_panels(self, ed_self):
        h = ed_self.get_prop(PROP_HANDLE_PARENT)
        for n in iter(lambda: dlg_proc(h, DLG_CTL_FIND, prop='cuda_scope_description_panel'), -1):
            dlg_proc(h, DLG_CTL_PROP_SET, index=n, prop={'vis': False})
            dlg_proc(h, DLG_CTL_DELETE, index=n)
    
    def clean_up(self):
        for edt in get_editors():
            edt.gap(GAP_DELETE_ALL, -1, 0, tag=UNIQUE_TAG)
            self.remove_panels(edt)
    
    def read_colors(self):
        global GAP_MODE
        
        theme_ui = app_proc(PROC_THEME_UI_DICT_GET, '')
        theme_syn = app_proc(PROC_THEME_SYNTAX_DICT_GET, '')
        if GAP_MODE:
            self.color_font = theme_syn['Comment']['color_font']
            self.color_back = theme_ui['EdTextBg']['color']
        else:
            self.color_font = theme_syn['LightBG5']['color_font']
            self.color_back = theme_syn['LightBG5']['color_back']
    
    def on_tab_change(self, ed_self: Editor):
        self.on_caret_slow(ed_self)
    
    def on_scroll(self, ed_self: Editor):
        self.on_caret_slow(ed_self)
        
    def on_caret_slow(self, ed_self: Editor):
        lexer = ed_self.get_prop(PROP_LEXER_FILE)
        if not lexer in allowed_lexers:
            return
        
        global PLUGIN_ENABLED
        global GAP_MODE
        
        if not PLUGIN_ENABLED:
            return
        
        top = ed_self.get_prop(PROP_LINE_TOP)
        bot = ed_self.get_prop(PROP_LINE_BOTTOM)
        
        if GAP_MODE:
            ed_self.gap(GAP_DELETE_ALL, -1, 0, tag=UNIQUE_TAG)
        else:
            self.remove_panels(ed_self)
            
        for line in range(top, bot+1):
            self.place_comment(ed_self, line)

    def on_state(self, ed_self, state):
        global PLUGIN_ENABLED
        global GAP_MODE
        
        if not PLUGIN_ENABLED:
            return
        
        if state == APPSTATE_THEME_UI:
            self.read_colors()
            
            if GAP_MODE:
                for edt in get_editors():
                    gaps = edt.gap(GAP_GET_ALL, -1, -1)
                    for gap in gaps:
                        if gap['tag'] == UNIQUE_TAG:
                            self.place_comment(edt, line=gap['line'])
            else:
                for edt in get_editors():
                    self.remove_panels(edt)
                    self.on_caret_slow(edt)        

def get_editors():
    return [Editor(h) for h in ed_handles()]

# ChatGPT's variant
def remove_comment(s, comment_chars):
    output = ""
    inside_quotes = False
    inside_single_line_comment = False
    inside_multi_line_comment = False
    i = 0
    while i < len(s):
        if not inside_quotes and not inside_multi_line_comment and s[i:i+2] == comment_chars:
            inside_single_line_comment = True
            i += 2
        elif not inside_quotes and not inside_single_line_comment and s[i:i+2] == multiline_comment_start:
            inside_multi_line_comment = True
            i += 2
        elif not inside_single_line_comment and not inside_multi_line_comment and s[i] in ('"', "'"):
            output += s[i]
            inside_quotes = not inside_quotes
            i += 1
        elif inside_single_line_comment and s[i] == '\n':
            inside_single_line_comment = False
        elif inside_multi_line_comment and s[i:i+2] == multiline_comment_end:
            inside_multi_line_comment = False
            i += 2
        elif not inside_single_line_comment and not inside_multi_line_comment:
            output += s[i]
            i += 1
        else:
            i += 1
    return output.rstrip()

def find_brackets(ed_self, x, y):
    x1, y1, x2, y2 = ed_self.action(EDACTION_FIND_BRACKETS, (x, y), all_bracket_symbols)
    if y2 < 0:
        return None

    # reorder coords if necessary (low to high)
    if (y1 > y2 or (y1 == y2 and x1 > x2)):
        x1, x2, y1, y2 = x2, x1, y2, y1
    return x1, y1, x2, y2

def get_line_strip_comment(ed_self, y):
    s = ed_self.get_text_line(y)
    s = '' if s is None else s
    r = remove_comment(s, comment_chars)
    return r
    
def truncate_string(string, max_length):
    if len(string) > max_length:
        return string[:max_length-3] + "..."
    else:
        return string