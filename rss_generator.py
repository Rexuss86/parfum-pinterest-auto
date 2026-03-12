#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Генератор RSS ленты с сортировкой по 6 доскам Pinterest
"""

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime
from html import escape
import argparse
import os
import re

# Чтение названий досок из GitHub Secrets
BOARD_MONTALE = os.getenv('BOARD_MONTALE', 'Montale')
BOARD_NISHEVAYA = os.getenv('BOARD_NISHEVAYA', 'Нишевая парфюмерия')
BOARD_STOYKIE = os.getenv('BOARD_STOYKIE', 'Стойкие ароматы')
BOARD_VOSTOCHNIE = os.getenv('BOARD_VOSTOCHNIE', 'Восточные ароматы')
BOARD_XERJOFF = os.getenv('BOARD_XERJOFF', 'Xerjoff')
BOARD_ZIMNIE = os.getenv('BOARD_ZIMNIE', 'Зимние ароматы')

# Словари для категоризации
BRANDS_MONTALE = ['montale', 'манталь']
BRANDS_XERJOFF = ['xerjoff', 'ксержофф']
KEYWORDS_NISHEVAYA = ['нише', 'niche', 'limited', 'коллекц', 'эксклюзив']
KEYWORDS_VOSTOCHNIE = ['восточ', 'oriental', 'oud', 'уд', 'араб', 'arab']
KEYWORDS_STOYKIE = ['стойк', 'long lasting', 'интенсив', 'extreme', 'парфюм']
KEYWORDS_ZIMNIE = ['зим', 'winter', 'cold', 'холод', 'мороз', 'снег', 'праздн', 'new year']


def get_board_name(product_name: str, description: str = '') -> str:
    """Определение доски по названию и описанию товара."""
    text = f"{product_name} {description}".lower()
    
    # 1. Сначала проверяем бренды (приоритет)
    for brand in BRANDS_MONTALE:
        if brand in text:
            return BOARD_MONTALE
    
    for brand in BRANDS_XERJOFF:
        if brand in text:
            return BOARD_XERJOFF
    
    # 2. Затем проверяем типы ароматов
    for keyword in KEYWORDS_VOSTOCHNIE:
        if keyword in text:
            return BOARD_VOSTOCHNIE
    
    for keyword in KEYWORDS_STOYKIE:
        if keyword in text:
            return BOARD_STOYKIE
    
    for keyword in KEYWORDS_ZIMNIE:
        if keyword in text:
            return BOARD_ZIMNIE
    
    # 3. По умолчанию — нишевая парфюмерия
    return BOARD_NISHEVAYA


def get_board_category(board_name: str) -> str:
    """Возвращает категорию для RSS фильтрации."""
    if board_name == BOARD_MONTALE:
        return "montale"
    elif board_name == BOARD_XERJOFF:
        return "xerjoff"
    elif board_name == BOARD_VOSTOCHNIE:
        return "vostochnie"
    elif board_name == BOARD_STOYKIE:
        return "stoykie"
    elif board_name == BOARD_ZIMNIE:
        return "zimnie"
    return "nishevaya"


def generate_rss(products_file: Path, output_file: Path, 
                 channel_title: str = "Parfum Pinterest Feed",
                 channel_description: str = "Автоматическая лента парфюмерии для Pinterest",
                 telegram_channel: str = "https://t.me/+8S-uIl2Ovms2NDJi"):
    
    with open(products_file, 'r', encoding='utf-8') as f:
        products = json.load(f)
    
    rss = ET.Element('rss', {'version': '2.0', 'xmlns:media': 'http://search.yahoo.com/mrss/'})
    channel = ET.SubElement(rss, 'channel')
    
    ET.SubElement(channel, 'title').text = channel_title
    ET.SubElement(channel, 'description').text = channel_description
    ET.SubElement(channel, 'link').text = telegram_channel
    ET.SubElement(channel, 'language').text = 'ru-ru'
    ET.SubElement(channel, 'lastBuildDate').text = datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT')
    
    stats = {
        BOARD_MONTALE: 0,
        BOARD_NISHEVAYA: 0,
        BOARD_STOYKIE: 0,
        BOARD_VOSTOCHNIE: 0,
        BOARD_XERJOFF: 0,
        BOARD_ZIMNIE: 0
    }
    
    for product in products:
        if not product.get('image_url'):
            continue
        
        item = ET.SubElement(channel, 'item')
        
        # Заголовок с префиксом доски для IFTTT
        board_name = get_board_name(product.get('name', ''), product.get('description', ''))
        category = get_board_category(board_name)
        
        prefix_map = {
            BOARD_MONTALE: "[MO]",
            BOARD_XERJOFF: "[XJ]",
            BOARD_VOSTOCHNIE: "[VO]",
            BOARD_STOYKIE: "[ST]",
            BOARD_ZIMNIE: "[ZI]",
            BOARD_NISHEVAYA: "[NI]"
        }
        title_prefix = prefix_map.get(board_name, "[NI]")
        
        title = f"{title_prefix} {product.get('name', 'Без названия')}"
        ET.SubElement(item, 'title').text = title
        
        # Описание
        desc_parts = [product.get('description', '')]
        if product.get('price'):
            desc_parts.append(f"💰 Цена: {product['price']} ₽")
        if product.get('volume'):
            desc_parts.append(f"📦 Объем: {product['volume']}")
        if product.get('brand'):
            desc_parts.append(f"🏷️ Бренд: {product['brand']}")
        desc_parts.append(f"📌 Доска: {board_name}")
        
        description = " | ".join(desc_parts) + f"\n\n👉 Подписаться: {telegram_channel}"
        ET.SubElement(item, 'description').text = escape(description)
        
        # Ссылка
        link = product.get('product_url', telegram_channel)
        ET.SubElement(item, 'link').text = link
        
        # GUID
        guid = ET.SubElement(item, 'guid')
        guid.text = product.get('id', title)
        guid.set('isPermaLink', 'false')
        
        # Дата
        pub_date = product.get('parsed_at', datetime.now().isoformat())
        try:
            dt = datetime.fromisoformat(pub_date)
            ET.SubElement(item, 'pubDate').text = dt.strftime('%a, %d %b %Y %H:%M:%S GMT')
        except:
            ET.SubElement(item, 'pubDate').text = datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT')
        
        # Категория
        category_elem = ET.SubElement(item, 'category')
        category_elem.text = category
        
        # Название доски
        board_elem = ET.SubElement(item, 'pinterest:board')
        board_elem.text = board_name
        
        # Изображение
        if product.get('image_url'):
            media_content = ET.SubElement(item, 'media:content')
            media_content.set('url', product['image_url'])
            media_content.set('medium', 'image')
            media_content.set('type', 'image/jpeg')
            
            enclosure = ET.SubElement(item, 'enclosure')
            enclosure.set('url', product['image_url'])
            enclosure.set('type', 'image/jpeg')
        
        # Статистика
        if board_name in stats:
            stats[board_name] += 1
    
    tree = ET.ElementTree(rss)
    ET.indent(tree, space="  ")
    
    output_file.parent.mkdir(parents=True, exist_ok=True)
    tree.write(output_file, encoding='utf-8', xml_declaration=True)
    
    print(f"✅ RSS лента создана: {output_file}")
    print(f"📊 Распределение по доскам:")
    for board, count in stats.items():
        if count > 0:
            print(f"   {board}: {count}")
    print(f"📊 Всего товаров: {sum(stats.values())}")


def main():
    parser = argparse.ArgumentParser(description="Генератор RSS из JSON")
    parser.add_argument("--input", default="data/products.json", help="Входной JSON")
    parser.add_argument("--output", default="rss/feed.xml", help="Выходной RSS файл")
    parser.add_argument("--title", default="Parfum Pinterest Feed", help="Заголовок канала")
    parser.add_argument("--telegram", default="https://t.me/+8S-uIl2Ovms2NDJi", help="Ссылка на ТГ канал")
    
    args = parser.parse_args()
    
    generate_rss(
        Path(args.input),
        Path(args.output),
        channel_title=args.title,
        telegram_channel=args.telegram
    )


if __name__ == "__main__":
    main()
