#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import os
import json
import hashlib
from datetime import datetime
import re

def load_config():
    """Load URL configuration"""
    config_file = '.github/scripts/urls_config.json'
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {"urls": []}

def get_url_info(url_id):
    """Get URL info by ID"""
    config = load_config()
    for url_config in config['urls']:
        if url_config['id'] == url_id:
            return url_config
    return None

def download_file(url_config, filename):
    """Download file to specified path"""
    try:
        url = url_config['url']
        timeout = url_config.get('timeout', 30)
        
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        
        os.makedirs('downloads', exist_ok=True)
        filepath = os.path.join('downloads', filename)
        
        with open(filepath, 'wb') as f:
            f.write(response.content)
        
        file_size = os.path.getsize(filepath)
        file_hash = hashlib.md5(response.content).hexdigest()
        
        return {
            'success': True,
            'filepath': filepath,
            'filename': filename,
            'size': file_size,
            'hash': file_hash,
            'url': url,
            'url_name': url_config.get('name', url_config['id']),
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'filename': filename,
            'url': url_config['url'],
            'url_name': url_config.get('name', url_config['id'])
        }

def generate_filename(url_config):
    """Generate download filename"""
    url_id = url_config['id']
    url_name = url_config.get('name', url_id)
    original_url = url_config['url']
    
    base_filename = os.path.basename(original_url) or f"{url_id}.bin"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    name, ext = os.path.splitext(base_filename)
    if not ext:
        ext = '.bin'
    
    safe_name = re.sub(r'[^\w\-_.]', '_', name)
    filename = f"{safe_name}_{timestamp}{ext}"
    
    return filename

def clean_output_text(text):
    """Clean output text for GitHub Actions"""
    # 移除换行符和可能引起问题的字符
    cleaned = re.sub(r'[\n\r]', ' ', text)
    cleaned = re.sub(r'[^\w\s\-\.:()]', '', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

def main():
    # Get changed URLs
    changed_urls_str = os.environ.get('CHANGED_URLS', '')
    changed_urls = [url.strip() for url in changed_urls_str.split(',') if url.strip()]
    
    if not changed_urls:
        print("No changed URLs detected, skipping download")
        with open(os.environ['GITHUB_OUTPUT'], 'a') as fh:
            fh.write('downloaded_files_list=No files to download\n')
            fh.write('total_downloaded=0\n')
        return
    
    print(f"URLs to download: {changed_urls}")
    
    # Download files
    download_results = []
    downloaded_files = []
    
    for url_id in changed_urls:
        url_config = get_url_info(url_id)
        if not url_config:
            print(f"Warning: URL config not found: {url_id}")
            continue
            
        filename = generate_filename(url_config)
        url_name = url_config.get('name', url_id)
        
        print(f"Downloading {url_name} ({url_id}): {url_config['url']} -> {filename}")
        
        result = download_file(url_config, filename)
        download_results.append(result)
        
        if result['success']:
            downloaded_files.append(result)
            print(f"  Success: {filename} ({result['size']} bytes)")
        else:
            print(f"  Failed: {result['error']}")
    
    # Generate file list - 使用单行格式
    file_list = []
    for file_info in downloaded_files:
        size_kb = file_info['size'] / 1024
        if size_kb < 1024:
            size_str = f"{size_kb:.1f} KB"
        else:
            size_mb = size_kb / 1024
            size_str = f"{size_mb:.1f} MB"
        
        file_entry = f"{file_info['filename']} ({size_str}) - {file_info['url_name']}"
        file_list.append(clean_output_text(file_entry))
    
    # Set GitHub Actions outputs - 使用管道符分隔，避免换行
    with open(os.environ['GITHUB_OUTPUT'], 'a') as fh:
        if file_list:
            # 使用管道符分隔文件列表
            files_output = " | ".join(file_list)
            fh.write(f'downloaded_files_list={files_output}\n')
            
            # 同时生成一个简化的版本用于显示
            simple_list = []
            for file_info in downloaded_files:
                simple_list.append(file_info['filename'])
            fh.write(f'downloaded_filenames={", ".join(simple_list)}\n')
        else:
            fh.write('downloaded_files_list=No files downloaded\n')
            fh.write('downloaded_filenames=\n')
        
        fh.write(f'total_downloaded={len(downloaded_files)}\n')
    
    # Save download history
    os.makedirs('.github/scripts', exist_ok=True)
    with open('.github/scripts/download_history.json', 'a') as f:
        record = {
            'timestamp': datetime.now().isoformat(),
            'run_id': os.environ.get('GITHUB_RUN_ID', 'unknown'),
            'downloads': download_results
        }
        f.write(json.dumps(record, ensure_ascii=False) + '\n')
    
    print(f"Download completed: {len(downloaded_files)} files")

if __name__ == "__main__":
    main()