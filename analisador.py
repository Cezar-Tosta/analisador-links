import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import json
import os
import sys
import subprocess
from datetime import datetime
import threading
import webbrowser
from random import choice
import re

OPENAI_API_KEY = "CHAVE_DA_API_OPENAI_AQUI"

def call_openai_api(prompt, api_key, temperature=0.3):
    import requests
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "gpt-4o",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature
    }
    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        elif response.status_code == 401:
            return "❌ ERRO: Chave da API inválida ou ausente"
        else:
            return f"❌ ERRO da API: {response.status_code}"
    except Exception as e:
        return f"❌ ERRO de conexão: {str(e)}"

def get_summary_text(text, min_words=60, max_words=150):
    words = text.split()
    if len(words) <= max_words:
        return ' '.join(words)
    else:
        return ' '.join(words[:max_words]) + '...'

def extract_metadata_from_url(url):
    try:
        import requests
        from bs4 import BeautifulSoup
        import urllib.parse
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        metadata = {
            'url': url,
            'title': '',
            'description': '',
            'keywords': '',
            'author': '',
            'publish_date': '',
            'site_name': '',
            'content_preview': '',
            'status_code': response.status_code,
            'content_length': len(response.content),
            'domain': urllib.parse.urlparse(url).netloc
        }
        title_tag = soup.find('title')
        if title_tag:
            metadata['title'] = title_tag.get_text().strip()
        meta_tags = soup.find_all('meta')
        for tag in meta_tags:
            name = tag.get('name', '').lower()
            property_attr = tag.get('property', '').lower()
            content = tag.get('content', '')
            if name == 'description' or property_attr == 'og:description':
                metadata['description'] = content
            elif name == 'keywords':
                metadata['keywords'] = content
            elif name == 'author':
                metadata['author'] = content
            elif name == 'publish_date' or property_attr == 'article:published_time':
                metadata['publish_date'] = content
            elif property_attr == 'og:site_name':
                metadata['site_name'] = content
        text_content = soup.get_text()
        clean_text = ' '.join(text_content.split())
        metadata['content_preview'] = get_summary_text(clean_text, 60, 150)
        return metadata
    except Exception as e:
        import urllib.parse
        return {
            'url': url,
            'title': 'Erro ao carregar',
            'description': f'Erro: {str(e)}',
            'keywords': '',
            'author': '',
            'publish_date': '',
            'site_name': '',
            'content_preview': '',
            'status_code': 0,
            'content_length': 0,
            'domain': urllib.parse.urlparse(url).netloc if url else ''
        }

def translate_text_to_portuguese(text):
    prompt = f"Traduza o seguinte texto para português de forma clara e natural:\n\n{text}"
    return call_openai_api(prompt, OPENAI_API_KEY)

def export_to_pdf(content, filename="panorama_links.pdf"):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from reportlab.lib.units import inch
        
        path = os.path.join(os.path.dirname(sys.argv[0]), filename)
        doc = SimpleDocTemplate(path, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
        
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            'Title',
            parent=styles['Heading1'],
            fontSize=16,
            textColor=colors.black,
            alignment=1,
            spaceAfter=20,
            fontName='Helvetica-Bold'
        )
        
        subtitle_style = ParagraphStyle(
            'Subtitle',
            parent=styles['Normal'],
            fontSize=12,
            textColor=colors.black,
            alignment=1,
            spaceAfter=15,
            fontName='Helvetica'
        )
        
        heading_style = ParagraphStyle(
            'Heading',
            parent=styles['Normal'],
            fontSize=14,
            textColor=colors.black,
            spaceAfter=10,
            spaceBefore=15,
            fontName='Helvetica-Bold'
        )
        
        normal_style = ParagraphStyle(
            'Normal',
            parent=styles['Normal'],
            fontSize=11,
            textColor=colors.black,
            spaceAfter=8,
            fontName='Helvetica',
            leading=14
        )
        
        story = []
        
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                story.append(Spacer(1, 6))
                continue
            
            if line.startswith('Panorama Geral'):
                story.append(Paragraph(line, title_style))
            elif line.startswith('Gerado em:') or line.startswith('Baseado em'):
                story.append(Paragraph(line, subtitle_style))
            elif line.startswith('='):
                story.append(Spacer(1, 10))
            elif line.strip().endswith(':') and any(char.isdigit() for char in line[:3]):
                story.append(Paragraph(f"<b>{line}</b>", heading_style))
            else:
                formatted_line = line
                formatted_line = formatted_line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                
                while '**' in formatted_line:
                    first_pos = formatted_line.find('**')
                    if first_pos != -1:
                        second_pos = formatted_line.find('**', first_pos + 2)
                        if second_pos != -1:
                            before = formatted_line[:first_pos]
                            bold_text = formatted_line[first_pos + 2:second_pos]
                            after = formatted_line[second_pos + 2:]
                            formatted_line = before + f'<b>{bold_text}</b>' + after
                        else:
                            break
                    else:
                        break
                
                temp_line = formatted_line
                bold_tags = re.findall(r'<b>.*?</b>', temp_line)
                for i, tag in enumerate(bold_tags):
                    temp_line = temp_line.replace(tag, f'BOLDTAG{i}', 1)
                
                while '*' in temp_line and '**' not in temp_line:
                    first_pos = temp_line.find('*')
                    if first_pos != -1:
                        second_pos = temp_line.find('*', first_pos + 1)
                        if second_pos != -1:
                            before = temp_line[:first_pos]
                            italic_text = temp_line[first_pos + 1:second_pos]
                            after = temp_line[second_pos + 1:]
                            temp_line = before + f'<i>{italic_text}</i>' + after
                        else:
                            break
                    else:
                        break
                
                for i, tag in enumerate(bold_tags):
                    temp_line = temp_line.replace(f'BOLDTAG{i}', tag, 1)
                
                formatted_line = temp_line
                
                if line.startswith('- ') or line.startswith('• '):
                    formatted_line = f"• {formatted_line[2:]}"
                
                story.append(Paragraph(formatted_line, normal_style))
        
        doc.build(story)
        return path
        
    except ImportError:
        path = os.path.join(os.path.dirname(sys.argv[0]), filename.replace('.pdf', '.txt'))
        with open(path, 'w', encoding='utf-8') as f:
            f.write("PANORAMA GERAL - ANALISADOR DE LINKS\n")
            f.write("="*50 + "\n\n")
            f.write(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n")
            f.write("Desenvolvido por Cezar Tosta\n\n")
            f.write(content)
        return path
    except Exception as e:
        raise Exception(f"Erro ao gerar PDF: {str(e)}")

class LinkAnalyzer:
    def __init__(self, url, categories=None, metadata=None, analysis="", created_date=None):
        self.url = url
        self.categories = categories or []
        self.metadata = metadata or {}
        self.analysis = analysis
        self.created_date = created_date or datetime.now().strftime("%d/%m/%Y %H:%M")
        self.contexto_historico = ""
        self.comparacao_atual = ""
        self.principais_assuntos = ""
    
    def to_dict(self):
        return {
            'url': self.url,
            'categories': self.categories,
            'metadata': self.metadata,
            'analysis': self.analysis,
            'created_date': self.created_date,
            'contexto_historico': self.contexto_historico,
            'comparacao_atual': self.comparacao_atual,
            'principais_assuntos': self.principais_assuntos
        }
    
    @classmethod
    def from_dict(cls, data):
        obj = cls(
            url=data.get('url'),
            categories=data.get('categories', []),
            metadata=data.get('metadata', {}),
            analysis=data.get('analysis', ''),
            created_date=data.get('created_date')
        )
        obj.contexto_historico = data.get('contexto_historico', "")
        obj.comparacao_atual = data.get('comparacao_atual', "")
        obj.principais_assuntos = data.get('principais_assuntos', "")
        return obj

class CategoryManager:
    def __init__(self):
        self.categories = []
        self.color_map = {}
        self.load_categories()
    
    def add_category(self, category):
        if category and category not in self.categories:
            self.categories.append(category)
            self.color_map[category] = "#" + ''.join([choice('0123456789abcdef') for i in range(6)])
            self.save_categories()
    
    def remove_category(self, category):
        if category in self.categories:
            self.categories.remove(category)
            if category in self.color_map:
                del self.color_map[category]
            self.save_categories()
    
    def get_categories(self):
        return self.categories
    
    def get_color(self, category):
        return self.color_map.get(category, "#808080")
    
    def save_categories(self):
        try:
            path = os.path.join(os.path.dirname(sys.argv[0]), 'categories.json')
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.categories, f, ensure_ascii=False, indent=2)
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao salvar categorias: {str(e)}")
    
    def load_categories(self):
        try:
            path = os.path.join(os.path.dirname(sys.argv[0]), 'categories.json')
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    self.categories = json.load(f)
            else:
                self.categories = []
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao carregar categorias: {str(e)}")
            self.categories = []

class MultiSelectCombobox(ttk.Frame):
    def __init__(self, parent, values=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.values = values or []
        self.selected_values = []
        
        self.entry_var = tk.StringVar()
        self.entry = ttk.Entry(self, textvariable=self.entry_var, state="readonly")
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.button = ttk.Button(self, text="▼", width=3, command=self.open_selection)
        self.button.pack(side=tk.RIGHT)
        
        self.update_display()
    
    def open_selection(self):
        popup = tk.Toplevel(self.master)
        popup.title("Selecionar Categorias")
        popup.geometry("300x400")
        popup.transient(self.master)
        popup.grab_set()
        
        frame = ttk.Frame(popup)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.checkbox_vars = {}
        
        for value in self.values:
            var = tk.BooleanVar()
            var.set(value in self.selected_values)
            self.checkbox_vars[value] = var
            
            cb = ttk.Checkbutton(frame, text=value, variable=var)
            cb.pack(anchor=tk.W, pady=2)
        
        btn_frame = ttk.Frame(popup)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        def apply_selection():
            self.selected_values = []
            for value, var in self.checkbox_vars.items():
                if var.get():
                    self.selected_values.append(value)
            self.update_display()
            popup.destroy()
        
        def clear_all():
            for var in self.checkbox_vars.values():
                var.set(False)
        
        ttk.Button(btn_frame, text="Limpar Tudo", command=clear_all).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="Cancelar", command=popup.destroy).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(btn_frame, text="Aplicar", command=apply_selection).pack(side=tk.RIGHT, padx=(5, 0))
    
    def update_display(self):
        if self.selected_values:
            display_text = ", ".join(self.selected_values)
            if len(display_text) > 50:
                display_text = display_text[:47] + "..."
        else:
            display_text = ""
        self.entry_var.set(display_text)
    
    def set_values(self, values):
        self.values = values or []
        self.selected_values = [v for v in self.selected_values if v in self.values]
        self.update_display()
    
    def get_selected(self):
        return self.selected_values.copy()
    
    def set_selected(self, values):
        self.selected_values = [v for v in values if v in self.values]
        self.update_display()

class LinkAnalyzerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Analisador de Links - Metadados e Análise")
        self.root.geometry("1600x1000")
        self.root.configure(bg='#f0f0f0')
        self.links = []
        self.category_manager = CategoryManager()
        self.load_links()
        self.setup_styles()
        self.create_widgets()
        self.refresh_link_list()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Action.TButton', font=('Arial', 10, 'bold'))

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        header_frame = ttk.Frame(main_frame)
        header_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        header_frame.columnconfigure(1, weight=1)
        
        title_label = tk.Label(header_frame, text="Analisador de Links", font=('Arial', 16, 'bold'), bg='#f0f0f0')
        title_label.grid(row=0, column=0, sticky=tk.W)
        
        dev_label = tk.Label(header_frame, text="Desenvolvido por Cezar Tosta", font=('Arial', 10, 'italic'), bg='#f0f0f0', fg='#666666')
        dev_label.grid(row=0, column=1, sticky=tk.E)
        
        left_frame = ttk.LabelFrame(main_frame, text="Cadastro de Links", padding="10")
        left_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        left_frame.columnconfigure(0, weight=1)
        
        tk.Label(left_frame, text="URL do Link:", font=('Arial', 10, 'bold')).grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.url_entry = ttk.Entry(left_frame, width=50)
        self.url_entry.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        tk.Label(left_frame, text="Categoria(s):", font=('Arial', 10, 'bold')).grid(row=2, column=0, sticky=tk.W, pady=(0, 5))
        self.category_multiselect = MultiSelectCombobox(left_frame, values=self.category_manager.get_categories())
        self.category_multiselect.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        cat_btn_frame = ttk.Frame(left_frame)
        cat_btn_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        cat_btn_frame.columnconfigure(0, weight=1)
        cat_btn_frame.columnconfigure(1, weight=1)
        
        add_cat_btn = ttk.Button(cat_btn_frame, text="➕ Nova Categoria", command=self.add_category_popup)
        add_cat_btn.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        
        del_cat_btn = ttk.Button(cat_btn_frame, text="🗑️ Excluir Categoria", command=self.delete_category_popup)
        del_cat_btn.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 0))
        
        button_frame = ttk.Frame(left_frame)
        button_frame.grid(row=5, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)
        
        analyze_btn = ttk.Button(button_frame, text="Analisar Link", command=self.analyze_link, style='Action.TButton')
        analyze_btn.grid(row=0, column=0, sticky=tk.EW, padx=(0, 5))
        
        add_btn = ttk.Button(button_frame, text="Adicionar Sem Análise", command=self.add_link_simple)
        add_btn.grid(row=0, column=1, sticky=tk.EW, padx=(5, 0))
        
        metadata_frame = ttk.LabelFrame(left_frame, text="Metadados do Link", padding="10")
        metadata_frame.grid(row=6, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        metadata_frame.columnconfigure(0, weight=1)
        metadata_frame.rowconfigure(0, weight=1)
        
        self.metadata_text = scrolledtext.ScrolledText(metadata_frame, height=20, width=50, wrap=tk.WORD)
        self.metadata_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        right_frame = ttk.Frame(main_frame)
        right_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0))
        right_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(0, weight=1)
        right_frame.rowconfigure(2, weight=1)
        
        list_frame = ttk.LabelFrame(right_frame, text="Links Cadastrados", padding="10")
        list_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 5))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(1, weight=1)
        
        filter_frame = ttk.Frame(list_frame)
        filter_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        filter_frame.columnconfigure(2, weight=1)
        
        tk.Label(filter_frame, text="Filtrar por:").grid(row=0, column=0, padx=(0, 5))
        self.filter_var = tk.StringVar()
        self.filter_combo = ttk.Combobox(filter_frame, textvariable=self.filter_var, values=["Todos"] + self.category_manager.get_categories())
        self.filter_combo.set("Todos")
        self.filter_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        self.filter_combo.bind('<<ComboboxSelected>>', lambda e: self.refresh_link_list())
        
        ttk.Button(filter_frame, text="Atualizar", command=self.refresh_link_list).grid(row=0, column=2, padx=2, sticky=tk.E)
        
        action_frame = ttk.Frame(filter_frame)
        action_frame.grid(row=0, column=3, sticky=tk.E)
        ttk.Button(action_frame, text="Salvar", command=self.save_links).pack(side=tk.LEFT, padx=2)
        ttk.Button(action_frame, text="Excluir Selecionado", command=self.delete_link).pack(side=tk.LEFT, padx=2)
        ttk.Button(action_frame, text="Abrir Link", command=self.open_selected_link).pack(side=tk.LEFT, padx=2)
        
        columns = ('Título', 'Domínio', 'Categoria(s)', 'Data', 'Status')
        self.link_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=12)
        self.link_tree.heading('Título', text='Título')
        self.link_tree.heading('Domínio', text='Domínio')
        self.link_tree.heading('Categoria(s)', text='Categoria(s)')
        self.link_tree.heading('Data', text='Data')
        self.link_tree.heading('Status', text='Status')
        
        self.link_tree.column('Título', width=250)
        self.link_tree.column('Domínio', width=150)
        self.link_tree.column('Categoria(s)', width=180)
        self.link_tree.column('Data', width=100, anchor=tk.CENTER)
        self.link_tree.column('Status', width=80, anchor=tk.CENTER)
        
        scrollbar_links = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.link_tree.yview)
        self.link_tree.configure(yscrollcommand=scrollbar_links.set)
        self.link_tree.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar_links.grid(row=1, column=1, sticky=(tk.N, tk.S))
        
        self.link_tree.bind('<Double-1>', self.show_link_details)
        self.link_tree.bind('<Button-3>', self.show_context_menu)
        
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Ver Detalhes", command=self.show_link_details)
        self.context_menu.add_command(label="Abrir no Navegador", command=self.open_selected_link)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Editar", command=self.edit_link)
        self.context_menu.add_command(label="Excluir", command=self.delete_link)
        
        panorama_frame = ttk.LabelFrame(right_frame, text="Panorama Geral por Categoria(s)", padding="10")
        panorama_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(5, 0))
        panorama_frame.columnconfigure(0, weight=1)
        panorama_frame.rowconfigure(1, weight=1)
        
        panorama_btn_frame = ttk.Frame(panorama_frame)
        panorama_btn_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        panorama_btn_frame.columnconfigure(1, weight=1)
        
        ttk.Button(panorama_btn_frame, text="Gerar Panorama com IA", command=self.generate_panorama, style='Action.TButton').grid(row=0, column=0, sticky=tk.W)
        
        self.panorama_category_multiselect = MultiSelectCombobox(panorama_btn_frame, values=self.category_manager.get_categories())
        self.panorama_category_multiselect.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(10, 0))
        
        ttk.Button(panorama_btn_frame, text="Exportar PDF", command=self.export_panorama_pdf).grid(row=0, column=2, sticky=tk.E, padx=(10, 0))
        
        self.panorama_text = scrolledtext.ScrolledText(panorama_frame, height=15, width=70, wrap=tk.WORD)
        self.panorama_text.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.status_var = tk.StringVar()
        self.status_var.set("Pronto - Analisador de Links iniciado")
        status_bar = tk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))

    def add_category_popup(self):
        popup = tk.Toplevel(self.root)
        popup.title("Nova Categoria")
        popup.geometry("350x120")
        popup.transient(self.root)
        popup.grab_set()
        
        tk.Label(popup, text="Nome da nova categoria:").pack(pady=10)
        entry = ttk.Entry(popup, width=30)
        entry.pack(pady=5)
        
        def add_cat():
            new_cat = entry.get().strip()
            if new_cat and new_cat not in self.category_manager.get_categories():
                self.category_manager.add_category(new_cat)
                self.update_category_options()
                messagebox.showinfo("Sucesso", f"Categoria '{new_cat}' adicionada com sucesso!")
            elif new_cat in self.category_manager.get_categories():
                messagebox.showwarning("Aviso", "Esta categoria já existe!")
            popup.destroy()
        
        ttk.Button(popup, text="Adicionar", command=add_cat).pack(pady=10)
        entry.focus_set()
        entry.bind('<Return>', lambda e: add_cat())

    def delete_category_popup(self):
        if not self.category_manager.get_categories():
            messagebox.showwarning("Aviso", "Não há categorias para excluir.")
            return
        
        popup = tk.Toplevel(self.root)
        popup.title("Excluir Categoria")
        popup.geometry("350x150")
        popup.transient(self.root)
        popup.grab_set()
        
        tk.Label(popup, text="Selecione a categoria para excluir:").pack(pady=10)
        
        category_var = tk.StringVar()
        category_combo = ttk.Combobox(popup, textvariable=category_var, values=self.category_manager.get_categories(), state="readonly")
        category_combo.pack(pady=5)
        
        def delete_cat():
            cat_to_delete = category_var.get()
            if not cat_to_delete:
                messagebox.showwarning("Aviso", "Selecione uma categoria para excluir.")
                return
            
            links_with_category = [link for link in self.links if cat_to_delete in link.categories]
            
            if links_with_category:
                if messagebox.askyesno("Confirmar", 
                    f"Existem {len(links_with_category)} links usando a categoria '{cat_to_delete}'.\n"
                    f"Estes links serão reclassificados como 'Não Classificado'.\n\n"
                    f"Deseja continuar?"):
                    
                    for link in links_with_category:
                        link.categories = [cat if cat != cat_to_delete else "Não Classificado" for cat in link.categories]
                        if not link.categories:
                            link.categories = ["Não Classificado"]
                    
                    self.category_manager.remove_category(cat_to_delete)
                    self.update_category_options()
                    self.refresh_link_list()
                    self.save_links()
                    messagebox.showinfo("Sucesso", f"Categoria '{cat_to_delete}' excluída com sucesso!")
                    popup.destroy()
            else:
                if messagebox.askyesno("Confirmar", f"Deseja excluir a categoria '{cat_to_delete}'?"):
                    self.category_manager.remove_category(cat_to_delete)
                    self.update_category_options()
                    messagebox.showinfo("Sucesso", f"Categoria '{cat_to_delete}' excluída com sucesso!")
                    popup.destroy()
        
        ttk.Button(popup, text="Excluir", command=delete_cat).pack(pady=10)

    def update_category_options(self):
        categories = self.category_manager.get_categories()
        self.category_multiselect.set_values(categories)
        self.filter_combo['values'] = ["Todos"] + categories
        self.panorama_category_multiselect.set_values(categories)

    def url_already_exists(self, url):
        return any(link.url == url for link in self.links)

    def analyze_link(self):
        url = self.url_entry.get().strip()
        categories = self.category_multiselect.get_selected()
        
        if not categories:
            categories = ["Não Classificado"]
        
        if not url:
            messagebox.showwarning("Aviso", "Por favor, insira uma URL para analisar.")
            return
        
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        if self.url_already_exists(url):
            messagebox.showwarning("Aviso", "Esta URL já está cadastrada no sistema.")
            return
        
        self.status_var.set("Analisando link...")
        self.root.update()
        
        def analyze_thread():
            try:
                self.status_var.set("Extraindo metadados...")
                self.root.update()
                
                metadata = extract_metadata_from_url(url)
                
                # Traduzir resumo para português
                resumo_pt = translate_text_to_portuguese(metadata.get('content_preview', ''))
                
                # Atualizar interface na thread principal
                def update_metadata_display():
                    self.display_metadata(metadata, resumo_pt)
                self.root.after(0, update_metadata_display)
                
                self.status_var.set("Analisando com IA...")
                self.root.update()
                
                analysis_prompt = f"""
Analise o seguinte link e seus metadados no contexto das categorias: {', '.join(categories)}:

URL: {url}
Título: {metadata.get('title', 'N/A')}
Descrição: {metadata.get('description', 'N/A')}
Conteúdo: {metadata.get('content_preview', 'N/A')[:1000]}

Forneça uma análise detalhada incluindo:
1. Relevância para as categorias selecionadas
2. Principais pontos abordados e definição dos seus conceitos
3. Qualidade e credibilidade da fonte
4. Possíveis aplicações práticas
5. Contexto histórico e atual
6. Perspectivas futuras 
7. Possíveis vieses, interesses e falácias
8. Principais referências e citações
9. Linha de raciocínio principal (relações de causa e efeito)
10. Cinco perguntas e respostas com base no panorama

Seja específico e técnico na análise.
"""
                analysis = call_openai_api(analysis_prompt, OPENAI_API_KEY)
                
                if "❌ ERRO" in analysis:
                    self.root.after(0, lambda: messagebox.showerror("Erro", analysis))
                    self.root.after(0, lambda: self.status_var.set("Erro na análise"))
                    return
                
                def add_analyzed_link():
                    link_analyzer = LinkAnalyzer(
                        url=url,
                        categories=categories,
                        metadata=metadata,
                        analysis=analysis
                    )
                    # Guardar resumo traduzido e campos extras
                    link_analyzer.metadata['content_preview'] = resumo_pt
                    # Inicializar campos extras vazios
                    link_analyzer.contexto_historico = "N/A"
                    link_analyzer.comparacao_atual = "N/A"
                    link_analyzer.principais_assuntos = "N/A"
                    
                    self.links.append(link_analyzer)
                    self.refresh_link_list()
                    self.save_links()
                    self.url_entry.delete(0, tk.END)
                    self.category_multiselect.set_selected([])
                    messagebox.showinfo("Sucesso", "Link analisado e adicionado com sucesso!")
                    self.status_var.set("Link analisado com sucesso")
                
                self.root.after(0, add_analyzed_link)
                
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Erro", f"Erro durante análise: {str(e)}"))
                self.root.after(0, lambda: self.status_var.set("Erro na análise"))
        
        thread = threading.Thread(target=analyze_thread)
        thread.daemon = True
        thread.start()

    def add_link_simple(self):
        url = self.url_entry.get().strip()
        categories = self.category_multiselect.get_selected()
        
        if not categories:
            categories = ["Não Classificado"]
        
        if not url:
            messagebox.showwarning("Aviso", "Por favor, insira uma URL.")
            return
        
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        import urllib.parse
        metadata = {
            'url': url,
            'title': url,
            'description': 'Link adicionado sem análise',
            'domain': urllib.parse.urlparse(url).netloc,
            'content_preview': 'N/A'
        }
        
        link_analyzer = LinkAnalyzer(
            url=url,
            categories=categories,
            metadata=metadata,
            analysis="Link adicionado sem análise detalhada"
        )
        link_analyzer.contexto_historico = "N/A"
        link_analyzer.comparacao_atual = "N/A"
        link_analyzer.principais_assuntos = "N/A"
        
        self.links.append(link_analyzer)
        self.refresh_link_list()
        self.save_links()
        self.url_entry.delete(0, tk.END)
        self.category_multiselect.set_selected([])
        self.status_var.set("Link adicionado")

    def display_metadata(self, metadata, resumo_pt=None):
        self.metadata_text.delete(1.0, tk.END)
        resumo = resumo_pt if resumo_pt else metadata.get('content_preview', 'N/A')
        metadata_display = f"""
Site: {metadata.get('site_name', 'N/A')}
Link: {metadata.get('url', 'N/A')}
Título: {metadata.get('title', 'N/A')}
Data de publicação: {metadata.get('publish_date', 'N/A')}

Resumo:
{resumo}
"""
        self.metadata_text.insert(1.0, metadata_display)

    def refresh_link_list(self):
        for item in self.link_tree.get_children():
            self.link_tree.delete(item)
        
        filter_category = self.filter_var.get()
        filtered_links = []
        
        for link in self.links:
            if filter_category == "Todos" or filter_category in link.categories:
                filtered_links.append(link)
        
        filtered_links.sort(key=lambda x: x.created_date, reverse=True)
        
        for link in filtered_links:
            title = link.metadata.get('title', link.url)
            if len(title) > 50:
                title = title[:50] + '...'
            
            domain = link.metadata.get('domain', 'N/A')
            status = "Analisado" if link.analysis and "Link adicionado sem análise" not in link.analysis else "Simples"
            cats = ', '.join(link.categories)
            
            self.link_tree.insert('', tk.END, values=(
                title,
                domain,
                cats,
                link.created_date.split()[0],
                status
            ))
        
        total = len(self.links)
        analyzed = len([l for l in self.links if l.analysis and "Link adicionado sem análise" not in l.analysis])
        self.status_var.set(f"Total: {total} links | Analisados: {analyzed} | Simples: {total - analyzed}")

    def show_link_details(self, event=None):
        selection = self.link_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        index = self.link_tree.index(item)
        
        filter_category = self.filter_var.get()
        filtered_links = []
        for link in self.links:
            if filter_category == "Todos" or filter_category in link.categories:
                filtered_links.append(link)
        
        filtered_links.sort(key=lambda x: x.created_date, reverse=True)
        
        if index >= len(filtered_links):
            return
        
        link = filtered_links[index]
        
        details_window = tk.Toplevel(self.root)
        details_window.title("Detalhes do Link")
        details_window.geometry("800x700")
        details_window.transient(self.root)
        details_window.grab_set()
        
        notebook = ttk.Notebook(details_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        metadata_frame = ttk.Frame(notebook)
        notebook.add(metadata_frame, text="Metadados")
        
        metadata_text = scrolledtext.ScrolledText(metadata_frame, wrap=tk.WORD)
        metadata_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        metadata_display = f"""
Site: {link.metadata.get('site_name', 'N/A')}
Link: {link.url}
Título: {link.metadata.get('title', 'N/A')}
Data de publicação: {link.metadata.get('publish_date', 'N/A')}

Resumo:
{link.metadata.get('content_preview', 'N/A')}
"""
        metadata_text.insert(1.0, metadata_display)
        metadata_text.config(state=tk.DISABLED)
        
        analysis_frame = ttk.Frame(notebook)
        notebook.add(analysis_frame, text="Análise IA")
        
        analysis_text = scrolledtext.ScrolledText(analysis_frame, wrap=tk.WORD)
        analysis_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        analysis_text.insert(1.0, link.analysis)
        analysis_text.config(state=tk.DISABLED)
        
        button_frame = tk.Frame(details_window)
        button_frame.pack(pady=10)
        ttk.Button(button_frame, text="Abrir Link", command=lambda: webbrowser.open(link.url)).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Fechar", command=details_window.destroy).pack(side=tk.LEFT, padx=5)

    def open_selected_link(self):
        selection = self.link_tree.selection()
        if not selection:
            messagebox.showwarning("Aviso", "Selecione um link para abrir.")
            return
        
        item = selection[0]
        index = self.link_tree.index(item)
        
        filter_category = self.filter_var.get()
        filtered_links = []
        for link in self.links:
            if filter_category == "Todos" or filter_category in link.categories:
                filtered_links.append(link)
        
        filtered_links.sort(key=lambda x: x.created_date, reverse=True)
        
        if index < len(filtered_links):
            link = filtered_links[index]
            webbrowser.open(link.url)

    def show_context_menu(self, event):
        selection = self.link_tree.selection()
        if selection:
            self.context_menu.post(event.x_root, event.y_root)

    def edit_link(self):
        selection = self.link_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        index = self.link_tree.index(item)
        
        filter_category = self.filter_var.get()
        filtered_links = []
        for link in self.links:
            if filter_category == "Todos" or filter_category in link.categories:
                filtered_links.append(link)
        
        filtered_links.sort(key=lambda x: x.created_date, reverse=True)
        
        if index >= len(filtered_links):
            return
        
        link = filtered_links[index]

        edit_window = tk.Toplevel(self.root)
        edit_window.title("Editar Link")
        edit_window.geometry("700x700")
        edit_window.transient(self.root)
        edit_window.grab_set()

        top_button_frame = ttk.Frame(edit_window, padding="10")
        top_button_frame.pack(fill=tk.X)
        
        def save_changes():
            new_url = url_entry.get().strip()
            selected_cats = edit_category_multiselect.get_selected()
            
            if not selected_cats:
                selected_cats = ["Não Classificado"]
            
            if new_url != link.url and self.url_already_exists(new_url):
                messagebox.showwarning("Aviso", "Esta URL já está cadastrada no sistema.")
                return
            
            link.url = new_url
            link.categories = selected_cats
            link.analysis = analysis_text.get(1.0, tk.END).strip()
            link.contexto_historico = contexto_text.get(1.0, tk.END).strip()
            link.comparacao_atual = comparacao_text.get(1.0, tk.END).strip()
            link.principais_assuntos = principais_text.get(1.0, tk.END).strip()
            
            self.refresh_link_list()
            self.save_links()
            edit_window.destroy()
            self.status_var.set("Link atualizado")
        
        ttk.Button(top_button_frame, text="💾 Salvar Alterações", command=save_changes, style='Action.TButton').pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(top_button_frame, text="❌ Cancelar", command=edit_window.destroy).pack(side=tk.LEFT)

        main_edit_frame = ttk.Frame(edit_window, padding="20")
        main_edit_frame.pack(fill=tk.BOTH, expand=True)

        url_frame = ttk.LabelFrame(main_edit_frame, text="URL", padding="10")
        url_frame.pack(fill=tk.X, pady=(0, 10))
        url_entry = tk.Entry(url_frame, font=('Arial', 12), width=100)
        url_entry.insert(0, link.url)
        url_entry.pack(fill=tk.X)

        category_frame = ttk.LabelFrame(main_edit_frame, text="Categoria(s)", padding="10")
        category_frame.pack(fill=tk.X, pady=(0, 10))
        edit_category_multiselect = MultiSelectCombobox(category_frame, values=self.category_manager.get_categories())
        edit_category_multiselect.set_selected(link.categories)
        edit_category_multiselect.pack(fill=tk.X, pady=(0, 5))

        def add_new_cat_edit():
            popup = tk.Toplevel(edit_window)
            popup.title("Nova Categoria")
            popup.geometry("350x120")
            popup.transient(edit_window)
            popup.grab_set()
            
            tk.Label(popup, text="Nome da nova categoria:").pack(pady=10)
            entry = ttk.Entry(popup, width=30)
            entry.pack(pady=5)
            
            def add_cat():
                new_cat = entry.get().strip()
                if new_cat and new_cat not in self.category_manager.get_categories():
                    self.category_manager.add_category(new_cat)
                    edit_category_multiselect.set_values(self.category_manager.get_categories())
                    self.update_category_options()
                popup.destroy()
            
            ttk.Button(popup, text="Adicionar", command=add_cat).pack(pady=10)
            entry.focus_set()

        ttk.Button(category_frame, text="➕ Nova Categoria", command=add_new_cat_edit).pack(pady=(0, 5))

        analysis_frame = ttk.LabelFrame(main_edit_frame, text="Análise", padding="10")
        analysis_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        analysis_text = scrolledtext.ScrolledText(analysis_frame, font=('Arial', 11), wrap=tk.WORD)
        analysis_text.pack(fill=tk.BOTH, expand=True)
        analysis_text.insert(1.0, link.analysis)

        contexto_frame = ttk.LabelFrame(main_edit_frame, text="Contexto histórico", padding="10")
        contexto_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        contexto_text = scrolledtext.ScrolledText(contexto_frame, font=('Arial', 11), wrap=tk.WORD, height=5)
        contexto_text.pack(fill=tk.BOTH, expand=True)
        contexto_text.insert(1.0, link.contexto_historico or "")

        comparacao_frame = ttk.LabelFrame(main_edit_frame, text="Comparação com a situação atual", padding="10")
        comparacao_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        comparacao_text = scrolledtext.ScrolledText(comparacao_frame, font=('Arial', 11), wrap=tk.WORD, height=5)
        comparacao_text.pack(fill=tk.BOTH, expand=True)
        comparacao_text.insert(1.0, link.comparacao_atual or "")

        principais_frame = ttk.LabelFrame(main_edit_frame, text="Principais assuntos relacionados", padding="10")
        principais_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        principais_text = scrolledtext.ScrolledText(principais_frame, font=('Arial', 11), wrap=tk.WORD, height=5)
        principais_text.pack(fill=tk.BOTH, expand=True)
        principais_text.insert(1.0, link.principais_assuntos or "")

    def delete_link(self):
        selection = self.link_tree.selection()
        if not selection:
            return
        
        if not messagebox.askyesno("Confirmar", "Tem certeza que deseja excluir este link?"):
            return
        
        item = selection[0]
        index = self.link_tree.index(item)
        
        filter_category = self.filter_var.get()
        filtered_links = []
        for link in self.links:
            if filter_category == "Todos" or filter_category in link.categories:
                filtered_links.append(link)
        
        filtered_links.sort(key=lambda x: x.created_date, reverse=True)
        
        if index < len(filtered_links):
            link_to_remove = filtered_links[index]
            self.links.remove(link_to_remove)
            self.refresh_link_list()
            self.save_links()
            self.status_var.set("Link excluído")

    def generate_panorama(self):
        selected_categories = self.panorama_category_multiselect.get_selected()
        
        if not selected_categories:
            messagebox.showwarning("Aviso", "Selecione ao menos uma categoria para gerar o panorama.")
            return
        
        category_links = [link for link in self.links if any(cat in link.categories for cat in selected_categories)]
        
        if not category_links:
            messagebox.showwarning("Aviso", f"Nenhum link encontrado para as categorias selecionadas.")
            return
        
        self.status_var.set("Gerando panorama com IA...")
        self.root.update()
        
        def generate_thread():
            try:
                links_summary = []
                for link in category_links[:15]:
                    summary = f"""
Título: {link.metadata.get('title', 'N/A')}
URL: {link.url}
Categoria(s): {', '.join(link.categories)}
Descrição: {link.metadata.get('description', 'N/A')}
Análise: {link.analysis[:500]}...
"""
                    links_summary.append(summary)
                
                categories_str = ", ".join(selected_categories)
                panorama_prompt = f"""
Com base nos seguintes links e análises das categorias: {categories_str}, forneça um panorama geral abrangente:

{chr(10).join(links_summary)}

Crie um panorama que inclua:

1. Visão geral das categorias selecionadas
2. Análise dos links específicos
3. Tendências e insights das áreas
4. Conexões e padrões identificados
5. Recomendações para as categorias
6. Lacunas de informação e áreas para pesquisa futura
7. Contexto histórico relevante
8. Comparação com a situação atual
9. Principais conceitos e definições abordados
10. Possíveis impactos ou aplicações práticas
11. Autores, instituições ou organizações recorrentes
12. Providências gerais em relação ao assunto
13. Fontes principais com assuntos mais atuais e relevantes
14. Principal linha de raciocínio (para condensar tudo)

Seja detalhado, técnico e forneça insights valiosos baseado no conteúdo analisado.
"""
                panorama = call_openai_api(panorama_prompt, OPENAI_API_KEY)
                
                if "❌ ERRO" in panorama:
                    self.root.after(0, lambda: messagebox.showerror("Erro", panorama))
                    self.root.after(0, lambda: self.status_var.set("Erro ao gerar panorama"))
                    return
                
                def update_panorama():
                    self.panorama_text.delete(1.0, tk.END)
                    self.panorama_text.insert(1.0, f"Panorama Geral - {categories_str.upper()}\n")
                    self.panorama_text.insert(tk.END, f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n")
                    self.panorama_text.insert(tk.END, f"Baseado em {len(category_links)} links\n\n")
                    self.panorama_text.insert(tk.END, "="*80 + "\n\n")
                    self.panorama_text.insert(tk.END, panorama)
                    self.status_var.set(f"Panorama gerado para {categories_str}")
                
                self.root.after(0, update_panorama)
                
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Erro", f"Erro ao gerar panorama: {str(e)}"))
                self.root.after(0, lambda: self.status_var.set("Erro ao gerar panorama"))
        
        thread = threading.Thread(target=generate_thread)
        thread.daemon = True
        thread.start()

    def export_panorama_pdf(self):
        content = self.panorama_text.get(1.0, tk.END).strip()
        if not content:
            messagebox.showwarning("Aviso", "Gere um panorama primeiro antes de exportar.")
            return
        
        try:
            categories = self.panorama_category_multiselect.get_selected()
            categories_str = "_".join([c.lower().replace(' ', '_').replace('+', 'mais') for c in categories]) or "geral"
            filename = f"panorama_{categories_str}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            
            self.status_var.set("Exportando para PDF...")
            self.root.update()
            
            file_path = export_to_pdf(content, filename)
            
            messagebox.showinfo("Sucesso", f"Panorama exportado com sucesso!\n\nArquivo: {filename}\nLocal: {os.path.dirname(file_path)}")
            self.status_var.set("PDF exportado com sucesso")
            
            if messagebox.askyesno("Abrir arquivo", "Deseja abrir o arquivo PDF gerado?"):
                try:
                    if sys.platform == "win32":
                        os.startfile(file_path)
                    elif sys.platform == "darwin":
                        subprocess.call(["open", file_path])
                    else:
                        subprocess.call(["xdg-open", file_path])
                except Exception as e:
                    messagebox.showwarning("Aviso", f"Não foi possível abrir o arquivo automaticamente: {e}")
        
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao exportar PDF: {str(e)}")
            self.status_var.set("Erro ao exportar PDF")

    def save_links(self):
        try:
            data = [link.to_dict() for link in self.links]
            path = os.path.join(os.path.dirname(sys.argv[0]), 'links_database.json')
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao salvar links: {str(e)}")

    def load_links(self):
        try:
            path = os.path.join(os.path.dirname(sys.argv[0]), 'links_database.json')
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.links = [LinkAnalyzer.from_dict(link_data) for link_data in data]
            else:
                self.links = []
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao carregar links: {str(e)}")
            self.links = []

def main():
    root = tk.Tk()
    app = LinkAnalyzerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()