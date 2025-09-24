#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os

def load_config():
    """����URL�����ļ�"""
    config_file = '.github/scripts/urls_config.json'
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # �������õ�URL
        enabled_urls = [url for url in config['urls'] if url.get('enabled', True)]
        all_urls = config['urls']
        
        # ���û��������������ű�ʹ��
        with open(os.environ['GITHUB_OUTPUT'], 'a') as fh:
            fh.write(f'total_urls={len(all_urls)}\n')
            fh.write(f'enabled_urls={len(enabled_urls)}\n')
            fh.write(f'config_file={config_file}\n')
        
        print(f"Config file loaded successfully: {config_file}")
        print(f"Total URLs: {len(all_urls)}")
        print(f"Enabled URLs: {len(enabled_urls)}")
        
        return config
        
    except Exception as e:
        print(f"Failed to load config file: {e}")
        # ����Ĭ������
        default_config = {
            "urls": [
                {
                    "id": "default_url",
                    "name": "Default URL",
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