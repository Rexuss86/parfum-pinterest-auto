#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Парсер DNK Parfum — обновлённая версия с универсальными селекторами
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
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import hashlib

BASE_URL = "https://dnkparfum.ru"
OUTPUT_DIR = Path("data")


def get_driver():
    """Headless Chrome driver с улучшенной маскировкой."""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver


def parse_product_card(card_element, base_url=BASE_URL):
    """Извлечение данных из карточки товара."""
    try:
        # Название и ссылка (универсальный поиск)
        title_elem = None
        for selector in [
            "a.product-title", ".product-name a", ".title a", 
            "a[href*='/product/']", "a[href*='/catalog/']"
        ]:
            try:
                title_elem = card_element.find_element(By.CSS_SELECTOR, selector)
                if title_elem:
                    break
            except:
                continue
        
        if not title_elem:
            # Фоллбэк: ищем любой текст, похожий на название
            name = card_element.text.strip().split('\n')[0][:100]
            product_url = None
        else:
            name = title_elem.text.strip() or title_elem.get_attribute("title") or "Без названия"
            product_url = title_elem.get_attribute("href")
        
        if not name or len(name) < 3:
            return None
        
        # Цена
        price = None
        for selector in [".price", ".product-price", ".cost", "[class*='price']"]:
            try:
                price_elem = card_element.find_element(By.CSS_SELECTOR, selector)
                price_text = price_elem.text.strip()
                match = re.search(r'(\d+\s?\d*)\s*₽', price_text)
                if match:
                    price = int(match.group(1).replace(' ', ''))
                    break
            except:
                continue
        
        # Изображение
        image_url = None
        try:
            img = card_element.find_element(By.TAG_NAME, "img")
            for attr in ["data-src", "src", "data-lazy-src", "data-original"]:
                image_url = img.get_attribute(attr)
                if image_url:
                    break
            if image_url:
                if image_url.startswith("//"):
                    image_url = "https:" + image_url
                elif not image_url.startswith("http"):
                    image_url = base_url + image_url
        except:
            pass
        
        if not image_url:
            return None  # Пропускаем без изображения
        
        # Парсинг метаданных
        brand = None
        volume = None
        gender = None
        
        vol_match = re.search(r'(\d+(?:\.\d+)?\s*ml)', name, re.I)
        if vol_match:
            volume = vol_match.group(1).strip()
        
        gender_match = re.search(r'\(([^)]*(женск|мужч|унисекс)[^)]*)\)', name, re.I)
        if gender_match:
            gender = gender_match.group(1).strip()
        
        # Бренд: первые слова на латинице
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
        print(f"⚠️ Ошибка парсинга карточки: {e}")
        return None


def parse_catalog_page(driver, url):
    """Парсинг страницы каталога с ожиданием загрузки."""
    driver.get(url)
    
    # Ждём появления хотя бы одного элемента, похожего на товар
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/product/'], .product-item, .catalog-item"))
        )
    except TimeoutException:
        print("⚠️ Таймаут загрузки страницы")
        return []
    
    time.sleep(2)
    
    # Прокрутка для подгрузки изображений
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)
    
    products = []
    
    # Универсальные селекторы для карточек
    selectors = [
        "div.product-item", "div.catalog-item", "article.product",
        ".products-grid > div", ".catalog-grid > div",
        "div[data-product-id]", "div[class*='product']",
        "a[href*='/product/']"  # Фоллбэк: прямые ссылки
    ]
    
    elements = []
    for selector in selectors:
        elements = driver.find_elements(By.CSS_SELECTOR, selector)
        if len(elements) > 0:
            print(f"✅ Найдено по селектору '{selector}': {len(elements)}")
            break
    
    if not elements:
        print("⚠️ Не найдено элементов ни по одному селектору")
        # Фоллбэк: ищем все ссылки на товары
        elements = driver.find_elements(By.CSS_SELECTOR, "a[href*='/product/']")
        print(f"🔍 Фоллбэк: найдено ссылок на товары: {len(elements)}")
    
    for elem in elements:
        # Если элемент — это ссылка, ищем её контейнер
        if elem.tag_name == "a":
            container = elem.find_element(By.XPATH, "./ancestor::div[contains(@class, 'product') or contains(@class, 'item') or contains(@class, 'card')]") if elem else None
            if container:
                product = parse_product_card(container)
            else:
                product = parse_product_card(elem)
        else:
            product = parse_product_card(elem)
        
        if product and product.get("name") and len(product.get("name", "")) > 3:
            products.append(product)
    
    # Удаляем дубликаты по URL
    seen_urls = set()
    unique_products = []
    for p in products:
        if p.get("product_url") and p["product_url"] not in seen_urls:
            seen_urls.add(p["product_url"])
            unique_products.append(p)
    
    return unique_products


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
            
            print(f"\n📄 Страница {page}/{args.pages}: {url}")
            products = parse_catalog_page(driver, url)
            print(f"✅ Добавлено товаров: {len(products)}")
            all_products.extend(products)
            
            if page < args.pages:
                time.sleep(3)
                
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
