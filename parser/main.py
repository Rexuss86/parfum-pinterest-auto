#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Парсер DNK Parfum → JSON данные для RSS
"""

import time
import json
import re
import argparse
from pathlib import Path
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException
import hashlib

BASE_URL = "https://dnkparfum.ru"
OUTPUT_DIR = Path("data")


def get_driver():
    """Headless Chrome driver."""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    options.add_argument("--disable-blink-features=AutomationControlled")
    
    driver = webdriver.Chrome(options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver


def parse_product_card(card_element, base_url=BASE_URL):
    """Извлечение данных из карточки товара."""
    try:
        title_elem = card_element.find_element(By.CSS_SELECTOR, "a.product-title, .product-name, .title, a[href*='/product/']")
        name = title_elem.text.strip()
        product_url = title_elem.get_attribute("href")
        
        if not product_url:
            return None
        
        price = None
        try:
            price_elem = card_element.find_element(By.CSS_SELECTOR, ".price, .product-price")
            price_text = price_elem.text.strip()
            match = re.search(r'(\d+\s?\d*)\s*₽', price_text)
            if match:
                price = int(match.group(1).replace(' ', ''))
        except NoSuchElementException:
            pass
        
        image_url = None
        try:
            img = card_element.find_element(By.TAG_NAME, "img")
            image_url = img.get_attribute("data-src") or img.get_attribute("src") or img.get_attribute("data-lazy-src")
            
            if image_url:
                if image_url.startswith("//"):
                    image_url = "https:" + image_url
                elif not image_url.startswith("http"):
                    image_url = base_url + image_url
        except NoSuchElementException:
            pass
        
        if not image_url:
            return None
        
        brand = None
        volume = None
        gender = None
        
        vol_match = re.search(r'(\d+(?:\.\d+)?\s*ml)', name, re.I)
        if vol_match:
            volume = vol_match.group(1).strip()
        
        gender_match = re.search(r'\(([^)]*(женск|мужч|унисекс)[^)]*)\)', name, re.I)
        if gender_match:
            gender = gender_match.group(1).strip()
        
        parts = name.split()
        brand_parts = []
        for part in parts:
            if re.match(r'^[A-Z\s\-&]+$', part) and len(part) > 1:
                brand_parts.append(part)
            else:
                break
        brand = ' '.join(brand_parts) if brand_parts else None
        
        product_id = hashlib.md5(f"{name}{price}".encode()).hexdigest()[:12]
        
        return {
            "id": product_id,
            "name": name,
            "brand": brand,
            "price": price,
            "volume": volume,
            "gender": gender,
            "image_url": image_url,
            "product_url": product_url,
            "description": f"{name} - {price}₽" if price else name,
            "parsed_at": datetime.now().isoformat(),
            "pinterest_ready": False
        }
        
    except Exception as e:
        print(f"⚠️ Ошибка парсинга: {e}")
        return None


def parse_catalog_page(driver, url):
    """Парсинг страницы каталога."""
    driver.get(url)
    time.sleep(3)
    
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)
    
    products = []
    
    selectors = [
        "div.product-item",
        "div.catalog-item",
        "article.product",
        ".products-grid > div, .catalog-grid > div"
    ]
    
    elements = []
    for selector in selectors:
        elements = driver.find_elements(By.CSS_SELECTOR, selector)
        if elements:
            break
    
    print(f"📦 Найдено элементов: {len(elements)}")
    
    for elem in elements:
        product = parse_product_card(elem)
        if product:
            products.append(product)
    
    return products


def save_json(data, filepath):
    """Сохранение в JSON."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"💾 Сохранено: {filepath} ({len(data)} записей)")


def main():
    parser = argparse.ArgumentParser(description="Парсер DNK Parfum")
    parser.add_argument("--url", default=f"{BASE_URL}/catalog", help="URL каталога")
    parser.add_argument("--pages", type=int, default=1, help="Количество страниц")
    parser.add_argument("--output", default="data/products.json", help="Выходной файл")
    
    args = parser.parse_args()
    
    driver = get_driver()
    all_products = []
    
    try:
        for page in range(1, args.pages + 1):
            url = args.url
            if page > 1:
                url = f"{args.url}?page={page}"
            
            print(f"\n📄 Страница {page}/{args.pages}")
            products = parse_catalog_page(driver, url)
            all_products.extend(products)
            print(f"✅ Добавлено: {len(products)} товаров")
            
            if page < args.pages:
                time.sleep(2)
                
    finally:
        driver.quit()
    
    output_file = Path(args.output)
    save_json(all_products, output_file)
    
    with_images = len([p for p in all_products if p.get('image_url')])
    print(f"\n🎉 Готово!")
    print(f"📊 Всего товаров: {len(all_products)}")
    print(f"🖼️  С изображениями: {with_images}")


if __name__ == "__main__":
    main()
