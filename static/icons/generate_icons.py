#!/usr/bin/env python3
"""アイコン生成スクリプト（pillow不要・SVGベース）"""
import os

# SVGアイコンを各サイズのPNGに変換（base64埋め込みで回避）
# シンプルな十字架+聖書デザイン
svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
  <rect width="512" height="512" fill="#1a3a6e" rx="80"/>
  <text x="256" y="320" font-family="serif" font-size="260" fill="#ffffff" text-anchor="middle">✝</text>
  <text x="256" y="430" font-family="sans-serif" font-size="72" fill="#7eb8f7" text-anchor="middle">聖書対照</text>
</svg>'''

with open(os.path.join(os.path.dirname(__file__), 'icon.svg'), 'w') as f:
    f.write(svg)
print("icon.svg created")
