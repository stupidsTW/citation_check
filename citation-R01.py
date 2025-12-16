import re
import sys
import os

# python citation-R01.py text.txt

def extract_years_with_fixed_context(text, context_chars=30):
    """
    提取所有 19xx 或 20xx 年份，前後固定提取 context_chars 個字元
    """
    pattern = r'\b(19\d{2}|20\d{2})\b'
    matches = []
    
    for match in re.finditer(pattern, text):
        year = match.group(0)
        start = match.start()
        end = match.end()
        
        # 提取上下文
        context_start = max(0, start - context_chars)
        context_end = min(len(text), end + context_chars)
        
        before = text[context_start:start]
        after = text[end:context_end]
        snippet = text[context_start:context_end]
        
        matches.append({
            'year': year,
            'snippet': snippet,
            'before': before,
            'after': after,
            'position': start
        })
    
    return matches

def main(paper_file):
    if not os.path.exists(paper_file):
        print(f"錯誤：找不到檔案 '{paper_file}'")
        return
    
    try:
        with open(paper_file, 'r', encoding='utf-8') as f:
            text = f.read()
        
        results = extract_years_with_fixed_context(text, context_chars=30)
        
        # 輸出檔案名稱
        base_name = os.path.basename(paper_file)
        output_file = f"年份提取結果_{base_name}"
        
        with open(output_file, 'w', encoding='utf-8') as out_f:
            out_f.write("西元年份提取結果（前後各 30 字元）\n")
            out_f.write("=" * 80 + "\n")
            out_f.write(f"來源檔案：{paper_file}\n")
            out_f.write(f"共找到 {len(results)} 處年份出現\n")
            out_f.write(f"輸出時間：{__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            out_f.write("=" * 80 + "\n\n")
            
            # 去重：相同年份 + 相同完整片段 只顯示一次
            seen = set()
            displayed_count = 0
            
            for i, item in enumerate(results, 1):
                key = (item['year'], item['snippet'])
                if key in seen:
                    continue
                seen.add(key)
                displayed_count += 1
                
                line = f"{displayed_count:3d}. ...{item['before']}[{item['year']}] {item['after']}...\n"
                out_f.write(line)
            
            out_f.write("\n" + "=" * 80 + "\n")
            out_f.write("說明：\n")
            out_f.write("  - [] 內為偵測到的西元年份（1900–2099）\n")
            out_f.write("  - 年份前後各提取 30 個字元（若檔首或檔尾不足則顯示全部）\n")
            out_f.write("  - 若同一上下文完全相同，只顯示一次（避免重複）\n")
            out_f.write("  - 建議用此結果手動檢查哪些年份出現在括號內，即為 in-text citation\n")
        
        print("提取完成！")
        print(f"共找到 {len(results)} 處年份（去重後顯示 {displayed_count} 處）")
        print(f"結果已儲存至：{output_file}")
        print("   → 你可以用記事本或文字編輯器開啟查看。")
    
    except Exception as e:
        print(f"發生錯誤：{e}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("使用方式：python extract_years_30chars.py 論文正文.txt")
        print("範例：python extract_years_30chars.py paper.txt")
        sys.exit(1)
    
    paper_file = sys.argv[1]
    main(paper_file)