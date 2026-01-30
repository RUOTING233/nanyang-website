import pandas as pd
import os
from app import db, Material, app

excel_filename = '史料统计.xlsx'

# 映射中文 Sheet 名 -> 英文 ID
author_mapping = {
    '莹姿': 'yingzi',
    '冯伊湄': 'fengyimei',
    '王映霞': 'wangyingxia',
    '王莹': 'wangying',
    '沈兹九': 'shenzijiu'
}

def init():
    print("🚀 开始导入史料目录 (按表格物理顺序)...")
    with app.app_context():
        # 1. 强制重建表结构 (为了加入 publish_time 字段)
        print("   🔨 重建数据库表...")
        Material.__table__.drop(db.engine, checkfirst=True)
        db.create_all()
        
        # 2. 检查文件
        if not os.path.exists(excel_filename):
            print(f"❌ 找不到 {excel_filename}")
            return

        try:
            xls = pd.ExcelFile(excel_filename)
        except Exception as e:
            print(f"❌ 读取 Excel 失败: {e}")
            return

        total = 0

        for sheet_name in xls.sheet_names:
            author_id = None
            for cn, en in author_mapping.items():
                if cn in sheet_name:
                    author_id = en
                    break
            
            if not author_id: continue

            print(f"📂 处理 Sheet: {sheet_name} -> {author_id}")
            df = pd.read_excel(xls, sheet_name=sheet_name)

            # 使用 iterrows 遍历，idx 就是行号 (0, 1, 2...)
            for idx, row in df.iterrows():
                
                # A. 具体信息
                folder = str(row.get('具体信息', '')).strip()
                if not folder or folder == 'nan': continue

                # B. 来源 (双重检查)
                source = str(row.get('史料来源', '')).strip()
                if not source or source == 'nan':
                    source = str(row.get('来源', '')).strip()
                if not source or source == 'nan': 
                    source = '暂无'

                # C. 出版刊物
                publication = str(row.get('出版刊物', '暂无')).strip()
                if publication == 'nan': publication = '暂无'

                # D. 【新增】出版时间 (读取您新加的那一列)
                # 请确保 Excel 表头真的是 "出版时间"
                p_time = str(row.get('出版时间', '')).strip()
                if p_time == 'nan': p_time = ''

                # E. 【关键修改】序号
                # 直接使用 Excel 的行号 (idx) 作为排序依据
                # 这样网页显示的顺序就和您表格里看到的一模一样了
                sort_idx = idx

                # 存入数据库
                m = Material(
                    author=author_id, 
                    folder_name=folder, 
                    source=source,
                    publication=publication, 
                    publish_time=p_time,  # 存入时间
                    sort_index=sort_idx   # 存入行号
                )
                db.session.add(m)
                total += 1
        
        db.session.commit()
        print(f"🎉 导入完成！共 {total} 条。")

if __name__ == '__main__':
    init()