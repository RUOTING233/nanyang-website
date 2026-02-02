import os
import re
from flask import Flask, render_template, request, abort
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import distinct

app = Flask(__name__)
CORS(app)  #
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
    # 【新增】这里加一行，用来存图片路径
    image_path = db.Column(db.String(300))

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

    dirs = []
    all_files = [] # 统一存放所有文件，避免分堆导致排序断层

    try:
        items = os.listdir(full_path)
    except OSError:
        return [], []

    for item in items:
        item_path = os.path.join(full_path, item)
        # 1. 排除隐藏文件
        if item.startswith('.'): 
            continue

        # 2. 文件夹和文件分开存放
        if os.path.isdir(item_path):
            dirs.append(item)
        else:
            # 只要是文件，不管后缀是什么（.jpg, .pdf, .txt），全部丢进一个列表
            # 这样 1.jpg 和 10.jpg 才能在一个列表里根据数字比大小
            all_files.append(item)

    # 3. 对文件夹进行自然排序
    dirs.sort(key=natural_sort_key)
    
    # 4. 对所有文件进行统一的自然排序
    # 这一步保证了 1.jpg, 2.pdf, 3.jpg 这种混合排列也是正确的
    all_files.sort(key=natural_sort_key)

    # 5. 直接返回，不要再加来加去了
    return dirs, all_files

# ============================================
# 3. 模板过滤器 (Template Filters)
# ============================================

@app.template_filter('highlight')
def highlight_filter(text, keyword):
    """
    功能：给文本中的关键词加上红色高亮标签
    """
    if not keyword or not text:
        return text
    # re.IGNORECASE 让搜索不区分大小写
    pattern = re.compile(f'({re.escape(keyword)})', re.IGNORECASE)
    return pattern.sub(r'<span class="highlight">\1</span>', text)

@app.template_filter('extract_sentence')
def extract_sentence_filter(content, keyword):
    """
    功能：在正文中找到关键词所在的句子，并截取出来。
    """
    if not keyword or not content:
        return None
    
    # 1. 为了查找方便，统一转小写找位置 (但截取时用原文本)
    idx = content.lower().find(keyword.lower())
    
    if idx == -1:
        return None # 正文里没这个词，返回 None
    
    # 2. 向前找句号（确定句子开头）
    # 往回找最近的 。 ！ ？ 换行符 或者 字符串开头
    start = idx
    while start > 0:
        char = content[start]
        if char in ['。', '！', '？', '\n', '!', '?']:
            start += 1 # 找到标点后，往后挪一位才是文字开始
            break
        start -= 1
        
    # 3. 向后找句号（确定句子结尾）
    end = idx
    total_len = len(content)
    while end < total_len:
        char = content[end]
        if char in ['。', '！', '？', '\n', '!', '?']:
            end += 1 # 把标点符号也带上
            break
        end += 1
    
    # 4. 截取这句话
    sentence = content[start:end].strip()
    
    # 5. 防御性截断：万一这句话特别长（比如几百字没标点），强行截取关键词前后
    if len(sentence) > 150:
        snippet_start = max(0, idx - 50)
        snippet_end = min(total_len, idx + 50)
        sentence = "..." + content[snippet_start:snippet_end] + "..."

    return sentence


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

    # ... 前面的代码不变 ...

    # 初始化词频统计列表
    chart_data = []

    # ... (前面的代码不变)

    # 初始化两个空列表，准备传给图表
    chart_x = [] # 存标题
    chart_y = [] # 存数量

    if keyword:
        # 1. 数据库筛选
        rule = (Work.title.contains(keyword) | Work.content.contains(keyword))
        query = query.filter(rule)
        
        works = query.order_by(Work.id).all()

        # 2. 【新增】统计词频逻辑
        stats = []
        for work in works:
            # 统计标题和正文里关键词出现的总次数
            c_title = work.title.count(keyword) if work.title else 0
            c_content = work.content.count(keyword) if work.content else 0
            total = c_title + c_content
            
            if total > 0:
                stats.append({'title': work.title, 'count': total})
        
        # 3. 【新增】排序：按数量从大到小
        stats.sort(key=lambda x: x['count'], reverse=True)
        
        # 4. 只取前 20 名 (防止柱子太多太挤)
        stats = stats[:20]
        
        # 5. 拆分数据给 Plotly 用
        chart_x = [item['title'] for item in stats]
        chart_y = [item['count'] for item in stats]

    else:
        works = query.order_by(Work.id).all()

    years_db = db.session.query(distinct(Work.year)).order_by(Work.year).all()
    available_years = [y[0] for y in years_db if y[0] and y[0] != 0]

    # 【修改】return 这里一定要把 chart_x 和 chart_y 传出去
    return render_template('creation.html', works=works, keyword=keyword, 
                           current_author=author_filter, current_genre=genre_filter,
                           current_year=year_filter, available_years=available_years,
                           chart_x=chart_x, chart_y=chart_y) # <--- 重点看这里

@app.route('/article/<int:work_id>')
def article(work_id):
    work = Work.query.get_or_404(work_id)
    
    # 【新增】获取 URL 里的关键词 (比如 ?q=黄河)
    keyword = request.args.get('q', '') 
    
    # 【修改】把 keyword 传给 article.html
    return render_template('article.html', work=work, keyword=keyword)

# --- 【修改】南洋史料路由 ---
@app.route('/materials')
def materials():
    # 1. 【修复关键】显式定义筛选变量
    author_filter = request.args.get('author', 'all')
    pub_filter = request.args.get('publication', 'all')

    # 2. 建立基础查询 (请确保 Material 是你存放史料的模型名)
    query = Material.query 

    # 3. 应用筛选逻辑
    if author_filter != 'all':
        query = query.filter(Material.author == author_filter)
    
    if pub_filter != 'all':
        query = query.filter(Material.publication == pub_filter)

    # 4. 获取筛选后的所有数据
    materials = query.all()

    # 5. 获取数据库中所有刊物列表 (用于下拉菜单)
    # distinct 需要从 sqlalchemy 导入: from sqlalchemy import distinct
    pubs_db = db.session.query(distinct(Material.publication)).all()
    available_publications = [p[0] for p in pubs_db if p[0]]

    # ==========================================
    # 旭日图数据处理逻辑 (Sunburst)
    # ==========================================
    
    author_map = {
        'yingzi': '莹姿', 'fengyimei': '冯伊湄',
        'wangyingxia': '王映霞', 'wangying': '王莹', 'shenzijiu': '沈兹九'
    }

    stats = {}
    
    for m in materials:
        # 获取中文人名
        author_name = author_map.get(m.author, m.author) if m.author else "未知作者"
        # 获取刊物名
        pub_name = m.publication if m.publication else "其他刊物"
        
        if author_name not in stats:
            stats[author_name] = {}
        
        if pub_name not in stats[author_name]:
            stats[author_name][pub_name] = 0
            
        stats[author_name][pub_name] += 1

    # 构建 Plotly 数据
    sb_ids = []
    sb_labels = []
    sb_parents = []
    sb_values = []

    # (1) 圆心
    root_id = "总览"
    sb_ids.append(root_id)
    sb_labels.append("史料总览")
    sb_parents.append("")
    sb_values.append(len(materials))

    # (2) 填充数据
    for author, pubs in stats.items():
        # 作家层
        author_total = sum(pubs.values())
        sb_ids.append(author) 
        sb_labels.append(author)
        sb_parents.append(root_id)
        sb_values.append(author_total)

        # 刊物层
        for pub, count in pubs.items():
            child_id = f"{author}-{pub}"
            sb_ids.append(child_id)
            sb_labels.append(pub)
            sb_parents.append(author)
            sb_values.append(count)
    
    # ==========================================

    # 6. 返回模板 (变量名现在已经对齐了)
    return render_template('materials.html', 
                           materials=materials, 
                           current_author=author_filter,        # 对应上面定义的变量
                           current_publication=pub_filter,      # 对应上面定义的变量
                           available_publications=available_publications,
                           sb_ids=sb_ids, sb_labels=sb_labels, 
                           sb_parents=sb_parents, sb_values=sb_values)
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