import pandas as pd
from app import db, Work, app
import os
import glob

# 配置
excel_filename = '作品统计.xlsx'

# 【关键修改在这里】把 'creations' 改成了 'works'，这样才能找到你的文件夹
creations_root = os.path.join(app.root_path, 'static', 'works')

author_mapping = {
    '莹姿': 'yingzi', '冯伊湄': 'fengyimei', 
    '王映霞': 'wangyingxia', '王莹': 'wangying', '沈兹九': 'shenzijiu'
}
def get_folder_content(author_en, title):
    work_dir = os.path.join(creations_root, author_en, title)
    content_text = ""
    image_rel_path = None

    if os.path.exists(work_dir):
        # 1. 找 txt
        # 1. 找 txt (兼容大写 .TXT)
        txt_files = glob.glob(os.path.join(work_dir, '*.txt'))
        txt_files.extend(glob.glob(os.path.join(work_dir, '*.TXT')))
        if txt_files:
            try:
                with open(txt_files[0], 'r', encoding='utf-8') as f:
                    raw_text = f.read()
                    # 【关键修改在此】
                    # 1. replace(' ', '') 删除普通空格
                    # 2. replace('\u3000', '') 删除中文全角空格
                    # 3. replace('\t', '') 删除制表符
                    # 注意：我们没有删 \n (换行符)，所以你的回车会被保留！
                    content_text = raw_text.replace(' ', '').replace('\u3000', '').replace('\t', '')
            except Exception as e:
                print(f"  ❌ 读取txt失败 ({title}): {e}")

        # 2. 找图片 (代码不变)
        # 2. 找图片 (增加大写后缀，防止 Linux 服务器找不到)
        img_patterns = [
            '*.jpg', '*.png', '*.jpeg', '*.webp',
            '*.JPG', '*.PNG', '*.JPEG', '*.WEBP'
        ]
        found_images = []
        for pattern in img_patterns:
            found_images.extend(glob.glob(os.path.join(work_dir, pattern)))
        
        if found_images:
            # 把所有找到的图片路径，转换成相对路径
            all_rel_paths = []
            for img in found_images:
                rel_path = os.path.relpath(img, app.root_path).replace('\\', '/')
                all_rel_paths.append(rel_path)
            
            # 用逗号把所有路径拼成一长串，存进数据库 (例如: "图1.jpg,图2.jpg")
            image_rel_path = ",".join(all_rel_paths)
            
    return content_text, image_rel_path

def init():
    print(f"🚀 正在扫描数据库... (目标文件夹: {creations_root})")
    
    if not os.path.exists(creations_root):
        print(f"❌ 错误：找不到根目录 {creations_root}")
        return

    with app.app_context():
        # 重置数据库
        Work.__table__.drop(db.engine, checkfirst=True)
        db.create_all()

        if not os.path.exists(excel_filename):
            print(f"❌ 找不到 {excel_filename}")
            return

        xls = pd.ExcelFile(excel_filename)
        success_count = 0
        fail_count = 0
        
        for sheet_name in xls.sheet_names:
            author_id = None
            for cn, en in author_mapping.items():
                if cn in sheet_name:
                    author_id = en
                    break
            
            if not author_id:
                continue

            print(f"\n📖 正在处理作者: {sheet_name} ({author_id})")
            df = pd.read_excel(xls, sheet_name=sheet_name)
            
            for index, row in df.iterrows():
                # 去除标题前后的空格，保证干净
                title = str(row.get('标题', '无标题')).strip()
                
                # 去文件夹找
                folder_text, folder_img = get_folder_content(author_id, title)
                
                # --- 核心修改：增加失败提示 ---
                if not folder_text and not folder_img:
                    # 如果文和图都没找到，打印出来！
                    expected_path = os.path.join(creations_root, author_id, title)
                    print(f"   ⚠️ 关联失败: 【{title}】")
                    # print(f"      -> 程序试图寻找: {expected_path}") 
                    fail_count += 1
                else:
                    # 成功了
                    status = []
                    if folder_text: status.append("文")
                    if folder_img: status.append("图")
                    print(f"   ✅ 成功: {title} ({','.join(status)})")
                    success_count += 1

                # 存入数据库
                final_content = folder_text if folder_text else ""
                try: year = int(float(row.get('年份', 0)))
                except: year = 0

                work = Work(
                    title=title,
                    author=author_id,
                    year=year,
                    date_display=str(row.get('时间', '')).strip(),
                    publication=str(row.get('发行', '未知')).strip(),
                    genre=str(row.get('文类', '未分类')).strip(),
                    source=str(row.get('来源', '')).strip(),
                    content=final_content,
                    image_path=folder_img
                )
                db.session.add(work)

        db.session.commit()
        print("\n" + "="*40)
        print(f"📊 统计报告：")
        print(f"✅ 成功关联: {success_count} 篇")
        print(f"⚠️ 关联失败: {fail_count} 篇 (请检查上面带⚠️的标题)")
        print("="*40)

if __name__ == '__main__':
    init()