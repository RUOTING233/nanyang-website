import os

def replace_quotes_in_txt(root_dir):
    modified_count = 0

    # os.walk 会自动钻进每一个子文件夹里去寻找
    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            # 【精准锁定】只处理后缀名是 .txt 的文件
            if filename.lower().endswith('.txt'):
                filepath = os.path.join(dirpath, filename)
                
                try:
                    # 读取 TXT 文件内容（这里默认你的 txt 是 utf-8 编码）
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # 检查文件里有没有「或」，有的话才处理，节省电脑性能
                    if '「' in content or '」' in content:
                        # 进行无情替换
                        new_content = content.replace('「', '“').replace('」', '”')
                        
                        # 把替换后的新内容写回到原文件，覆盖掉
                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        
                        print(f"✅ 成功替换: {filepath}")
                        modified_count += 1
                        
                except UnicodeDecodeError:
                    # 如果遇到不是 utf-8 编码的 txt (比如老式的 GBK)，会提示你
                    print(f"⚠️ 编码跳过 (可能不是UTF-8): {filepath}")
                except Exception as e:
                    print(f"❌ 处理出错 {filepath}: {e}")
                    
    return modified_count

if __name__ == "__main__":
    # 你的目标大文件夹路径
    target_directory = r"D:\留声南洋\static\works"
    
    print(f"🔍 开始扫描并替换所有的 TXT 文件: {target_directory} ...\n")
    
    if not os.path.exists(target_directory):
        print("⚠️ 路径不存在，请检查你填写的文件夹路径是否正确！")
    else:
        # 开始干活
        count = replace_quotes_in_txt(target_directory)
        print(f"\n🎉 大功告成！一共在 {count} 个 TXT 文件中完成了引号替换。")