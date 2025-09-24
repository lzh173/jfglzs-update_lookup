#!/usr/bin/env python3
# -*- coding: gbk -*-
import json
import os

def load_config():
    """加载URL配置文件"""
    config_file = '.github/scripts/urls_config.json'
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 过滤启用的URL
        enabled_urls = [url for url in config['urls'] if url.get('enabled', True)]
        all_urls = config['urls']
        
        # 设置环境变量供其他脚本使用
        with open(os.environ['GITHUB_OUTPUT'], 'a') as fh:
            fh.write(f'total_urls={len(all_urls)}\n')
            fh.write(f'enabled_urls={len(enabled_urls)}\n')
            fh.write(f'config_file={config_file}\n')
        
        print(f"配置文件加载成功: {config_file}")
        print(f"总URL数量: {len(all_urls)}")
        print(f"启用URL数量: {len(enabled_urls)}")
        
        return config
        
    except Exception as e:
        print(f"加载配置文件失败: {e}")
        # 返回默认配置
        default_config = {
            "urls": [
                {
                    "id": "default_url",
                    "name": "默认URL",
                    "url": "https://example.com/default.txt",
                    "enabled": True
                }
            ],
            "settings": {
                "check_interval_hours": 1,
                "max_file_size_mb": 50,
                "timeout_seconds": 30
            }
        }
        
        with open(os.environ['GITHUB_OUTPUT'], 'a') as fh:
            fh.write('total_urls=1\n')
            fh.write('enabled_urls=1\n')
            fh.write('config_file=default\n')
        
        return default_config

if __name__ == "__main__":
    load_config()