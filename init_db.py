import pandas as pd
from app import db, Work, app
import os

excel_filename = '作品统计.xlsx'

# 对应关系不变
author_mapping = {
    '莹姿': 'yingzi', '冯伊湄': 'fengyimei', 
    '王映霞': 'wangyingxia', '王莹': 'wangying', '沈兹九': 'shenzijiu'
}

def init():
    print("🚀 正在重新初始化数据库 (适应新表头)...")
    
    with app.app_context():
        db.drop_all()
        db.create_all()

        if not os.path.exists(excel_filename):
            print(f"❌ 找不到 {excel_filename}")
            return

        xls = pd.ExcelFile(excel_filename)
        count = 0
        
        # 按照 Excel 的 Sheet 顺序读取，保证 ID 顺序就是 Sheet 顺序
        for sheet_name in xls.sheet_names:
            author_id = None
            for cn, en in author_mapping.items():
                if cn in sheet_name:
                    author_id = en
                    break
            if not author_id: continue

            print(f"正在导入: {sheet_name} ...")
            df = pd.read_excel(xls, sheet_name=sheet_name)
            
            for _, row in df.iterrows():
                # --- 修改重点：这里的列名已经改成了纯中文 ---
                
                # 1. 处理年份 (防止空值或非数字)
                raw_year = row.get('年份', 0)
                try: year = int(float(raw_year))
                except: year = 0 # 0 代表未知

                # 2. 读取其他字段
                work = Work(
                    title=str(row.get('标题', '无标题')).strip(),
                    author=author_id,
                    year=year,
                    # 如果这列叫"时间"，就写'时间'
                    date_display=str(row.get('时间', '')).strip(), 
                    publication=str(row.get('发行', '未知')).strip(),
                    genre=str(row.get('文类', '未分类')).strip(),
                    source=str(row.get('来源', '')).strip(),
                    content="" 
                )
                db.session.add(work)
                count += 1
        
        db.session.commit()
        print(f"✅ 成功导入 {count} 条数据！")

if __name__ == '__main__':
    init()