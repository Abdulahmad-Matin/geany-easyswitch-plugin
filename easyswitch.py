import os
import gtk
import gobject
import geany

class Easyswitch(geany.Plugin):

    __plugin_name__ = "Easyswitch"
    __plugin_version__ = "0.1"
    __plugin_description__ = "Switch between multiple kind of documents easily"
    __plugin_author__ = "Saber Rastikerdar"
    __plugin_license__ = 'MIT'

    # configuraion
    
    # shows ancestor directory name after the file name
    show_parent = True
    # 1 = z/ , 2 = y/z/ , 3 = x/y/z/ , ...
    parent_levels = 1    
    show_full_path = False
    tab_position = gtk.POS_TOP
    
    def __init__(self):
        geany.Plugin.__init__(self)

        sidebar_notebook = geany.main_widgets.sidebar_notebook
        label = gtk.Label('Easy Switch')
        self.notebook = gtk.Notebook()
        self.notebook.set_scrollable(True)
        self.notebook.popup_enable()
        self.notebook.set_tab_pos(self.tab_position)
        self.notebook.connect('page-reordered', 
                              self.notebook_page_reordered)
        self.sidebar_page_num = sidebar_notebook.append_page(self.notebook, 
                                                             label)
        self.types = {}
        self.notebook.show_all()
                
        #geany.signals.connect('document-new', self.document_add)                    
        geany.signals.connect('document-open', self.document_add)
        geany.signals.connect('document-save', self.document_save)
        geany.signals.connect('document-close', self.document_close)                    
        geany.signals.connect('document-activate', self.document_activate)                    

        docs = geany.document.get_documents_list() or []
        for doc in docs:
            self.document_add(None, doc)

    def document_add(self, x, doc):
        type_dict = self.get_type_dict(doc)
        if type_dict is None:
            type_name = self.get_type_name(doc)
            liststore = gtk.ListStore(str, str, gobject.TYPE_PYOBJECT)
            sorted_model = gtk.TreeModelSort(liststore)
            sorted_model.set_sort_column_id(0, gtk.SORT_ASCENDING)
            tvcolumn = gtk.TreeViewColumn()
            tv2column = gtk.TreeViewColumn()
            treeview = gtk.TreeView(sorted_model)
            treeview.append_column(tvcolumn)
            treeview.add_events(gtk.gdk.BUTTON_PRESS_MASK)
            treeview.connect('button-press-event', self.switch)
            treeview.set_headers_visible(False)
            cell = gtk.CellRendererText()
            cell2 = gtk.CellRendererText()
            tvcolumn.pack_start(cell, True) # render base name
            tvcolumn.set_attributes(cell, text=0)
            if self.show_full_path:
                tvcolumn.pack_start(cell2, True) # render full path
                tvcolumn.set_attributes(cell2, text=1)
            tvcolumn.set_sort_column_id(0)

            scrolled_window = gtk.ScrolledWindow()
            scrolled_window.add_with_viewport(treeview)
            scrolled_window.set_policy(gtk.POLICY_AUTOMATIC, 
                                       gtk.POLICY_AUTOMATIC)
            
            label = gtk.Label(type_name + (' '*(5-len(type_name))) +'\n')
            page_num = self.notebook.append_page(scrolled_window, label)
            self.notebook.set_tab_reorderable(scrolled_window, True)
            
            # doh! oh man! much code for just a simple listing widget!
            
            type_dict = {
                'name': type_name,
                'page_num': page_num, 
                'window': scrolled_window, 
                'treeview': treeview,   
                'tvcolumn': tvcolumn,   
                'liststore': liststore,
                'model': sorted_model,
                'docs': {},
            }

            self.types[type_name] = type_dict
        celltext = self.get_celltext_for(doc)
        celltext2 = doc.file_name
        ref = type_dict['liststore'].append([celltext, celltext2, self.id_of(doc)])
        type_dict['docs'][doc.file_name] = { 'ref': ref }
        self.notebook.show_all()
    
    def id_of(self, doc):
        """indeed something unique about doc for referencing"""
        return doc.editor.scintilla.widget
    
    def document_close(self, x, doc):
        if not doc.file_name:
            return
            
        titer, path = self.get_titer_path_of(doc)
        type_dict = self.get_type_dict(doc)
        file_name = type_dict['model'].get(titer, 1)[0]
        ref = type_dict['docs'][file_name]['ref']
        type_dict['liststore'].remove(ref)
        type_dict['docs'].pop(file_name)

        if not type_dict['docs']:
            self.notebook.remove_page(type_dict['page_num'])
            self.types.pop(type_dict['name'])
        
    
    def document_activate(self, x, doc):
        if not doc.file_name:
            return
        
        geany.d = doc
        type_dict = self.get_type_dict(doc)
        self.notebook.set_current_page(type_dict['page_num'])
        titer, path = self.get_titer_path_of(doc)
        type_dict['treeview'].set_cursor(path)

    def document_save(self, x, doc):
        print 'saved'
        type_dict = self.get_type_dict(doc)
        titer_path = self.get_titer_path_of(doc)
        
        if not titer_path:
            self.document_add(None, doc)
            return

        if doc.file_name != type_dict['model'].get(titer_path[0], 1)[0]:
            self.document_close(None, doc)
            self.document_add(None, doc)            

    def switch(self, treeview, x):
        gtk.timeout_add(20, self._switch, treeview)

    def _switch(self, treeview):
        tree_selection = treeview.get_selection()
        (model, paths) = tree_selection.get_selected_rows()
        if paths:
            path = paths[0]
            tree_iter = model.get_iter(path)
            file_name = model.get_value(tree_iter,1)
            for doc in geany.document.get_documents_list():
                if doc.file_name == file_name:
                    self.unselect_all_except_for_type(self.get_type_name(doc))
                    self.focus_editor(doc)
                    break
        return False

    def get_titer_path_of(self, doc):
        type_dict = self.get_type_dict(doc)
        model = type_dict['model']
        titer = model.get_iter_first()
        while titer:
            if self.id_of(doc) is model.get(titer, 2)[0]:
                return titer, model.get_path(titer)
                
            titer = model.iter_next(titer)
    def get_type_dict(self, doc):
        type_name = self.get_type_name(doc)
        if type_name in self.types:
            return self.types[type_name]

        return None

    def unselect_all_except_for_type(self, excepted_type):
        for type_name in self.types:
            if type_name != excepted_type:
                self.types[type_name]['treeview'].get_selection().unselect_all()


    def _focus_editor(self, doc):
        gn = geany.main_widgets.notebook
        gn.set_current_page(doc.notebook_page)
        doc.editor.scintilla.widget.grab_focus()
        return False
    
    def focus_editor(self, doc):
        gtk.timeout_add(10, self._focus_editor, doc)
            
    def get_type_name(self, doc):
        if doc.file_name:
            parts = doc.file_name.split('.')
            if len(parts) > 1:
                return parts[-1]
            else:
                return 'None'
        else:
            return 'None'

    def notebook_page_reordered(self, notebook, child, new_page_num):
        for name in self.types:
            if self.types[name]['window'] is child:
                type_name = name
                break
                
        old_page_num = self.types[type_name]['page_num']
        for key, item in self.types.iteritems():
            if key != type_name:
                if new_page_num < old_page_num:
                    if item['page_num'] < old_page_num and item['page_num'] >= new_page_num:
                        item['page_num'] += 1
                elif new_page_num > old_page_num:
                    if item['page_num'] > old_page_num and item['page_num'] <= new_page_num:
                        item['page_num'] -= 1

        self.types[type_name]['page_num'] = new_page_num
            
    def get_celltext_for(self, doc):
        basename = os.path.basename(doc.file_name)
        
        if self.show_parent:
            try:
                # Sorry i need only two levels up for type(tpl) :| What? 
                # I'm not selfish! Just remove it!
                # TODO: create a config dict/object for customizing every types
                if self.get_type_name(doc) == 'tpl':
                    parent = '/'.join(doc.file_name.split('/')[-3:-1])
                else:
                    parent = '/'.join(doc.file_name.split('/')[-(self.parent_levels+1):-1])
            except:
                parent = '/'
            celltext = '%s  (%s/)' % (basename, parent)
        else:
            celltext = basename
        
        return celltext
        
    def cleanup(self):
        geany.main_widgets.sidebar_notebook.remove_page(self.sidebar_page_num)
