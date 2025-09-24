#!/usr/bin/env python3
import requests
import hashlib
import os
import json
from datetime import datetime
import sys
import re

def load_config():
    """加载URL配置"""
    config_file = '.github/scripts/urls_config.json'
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"警告: 无法加载配置文件 {config_file}: {e}")
        # 返回空配置
        return {"urls": [], "settings": {}}

def get_urls_to_check(check_all=False):
    """获取需要检查的URL列表"""
    config = load_config()
    urls = config.get('urls', [])
    
    if check_all:
        return urls
    else:
        return [url for url in urls if url.get('enabled', True)]

def get_content_hash(url_config):
    """获取URL内容的哈希值"""
    url = url_config['url']
    timeout = url_config.get('timeout', 30)
    max_size = url_config.get('max_size_mb', 50) * 1024 * 1024  # 转换为字节
    
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        
        # 检查文件大小
        content_length = len(response.content)
        if content_length > max_size:
            raise ValueError(f"文件过大: {content_length}字节 > {max_size}字节限制")
            
        content = response.content
        return hashlib.md5(content).hexdigest(), content_length, True
    except Exception as e:
        return f"error: {str(e)}", 0, False

def load_previous_hashes():
    """加载之前存储的哈希值"""
    hash_file = '.github/scripts/url_hashes.json'
    if os.path.exists(hash_file):
        with open(hash_file, 'r') as f:
            return json.load(f)
    return {}

def save_current_hashes(hashes):
    """保存当前哈希值"""
    os.makedirs('.github/scripts', exist_ok=True)
    hash_file = '.github/scripts/url_hashes.json'
    with open(hash_file, 'w') as f:
        json.dump(hashes, f, indent=2)

def clean_output_text(text):
    """清理输出文本，移除可能引起问题的字符"""
    cleaned = re.sub(r'[^\w\s\u4e00-\u9fff\-\.:>]', '', text)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

def save_change_details(changed_urls):
    """保存变化详情供下载脚本使用"""
    change_file = '.github/scripts/changed_urls.json'
    os.makedirs(os.path.dirname(change_file), exist_ok=True)
    
    with open(change_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'changed_urls': changed_urls,
            'run_id': os.environ.get('GITHUB_RUN_ID', 'unknown')
        }, f, indent=2)

def main():
    # 获取检查模式
    check_all = os.environ.get('CHECK_ALL_URLS', 'false').lower() == 'true'
    
    # 获取需要检查的URL
    urls_to_check = get_urls_to_check(check_all)
    
    if not urls_to_check:
        print("错误：没有配置有效的URL")
        sys.exit(1)
    
    print(f"开始检查 {len(urls_to_check)} 个URL (检查所有: {check_all})")
    
    # 加载之前的哈希值
    previous_hashes = load_previous_hashes()
    current_hashes = {}
    changes = []
    detailed_status = []
    status_messages = []
    
    changed_urls = []
    has_changes = False
    
    for url_config in urls_to_check:
        url_id = url_config['id']
        url_name = url_config.get('name', url_id)
        url = url_config['url']
        
        print(f"检查 {url_id} ({url_name}): {url}")
        
        # 合并配置中的超时设置
        url_config['timeout'] = url_config.get('timeout', 30)
        
        current_hash, size, success = get_content_hash(url_config)
        
        current_hashes[url_id] = {
            'hash': current_hash,
            'size': size,
            'url': url,
            'name': url_name,
            'timestamp': datetime.now().isoformat(),
            'success': success
        }
        
        if not success:
            status_msg = f"获取失败: {current_hash}"
            display_msg = f"{url_name} 获取失败"
            detailed_msg = f"❌ {url_name} ({url_id}) - 获取失败: {current_hash}"
        elif url_id not in previous_hashes:
            status_msg = "首次检查"
            display_msg = f"{url_name} 首次检查"
            detailed_msg = f"✅ {url_name} ({url_id}) - 首次检查"
            changed_urls.append(url_id)
            has_changes = True
        elif previous_hashes[url_id].get('hash') != current_hash:
            old_size = previous_hashes[url_id].get('size', 0)
            status_msg = f"内容变化: {old_size} → {size} 字节"
            display_msg = f"{url_name} 内容已变化"
            detailed_msg = f"🔄 {url_name} ({url_id}) - 内容变化: {old_size} → {size} 字节"
            changed_urls.append(url_id)
            has_changes = True
        else:
            status_msg = "无变化"
            display_msg = f"{url_name} 无变化"
            detailed_msg = f"⚪ {url_name} ({url_id}) - 无变化"
        
        changes.append(clean_output_text(display_msg))
        detailed_status.append(clean_output_text(detailed_msg))
        status_messages.append(clean_output_text(f"{url_name}: {status_msg}"))
        
        print(f"  结果: {status_msg}")
    
    # 保存当前哈希值
    save_current_hashes(current_hashes)
    
    # 保存变化详情
    if has_changes:
        save_change_details(changed_urls)
    
    # 设置GitHub Actions输出
    with open(os.environ['GITHUB_OUTPUT'], 'a') as fh:
        fh.write(f'changed={str(has_changes).lower()}\n')
        fh.write(f'change_details={" | ".join(changes)}\n')
        fh.write(f'detailed_status={" | ".join(detailed_status)}\n')
        fh.write(f'changed_urls={",".join(changed_urls)}\n')
        fh.write(f'changed_count={len(changed_urls)}\n')
        fh.write(f'total_checked={len(urls_to_check)}\n')
    
    if has_changes:
        print(f"检测到内容变化，将下载文件: {changed_urls}")
    else:
        print("未检测到内容变化")

if __name__ == "__main__":
    main()