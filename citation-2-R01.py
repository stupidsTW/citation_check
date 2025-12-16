import re
import sys

# 使用方法 python citation-2-R01.py bib.txt text_extract.txt

def extract_bib_entries_full_line_context(bib_file):
    """
    從 bibliography 提取每筆：年份 + 年份前整行文字（到上一行換行）作為關鍵上下文
    支援半形 () 和全形（）
    """
    entries = []
    try:
        with open(bib_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"錯誤：找不到 bibliography 檔案 '{bib_file}'")
        sys.exit(1)
    
    # 按行分割，但保留空行作為分隔
    lines = content.splitlines()
    
    current_entry = ""
    for line in lines:
        stripped = line.strip()
        
        # 偵測是否為新條目開始（非空且包含年份括號）
        if stripped and re.search(r'[（(]\d{4}[）)]', stripped):
            # 如果已有正在處理的條目，先儲存
            if current_entry:
                process_entry(current_entry, entries)
            
            # 開始新條目
            current_entry = stripped
        elif current_entry and stripped:
            # 屬於同一條目（多行情況，如學位論文）
            current_entry += " " + stripped
        # 空行或無年份 → 暫不處理（避免誤抓標題如「專書」「期刊論文」）
    
    # 處理最後一筆
    if current_entry:
        process_entry(current_entry, entries)
    
    return entries

def process_entry(entry_line, entries):
    """處理單一文獻條目，提取年份與前方全文關鍵詞"""
    # 支援半形與全形括號
    year_match = re.search(r'[（(](\d{4})[）)]', entry_line)
    if not year_match:
        return
    year = year_match.group(1)
    
    # 找到左括號位置
    left_bracket = year_match.group(0)[0]
    bracket_pos = entry_line.find(left_bracket + year)
    if bracket_pos == -1:
        return
    
    # 關鍵上下文：年份括號前所有文字（整筆開頭到年份前）
    pre_full_text = entry_line[:bracket_pos].strip()
    
    # 清理結尾標點
    pre_full_text = re.sub(r'[.,;，。；、]\s*$', '', pre_full_text)
    
    # 提取關鍵詞（中文詞 + 英文詞）
    words = []
    words.extend(re.findall(r'[\u4e00-\u9fff]+', pre_full_text))  # 中文詞
    words.extend(re.findall(r'\b[a-zA-Z]+\b', pre_full_text))     # 英文詞
    
    # 去重、轉小寫、過濾短詞（<2）
    keywords = {w.lower() for w in words if len(w) >= 2}
    
    # fallback：若無詞，至少保留部分文字（如作者姓）
    if not keywords and pre_full_text:
        fallback = re.sub(r'[^\w\u4e00-\u9fff]', '', pre_full_text)[:10].lower()
        keywords = {fallback} if fallback else set()
    
    # 顯示用：前幾個關鍵詞 + 截斷前文
    display_pre = pre_full_text[:60] + "..." if len(pre_full_text) > 60 else pre_full_text
    
    entries.append({
        'original_line': entry_line,
        'year': year,
        'pre_full_text': pre_full_text,           # 完整前方文字
        'keywords': keywords,                    # 用於匹配
        'display_pre': display_pre,
        'top_keywords': list(keywords)[:8]        # 顯示用
    })

def find_matches_by_full_pretext(extracted_file, bib_entries):
    """
    在提取結果中：年份出現 + 前方全文關鍵詞任一出現 → match
    """
    try:
        with open(extracted_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"錯誤：找不到提取結果檔案 '{extracted_file}'")
        sys.exit(1)
    
    snippets = [line.strip() for line in lines if '[' in line and ']' in line]
    
    matches = []
    not_found = []
    
    for entry in bib_entries:
        year = entry['year']
        keywords = entry['keywords']
        
        matched_snippets = []
        matched_keywords_set = set()
        
        for snippet in snippets:
            if year not in snippet:
                continue
            
            snippet_words = set()
            snippet_words.update(re.findall(r'[\u4e00-\u9fff]+', snippet))
            snippet_words.update(re.findall(r'\b[a-zA-Z]+\b', snippet))
            snippet_words = {w.lower() for w in snippet_words if len(w) >= 2}
            
            common = keywords & snippet_words
            if common:
                matched_snippets.append(snippet)
                matched_keywords_set.update(common)
        
        if matched_snippets:
            matches.append({
                'bib': entry,
                'evidence': matched_snippets,
                'matched_keywords': list(matched_keywords_set)
            })
        else:
            not_found.append(entry)
    
    return matches, not_found

def main():
    if len(sys.argv) != 3:
        print("使用方式：")
        print("python bib_match_fullpre.py <bibliography檔案> <年份提取結果檔案>")
        print("")
        print("範例：")
        print("python bib_match_fullpre.py S1-bib.txt 年份提取結果_paper.txt")
        sys.exit(1)
    
    bib_file = sys.argv[1]
    extracted_file = sys.argv[2]
    
    print("開始進行 bibliography 與 in-text citation 匹配檢查（進階版）")
    print("匹配規則：年份出現 + 年份前整筆文字中的任一關鍵詞出現 → 視為已引用")
    print("已支援：半形括號 () 與 全形括號（）\n")
    print(f"參考文獻檔案：{bib_file}")
    print(f"年份提取檔案：{extracted_file}\n")
    
    bib_entries = extract_bib_entries_full_line_context(bib_file)
    print(f"成功提取 {len(bib_entries)} 筆文獻條目\n")
    
    matches, not_found = find_matches_by_full_pretext(extracted_file, bib_entries)
    
    print("=" * 80)
    print("匹配結果報告（基於年份前整筆文字關鍵詞）")
    print("=" * 80)
    
    print(f"✔ 已匹配（正文中有明確引用跡象）：{len(matches)} 筆")
    print(f"✖ 未找到匹配：{len(not_found)} 筆\n")
    
    if matches:
        print("【已匹配的文獻】")
        for i, item in enumerate(matches, 1):
            bib = item['bib']
            print(f"{i:3d}. [{bib['year']}] {bib['display_pre']}")
            print(f"     匹配關鍵詞：{', '.join(item['matched_keywords'][:10])}")
            print(f"     參考文獻：{bib['original_line'][:120]}...")
            print("     正文證據（前2筆）：")
            for ev in item['evidence'][:2]:
                print(f"        → {ev}")
            print()
    
    if not_found:
        print("【正文中未找到匹配的文獻（建議檢查是否真的被引用）】")
        for i, item in enumerate(not_found, 1):
            print(f"{i:3d}. [{item['year']}] {item['display_pre']}")
            if item['top_keywords']:
                print(f"     期望關鍵詞（前8）：{', '.join(item['top_keywords'])}")
            print(f"     完整條目：{item['original_line'][:120]}...")
            print()
    
    print("檢查完成！此版本對中文論文引用格式（如「王新衡（2024）」）極為寬容，匹配率應大幅提升。")

if __name__ == "__main__":
    main()