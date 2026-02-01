import pandas as pd
from app import db, Work, app
import os

excel_filename = '作品统计.xlsx'

author_mapping = {
    '莹姿': 'yingzi', '冯伊湄': 'fengyimei', 
    '王映霞': 'wangyingxia', '王莹': 'wangying', '沈兹九': 'shenzijiu'
}

def init():
    print("🚀 正在重新初始化数据库...")
    
    with app.app_context():
        Work.__table__.drop(db.engine, checkfirst=True)
        db.create_all()

        if not os.path.exists(excel_filename):
            print(f"❌ 找不到 {excel_filename}")
            return

        xls = pd.ExcelFile(excel_filename)
        count = 0
        
        # 用来统计每个分类各有多少条，方便对账
        genre_stats = {}

        for sheet_name in xls.sheet_names:
            author_id = None
            for cn, en in author_mapping.items():
                if cn in sheet_name:
                    author_id = en
                    break
            if not author_id:
                print(f"⚠️ 跳过不匹配的 Sheet: {sheet_name}")
                continue

            print(f"正在导入: {sheet_name} ...")
            df = pd.read_excel(xls, sheet_name=sheet_name)
            
            # --- 关键检查点 1：检查列名 ---
            # 如果你的 Excel 里“文类”多了一个空格或者叫“文章类型”，这里会列出来
            actual_columns = df.columns.tolist()
            if '文类' not in actual_columns:
                print(f"🚨 警告：在 {sheet_name} 中没找到名为'文类'的列！当前的列名有：{actual_columns}")

            for index, row in df.iterrows():
                # 处理年份
                raw_year = row.get('年份', 0)
                try: year = int(float(raw_year))
                except: year = 0

                # 处理文类 (增加强制去空格)
                raw_genre = str(row.get('文类', '未分类')).strip()
                
                # --- 关键检查点 2：实时监控“时事报道” ---
                if "时事" in raw_genre:
                    print(f"🔍 捕捉到时事类条目: 标题={row.get('标题')} | 识别为={raw_genre}")

                # 统计分类
                genre_stats[raw_genre] = genre_stats.get(raw_genre, 0) + 1

                work = Work(
                    title=str(row.get('标题', '无标题')).strip(),
                    author=author_id,
                    year=year,
                    date_display=str(row.get('时间', '')).strip(), 
                    publication=str(row.get('发行', '未知')).strip(),
                    genre=raw_genre,
                    source=str(row.get('来源', '')).strip(),
                    content="" 
                )
                db.session.add(work)
                count += 1
        
        db.session.commit()
        
        print("\n" + "="*30)
        print(f"✅ 成功导入 {count} 条数据！")
        print("📊 分类统计结果如下：")
        for g, c in genre_stats.items():
            print(f" - 【{g}】: {c} 条")
        print("="*30)

if __name__ == '__main__':
    init()