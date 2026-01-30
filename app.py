import os
import re
from flask import Flask, render_template, request, abort
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import distinct

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///works.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ============================================
# 1. 模型定义
# ============================================

# (1) 文章/作品表 (保持不变)
class Work(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    author = db.Column(db.String(50))
    year = db.Column(db.Integer)
    date_display = db.Column(db.String(50))
    publication = db.Column(db.String(100))
    genre = db.Column(db.String(50))
    source = db.Column(db.String(500))
    content = db.Column(db.Text)

# ... (前面的代码不变)

# (2) 【修改】史料表
class Material(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    author = db.Column(db.String(50))
    folder_name = db.Column(db.String(200))
    publication = db.Column(db.String(200))
    
    # 【新增】出版时间 (对应您表格里的新列)
    publish_time = db.Column(db.String(100)) 
    
    source = db.Column(db.String(200))
    sort_index = db.Column(db.Integer, default=0)

# ... (后面的代码不变)
# 2. 辅助工具：文件扫描与排序 (保持不变)
# ============================================

def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split('([0-9]+)', s)]

def get_files_in_folder(base_path, sub_path=''):
    full_path = os.path.join(base_path, sub_path)
    if not os.path.exists(full_path):
        return [], []

    dirs, jpgs, pdfs, txts, others = [], [], [], [], []

    try:
        items = os.listdir(full_path)
    except OSError:
        return [], []

    for item in items:
        item_path = os.path.join(full_path, item)
        if item.startswith('.'): continue

        if os.path.isdir(item_path):
            dirs.append(item)
        else:
            lower = item.lower()
            if lower.endswith(('.jpg', '.jpeg', '.png')): jpgs.append(item)
            elif lower.endswith('.pdf'): pdfs.append(item)
            elif lower.endswith('.txt'): txts.append(item)
            else: others.append(item)

    dirs.sort(key=natural_sort_key)
    jpgs.sort(key=natural_sort_key)
    pdfs.sort(key=natural_sort_key)
    txts.sort(key=natural_sort_key)

    return dirs, jpgs + pdfs + txts + others

@app.template_filter('highlight')
def highlight_filter(text, keyword):
    if not keyword or not text: return text
    pattern = re.compile(f'({re.escape(keyword)})', re.IGNORECASE)
    return pattern.sub(r'<span class="highlight">\1</span>', text)

# ============================================
# 3. 路由
# ============================================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/creation')
def creation():
    keyword = request.args.get('q', '').strip()
    author_filter = request.args.get('author', 'all')
    genre_filter = request.args.get('genre', 'all')
    year_filter = request.args.get('year', 'all')

    query = Work.query
    if author_filter != 'all': query = query.filter_by(author=author_filter)
    if genre_filter != 'all': query = query.filter_by(genre=genre_filter)
    if year_filter != 'all':
        if year_filter == 'unknown': query = query.filter((Work.year == 0) | (Work.year == None))
        else:
            try: query = query.filter_by(year=int(year_filter))
            except: pass

    if keyword:
        rule = (Work.title.contains(keyword) | Work.content.contains(keyword) | Work.genre.contains(keyword))
        query = query.filter(rule)
    
    works = query.order_by(Work.id).all()
    years_db = db.session.query(distinct(Work.year)).order_by(Work.year).all()
    available_years = [y[0] for y in years_db if y[0] and y[0] != 0]

    return render_template('creation.html', works=works, keyword=keyword, 
                           current_author=author_filter, current_genre=genre_filter,
                           current_year=year_filter, available_years=available_years)

@app.route('/article/<int:work_id>')
def article(work_id):
    work = Work.query.get_or_404(work_id)
    return render_template('article.html', work=work)

# --- 【修改】南洋史料路由 ---
@app.route('/materials')
def materials_list():
    # 获取筛选参数：涉及人物 & 出版刊物
    current_author = request.args.get('author', 'all')
    current_publication = request.args.get('publication', 'all') # 变量名改了
    
    query = Material.query

    # 1. 筛选作家
    if current_author != 'all':
        query = query.filter_by(author=current_author)
    
    # 2. 筛选出版刊物 (不再是 source)
    if current_publication != 'all':
        query = query.filter_by(publication=current_publication)
    
    # 3. 排序
    materials = query.order_by(Material.sort_index, Material.id).all()
    
    # 4. 获取所有“出版刊物”选项 (去重)
    pub_query = db.session.query(distinct(Material.publication)).order_by(Material.publication).all()
    # 过滤空值
    available_publications = [p[0] for p in pub_query if p[0] and p[0] != '暂无']
    
    return render_template('materials.html', 
                           materials=materials, 
                           current_author=current_author,
                           current_publication=current_publication, # 传给前端
                           available_publications=available_publications)

@app.route('/material/<int:id>')
@app.route('/material/<int:id>/<path:subpath>')
def material_detail(id, subpath=''):
    material = Material.query.get_or_404(id)
    base_folder = os.path.join(app.root_path, 'static', 'materials', material.author, material.folder_name)
    dirs, files = get_files_in_folder(base_folder, subpath)
    
    breadcrumbs = []
    if subpath:
        parts = subpath.split('/')
        accumulated = ''
        for part in parts:
            if accumulated: accumulated += '/'
            accumulated += part
            breadcrumbs.append({'name': part, 'path': accumulated})

    return render_template('material_detail.html', material=material, subpath=subpath,
                           dirs=dirs, files=files, breadcrumbs=breadcrumbs)

@app.route('/<page_name>')
def static_page(page_name):
    if page_name.endswith('.html'): page_name = page_name[:-5]
    try: return render_template(f'{page_name}.html')
    except: return f"页面 {page_name} 不存在", 404

if __name__ == '__main__':
    app.run(debug=True)